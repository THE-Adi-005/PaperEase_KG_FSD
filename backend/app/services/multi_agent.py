"""Multi-Agent Multi-Hop Reasoning Pipeline.

Replaces the monolithic single-agent ReACT loop with a 4-stage specialist pipeline:

    Question → [Planner] → [Retriever] → [Reasoner] → [Verifier] → Answer
                                 ↑              |
                                 └──────────────┘
                                  (revision loop if confidence < threshold)

Each agent has a focused role:
- Planner: Decomposes question into sub-questions with retrieval strategy
- Retriever: Executes KG traversals to gather evidence for each sub-question
- Reasoner: Synthesizes evidence into answer with explicit reasoning chain
- Verifier: Fact-checks the answer against the graph, identifies unsupported claims

Research backing:
- Wang et al., 2024 — "Mixture-of-Agents" (arXiv:2406.04692)
- Li et al., 2024 — "More Agents Is All You Need" (arXiv:2402.05120)
- Yao et al., 2023 — "Tree of Thoughts" (arXiv:2305.10601)

Streams SSE events at each stage for full traceability.
"""

import re
import json
import time
import logging
import uuid
from typing import AsyncGenerator

from app.config import settings
from app.models.schemas import QueryMode
from app.models.reasoning_trace import (
    SubQuestion, Evidence, EvidenceBundle, GroundedStep,
    ReasonedAnswer, ClaimVerification, VerificationReport,
    VerificationResult, MultiAgentTrace, PipelineStageResult, AgentStage,
    RetrievalStrategy, EvidenceType,
)
from app.services.neo4j_client import neo4j_service
from app.services.llm_client import llm_client

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# PLANNER AGENT
# ═══════════════════════════════════════════════════════════════════════

PLANNER_PROMPT = """You are a research question decomposition expert. Break down the user's question into 2-4 focused sub-questions that can each be answered by searching a knowledge graph of research papers.

The knowledge graph contains nodes: Paper, Author, Method, Dataset, Metric, Concept, Table, Figure, Citation
And relationships: USES_METHOD, EVALUATED_ON, ACHIEVES, REPORTS_METRIC, COMPARES_TO, EXTENDS, DISCUSSES_CONCEPT, CITES, SAME_AS

For each sub-question, specify:
1. The sub-question text
2. retrieval_strategy: one of "entity_search", "neighbor_traversal", "section_inspect", "metric_lookup", "cross_paper_link"
3. expected_evidence_type: one of "metric", "method_comparison", "conceptual", "factual", "structural"

Return a JSON array of sub-questions. Example:
[
  {{"id": "sq1", "text": "What methods does the paper propose?", "retrieval_strategy": "entity_search", "expected_evidence_type": "factual"}},
  {{"id": "sq2", "text": "What scores did the method achieve?", "retrieval_strategy": "metric_lookup", "expected_evidence_type": "metric"}}
]

User question: {question}

Papers being analyzed: {paper_context}

Return ONLY the JSON array:"""


async def _run_planner(question: str, paper_titles: list[str]) -> list[SubQuestion]:
    """Decompose question into sub-questions with retrieval strategies."""
    paper_context = ", ".join(paper_titles) if paper_titles else "uploaded papers"

    messages = [
        {"role": "user", "content": PLANNER_PROMPT.format(
            question=question, paper_context=paper_context
        )}
    ]

    try:
        response = await llm_client.generate(messages, temperature=0.2, max_tokens=1024)
        raw_sqs = llm_client._parse_json_array(response)

        sub_questions = []
        for i, sq in enumerate(raw_sqs):
            if not isinstance(sq, dict):
                continue
            sub_questions.append(SubQuestion(
                id=sq.get("id", f"sq{i+1}"),
                text=sq.get("text", ""),
                retrieval_strategy=_safe_enum(
                    sq.get("retrieval_strategy", "entity_search"),
                    RetrievalStrategy, RetrievalStrategy.ENTITY_SEARCH
                ),
                expected_evidence_type=_safe_enum(
                    sq.get("expected_evidence_type", "factual"),
                    EvidenceType, EvidenceType.FACTUAL
                ),
                priority=i + 1,
            ))

        # Fallback: if planner returns nothing, use the original question
        if not sub_questions:
            sub_questions = [SubQuestion(
                id="sq1", text=question,
                retrieval_strategy=RetrievalStrategy.ENTITY_SEARCH,
                expected_evidence_type=EvidenceType.FACTUAL,
            )]

        return sub_questions

    except Exception as e:
        logger.warning(f"Planner failed: {e}, using original question")
        return [SubQuestion(
            id="sq1", text=question,
            retrieval_strategy=RetrievalStrategy.ENTITY_SEARCH,
            expected_evidence_type=EvidenceType.FACTUAL,
        )]


