"""Three-Way Evaluation — KG Single-Agent vs KG Multi-Agent vs Naive RAG.

Extended evaluation framework that compares all three pipelines with
additional metrics for traceability, verification confidence, and multi-hop depth.

Usage:
    cd backend
    python -m eval.evaluate --qa_file eval/qa_sets/qa_multi_hop.json
    python -m eval.evaluate --qa_file eval/qa_sets/qa_multi_hop.json --pipeline all

Output:
    eval/results_comparison.json   — full per-question results
    eval/results_summary.json      — summary table (for slides)

NOTE: Both the backend (port 8000) and the LLM provider must be running.
"""

import json
import argparse
import asyncio
import time
import httpx
from rouge_score import rouge_scorer
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_BASE = "http://localhost:8000/api"


# ── Answer collection ────────────────────────────────────────────────

async def get_answer_kg(question: str, paper_ids: list[str]) -> dict:
    """Query the KG-grounded single-agent endpoint."""
    return await _collect_sse_answer(
        f"{API_BASE}/query",
        {"question": question, "paper_ids": paper_ids, "mode": "single", "pipeline": "single"},
    )


async def get_answer_multi_agent(question: str, paper_ids: list[str]) -> dict:
    """Query the multi-agent pipeline endpoint."""
    return await _collect_sse_answer(
        f"{API_BASE}/query",
        {"question": question, "paper_ids": paper_ids, "mode": "single", "pipeline": "multi"},
    )


async def get_answer_naive(question: str, paper_ids: list[str]) -> dict:
    """Query the naive RAG baseline endpoint."""
    return await _collect_sse_answer(
        f"{API_BASE}/query-naive",
        {"question": question, "paper_ids": paper_ids, "mode": "single"},
    )


async def _collect_sse_answer(url: str, body: dict) -> dict:
    """Generic SSE answer collector. Works for all endpoints."""
    start_time = time.time()
    async with httpx.AsyncClient(timeout=300.0) as client:
        async with client.stream("POST", url, json=body) as response:
            answer_text = ""
            steps_used = 0
            lazy_count = 0
            mode_label = "unknown"
            pipeline_trace = {}
            reasoning_steps = []

            async for line in response.aiter_lines():
                if line.startswith("event:"):
                    continue
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        if "text" in data and "steps_used" in data:
                            answer_text = data["text"]
                            steps_used = data.get("steps_used", 0)
                            lazy_count = data.get("lazy_completion_count", 0)
                            mode_label = data.get("mode", "kg_agent")
                            pipeline_trace = data.get("pipeline_trace", {})
                            reasoning_steps = data.get("reasoning_steps", [])
                    except json.JSONDecodeError:
                        pass

    elapsed_ms = int((time.time() - start_time) * 1000)
    return {
        "answer": answer_text,
        "steps_used": steps_used,
        "lazy_completion_count": lazy_count,
        "latency_ms": elapsed_ms,
        "mode": mode_label,
        "pipeline_trace": pipeline_trace,
        "reasoning_steps": reasoning_steps,
    }


# ── Scoring functions ────────────────────────────────────────────────

def compute_rouge_l(prediction: str, reference: str) -> float:
    """Compute Rouge-L F1 score."""
    scorer = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=True)
    scores = scorer.score(reference, prediction)
    return scores["rougeL"].fmeasure


async def llm_judge(question: str, expected: str, predicted: str,
                     num_samples: int = 3) -> float:
    """LLM-as-judge using the same local model. Majority vote over N samples."""
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


def detect_hallucination_signals(answer: str, expected: str) -> float:
    """Simple heuristic hallucination detector. Returns 0-1 (1=likely grounded)."""
    if not answer:
        return 0.0

    answer_lower = answer.lower()

    hedging_phrases = [
        "i don't have enough",
        "i cannot determine",
        "not enough information",
        "unable to find",
        "cannot be determined",
        "context does not contain",
        "no information available",
    ]
    hedge_score = 1.0 - (sum(1 for h in hedging_phrases if h in answer_lower) * 0.15)

    len_ratio = len(answer) / max(len(expected), 1)
    if len_ratio < 0.2 or len_ratio > 5.0:
        hedge_score *= 0.8

    return max(0.0, min(1.0, hedge_score))


# ── New metrics for multi-agent evaluation ───────────────────────────

def compute_traceability_score(reasoning_steps: list[dict]) -> float:
    """Fraction of reasoning steps that cite specific graph evidence."""
    if not reasoning_steps:
        return 0.0
    cited = sum(1 for step in reasoning_steps
                if step.get("evidence") or step.get("graph_path"))
    return cited / len(reasoning_steps)


