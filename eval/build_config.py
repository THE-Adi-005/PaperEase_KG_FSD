"""Build and materialize an ablation knowledge graph configuration in Neo4j."""

import argparse
import asyncio
import json
import logging
import sys
from collections import Counter
from pathlib import Path

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import yaml
from app.config import settings
from app.models.schemas import Triple
from app.schema_profiles import PROFILES
from app.services.embeddings import embedding_service
from app.services.kg_builder import filter_runs
from app.services.neo4j_client import neo4j_service
from eval.cache import get_runs, get_table_triples

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("build_config")

PROJECT_ROOT = Path(__file__).resolve().parent.parent


async def fetch_paper_sections(paper_filter: str | list[str] | None = None) -> list[dict]:
    """Fetch sections for specified papers from Neo4j."""
    async with neo4j_service.driver.session() as session:
        if isinstance(paper_filter, list):
            query = """
                MATCH (p:Paper)-[:CONTAINS_SECTION]->(s:Section)
                WHERE p.id IN $pids
                RETURN DISTINCT p.id as paper_id, s.id as section_id,
                                s.title as title, s.text as text,
                                coalesce(s.order_idx, 0) as order_idx
                ORDER BY p.id, order_idx
            """
            result = await session.run(query, pids=paper_filter)
        else:
            query = """
                MATCH (p:Paper)-[:CONTAINS_SECTION]->(s:Section)
                RETURN DISTINCT p.id as paper_id, s.id as section_id,
                                s.title as title, s.text as text,
                                coalesce(s.order_idx, 0) as order_idx
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


async def build_config(cfg: dict) -> dict:
    config_id = cfg.get("config_id")
    if not config_id or config_id == "default":
        raise ValueError(f"Refusing to build or overwrite protected config_id 'default': '{config_id}'")

    prompt_profile_name = cfg.get("prompt_profile", "R7")
    if prompt_profile_name not in PROFILES:
        raise ValueError(f"Unknown prompt_profile: '{prompt_profile_name}'")
    profile = PROFILES[prompt_profile_name]

    runs = int(cfg.get("runs", 3))
    vote_fraction = float(cfg.get("vote_fraction", 0.5))
    cap = int(cfg.get("cap", 0))
    enforce_signatures = bool(cfg.get("enforce_signatures", False))
    allow_dynamic = bool(cfg.get("allow_dynamic", False))
    relation_subset = cfg.get("relation_subset")
    if relation_subset is not None:
        relation_subset = set(relation_subset)
    include_tables = bool(cfg.get("include_tables", True))
    enable_same_as = bool(cfg.get("enable_same_as", True))
    same_as_threshold = float(cfg.get("same_as_threshold", settings.SAME_AS_THRESHOLD))
    trunc = int(cfg.get("trunc", settings.SECTION_TEXT_LIMIT))
    temperature = float(cfg.get("temperature", 0.6))
    papers_cfg = cfg.get("papers", "all")
    model = cfg.get("model", settings.LLM_MODEL)

    logger.info("==================================================")
    logger.info("Building KG configuration: %s", config_id)
    logger.info("==================================================")

    # Step 1: Delete existing data for this config_id
    logger.info("Clearing any previous data for config_id='%s'...", config_id)
    await neo4j_service.delete_config(config_id)

    # Step 2: Fetch target sections
    paper_filter = papers_cfg if isinstance(papers_cfg, list) else None
    sections = await fetch_paper_sections(paper_filter)
    valid_sections = [s for s in sections if s["text"] and len(s["text"].strip()) >= 50]
    logger.info("Loaded %d sections (%d valid).", len(sections), len(valid_sections))

    # Step 3: Filter cached runs and merge triples
    total_before_filtering = 0
    total_after_filtering = 0
    triples_per_relation = Counter()
    processed_paper_ids = set()

    for sec in valid_sections:
        p_id = sec["paper_id"]
        s_id = sec["section_id"]
        processed_paper_ids.add(p_id)

        cached_runs = get_runs(
            paper_id=p_id,
            section_id=s_id,
            prompt_profile=prompt_profile_name,
            trunc=trunc,
            temperature=temperature,
            model=model,
            max_runs=runs,
        )

        total_before_filtering += sum(len(r) for r in cached_runs)

        if not cached_runs:
            continue

        sec_triples = filter_runs(
            cached_runs,
            paper_id=p_id,
            section_id=s_id,
            vote_fraction=vote_fraction,
            profile=profile,
            allow_dynamic=allow_dynamic,
            enforce_signatures=enforce_signatures,
            cap=cap,
        )

        if relation_subset is not None:
            sec_triples = [t for t in sec_triples if t.relation in relation_subset]

        total_after_filtering += len(sec_triples)
        for t in sec_triples:
            triples_per_relation[t.relation] += 1

        if sec_triples:
            await neo4j_service.merge_triples(sec_triples, config_id=config_id)

    logger.info("LLM triples merged: %d (from %d raw cached triples).",
                total_after_filtering, total_before_filtering)

    # Step 4: Tables
    if include_tables:
        table_triples_all = []
        for p_id in processed_paper_ids:
            raw_t = get_table_triples(paper_id=p_id)
            for item in raw_t:
                rel = item["relation"]
                if relation_subset is not None and rel not in relation_subset:
                    continue
                table_triples_all.append(Triple(
                    head=item["head"],
                    head_type="Method",
                    relation=rel,
                    tail=item["tail"],
                    tail_type="Metric" if rel == "REPORTS_METRIC" else "Dataset",
                    source_paper_id=item["paper_id"],
                    source_section_id=item.get("section_id", ""),
                ))
        if table_triples_all:
            merged_tables = await neo4j_service.merge_triples(table_triples_all, config_id=config_id)
            logger.info("Merged %d table triples.", merged_tables)

    # Step 5: SAME_AS entity linking
    if enable_same_as:
        total_same_as = 0
        for p_id in processed_paper_ids:
            count = await embedding_service.link_cross_paper_entities(
                p_id, config_id=config_id, threshold=same_as_threshold
            )
            total_same_as += count
        logger.info("Created %d SAME_AS edges (threshold=%.2f).", total_same_as, same_as_threshold)

    # Step 6: Graph statistics & saving results
    stats = await neo4j_service.get_semantic_graph_stats(config_id=config_id)
    stats["extraction_counts"] = {
        "total_before_filtering": total_before_filtering,
        "total_after_filtering": total_after_filtering,
        "triples_per_relation": dict(triples_per_relation),
    }

    results_dir = PROJECT_ROOT / "results" / config_id
    results_dir.mkdir(parents=True, exist_ok=True)

    config_json_path = results_dir / "config.json"
    with open(config_json_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

    graph_stats_json_path = results_dir / "graph_stats.json"
    with open(graph_stats_json_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    logger.info("Saved results to %s.", results_dir)

    # Step 7: Print summary table
    print("\n" + "=" * 70)
    print(f"CONFIG BUILD SUMMARY: {config_id}")
    print("=" * 70)
    print(f"Prompt Profile:            {prompt_profile_name}")
    print(f"Runs Used:                 {runs}")
    print(f"Vote Fraction:             {vote_fraction}")
    print(f"Cap:                       {cap if cap > 0 else 'None (uncapped)'}")
    print(f"Allow Dynamic / Sigs:      {allow_dynamic} / {enforce_signatures}")
    print(f"Total Raw Triples:         {total_before_filtering}")
    print(f"Filtered LLM Triples:      {total_after_filtering}")
    print(f"Total Entity Nodes:        {stats.get('total_nodes', 0)}")
    print(f"Total Semantic Edges:      {stats.get('total_edges', 0)}")
    print(f"SAME_AS Edges:             {stats.get('same_as_edges', 0)}")
    print(f"Average Degree:            {stats.get('avg_degree', 0.0):.2f}")
    print(f"Graph Density:             {stats.get('graph_density', 0.0):.4f}")
    print("=" * 70 + "\n")

    return stats


def main():
    parser = argparse.ArgumentParser(description="Build and materialize an ablation KG configuration.")
    parser.add_argument("config_yaml", type=str, help="Path to YAML config file (e.g. configs/cfg_base.yaml)")
    args = parser.parse_args()

    yaml_path = Path(args.config_yaml)
    if not yaml_path.is_absolute():
        yaml_path = PROJECT_ROOT / yaml_path

    if not yaml_path.exists():
        logger.error("Configuration file %s does not exist.", yaml_path)
        sys.exit(1)

    with open(yaml_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    asyncio.run(build_config(cfg))


if __name__ == "__main__":
    main()