# ═══════════════════════════════════════════════════════════════════════
# RETRIEVER AGENT
# ═══════════════════════════════════════════════════════════════════════

RETRIEVER_KEYWORD_PROMPT = """Extract 2-5 search keywords from this research question for querying a knowledge graph. Focus on specific entity names (methods, datasets, metrics, concepts).

Question: {question}

Return ONLY a JSON array of keyword strings, e.g.: ["BERT", "SQuAD", "F1 score"]"""


async def _run_retriever(
    sub_questions: list[SubQuestion],
    paper_ids: list[str]
) -> list[EvidenceBundle]:
    """Execute KG traversals to gather evidence for each sub-question."""
    bundles = []

    for sq in sub_questions:
        evidence_list = []
        retrieval_steps = 0

        # Step 1: Extract keywords from sub-question
        keywords = await _extract_search_keywords(sq.text)

        # Step 2: Execute retrieval strategy
        if sq.retrieval_strategy == RetrievalStrategy.ENTITY_SEARCH:
            for kw in keywords[:3]:
                retrieval_steps += 1
                results = await neo4j_service.retrieve_node(kw, paper_ids or None)
                for r in results[:5]:
                    evidence_list.append(Evidence(
                        source_node=r.get("name", ""),
                        source_node_type=r.get("type", "Unknown"),
                        text=f"Found entity: {r.get('name', '')} (type: {r.get('type', '')})",
                        source_paper_id=r.get("properties", {}).get("source_paper_id", ""),
                        confidence=min(r.get("score", 0.5) / 2.0, 1.0),
                    ))

        if sq.retrieval_strategy in (
            RetrievalStrategy.NEIGHBOR_TRAVERSAL,
            RetrievalStrategy.METRIC_LOOKUP,
            RetrievalStrategy.ENTITY_SEARCH,  # Also do neighbor traversal for entity search
        ):
            # Get neighbors for found entities
            found_entities = [e.source_node for e in evidence_list]
            if not found_entities:
                # Try direct keyword search
                found_entities = keywords[:2]

            for entity in found_entities[:3]:
                retrieval_steps += 1
                edge_type = None
                if sq.retrieval_strategy == RetrievalStrategy.METRIC_LOOKUP:
                    edge_type = "ACHIEVES"

                neighbors = await neo4j_service.neighbor_check(entity, edge_type)
                for n in neighbors[:8]:
                    evidence_list.append(Evidence(
                        source_node=entity,
                        source_node_type="",
                        source_edge=n.get("relation", ""),
                        target_node=n.get("name", ""),
                        target_node_type=n.get("type", "Unknown"),
                        text=f"{entity} --[{n.get('relation', '')}]--> {n.get('name', '')}",
                        source_paper_id="",
                        source_paper_title=n.get("source_paper", ""),
                        confidence=0.9,
                        graph_path=[entity, n.get("relation", ""), n.get("name", "")],
                    ))

        if sq.retrieval_strategy == RetrievalStrategy.SECTION_INSPECT:
            for kw in keywords[:2]:
                retrieval_steps += 1
                for pid in paper_ids:
                    info = await neo4j_service.get_paper_info(pid)
                    paper_kw = info.title[:30] if info else pid
                    snippet = await neo4j_service.inspect_section(paper_kw, kw)
                    if "No section found" not in snippet:
                        evidence_list.append(Evidence(
                            source_node=f"Section about '{kw}'",
                            source_node_type="Section",
                            text=snippet[:500],
                            source_paper_id=pid,
                            confidence=0.8,
                        ))

        if sq.retrieval_strategy == RetrievalStrategy.CROSS_PAPER_LINK:
            for kw in keywords[:3]:
                retrieval_steps += 1
                results = await neo4j_service.retrieve_node(kw, None)
                for r in results[:5]:
                    neighbors = await neo4j_service.neighbor_check(r.get("name", ""), "SAME_AS")
                    for n in neighbors:
                        evidence_list.append(Evidence(
                            source_node=r.get("name", ""),
                            source_edge="SAME_AS",
                            target_node=n.get("name", ""),
                            text=f"Cross-paper link: {r.get('name', '')} ↔ {n.get('name', '')}",
                            source_paper_title=n.get("source_paper", ""),
                            confidence=0.85,
                            graph_path=[r.get("name", ""), "SAME_AS", n.get("name", "")],
                        ))

        # Trigger lazy completion if no evidence found
        if not evidence_list:
            from app.services.lazy_completion import trigger_lazy_completion
            new_triples = await trigger_lazy_completion(
                question=sq.text,
                thought=f"Sub-question: {sq.text}",
                action_name="RetrieveNode",
                action_input=keywords[0] if keywords else sq.text,
                paper_ids=paper_ids,
            )
            if new_triples > 0:
                # Retry search after lazy completion
                for kw in keywords[:2]:
                    results = await neo4j_service.retrieve_node(kw, paper_ids or None)
                    for r in results[:5]:
                        evidence_list.append(Evidence(
                            source_node=r.get("name", ""),
                            source_node_type=r.get("type", "Unknown"),
                            text=f"[After lazy completion] Found: {r.get('name', '')}",
                            confidence=0.7,
                        ))

        bundles.append(EvidenceBundle(
            sub_question_id=sq.id,
            sub_question_text=sq.text,
            evidence=evidence_list,
            retrieval_steps=retrieval_steps,
            is_satisfied=len(evidence_list) > 0,
        ))

    return bundles


