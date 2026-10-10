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


async def run_migration(dry_run: bool = False):
    logger.info("Connecting to Neo4j at %s...", settings.NEO4J_URI)
    driver = AsyncGraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
    )

    try:
        async with driver.session() as session:
            # 1. Find semantic entity nodes needing migration
            labels_str = "|".join(SEMANTIC_ENTITY_LABELS)
            find_nodes_cypher = f"""
                MATCH (n)
                WHERE any(lbl IN labels(n) WHERE lbl IN $labels)
                RETURN elementId(n) as eid, labels(n) as lbls, n.name as name,
                       n.config_id as cid, n.norm_name as norm
            """
            result = await session.run(find_nodes_cypher, labels=SEMANTIC_ENTITY_LABELS)
            nodes = [record async for record in result]
            logger.info("Found %d semantic entity nodes in Neo4j.", len(nodes))

            if not dry_run:
                # Update nodes in batches
                migrated_nodes = 0
                for record in nodes:
                    raw_name = record["name"] or ""
                    normalized = norm_name(raw_name)
                    lbls = record["lbls"]
                    is_metric = "Metric" in lbls

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

            # 2. Migrate relationships with source_paper_id
            find_edges_cypher = """
                MATCH ()-[r]->()
                WHERE r.source_paper_id IS NOT NULL AND r.config_id IS NULL
                RETURN count(r) as count
            """
            result = await session.run(find_edges_cypher)
            edge_count = (await result.single())["count"]
            logger.info("Found %d relationships with source_paper_id missing config_id.", edge_count)

            if not dry_run and edge_count > 0:
                update_edges_cypher = """
                    MATCH ()-[r]->()
                    WHERE r.source_paper_id IS NOT NULL AND r.config_id IS NULL
                    SET r.config_id = 'default'
                    RETURN count(r) as count
                """
                res = await session.run(update_edges_cypher)
                updated_edges = (await res.single())["count"]
                logger.info("Set config_id='default' on %d relationships.", updated_edges)

            # 3. Ensure composite index exists
            if not dry_run:
                index_cypher = "CREATE INDEX entity_norm_config IF NOT EXISTS FOR (n:Entity) ON (n.norm_name, n.config_id)"
                await session.run(index_cypher)
                logger.info("Ensured index entity_norm_config exists.")

            logger.info("Migration completed successfully (dry_run=%s).", dry_run)
    finally:
        await driver.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Migrate Neo4j nodes and edges for config_id namespacing.")
    parser.add_argument("--dry-run", action="store_true", help="Report counts without modifying the database.")
    args = parser.parse_args()

    print("=" * 70)
    print("WARNING: This will update existing Neo4j nodes and edges.")
    print("Run with --dry-run to preview changes.")
    print("=" * 70)
    asyncio.run(run_migration(dry_run=args.dry_run))
