"""Migration script: Backfill config_id and norm_name on existing KG nodes & edges.

WARNING: DO NOT RUN THIS SCRIPT UNTIL EXPLICITLY CONFIRMED BY THE USER.

What this migration does:
1. Adds `:Entity` base label and sets `config_id = 'default'`, `norm_name = toLower(trim(n.name))`
   on all existing semantic entity nodes (:Concept, :Method, :Dataset, :Metric, :Citation).
2. Sets `config_id = 'default'` on all relationships carrying a `source_paper_id`.
3. Backfills `metric_name`, `value` (float), and `is_percent` on Metric nodes whose name matches '<metric>=<val>'.
4. Ensures the index `entity_norm_config` on `(:Entity {norm_name, config_id})` exists.
"""

import asyncio
import logging
import re
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.config import settings
from app.models.neo4j_schema import SEMANTIC_ENTITY_LABELS
from app.schema_profiles import norm_name
from neo4j import AsyncGraphDatabase

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("migrate_config_id")


def parse_metric(name: str):
    m = re.match(r"^(.+?)=(.+)$", name.strip())
    if m:
        metric_name = m.group(1).strip()
        val_str = m.group(2).strip()
        is_pct = val_str.endswith("%")
        if is_pct:
            val_str = val_str[:-1].strip()
        try:
            val = float(val_str)
            return metric_name, val, is_pct
        except ValueError:
            pass
    return name, None, False


