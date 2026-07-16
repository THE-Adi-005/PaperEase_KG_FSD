"""ReACT Agent — the core reasoning engine.

Implements the Agent + CoT pattern from the reference paper (Section 4.2.1):
Thought → Action → Observation → repeat, grounded in the KG.

Four tools (Cypher-backed):
1. RetrieveNode[keyword] — full-text search
2. NodeFeature[node, feature] — get node properties
3. NeighborCheck[node, edge_type] — list neighbors
4. NodeDegree[node, edge_type] — count neighbors
5. Finish[answer] — return final answer

Streams each step as an SSE event for live UI updates.
"""

import re
import json
import logging
from typing import AsyncGenerator, Optional

from app.config import settings
from app.models.schemas import ReasoningStep, SubGraph, QueryMode
from app.services.neo4j_client import neo4j_service
from app.services.llm_client import llm_client

logger = logging.getLogger(__name__)

# ── System prompt adapted from Appendix F ────────────────────────────

AGENT_SYSTEM_PROMPT = """You are a research paper analysis agent. Solve questions by interleaving Thought, Action, and Observation steps.

AVAILABLE ACTIONS:
(1) RetrieveNode[keyword] — Find nodes in the knowledge graph matching the keyword. Use this to discover entities, methods, datasets, concepts mentioned in the papers.
(2) NodeFeature[node_name, feature] — Get a specific attribute of a node. Use "all" to get all attributes.
(3) NeighborCheck[node_name, edge_type] — List neighbors connected by the given edge type. Leave edge_type empty for all neighbors. Edge types: USES_METHOD, REPORTS_METRIC, DISCUSSES_CONCEPT, EVALUATED_ON, ACHIEVES, COMPARES_TO, EXTENDS, CITES, ILLUSTRATED_BY, SAME_AS
(4) NodeDegree[node_name, edge_type] — Count how many neighbors a node has for a given edge type.
(5) Finish[answer] — Return your final answer. Include specific facts from your observations.

RULES:
- Always start with a Thought explaining your reasoning
- Then choose exactly ONE Action
- Wait for the Observation before your next Thought
- When you have enough information, use Finish[your answer here]
- Provide node names (not IDs) in your answers
- Cite specific facts from the graph (e.g., "Method X achieves F1=0.85")
- If a search returns no results, try rephrasing or different keywords

FORMAT:
Thought: <your reasoning about what information you need>
Action: <ActionName>[<argument1>, <argument2>]

You may take up to {max_steps} steps."""

MULTI_PAPER_PROMPT_ADDITION = """
MULTI-PAPER MODE:
You are comparing information across multiple papers. When answering:
- Clearly attribute each claim to its source paper
- Use phrases like "According to Paper A, ..." and "Paper B reports..."
- Highlight similarities and differences
- Follow SAME_AS edges to find equivalent concepts across papers
"""


async def run_agent(question: str, paper_ids: list[str],
                     mode: QueryMode = QueryMode.SINGLE,
                     max_steps: int | None = None) -> AsyncGenerator[dict, None]:
    """Run the ReACT agent loop, yielding SSE events.
    
    Yields dicts with 'event' and 'data' keys:
    - {event: "thought", data: {step, text}}
    - {event: "action", data: {step, name, input}}
    - {event: "observation", data: {step, text, node_ids}}
    - {event: "lazy_completion", data: {step, new_triples}}
    - {event: "answer", data: {text, steps_used}}
    - {event: "subgraph", data: {nodes, edges}}
    - {event: "error", data: {message}}
    """
    if max_steps is None:
        max_steps = settings.AGENT_MAX_STEPS

    # Build system prompt
    system_prompt = AGENT_SYSTEM_PROMPT.format(max_steps=max_steps)
    if mode == QueryMode.COMPARE:
        system_prompt += MULTI_PAPER_PROMPT_ADDITION

    scratchpad = ""
    all_touched_nodes = []
    reasoning_steps = []
    lazy_completion_count = 0

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Question: {question}"},
    ]

    for step in range(1, max_steps + 1):
        # Add scratchpad to context
        if scratchpad:
            current_messages = messages + [
                {"role": "assistant", "content": scratchpad}
            ]
        else:
            current_messages = messages.copy()

        # Generate next thought + action
        try:
            response = await llm_client.generate(
                current_messages, temperature=0.1, max_tokens=512
            )
        except Exception as e:
            yield {"event": "error", "data": {"message": f"LLM error: {str(e)}"}}
            return

        # Parse thought and action
        thought, action_name, action_input = _parse_response(response)

        # Yield thought
        if thought:
            yield {"event": "thought", "data": {"step": step, "text": thought}}

        # Check for Finish
        if action_name and action_name.lower() == "finish":
            yield {"event": "answer", "data": {
                "text": action_input,
                "steps_used": step,
                "lazy_completion_count": lazy_completion_count,
            }}

            # Get subgraph of touched nodes
            if all_touched_nodes:
                subgraph = await neo4j_service.get_subgraph_for_nodes(all_touched_nodes)
                yield {"event": "subgraph", "data": {
                    "nodes": [n.model_dump() for n in subgraph.nodes],
                    "edges": [e.model_dump() for e in subgraph.edges],
                }}
            return

        # Execute action
        if action_name:
            yield {"event": "action", "data": {
                "step": step, "name": action_name, "input": action_input
            }}

            observation, node_ids = await _execute_action(
                action_name, action_input, paper_ids
            )

            all_touched_nodes.extend(node_ids)

            yield {"event": "observation", "data": {
                "step": step, "text": observation, "node_ids": node_ids
            }}

            # ── Lazy completion check ──
            if _should_trigger_lazy_completion(observation, action_name):
                from app.services.lazy_completion import trigger_lazy_completion
                new_triples = await trigger_lazy_completion(
                    question=question,
                    thought=thought,
                    action_name=action_name,
                    action_input=action_input,
                    paper_ids=paper_ids,
                )
                if new_triples > 0:
                    lazy_completion_count += 1
                    yield {"event": "lazy_completion", "data": {
                        "step": step, "new_triples": new_triples,
                        "reason": f"No results for {action_name}[{action_input}]"
                    }}
                    # Retry the action after lazy completion
                    observation, node_ids = await _execute_action(
                        action_name, action_input, paper_ids
                    )
                    all_touched_nodes.extend(node_ids)
                    yield {"event": "observation", "data": {
                        "step": step, "text": f"[After lazy completion] {observation}",
                        "node_ids": node_ids,
                    }}

            # Update scratchpad
            scratchpad += f"\nThought {step}: {thought}\n"
            scratchpad += f"Action {step}: {action_name}[{action_input}]\n"
            scratchpad += f"Observation {step}: {observation}\n"

        else:
            # No action parsed — try to extract answer from thought
            scratchpad += f"\nThought {step}: {thought}\n"

    # Max steps reached — force an answer
    yield {"event": "answer", "data": {
        "text": f"Based on my analysis: {thought}" if thought else "I was unable to find enough information to answer this question confidently.",
        "steps_used": max_steps,
        "lazy_completion_count": lazy_completion_count,
    }}

    if all_touched_nodes:
        subgraph = await neo4j_service.get_subgraph_for_nodes(all_touched_nodes)
        yield {"event": "subgraph", "data": {
            "nodes": [n.model_dump() for n in subgraph.nodes],
            "edges": [e.model_dump() for e in subgraph.edges],
        }}


