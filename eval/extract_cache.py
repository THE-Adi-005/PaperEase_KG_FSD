"""CLI script to pre-populate extraction cache from Neo4j paper sections."""

import argparse
import asyncio
import logging
import sys
import time
from pathlib import Path

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.config import settings
from app.services.llm_client import llm_client
from app.services.neo4j_client import neo4j_service
from eval.cache import has_run, put_run

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("extract_cache")


async def get_sections_from_neo4j(paper_ids: list[str] | None = None) -> list[dict]:
    """Fetch sections for given paper_ids or all papers from Neo4j."""
    if neo4j_service.driver is None:
        await neo4j_service.connect()
    async with neo4j_service.driver.session() as session:
        if paper_ids:
            query = """
                MATCH (p:Paper)-[:CONTAINS_SECTION]->(s:Section)
                WHERE p.id IN $pids
                RETURN p.id as paper_id, s.id as section_id, s.title as title,
                       s.text as text, coalesce(s.order_idx, 0) as order_idx
                ORDER BY p.id, order_idx
            """
            result = await session.run(query, pids=paper_ids)
        else:
            query = """
                MATCH (p:Paper)-[:CONTAINS_SECTION]->(s:Section)
                RETURN p.id as paper_id, s.id as section_id, s.title as title,
                       s.text as text, coalesce(s.order_idx, 0) as order_idx
                ORDER BY p.id, order_idx
            """
            result = await session.run(query)

        sections = []
        async for record in result:
            sections.append({
                "paper_id": record["paper_id"],
                "section_id": record["section_id"],
                "title": record["title"] or "",
                "text": record["text"] or "",
                "order_idx": record["order_idx"],
            })
        return sections


async def main():
    parser = argparse.ArgumentParser(description="Extract triples and cache them in sqlite.")
    parser.add_argument("--profile", choices=["R3", "R5", "R7", "R10"], default="R7", help="Prompt profile")
    parser.add_argument("--runs", type=int, default=3, help="Number of extraction runs per section (default: 3)")
    parser.add_argument("--trunc", type=int, default=settings.SECTION_TEXT_LIMIT, help="Text limit per section")
    parser.add_argument("--temp", type=float, default=0.6, help="LLM temperature (default: 0.6)")
    parser.add_argument("--model", type=str, default=settings.LLM_MODEL, help="LLM model name")
    parser.add_argument("--papers", type=str, default=None, help="Comma-separated paper IDs (default: all)")
    parser.add_argument("--concurrency", type=int, default=2, help="Max concurrent LLM requests (default: 2)")
    parser.add_argument("--smoke", action="store_true", help="Run 1 run on only 3 sections and estimate total time")

    args = parser.parse_args()

    paper_ids = [p.strip() for p in args.papers.split(",") if p.strip()] if args.papers else None

    logger.info("Fetching paper sections from Neo4j...")
    raw_sections = await get_sections_from_neo4j(paper_ids)

    # Reuse section-selection rule from normal ingestion: skip text < 50 chars
    valid_sections = [
        s for s in raw_sections
        if s["text"] and len(s["text"].strip()) >= 50
    ]
    logger.info("Found %d total sections, %d pass length threshold (>= 50 chars).",
                len(raw_sections), len(valid_sections))

    if not valid_sections:
        logger.warning("No valid sections found to process.")
        return

    full_job_calls = len(valid_sections) * args.runs

    if args.smoke:
        selected_sections = valid_sections[:3]
        target_runs = 1
        logger.info("[SMOKE MODE] Processing 3 sections with 1 run each...")
    else:
        selected_sections = valid_sections
        target_runs = args.runs

    semaphore = asyncio.Semaphore(args.concurrency)
    call_times = []
    completed_calls = 0
    total_calls_scheduled = len(selected_sections) * target_runs
    skipped_calls = 0

    async def process_task(sec: dict, run_idx: int):
        nonlocal completed_calls, skipped_calls
        p_id = sec["paper_id"]
        s_id = sec["section_id"]
        text = sec["text"]

        # Resumable: check if cached
        if has_run(p_id, s_id, run_idx, args.profile, args.trunc, args.temp, args.model):
            skipped_calls += 1
            return

        async with semaphore:
            t0 = time.perf_counter()
            try:
                triples = await llm_client.extract_triples(
                    section_text=text,
                    section_id=s_id,
                    paper_id=p_id,
                    temperature=args.temp,
                    profile=args.profile,
                    trunc=args.trunc,
                )
                put_run(
                    paper_id=p_id,
                    section_id=s_id,
                    run_idx=run_idx,
                    prompt_profile=args.profile,
                    trunc=args.trunc,
                    temperature=args.temp,
                    model=args.model,
                    raw_triples=triples,
                )
                elapsed = time.perf_counter() - t0
                call_times.append(elapsed)
                completed_calls += 1

                if args.smoke:
                    print(f"  [SMOKE] Paper {p_id} Sec {s_id} run {run_idx}: {elapsed:.2f}s ({len(triples)} triples)")

                if completed_calls % 10 == 0:
                    avg_t = sum(call_times) / len(call_times) if call_times else 0.0
                    print(f"  [PROGRESS] Completed {completed_calls} calls (avg {avg_t:.2f}s/call). Skipped {skipped_calls}.")

            except Exception as e:
                logger.error(f"Failed extraction for paper {p_id} section {s_id} run {run_idx}: {e}")

    # Build tasks
    tasks = []
    for sec in selected_sections:
        for r_idx in range(target_runs):
            tasks.append(process_task(sec, r_idx))

    logger.info("Executing %d tasks (concurrency=%d)...", len(tasks), args.concurrency)
    await asyncio.gather(*tasks)

    logger.info("Extraction finished: %d completed, %d skipped (cached).", completed_calls, skipped_calls)

    if args.smoke and call_times:
        avg_time = sum(call_times) / len(call_times)
        estimated_total_sec = avg_time * full_job_calls
        est_min = estimated_total_sec / 60
        print("\n" + "=" * 65)
        print("SMOKE BENCHMARK REPORT")
        print("=" * 65)
        print(f"Calls executed:               {len(call_times)}")
        print(f"Average seconds per call:     {avg_time:.2f}s")
        print(f"Full job total calls:         {full_job_calls} ({len(valid_sections)} sections x {args.runs} runs)")
        print(f"Estimated full job runtime:   {estimated_total_sec:.1f}s (~{est_min:.1f} minutes)")
        print("=" * 65 + "\n")

    if neo4j_service.driver:
        await neo4j_service.close()


if __name__ == "__main__":
    asyncio.run(main())