async def run_migration(apply: bool = False):
    logger.info("Connecting to Neo4j at %s...", settings.NEO4J_URI)
    driver = AsyncGraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
    )

    try:
        async with driver.session() as session:
            # 1. Find semantic entity nodes needing migration
            find_nodes_cypher = """
                MATCH (n)
                WHERE any(lbl IN labels(n) WHERE lbl IN $labels) OR 'Entity' IN labels(n)
                RETURN elementId(n) as eid, labels(n) as lbls, n.name as name,
                       n.config_id as cid, n.norm_name as norm
            """
            result = await session.run(find_nodes_cypher, labels=SEMANTIC_ENTITY_LABELS)
            nodes = [record async for record in result]
            nodes_to_update = [
                n for n in nodes
                if n["cid"] is None or n["norm"] is None or "Entity" not in n["lbls"]
                or not any(l in SEMANTIC_ENTITY_LABELS for l in n["lbls"])
            ]
            logger.info("Found %d semantic entity nodes in Neo4j (%d need update).", len(nodes), len(nodes_to_update))

            # 2. Find relationships with source_paper_id missing config_id
            find_edges_cypher = """
                MATCH ()-[r]->()
                WHERE r.source_paper_id IS NOT NULL AND r.config_id IS NULL
                RETURN count(r) as count
            """
            result = await session.run(find_edges_cypher)
            edge_count = (await result.single())["count"]
            logger.info("Found %d relationships with source_paper_id missing config_id.", edge_count)

            # Always print counts of nodes/edges that would change
            print("\n" + "=" * 70)
            print("MIGRATION SUMMARY COUNTS")
            print("=" * 70)
            print(f"Semantic entity nodes total:       {len(nodes)}")
            print(f"Semantic entity nodes to update:   {len(nodes_to_update)}")
            print(f"Relationships to update:           {edge_count}")
            print("=" * 70)

            # 3. Always generate & print DUPLICATE REPORT
            dup_cypher = """
                MATCH (n)
                WHERE any(lbl IN labels(n) WHERE lbl IN $labels) OR 'Entity' IN labels(n)
                OPTIONAL MATCH (n)-[r]-()
                WITH n, count(r) AS degree
                WITH coalesce(n.norm_name, toLower(trim(n.name))) AS norm_name,
                     coalesce(n.config_id, 'default') AS config_id,
                     collect({name: n.name, labels: labels(n), degree: degree}) AS nodes,
                     count(n) AS group_size
                WHERE group_size > 1
                RETURN norm_name, config_id, group_size, nodes
                ORDER BY group_size DESC, norm_name ASC
                LIMIT 30
            """
            dup_result = await session.run(dup_cypher, labels=SEMANTIC_ENTITY_LABELS)
            dup_groups = [record async for record in dup_result]

            print("\n" + "=" * 70)
            print("DUPLICATE REPORT: Groups sharing (norm_name, config_id) [Top 30]")
            print("=" * 70)
            if not dup_groups:
                print("No duplicate entity nodes found.")
            else:
                for idx, grp in enumerate(dup_groups, 1):
                    print(f"Group #{idx}: norm_name='{grp['norm_name']}', config_id='{grp['config_id']}' (count={grp['group_size']})")
                    for node_info in grp["nodes"]:
                        lbls = [l for l in node_info["labels"] if l != "Entity"]
                        print(f"   - name: {node_info['name']!r:30} labels: {lbls}  degree: {node_info['degree']}")
            print("=" * 70 + "\n")

            if not apply:
                print("[DRY-RUN] No changes written to database. Run with --apply to execute migration.\n")
                return

            # Apply updates if requested
            logger.info("Applying migration changes...")

            migrated_nodes = 0
            for record in nodes:
                raw_name = record["name"] or ""
                normalized = norm_name(raw_name)
                lbls = record["lbls"]
                is_metric = "Metric" in lbls
                has_semantic = any(l in SEMANTIC_ENTITY_LABELS for l in lbls)

                metric_params = {}
                if is_metric and raw_name:
                    m_name, val, is_pct = parse_metric(raw_name)
                    metric_params = {
                        "metric_name": m_name,
                        "metric_value": val,
                        "is_percent": is_pct,
                    }

                update_cypher = """
                    MATCH (n) WHERE elementId(n) = $eid
                    SET n:Entity,
                        n.config_id = coalesce(n.config_id, 'default'),
                        n.norm_name = coalesce(n.norm_name, $norm)
                """
                if not has_semantic:
                    update_cypher += """
                        SET n:Concept
                    """
                if metric_params:
                    update_cypher += """
                        SET n.metric_name = coalesce(n.metric_name, $metric_name),
                            n.value       = coalesce(n.value, $metric_value),
                            n.is_percent  = coalesce(n.is_percent, $is_percent)
                    """

                await session.run(
                    update_cypher,
                    eid=record["eid"],
                    norm=normalized,
                    **metric_params,
                )
                migrated_nodes += 1

            logger.info("Migrated %d entity nodes with :Entity, norm_name, and config_id='default'.", migrated_nodes)

            if edge_count > 0:
                update_edges_cypher = """
                    MATCH ()-[r]->()
                    WHERE r.source_paper_id IS NOT NULL AND r.config_id IS NULL
                    SET r.config_id = 'default'
                    RETURN count(r) as count
                """
                res = await session.run(update_edges_cypher)
                updated_edges = (await res.single())["count"]
                logger.info("Set config_id='default' on %d relationships.", updated_edges)

            index_cypher = "CREATE INDEX entity_norm_config IF NOT EXISTS FOR (n:Entity) ON (n.norm_name, n.config_id)"
            await session.run(index_cypher)
            logger.info("Ensured index entity_norm_config exists.")

            logger.info("Migration completed successfully (apply=True).")
    finally:
        await driver.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Migrate Neo4j nodes and edges for config_id namespacing.")
    parser.add_argument("--apply", action="store_true", help="Apply migration changes to Neo4j. By default, runs in dry-run mode.")
    args = parser.parse_args()

    mode_str = "APPLY (CHANGES WILL BE WRITTEN)" if args.apply else "DRY-RUN (NO CHANGES WILL BE WRITTEN)"
    print("=" * 70)
    print(f"Neo4j Migration - Mode: {mode_str}")
    if not args.apply:
        print("Run with --apply to apply changes to the database.")
    print("=" * 70)
    asyncio.run(run_migration(apply=args.apply))