async def _extract_search_keywords(question: str) -> list[str]:
    """Extract search keywords from a question using the LLM."""
    try:
        messages = [{"role": "user", "content": RETRIEVER_KEYWORD_PROMPT.format(question=question)}]
        response = await llm_client.generate(messages, temperature=0.1, max_tokens=200)
        keywords = llm_client._parse_json_array(response)
        # Handle case where LLM returns list of strings
        result = []
        for kw in keywords:
            if isinstance(kw, str):
                result.append(kw)
            elif isinstance(kw, dict):
                result.append(str(kw.get("keyword", kw.get("text", ""))))
        return result if result else _fallback_keywords(question)
    except Exception:
        return _fallback_keywords(question)


def _fallback_keywords(text: str) -> list[str]:
    """Simple keyword extraction fallback."""
    stopwords = {"the", "a", "an", "is", "are", "what", "how", "does", "do", "which",
                 "this", "that", "in", "on", "for", "with", "of", "to", "and", "or",
                 "paper", "study", "research", "work", "propose", "proposed"}
    words = text.split()
    keywords = [w.strip('?,.:;!"\'"()[]') for w in words
                if w.strip('?,.:;!"\'"()[]').lower() not in stopwords and len(w) > 2]
    return list(dict.fromkeys(keywords))[:5]


# ═══════════════════════════════════════════════════════════════════════
# REASONER AGENT
# ═══════════════════════════════════════════════════════════════════════

REASONER_PROMPT = """You are a research analysis reasoner. Synthesize the evidence below into a clear, well-structured answer to the user's question.

CRITICAL RULES:
1. Base every claim ONLY on the provided evidence. Do NOT add information not in the evidence.
2. For each key claim, cite the specific graph evidence (e.g., "BERT --[ACHIEVES]--> F1=92.4").
3. If evidence is insufficient for a sub-question, say so explicitly.
4. Copy metric values EXACTLY — do not round or modify numbers.
5. Attribute facts to the correct source paper.

USER QUESTION: {question}

EVIDENCE BY SUB-QUESTION:
{evidence_text}

Provide your answer in this format:
REASONING STEPS:
Step 1: [claim] | Evidence: [graph path or evidence text]
Step 2: [claim] | Evidence: [graph path or evidence text]
...

FINAL ANSWER:
[Your synthesized answer here]"""