async def _execute_action(action_name: str, action_input: str,
                           paper_ids: list[str]) -> tuple[str, list[str]]:
    """Execute an agent action against Neo4j. Returns (observation_text, node_ids)."""
    node_ids = []
    try:
        name = action_name.lower().strip()

        if name == "retrievenode":
            keyword = action_input.strip()
            results = await neo4j_service.retrieve_node(keyword, paper_ids or None)
            if results:
                node_ids = [r["name"] for r in results if r.get("name")]
                obs = "Found nodes:\n" + "\n".join(
                    f"  - {r['name']} (type: {r['type']}, score: {r['score']:.2f})"
                    for r in results[:5]
                )
            else:
                obs = f"No nodes found matching '{keyword}'."
            return obs, node_ids

        elif name == "nodefeature":
            parts = _split_args(action_input)
            node_name = parts[0] if parts else action_input
            feature = parts[1] if len(parts) > 1 else "all"
            result = await neo4j_service.node_feature(node_name, feature)
            return result, [node_name]

        elif name == "neighborcheck":
            parts = _split_args(action_input)
            node_name = parts[0] if parts else action_input
            edge_type = parts[1] if len(parts) > 1 else None
            neighbors = await neo4j_service.neighbor_check(node_name, edge_type)
            if neighbors:
                node_ids = [node_name] + [n["name"] for n in neighbors if n.get("name")]
                obs = f"Neighbors of '{node_name}'" + (f" ({edge_type})" if edge_type else "") + ":\n"
                obs += "\n".join(
                    f"  - {n['name']} (type: {n['type']}, relation: {n['relation']})"
                    for n in neighbors[:10]
                )
            else:
                obs = f"No neighbors found for '{node_name}'" + (f" with edge type '{edge_type}'" if edge_type else "") + "."
                node_ids = [node_name]
            return obs, node_ids

        elif name == "nodedegree":
            parts = _split_args(action_input)
            node_name = parts[0] if parts else action_input
            edge_type = parts[1] if len(parts) > 1 else None
            degree = await neo4j_service.node_degree(node_name, edge_type)
            return f"Node '{node_name}' has {degree} neighbors" + (f" of type '{edge_type}'" if edge_type else "") + ".", [node_name]

        else:
            return f"Unknown action: {action_name}. Available: RetrieveNode, NodeFeature, NeighborCheck, NodeDegree, Finish", []

    except Exception as e:
        logger.error(f"Action execution error: {e}")
        return f"Error executing {action_name}: {str(e)}", []


def _parse_response(text: str) -> tuple[str, str, str]:
    """Parse LLM response into (thought, action_name, action_input)."""
    thought = ""
    action_name = ""
    action_input = ""

    # Extract thought
    thought_match = re.search(r'Thought\s*\d*\s*:\s*(.*?)(?=Action|$)', text, re.DOTALL | re.IGNORECASE)
    if thought_match:
        thought = thought_match.group(1).strip()
    elif not re.search(r'Action', text, re.IGNORECASE):
        thought = text.strip()

    # Extract action
    action_match = re.search(
        r'Action\s*\d*\s*:\s*(\w+)\[(.*?)\]',
        text, re.DOTALL | re.IGNORECASE
    )
    if action_match:
        action_name = action_match.group(1).strip()
        action_input = action_match.group(2).strip()

    return thought, action_name, action_input


def _split_args(text: str) -> list[str]:
    """Split action arguments like 'node_name, feature' into parts."""
    parts = [p.strip().strip('"').strip("'") for p in text.split(",")]
    return [p for p in parts if p]


def _should_trigger_lazy_completion(observation: str, action_name: str) -> bool:
    """Decide if lazy graph completion should be triggered."""
    if action_name.lower() not in ("retrievenode", "neighborcheck"):
        return False
    indicators = [
        "no nodes found",
        "no neighbors found",
        "not found",
        "no results",
    ]
    obs_lower = observation.lower()
    return any(ind in obs_lower for ind in indicators)