def compute_sub_question_coverage(pipeline_trace: dict) -> float:
    """Fraction of sub-questions that received evidence."""
    total_sq = pipeline_trace.get("sub_questions", 0)
    total_evidence = pipeline_trace.get("total_evidence", 0)
    if total_sq == 0:
        return 0.0
    # If any evidence was found, coverage is proportional
    return min(1.0, total_evidence / max(total_sq, 1))


def compute_provenance_accuracy(answer: str, expected: str, reasoning_steps: list[dict]) -> float:
    """Estimate how well the answer attributes facts to correct sources."""
    if not reasoning_steps:
        return 0.5  # Unknown
    verified = sum(1 for step in reasoning_steps if step.get("verified", False))
    return verified / len(reasoning_steps) if reasoning_steps else 0.0


# ── Main evaluation loop ─────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser(
        description="Three-Way Evaluation: KG Single-Agent vs Multi-Agent vs Naive RAG"
    )
    parser.add_argument("--qa_file", required=True, help="Path to QA JSON file")
    parser.add_argument(
        "--output", default="eval/results_comparison.json", help="Output file"
    )
    parser.add_argument(
        "--pipeline", default="all", choices=["all", "single", "multi", "naive"],
        help="Which pipelines to evaluate"
    )
    parser.add_argument(
        "--skip-naive", action="store_true",
        help="Skip naive RAG baseline (only run KG modes)"
    )
    args = parser.parse_args()

    with open(args.qa_file) as f:
        qa_pairs = json.load(f)

    results = []
    totals = {
        "kg_single": {"rouge": 0, "judge": 0, "steps": 0, "latency": 0, "lazy": 0, "grounding": 0},
        "kg_multi": {"rouge": 0, "judge": 0, "steps": 0, "latency": 0,
                     "traceability": 0, "verification_conf": 0, "sub_q_coverage": 0},
        "naive": {"rouge": 0, "judge": 0, "steps": 0, "latency": 0, "grounding": 0},
    }
    categories = {}

    n = len(qa_pairs)
    run_single = args.pipeline in ("all", "single")
    run_multi = args.pipeline in ("all", "multi")
    run_naive = args.pipeline in ("all", "naive") and not args.skip_naive

    logger.info(f"\n{'='*70}")
    logger.info(f"  THREE-WAY EVALUATION")
    logger.info(f"  Questions: {n}")
    logger.info(f"  Pipelines: single={run_single}, multi={run_multi}, naive={run_naive}")
    logger.info(f"{'='*70}\n")

    for i, qa in enumerate(qa_pairs):
        question = qa["question"]
        expected = qa["expected"]
        paper_ids = qa.get("paper_ids", [])
        category = qa.get("category", "general")
        required_hops = qa.get("required_hops", 1)

        logger.info(f"[{i+1}/{n}] {question[:70]}...")

        entry = {
            "question": question,
            "category": category,
            "required_hops": required_hops,
            "expected": expected,
        }

        # ── Run KG Single-Agent ──
        if run_single:
            logger.info(f"  → KG Single-Agent...")
            kg_result = await get_answer_kg(question, paper_ids)
            kg_rouge = compute_rouge_l(kg_result["answer"], expected)
            kg_judge = await llm_judge(question, expected, kg_result["answer"])
            kg_grounding = detect_hallucination_signals(kg_result["answer"], expected)

            totals["kg_single"]["rouge"] += kg_rouge
            totals["kg_single"]["judge"] += kg_judge
            totals["kg_single"]["steps"] += kg_result["steps_used"]
            totals["kg_single"]["latency"] += kg_result["latency_ms"]
            totals["kg_single"]["lazy"] += kg_result["lazy_completion_count"]
            totals["kg_single"]["grounding"] += kg_grounding

            entry.update({
                "kg_single_answer": kg_result["answer"],
                "kg_single_rouge_l": round(kg_rouge, 4),
                "kg_single_judge": round(kg_judge, 4),
                "kg_single_grounding": round(kg_grounding, 4),
                "kg_single_steps": kg_result["steps_used"],
                "kg_single_latency_ms": kg_result["latency_ms"],
            })

            logger.info(
                f"     Single: Rouge-L={kg_rouge:.3f}, Judge={kg_judge:.2f}, "
                f"Steps={kg_result['steps_used']}, Latency={kg_result['latency_ms']}ms"
            )

        # ── Run KG Multi-Agent ──
        if run_multi:
            logger.info(f"  → KG Multi-Agent...")
            multi_result = await get_answer_multi_agent(question, paper_ids)
            multi_rouge = compute_rouge_l(multi_result["answer"], expected)
            multi_judge = await llm_judge(question, expected, multi_result["answer"])

            # Multi-agent specific metrics
            trace = multi_result.get("pipeline_trace", {})
            reasoning_steps = multi_result.get("reasoning_steps", [])
            traceability = compute_traceability_score(reasoning_steps)
            verification_conf = trace.get("verification_confidence", 0.0)
            sub_q_coverage = compute_sub_question_coverage(trace)

            totals["kg_multi"]["rouge"] += multi_rouge
            totals["kg_multi"]["judge"] += multi_judge
            totals["kg_multi"]["steps"] += multi_result["steps_used"]
            totals["kg_multi"]["latency"] += multi_result["latency_ms"]
            totals["kg_multi"]["traceability"] += traceability
            totals["kg_multi"]["verification_conf"] += verification_conf
            totals["kg_multi"]["sub_q_coverage"] += sub_q_coverage

            entry.update({
                "multi_answer": multi_result["answer"],
                "multi_rouge_l": round(multi_rouge, 4),
                "multi_judge": round(multi_judge, 4),
                "multi_traceability": round(traceability, 4),
                "multi_verification_confidence": round(verification_conf, 4),
                "multi_sub_q_coverage": round(sub_q_coverage, 4),
                "multi_steps": multi_result["steps_used"],
                "multi_latency_ms": multi_result["latency_ms"],
                "multi_pipeline_trace": trace,
            })

            logger.info(
                f"     Multi:  Rouge-L={multi_rouge:.3f}, Judge={multi_judge:.2f}, "
                f"Trace={traceability:.2f}, Verify={verification_conf:.2f}, "
                f"Latency={multi_result['latency_ms']}ms"
            )

        # ── Run Naive RAG ──
        if run_naive:
            logger.info(f"  → Naive RAG...")
            naive_result = await get_answer_naive(question, paper_ids)
            naive_rouge = compute_rouge_l(naive_result["answer"], expected)
            naive_judge = await llm_judge(question, expected, naive_result["answer"])
            naive_grounding = detect_hallucination_signals(naive_result["answer"], expected)

            totals["naive"]["rouge"] += naive_rouge
            totals["naive"]["judge"] += naive_judge
            totals["naive"]["latency"] += naive_result["latency_ms"]
            totals["naive"]["grounding"] += naive_grounding

            entry.update({
                "naive_answer": naive_result["answer"],
                "naive_rouge_l": round(naive_rouge, 4),
                "naive_judge": round(naive_judge, 4),
                "naive_grounding": round(naive_grounding, 4),
                "naive_latency_ms": naive_result["latency_ms"],
            })

            logger.info(
                f"     Naive:  Rouge-L={naive_rouge:.3f}, Judge={naive_judge:.2f}, "
                f"Latency={naive_result['latency_ms']}ms"
            )

        results.append(entry)

        # Track per-category
        if category not in categories:
            categories[category] = {"kg_single_judge": 0, "kg_multi_judge": 0,
                                    "naive_judge": 0, "count": 0}
        categories[category]["count"] += 1
        if run_single:
            categories[category]["kg_single_judge"] += entry.get("kg_single_judge", 0)
        if run_multi:
            categories[category]["kg_multi_judge"] += entry.get("multi_judge", 0)
        if run_naive:
            categories[category]["naive_judge"] += entry.get("naive_judge", 0)

    # ── Summary ──────────────────────────────────────────────────────

    summary = {"total_questions": n, "pipelines_evaluated": []}

    if run_single:
        summary["pipelines_evaluated"].append("kg_single")
        summary["kg_single"] = {
            "avg_rouge_l": round(totals["kg_single"]["rouge"] / n, 4) if n else 0,
            "avg_judge_score": round(totals["kg_single"]["judge"] / n, 4) if n else 0,
            "avg_grounding_score": round(totals["kg_single"]["grounding"] / n, 4) if n else 0,
            "avg_steps": round(totals["kg_single"]["steps"] / n, 2) if n else 0,
            "avg_latency_ms": round(totals["kg_single"]["latency"] / n) if n else 0,
            "total_lazy_completions": totals["kg_single"]["lazy"],
        }

    if run_multi:
        summary["pipelines_evaluated"].append("kg_multi")
        summary["kg_multi"] = {
            "avg_rouge_l": round(totals["kg_multi"]["rouge"] / n, 4) if n else 0,
            "avg_judge_score": round(totals["kg_multi"]["judge"] / n, 4) if n else 0,
            "avg_traceability": round(totals["kg_multi"]["traceability"] / n, 4) if n else 0,
            "avg_verification_confidence": round(totals["kg_multi"]["verification_conf"] / n, 4) if n else 0,
            "avg_sub_question_coverage": round(totals["kg_multi"]["sub_q_coverage"] / n, 4) if n else 0,
            "avg_steps": round(totals["kg_multi"]["steps"] / n, 2) if n else 0,
            "avg_latency_ms": round(totals["kg_multi"]["latency"] / n) if n else 0,
        }

    if run_naive:
        summary["pipelines_evaluated"].append("naive")
        summary["naive_rag"] = {
            "avg_rouge_l": round(totals["naive"]["rouge"] / n, 4) if n else 0,
            "avg_judge_score": round(totals["naive"]["judge"] / n, 4) if n else 0,
            "avg_grounding_score": round(totals["naive"]["grounding"] / n, 4) if n else 0,
            "avg_steps": 1,
            "avg_latency_ms": round(totals["naive"]["latency"] / n) if n else 0,
        }

    # Per-category breakdown
    summary["per_category"] = {}
    for cat, data in categories.items():
        c = data["count"]
        cat_summary = {"count": c}
        if run_single:
            cat_summary["kg_single_avg_judge"] = round(data["kg_single_judge"] / c, 4) if c else 0
        if run_multi:
            cat_summary["kg_multi_avg_judge"] = round(data["kg_multi_judge"] / c, 4) if c else 0
        if run_naive:
            cat_summary["naive_avg_judge"] = round(data["naive_judge"] / c, 4) if c else 0
        summary["per_category"][cat] = cat_summary

    # ── Save results ─────────────────────────────────────────────────

    full_output = {"summary": summary, "results": results}

    with open(args.output, "w") as f:
        json.dump(full_output, f, indent=2)

    summary_path = args.output.replace("_comparison", "_summary").replace(".json", ".json")
    if summary_path == args.output:
        summary_path = "eval/results_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    # ── Print results table ──────────────────────────────────────────

    logger.info(f"\n{'='*80}")
    logger.info(f"  THREE-WAY COMPARISON RESULTS")
    logger.info(f"{'='*80}")
    logger.info(f"")

    header = f"  {'Metric':<35}"
    if run_single:
        header += f" {'KG-Single':>15}"
    if run_multi:
        header += f" {'KG-Multi':>15}"
    if run_naive:
        header += f" {'Naive RAG':>15}"
    logger.info(header)
    logger.info(f"  {'-'*35}" + f" {'-'*15}" * sum([run_single, run_multi, run_naive]))

    # Judge score
    row = f"  {'Avg Judge Score':<35}"
    if run_single:
        row += f" {summary['kg_single']['avg_judge_score']:>15.4f}"
    if run_multi:
        row += f" {summary['kg_multi']['avg_judge_score']:>15.4f}"
    if run_naive:
        row += f" {summary['naive_rag']['avg_judge_score']:>15.4f}"
    logger.info(row)

    # ROUGE-L
    row = f"  {'Avg ROUGE-L':<35}"
    if run_single:
        row += f" {summary['kg_single']['avg_rouge_l']:>15.4f}"
    if run_multi:
        row += f" {summary['kg_multi']['avg_rouge_l']:>15.4f}"
    if run_naive:
        row += f" {summary['naive_rag']['avg_rouge_l']:>15.4f}"
    logger.info(row)

    # Multi-agent specific metrics
    if run_multi:
        logger.info(f"  {'Avg Traceability':<35} {'':>15} {summary['kg_multi']['avg_traceability']:>15.4f}")
        logger.info(f"  {'Avg Verification Confidence':<35} {'':>15} {summary['kg_multi']['avg_verification_confidence']:>15.4f}")
        logger.info(f"  {'Avg Sub-Q Coverage':<35} {'':>15} {summary['kg_multi']['avg_sub_question_coverage']:>15.4f}")

    # Latency
    row = f"  {'Avg Latency (ms)':<35}"
    if run_single:
        row += f" {summary['kg_single']['avg_latency_ms']:>15}"
    if run_multi:
        row += f" {summary['kg_multi']['avg_latency_ms']:>15}"
    if run_naive:
        row += f" {summary['naive_rag']['avg_latency_ms']:>15}"
    logger.info(row)

    logger.info(f"")
    logger.info(f"  Per-Category Breakdown:")
    for cat, data in summary["per_category"].items():
        parts = [f"{cat}:"]
        if run_single:
            parts.append(f"Single={data.get('kg_single_avg_judge', 0):.3f}")
        if run_multi:
            parts.append(f"Multi={data.get('kg_multi_avg_judge', 0):.3f}")
        if run_naive:
            parts.append(f"Naive={data.get('naive_avg_judge', 0):.3f}")
        parts.append(f"({data['count']} Qs)")
        logger.info(f"    {' | '.join(parts)}")

    logger.info(f"\n{'='*80}")
    logger.info(f"  Results saved to: {args.output}")
    logger.info(f"  Summary saved to: {summary_path}")
    logger.info(f"{'='*80}")


if __name__ == "__main__":
    asyncio.run(main())
