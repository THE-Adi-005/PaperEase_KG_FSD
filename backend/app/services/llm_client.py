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

logger = logging.getLogger(__name__)


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
                               paper_id: str, temperature: float = 0.6) -> list[dict]:
        """Extract KG triples from section text.
        
        Returns list of dicts with keys: head, head_type, relation, tail, tail_type
        """
        prompt = f"""You are a knowledge graph extraction expert. Extract factual triples from this research paper section.

Each triple should be: (head_entity, relation_type, tail_entity)

RELATION TYPES (use only these):
- USES_METHOD: entity uses a method/technique
- REPORTS_METRIC: entity reports a numerical result
- DISCUSSES_CONCEPT: section discusses a concept
- EVALUATED_ON: method evaluated on dataset  
- ACHIEVES: method achieves a metric value
- COMPARES_TO: method compared to another method
- EXTENDS: method extends another method
- CITES: paper/work cites another work

ENTITY TYPES:
- Method: algorithms, models, techniques, architectures
- Dataset: datasets, benchmarks, corpora
- Metric: evaluation metrics (accuracy, F1, BLEU, etc.)
- Concept: theoretical concepts, ideas, phenomena
- Citation: referenced papers/works

RULES:
- Extract concrete, factual triples only
- Include metric values when mentioned (e.g., "achieves 85.3% accuracy")
- Use canonical names (e.g., "BERT" not "the BERT model")
- Each triple must be independently meaningful

Section text:
\"\"\"
{section_text[:settings.SECTION_TEXT_LIMIT]}
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
                                        paper_id: str) -> list[dict]:
        """Targeted re-extraction for lazy graph completion.
        
        Only extracts triples relevant to the missing information.
        """
        prompt = f"""You are a knowledge graph extraction expert. Extract ONLY triples relevant to this specific query from the research paper section.

QUERY: Find information about: {missing_info}

Section text:
\"\"\"
{section_text[:settings.SECTION_TEXT_LIMIT]}
\"\"\"

Extract triples that help answer the query. Use these relation types:
USES_METHOD, REPORTS_METRIC, DISCUSSES_CONCEPT, EVALUATED_ON, ACHIEVES, COMPARES_TO, EXTENDS, CITES

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
