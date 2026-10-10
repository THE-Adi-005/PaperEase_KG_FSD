"""Merge duplicate entity nodes sharing (norm_name, config_id) using APOC."""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.config import settings
from neo4j import AsyncGraphDatabase

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("merge_duplicates")


async def run_merge(apply: bool = False):
    logger.info("Connecting to Neo4j at %s...", settings.NEO4J_URI)
    driver = AsyncGraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
    )

    try:
        async with driver.session() as session:
            # Query duplicate groups with degree per node
            query = """
                MATCH (n:Entity)
                OPTIONAL MATCH (n)-[r]-()
                WITH n, count(r) AS degree
                WITH coalesce(n.norm_name, toLower(trim(n.name))) AS norm_name,
                     coalesce(n.config_id, 'default') AS config_id,
                     collect({
                         eid: elementId(n),
                         name: n.name,
                         labels: labels(n),
                         degree: degree
                     }) AS nodes,
                     count(n) AS cnt
                WHERE cnt > 1
                RETURN norm_name, config_id, cnt, nodes
                ORDER BY cnt DESC, norm_name ASC
            """
            result = await session.run(query)
            groups = [record async for record in result]

            mode_str = "APPLY (CHANGES WILL BE WRITTEN)" if apply else "DRY-RUN (NO CHANGES WILL BE WRITTEN)"
            print("\n" + "=" * 70)
            print(f"DUPLICATE MERGE - Mode: {mode_str}")
            print(f"Found {len(groups)} duplicate entity group(s)")
            print("=" * 70)

            if not groups:
                print("No duplicate entity groups found to merge.")
                return 0

            merge_plan = []
            for idx, record in enumerate(groups, 1):
                norm = record["norm_name"]
                cid = record["config_id"]
                raw_nodes = record["nodes"]

                # Sort by (-degree, eid) so index 0 has highest degree, tie: lowest elementId
                sorted_nodes = sorted(raw_nodes, key=lambda n: (-n["degree"], n["eid"]))
                target = sorted_nodes[0]
                others = sorted_nodes[1:]

                merge_plan.append({
                    "norm_name": norm,
                    "config_id": cid,
                    "target": target,
                    "others": others,
                })

                print(f"\nGroup #{idx}: norm_name='{norm}', config_id='{cid}' (total={len(sorted_nodes)} nodes)")
                t_lbls = [l for l in target["labels"] if l != "Entity"]
                print(f"  [KEEP]  eid={target['eid']} degree={target['degree']} labels={t_lbls} name={target['name']!r}")
                for other in others:
                    o_lbls = [l for l in other["labels"] if l != "Entity"]
                    print(f"  [MERGE] eid={other['eid']} degree={other['degree']} labels={o_lbls} name={other['name']!r}")

            print("\n" + "=" * 70)

            if not apply:
                print("[DRY-RUN] No changes were written to the database. Run with --apply to execute merge.\n")
                return len(groups)

            logger.info("Executing APOC node merges for %d group(s)...", len(merge_plan))
            merged_count = 0

            for item in merge_plan:
                target_eid = item["target"]["eid"]
                other_eids = [o["eid"] for o in item["others"]]

                merge_cypher = """
                    MATCH (target) WHERE elementId(target) = $target_eid
                    MATCH (other) WHERE elementId(other) IN $other_eids
                    WITH target, collect(other) AS others
                    CALL apoc.refactor.mergeNodes([target] + others, {
                        properties: 'discard',
                        mergeRels: false,
                        produceSelfRel: false
                    })
                    YIELD node
                    RETURN elementId(node) AS merged_eid
                """
                await session.run(merge_cypher, target_eid=target_eid, other_eids=other_eids)
                merged_count += 1

            logger.info("Successfully merged %d duplicate group(s).", merged_count)
            print(f"[APPLY COMPLETE] Successfully merged {merged_count} duplicate group(s).\n")
            return merged_count
    finally:
        await driver.close()


def main():
    parser = argparse.ArgumentParser(description="Merge duplicate entity nodes sharing (norm_name, config_id).")
    parser.add_argument("--apply", action="store_true", help="Apply merge changes to Neo4j. By default, runs in dry-run mode.")
    args = parser.parse_args()

    asyncio.run(run_merge(apply=args.apply))


if __name__ == "__main__":
    main()
