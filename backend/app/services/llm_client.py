"""LLM client — OpenAI-compatible wrapper for Ollama.

Uses the openai package pointed at Ollama's /v1 endpoint.
Provides methods for extraction, generation, and streaming.
"""

from openai import AsyncOpenAI
import json
import re
import logging
from typing import AsyncGenerator

from app.config import settings
from app.schema_profiles import get_active_profile, SchemaProfile, PROFILES

logger = logging.getLogger(__name__)

_RELATION_DESCRIPTIONS: dict[str, str] = {
    "USES_METHOD": "entity uses a method/technique",
    "DISCUSSES_CONCEPT": "section discusses a concept",
    "EVALUATED_ON": "method evaluated on dataset",
    "ACHIEVES": "method achieves a metric value",
    "COMPARES_TO": "method compared to another method",
    "EXTENDS": "method extends another method",
    "CITES": "paper/work cites another work",
    "SAME_AS": "two entities represent the same concept/method/dataset",
    "TRAINED_ON": "method is trained on a dataset",
    "OUTPERFORMS": "method explicitly outperforms another method",
    "HAS_COMPONENT": "method has a module or component",
}

_ENTITY_DESCRIPTIONS: dict[str, str] = {
    "Method": "algorithms, models, techniques, architectures",
    "Dataset": "datasets, benchmarks, corpora",
    "Metric": "evaluation metrics (accuracy, F1, BLEU, etc.)",
    "Concept": "theoretical concepts, ideas, phenomena",
    "Citation": "referenced papers/works",
}


class LLMClient:
    """Async LLM client for Ollama via OpenAI-compatible API."""

    def __init__(self):
        self.client = AsyncOpenAI(
            base_url=settings.LLM_BASE_URL,
            api_key=settings.LLM_API_KEY,  
        )
        self.model = settings.LLM_MODEL

    async def generate(self, messages: list[dict], temperature: float = 0.1,
                       max_tokens: int = 2048) -> str:
        """Single completion call."""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"LLM generate error: {e}")
            raise

    async def stream(self, messages: list[dict], temperature: float = 0.1,
                     max_tokens: int = 2048) -> AsyncGenerator[str, None]:
        """Streaming completion — yields text chunks."""
        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"LLM stream error: {e}")
            raise

    async def extract_triples(self, section_text: str, section_id: str,
                               paper_id: str, temperature: float = 0.6,
                               profile: SchemaProfile | str | None = None,
                               trunc: int | None = None) -> list[dict]:
        """Extract KG triples from section text.
        
        Returns list of dicts with keys: head, head_type, relation, tail, tail_type
        """
        prof = (
            profile if isinstance(profile, SchemaProfile)
            else PROFILES.get(profile, get_active_profile()) if profile
            else get_active_profile()
        )
        rel_lines = "\n".join(
            f"- {r}: {_RELATION_DESCRIPTIONS.get(r, 'relationship between entities')}"
            for r in prof.llm_relations
        )
        ent_lines = "\n".join(
            f"- {e}: {_ENTITY_DESCRIPTIONS.get(e, 'entity mention')}"
            for e in prof.entity_types
        )

        limit = trunc if trunc is not None else settings.SECTION_TEXT_LIMIT
        text_slice = section_text[:limit] if limit > 0 else section_text

        prompt = f"""You are a knowledge graph extraction expert. Extract factual triples from this research paper section.

Each triple should be: (head_entity, relation_type, tail_entity)

RELATION TYPES (use only these):
{rel_lines}

ENTITY TYPES:
{ent_lines}

RULES:
- Extract concrete, factual triples only
- Include metric values when mentioned (e.g., "achieves 85.3% accuracy")
- Use canonical names (e.g., "BERT" not "the BERT model")
- Each triple must be independently meaningful

Section text:
\"\"\"
{text_slice}
\"\"\"

Return a JSON array. Example:
[
  {{"head": "BERT", "head_type": "Method", "relation": "ACHIEVES", "tail": "F1=92.4", "tail_type": "Metric"}},
  {{"head": "BERT", "head_type": "Method", "relation": "EVALUATED_ON", "tail": "SQuAD", "tail_type": "Dataset"}}
]

Return ONLY the JSON array, no other text:"""

        messages = [{"role": "user", "content": prompt}]

        try:
            response = await self.generate(messages, temperature=temperature, max_tokens=2048)
            # Parse JSON from response
            triples = self._parse_json_array(response)
            return triples
        except Exception as e:
            logger.warning(f"Triple extraction failed for section {section_id}: {e}")
            return []

    async def extract_triples_targeted(self, section_text: str,
                                        missing_info: str,
                                        section_id: str,
                                        paper_id: str,
                                        profile: SchemaProfile | str | None = None) -> list[dict]:
        """Targeted re-extraction for lazy graph completion.
        
        Only extracts triples relevant to the missing information.
        """
        prof = (
            profile if isinstance(profile, SchemaProfile)
            else PROFILES.get(profile, get_active_profile()) if profile
            else get_active_profile()
        )
        rel_str = ", ".join(prof.llm_relations)

        prompt = f"""You are a knowledge graph extraction expert. Extract ONLY triples relevant to this specific query from the research paper section.

QUERY: Find information about: {missing_info}

Section text:
\"\"\"
{section_text[:settings.SECTION_TEXT_LIMIT]}
\"\"\"

Extract triples that help answer the query. Use these relation types:
{rel_str}

Return a JSON array of triples:
[{{"head": "...", "head_type": "...", "relation": "...", "tail": "...", "tail_type": "..."}}]

Return ONLY the JSON array:"""

        messages = [{"role": "user", "content": prompt}]
        try:
            response = await self.generate(messages, temperature=0.3, max_tokens=1024)
            return self._parse_json_array(response)
        except Exception as e:
            logger.warning(f"Targeted extraction failed: {e}")
            return []

    def _parse_json_array(self, text: str) -> list[dict]:
        """Extract JSON array from LLM response text."""
        # Try direct parse
        text = text.strip()
        try:
            result = json.loads(text)
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

        # Try to find JSON array in the text
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group())
                if isinstance(result, list):
                    return result
            except json.JSONDecodeError:
                pass

        # Try line-by-line JSON objects
        objects = []
        for match in re.finditer(r'\{[^{}]+\}', text):
            try:
                obj = json.loads(match.group())
                if "head" in obj and "tail" in obj:
                    objects.append(obj)
            except json.JSONDecodeError:
                continue

        return objects


# Singleton
llm_client = LLMClient()