async def _run_reasoner(
    question: str,
    evidence_bundles: list[EvidenceBundle],
) -> ReasonedAnswer:
    """Synthesize evidence into answer with explicit reasoning chain."""

    # Format evidence for the prompt
    evidence_text = ""
    for bundle in evidence_bundles:
        evidence_text += f"\n--- Sub-question: {bundle.sub_question_text} ---\n"
        if bundle.evidence:
            for e in bundle.evidence:
                evidence_text += f"  • {e.text}\n"
                if e.graph_path:
                    evidence_text += f"    Graph path: {' → '.join(e.graph_path)}\n"
                if e.source_paper_title:
                    evidence_text += f"    Source: {e.source_paper_title}\n"
        else:
            evidence_text += "  (No evidence found for this sub-question)\n"

    messages = [{"role": "user", "content": REASONER_PROMPT.format(
        question=question, evidence_text=evidence_text
    )}]

    try:
        response = await llm_client.generate(messages, temperature=0.1, max_tokens=1500)
    except Exception as e:
        return ReasonedAnswer(
            text=f"Error during reasoning: {str(e)}",
            reasoning_steps=[],
        )

    # Parse reasoning steps and final answer
    steps = _parse_reasoning_steps(response, evidence_bundles)
    final_answer = _extract_final_answer(response)

    return ReasonedAnswer(
        text=final_answer,
        reasoning_steps=steps,
        sub_questions_answered=[b.sub_question_id for b in evidence_bundles if b.is_satisfied],
    )


def _parse_reasoning_steps(
    response: str,
    evidence_bundles: list[EvidenceBundle],
) -> list[GroundedStep]:
    """Parse the reasoner's response into structured GroundedStep objects."""
    steps = []
    step_pattern = re.compile(
        r'Step\s*(\d+)\s*:\s*(.*?)(?:\|\s*Evidence\s*:\s*(.*?))?(?=Step\s*\d+|FINAL ANSWER|$)',
        re.DOTALL | re.IGNORECASE
    )

    # Collect all evidence for cross-referencing
    all_evidence = []
    for bundle in evidence_bundles:
        all_evidence.extend(bundle.evidence)

    for match in step_pattern.finditer(response):
        step_num = int(match.group(1))
        claim = match.group(2).strip()
        evidence_ref = match.group(3).strip() if match.group(3) else ""

        # Try to link claim to actual evidence
        supporting = []
        graph_path = []
        for e in all_evidence:
            # Simple matching: check if evidence entities appear in the claim
            if e.source_node and e.source_node.lower() in claim.lower():
                supporting.append(e)
                if e.graph_path:
                    graph_path = e.graph_path

        steps.append(GroundedStep(
            step_number=step_num,
            claim=claim,
            supporting_evidence=supporting[:3],  # Limit to top 3
            graph_path=graph_path,
            is_verified=False,  # Will be set by verifier
        ))

    # If no steps were parsed, create one from the full response
    if not steps:
        steps.append(GroundedStep(
            step_number=1,
            claim=response[:300],
            supporting_evidence=[],
            graph_path=[],
        ))

    return steps


