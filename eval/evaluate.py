"""Evaluation script — Rouge-L and LLM-as-judge scoring.

Usage:
    python eval/evaluate.py --qa_file eval/qa_sets/paper1.json

QA file format (JSON):
[
    {"question": "...", "expected": "...", "paper_ids": ["..."]}
]
"""

import json
import argparse
import asyncio
import httpx
from rouge_score import rouge_scorer
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_BASE = "http://localhost:8000/api"


async def get_answer(question: str, paper_ids: list[str]) -> dict:
    """Query the API and collect the streamed answer."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream(
            "POST",
            f"{API_BASE}/query",
            json={"question": question, "paper_ids": paper_ids, "mode": "single"},
        ) as response:
            answer_text = ""
            steps_used = 0
            lazy_count = 0

            async for line in response.aiter_lines():
                if line.startswith("event: answer"):
                    continue
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        if "text" in data and "steps_used" in data:
                            answer_text = data["text"]
                            steps_used = data.get("steps_used", 0)
                            lazy_count = data.get("lazy_completion_count", 0)
                    except json.JSONDecodeError:
                        pass

            return {
                "answer": answer_text,
                "steps_used": steps_used,
                "lazy_completion_count": lazy_count,
            }


def compute_rouge_l(prediction: str, reference: str) -> float:
    """Compute Rouge-L F1 score."""
    scorer = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=True)
    scores = scorer.score(reference, prediction)
    return scores["rougeL"].fmeasure


async def llm_judge(question: str, expected: str, predicted: str,
                     num_samples: int = 3) -> float:
    """LLM-as-judge using the same local model. Majority vote over N samples.
    
    NOTE: A local 7-8B judge is weaker/noisier than GPT-4o-class judges.
    Mitigated by sampling 2-3 times and taking majority vote.
    """
    prompt = f"""You are an evaluation judge. Determine if the predicted answer correctly answers the question compared to the expected answer.

Question: {question}
Expected Answer: {expected}
Predicted Answer: {predicted}

Does the predicted answer correctly capture the key information from the expected answer?
Reply with ONLY "correct" or "incorrect"."""

    correct_votes = 0

    async with httpx.AsyncClient(timeout=60.0) as client:
        for _ in range(num_samples):
            try:
                resp = await client.post(
                    "http://localhost:11434/v1/chat/completions",
                    json={
                        "model": "qwen2.5:7b",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.3,
                        "max_tokens": 10,
                    },
                )
                if resp.status_code == 200:
                    text = resp.json()["choices"][0]["message"]["content"].strip().lower()
                    if "correct" in text and "incorrect" not in text:
                        correct_votes += 1
            except Exception as e:
                logger.warning(f"Judge call failed: {e}")

    return correct_votes / num_samples


async def main():
    parser = argparse.ArgumentParser(description="Evaluate KG Paper Assistant")
    parser.add_argument("--qa_file", required=True, help="Path to QA JSON file")
    parser.add_argument("--output", default="eval/results.json", help="Output file")
    args = parser.parse_args()

    with open(args.qa_file) as f:
        qa_pairs = json.load(f)

    results = []
    total_rouge = 0
    total_judge = 0
    total_lazy = 0

    for i, qa in enumerate(qa_pairs):
        logger.info(f"Evaluating {i+1}/{len(qa_pairs)}: {qa['question'][:60]}...")

        # Get answer from system
        result = await get_answer(qa["question"], qa["paper_ids"])

        # Rouge-L
        rouge_l = compute_rouge_l(result["answer"], qa["expected"])

        # LLM judge
        judge_score = await llm_judge(qa["question"], qa["expected"], result["answer"])

        total_rouge += rouge_l
        total_judge += judge_score
        total_lazy += result["lazy_completion_count"]

        entry = {
            "question": qa["question"],
            "expected": qa["expected"],
            "predicted": result["answer"],
            "rouge_l": round(rouge_l, 4),
            "judge_score": round(judge_score, 4),
            "steps_used": result["steps_used"],
            "lazy_completions": result["lazy_completion_count"],
        }
        results.append(entry)
        logger.info(f"  Rouge-L={rouge_l:.3f}, Judge={judge_score:.3f}, Steps={result['steps_used']}")

    # Summary
    n = len(qa_pairs)
    summary = {
        "total_questions": n,
        "avg_rouge_l": round(total_rouge / n, 4) if n else 0,
        "avg_judge_score": round(total_judge / n, 4) if n else 0,
        "total_lazy_completions": total_lazy,
        "lazy_trigger_rate": f"{total_lazy}/{n}",
        "results": results,
    }

    # Get lazy completion metrics from API
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{API_BASE}/metrics/lazy-completion")
            if resp.status_code == 200:
                summary["lazy_completion_metrics"] = resp.json()
    except Exception:
        pass

    with open(args.output, "w") as f:
        json.dump(summary, f, indent=2)

    logger.info(f"\n{'='*50}")
    logger.info(f"RESULTS SUMMARY")
    logger.info(f"{'='*50}")
    logger.info(f"Questions: {n}")
    logger.info(f"Avg Rouge-L: {summary['avg_rouge_l']:.4f}")
    logger.info(f"Avg Judge Score: {summary['avg_judge_score']:.4f}")
    logger.info(f"Lazy Completions Triggered: {total_lazy}")
    logger.info(f"Results saved to: {args.output}")


if __name__ == "__main__":
    asyncio.run(main())