def _extract_final_answer(response: str) -> str:
    """Extract the FINAL ANSWER section from the reasoner's response."""
    match = re.search(r'FINAL ANSWER\s*:\s*(.*)', response, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # Fallback: return everything after last reasoning step
    lines = response.strip().split('\n')
    # Find last "Step N:" line
    last_step_idx = 0
    for i, line in enumerate(lines):
        if re.match(r'Step\s*\d+', line, re.IGNORECASE):
            last_step_idx = i

    if last_step_idx < len(lines) - 1:
        return '\n'.join(lines[last_step_idx + 1:]).strip()

    return response.strip()


# ═══════════════════════════════════════════════════════════════════════
# VERIFIER AGENT
# ═══════════════════════════════════════════════════════════════════════

VERIFIER_PROMPT = """You are a fact-checking verifier for research paper QA. Your job is to verify each claim in the answer against the provided graph evidence.

For each claim, determine:
- "verified": The claim is directly supported by the evidence
- "unsupported": No evidence supports this claim
- "contradicted": Evidence contradicts this claim
- "partial": Partially supported

ANSWER TO VERIFY:
{answer}

AVAILABLE EVIDENCE:
{evidence_text}

Return a JSON object:
{{
  "claims": [
    {{"claim": "...", "result": "verified|unsupported|contradicted|partial", "note": "..."}}
  ],
  "overall_confidence": 0.0-1.0,
  "revision_needed": true/false,
  "revision_reason": "..."
}}

Return ONLY the JSON:"""


async def _run_verifier(
    answer: ReasonedAnswer,
    evidence_bundles: list[EvidenceBundle],
    paper_ids: list[str],
) -> VerificationReport:
    """Fact-check the answer against graph evidence."""

    # Format evidence
    evidence_text = ""
    for bundle in evidence_bundles:
        for e in bundle.evidence:
            evidence_text += f"  • {e.text}"
            if e.source_paper_title:
                evidence_text += f" (from: {e.source_paper_title})"
            evidence_text += "\n"

    messages = [{"role": "user", "content": VERIFIER_PROMPT.format(
        answer=answer.text, evidence_text=evidence_text
    )}]

    try:
        response = await llm_client.generate(messages, temperature=0.1, max_tokens=1024)

        # Parse verification result
        result = _parse_verification_json(response)

        claims = []
        verified_count = 0
        unsupported_count = 0
        contradicted_count = 0

        for claim_data in result.get("claims", []):
            if not isinstance(claim_data, dict):
                continue
            result_str = claim_data.get("result", "unsupported")
            verification_result = _safe_enum(result_str, VerificationResult, VerificationResult.UNSUPPORTED)

            claims.append(ClaimVerification(
                claim=claim_data.get("claim", ""),
                result=verification_result,
                note=claim_data.get("note", ""),
            ))

            if verification_result == VerificationResult.VERIFIED:
                verified_count += 1
            elif verification_result == VerificationResult.UNSUPPORTED:
                unsupported_count += 1
            elif verification_result == VerificationResult.CONTRADICTED:
                contradicted_count += 1

        confidence = result.get("overall_confidence", 0.5)
        if isinstance(confidence, str):
            try:
                confidence = float(confidence)
            except ValueError:
                confidence = 0.5

        return VerificationReport(
            verified_claims=claims,
            confidence_score=max(0.0, min(1.0, confidence)),
            provenance_check_passed=contradicted_count == 0,
            revision_suggested=result.get("revision_needed", False),
            revision_reason=result.get("revision_reason", ""),
            total_claims=len(claims),
            verified_count=verified_count,
            unsupported_count=unsupported_count,
            contradicted_count=contradicted_count,
        )

    except Exception as e:
        logger.warning(f"Verifier failed: {e}")
        return VerificationReport(
            confidence_score=0.5,
            revision_suggested=False,
        )


def _parse_verification_json(text: str) -> dict:
    """Parse the verifier's JSON response."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find JSON object in text
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return {"claims": [], "overall_confidence": 0.5, "revision_needed": False}


# ═══════════════════════════════════════════════════════════════════════
# ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════

async def run_multi_agent(
    question: str,
    paper_ids: list[str],
    mode: QueryMode = QueryMode.SINGLE,
    max_revision_loops: int | None = None,
) -> AsyncGenerator[dict, None]:
    """Run the multi-agent pipeline, yielding SSE events at each stage.

    Yields dicts with 'event' and 'data' keys:
    - {event: "planning", data: {sub_questions: [...]}}
    - {event: "retrieving", data: {sub_question, evidence_count}}
    - {event: "reasoning", data: {steps: [...], answer}}
    - {event: "verifying", data: {confidence, verified, flagged}}
    - {event: "revision", data: {reason, loop}}
    - {event: "answer", data: {text, steps_used, ...}}
    - {event: "trace", data: {full MultiAgentTrace}}
    - {event: "subgraph", data: {nodes, edges}}
    - {event: "error", data: {message}}
    """
    if max_revision_loops is None:
        max_revision_loops = settings.MAX_REVISION_LOOPS

    trace = MultiAgentTrace(question=question, paper_ids=paper_ids)
    pipeline_start = time.time()

    # Look up paper titles for context
    paper_titles = []
    try:
        for pid in paper_ids:
            info = await neo4j_service.get_paper_info(pid)
            if info and info.title:
                paper_titles.append(info.title)
    except Exception as e:
        logger.warning(f"Could not fetch paper titles: {e}")

    # ── Stage 1: PLANNER ──────────────────────────────────────────────
    stage_start = time.time()
    yield {"event": "thought", "data": {
        "step": 1,
        "text": f"🧠 Planner Agent: Decomposing question into sub-questions..."
    }}

    sub_questions = await _run_planner(question, paper_titles)
    trace.sub_questions = sub_questions
    planner_ms = int((time.time() - stage_start) * 1000)

    yield {"event": "planning", "data": {
        "step": 1,
        "sub_questions": [sq.model_dump() for sq in sub_questions],
        "duration_ms": planner_ms,
    }}

    trace.stage_results.append(PipelineStageResult(
        stage=AgentStage.PLANNER, duration_ms=planner_ms,
        input_summary=question,
        output_summary=f"{len(sub_questions)} sub-questions generated",
        llm_calls=1, kg_queries=0,
    ))

    # ── Stage 2: RETRIEVER ────────────────────────────────────────────
    for revision_loop in range(max_revision_loops + 1):
        stage_start = time.time()
        yield {"event": "thought", "data": {
            "step": 2 + revision_loop,
            "text": f"🔍 Retriever Agent: Gathering evidence from the Knowledge Graph..."
                    + (f" (revision loop {revision_loop})" if revision_loop > 0 else ""),
        }}

        evidence_bundles = await _run_retriever(sub_questions, paper_ids)
        trace.evidence_bundles = evidence_bundles
        retriever_ms = int((time.time() - stage_start) * 1000)

        total_evidence = sum(len(b.evidence) for b in evidence_bundles)
        total_kg_queries = sum(b.retrieval_steps for b in evidence_bundles)
        trace.total_kg_queries = total_kg_queries

        for bundle in evidence_bundles:
            yield {"event": "action", "data": {
                "step": 2 + revision_loop,
                "name": "Retrieve",
                "input": bundle.sub_question_text,
            }}
            yield {"event": "observation", "data": {
                "step": 2 + revision_loop,
                "text": f"Found {len(bundle.evidence)} pieces of evidence for: {bundle.sub_question_text}",
                "node_ids": [e.source_node for e in bundle.evidence if e.source_node],
            }}

        trace.stage_results.append(PipelineStageResult(
            stage=AgentStage.RETRIEVER, duration_ms=retriever_ms,
            input_summary=f"{len(sub_questions)} sub-questions",
            output_summary=f"{total_evidence} evidence items from {total_kg_queries} KG queries",
            llm_calls=len(sub_questions), kg_queries=total_kg_queries,
        ))

        # ── Stage 3: REASONER ────────────────────────────────────────
        stage_start = time.time()
        yield {"event": "thought", "data": {
            "step": 3 + revision_loop,
            "text": "💡 Reasoner Agent: Synthesizing evidence into a grounded answer..."
        }}

        reasoned_answer = await _run_reasoner(question, evidence_bundles)
        trace.reasoned_answer = reasoned_answer
        reasoner_ms = int((time.time() - stage_start) * 1000)

        yield {"event": "reasoning", "data": {
            "step": 3 + revision_loop,
            "answer_preview": reasoned_answer.text[:200],
            "reasoning_steps": [s.model_dump() for s in reasoned_answer.reasoning_steps],
            "duration_ms": reasoner_ms,
        }}

        trace.stage_results.append(PipelineStageResult(
            stage=AgentStage.REASONER, duration_ms=reasoner_ms,
            input_summary=f"{total_evidence} evidence items",
            output_summary=f"{len(reasoned_answer.reasoning_steps)} reasoning steps",
            llm_calls=1, kg_queries=0,
        ))

        # ── Stage 4: VERIFIER ────────────────────────────────────────
        stage_start = time.time()
        yield {"event": "thought", "data": {
            "step": 4 + revision_loop,
            "text": "✅ Verifier Agent: Fact-checking answer against the Knowledge Graph..."
        }}

        verification = await _run_verifier(reasoned_answer, evidence_bundles, paper_ids)
        trace.verification_report = verification
        verifier_ms = int((time.time() - stage_start) * 1000)

        yield {"event": "verifying", "data": {
            "step": 4 + revision_loop,
            "confidence": verification.confidence_score,
            "total_claims": verification.total_claims,
            "verified_count": verification.verified_count,
            "unsupported_count": verification.unsupported_count,
            "contradicted_count": verification.contradicted_count,
            "provenance_passed": verification.provenance_check_passed,
            "duration_ms": verifier_ms,
        }}

        trace.stage_results.append(PipelineStageResult(
            stage=AgentStage.VERIFIER, duration_ms=verifier_ms,
            input_summary=f"Answer with {verification.total_claims} claims",
            output_summary=f"Confidence: {verification.confidence_score:.2f}, "
                          f"Verified: {verification.verified_count}/{verification.total_claims}",
            llm_calls=1, kg_queries=0,
        ))

        # ── Revision loop check ──────────────────────────────────────
        if (verification.revision_suggested
            and verification.confidence_score < settings.VERIFIER_CONFIDENCE_THRESHOLD
            and revision_loop < max_revision_loops):

            trace.revision_loops += 1
            yield {"event": "revision", "data": {
                "step": 4 + revision_loop,
                "reason": verification.revision_reason or "Low confidence — re-retrieving evidence",
                "loop": revision_loop + 1,
                "confidence": verification.confidence_score,
            }}

            # Refine sub-questions based on unsupported claims
            unsupported_claims = [
                c.claim for c in verification.verified_claims
                if c.result in (VerificationResult.UNSUPPORTED, VerificationResult.CONTRADICTED)
            ]
            if unsupported_claims:
                # Add new sub-questions targeting unsupported claims
                for i, claim in enumerate(unsupported_claims[:2]):
                    sub_questions.append(SubQuestion(
                        id=f"revision_{revision_loop}_{i}",
                        text=f"Find specific evidence for: {claim}",
                        retrieval_strategy=RetrievalStrategy.NEIGHBOR_TRAVERSAL,
                        expected_evidence_type=EvidenceType.FACTUAL,
                    ))

            continue  # Go back to retriever

        # Confidence is acceptable — proceed to final answer
        break

    # ── Emit final answer ─────────────────────────────────────────────
    total_ms = int((time.time() - pipeline_start) * 1000)
    trace.total_duration_ms = total_ms
    trace.total_llm_calls = sum(s.llm_calls for s in trace.stage_results)
    trace.final_answer = reasoned_answer.text
    trace.final_confidence = verification.confidence_score

    # Mark verified steps
    for step in reasoned_answer.reasoning_steps:
        for cv in verification.verified_claims:
            if cv.claim.lower() in step.claim.lower() or step.claim.lower() in cv.claim.lower():
                step.is_verified = (cv.result == VerificationResult.VERIFIED)
                step.verification_note = cv.note

    # Calculate total steps used (each agent stage counts as a step)
    total_steps = len(trace.stage_results)

    yield {"event": "answer", "data": {
        "text": reasoned_answer.text,
        "steps_used": total_steps,
        "lazy_completion_count": 0,
        "mode": "multi_agent",
        "pipeline_trace": {
            "sub_questions": len(sub_questions),
            "total_evidence": sum(len(b.evidence) for b in evidence_bundles),
            "total_kg_queries": trace.total_kg_queries,
            "verification_confidence": verification.confidence_score,
            "verified_claims": verification.verified_count,
            "total_claims": verification.total_claims,
            "revision_loops": trace.revision_loops,
            "total_duration_ms": total_ms,
            "stage_durations": {
                s.stage.value: s.duration_ms for s in trace.stage_results
            },
        },
        "reasoning_steps": [
            {
                "step": s.step_number,
                "claim": s.claim,
                "evidence": [e.text for e in s.supporting_evidence],
                "graph_path": s.graph_path,
                "verified": s.is_verified,
            }
            for s in reasoned_answer.reasoning_steps
        ],
    }}

    # Emit subgraph of all touched nodes
    all_nodes = set()
    for bundle in evidence_bundles:
        for e in bundle.evidence:
            if e.source_node:
                all_nodes.add(e.source_node)
            if e.target_node:
                all_nodes.add(e.target_node)

    if all_nodes:
        subgraph = await neo4j_service.get_subgraph_for_nodes(list(all_nodes))
        yield {"event": "subgraph", "data": {
            "nodes": [n.model_dump() for n in subgraph.nodes],
            "edges": [e.model_dump() for e in subgraph.edges],
        }}

    # Emit full trace for detailed analysis
    yield {"event": "trace", "data": trace.model_dump()}


# ═══════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════

def _safe_enum(value: str, enum_class, default):
    """Safely convert a string to an enum value."""
    try:
        return enum_class(value)
    except (ValueError, KeyError):
        return default
