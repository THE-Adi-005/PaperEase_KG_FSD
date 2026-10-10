"""Read-only report on generic entity nodes in Neo4j for config_id='default'."""

import asyncio
import logging
import sys
from pathlib import Path

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.config import settings
from app.triple_filters import is_generic
from neo4j import AsyncGraphDatabase

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("generic_report")


async def generate_report(config_id: str = "default"):
    driver = AsyncGraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
    )

    try:
        async with driver.session() as session:
            # (a) Number of entity nodes that are generic
            all_nodes_cypher = """
                MATCH (n:Entity)
                WHERE coalesce(n.config_id, 'default') = $cid
                RETURN n.name as name, n.norm_name as norm_name, labels(n) as labels
            """
            result = await session.run(all_nodes_cypher, cid=config_id)
            all_nodes = [record async for record in result]

            generic_nodes = [
                n for n in all_nodes
                if is_generic(n["name"] or "") or is_generic(n["norm_name"] or "")
            ]

            # (b) & (c) Nodes connected by edges from > 1 distinct source_paper_id
            cross_paper_cypher = """
                MATCH (n:Entity)
                WHERE coalesce(n.config_id, 'default') = $cid
                OPTIONAL MATCH (n)-[r]-()
                WHERE r.source_paper_id IS NOT NULL AND coalesce(r.config_id, 'default') = $cid
                WITH n, count(DISTINCT r.source_paper_id) as paper_count
                WHERE paper_count > 1
                RETURN n.name as name, n.norm_name as norm_name, labels(n) as labels, paper_count
                ORDER BY paper_count DESC, name ASC
            """
            result = await session.run(cross_paper_cypher, cid=config_id)
            cross_paper_nodes = [record async for record in result]

            generic_cross = [
                n for n in cross_paper_nodes
                if is_generic(n["name"] or "") or is_generic(n["norm_name"] or "")
            ]
            non_generic_cross = [
                n for n in cross_paper_nodes
                if not (is_generic(n["name"] or "") or is_generic(n["norm_name"] or ""))
            ]

            print("\n" + "=" * 70)
            print(f"GENERIC ENTITY REPORT (config_id='{config_id}')")
            print("=" * 70)
            print(f"(a) Total Entity nodes:                      {len(all_nodes)}")
            print(f"    Generic Entity nodes:                    {len(generic_nodes)}")
            print(f"    Non-generic Entity nodes:                {len(all_nodes) - len(generic_nodes)}")
            print("-" * 70)
            print(f"(b) Cross-paper nodes (>1 distinct papers):  {len(cross_paper_nodes)}")
            print(f"    - Generic cross-paper nodes:             {len(generic_cross)}")
            print(f"    - Non-generic cross-paper nodes:         {len(non_generic_cross)}")
            print("-" * 70)
            print("(c) Top 10 cross-paper nodes by number of distinct papers:")
            for idx, n in enumerate(cross_paper_nodes[:10], 1):
                gen_flag = "GENERIC" if (is_generic(n["name"] or "") or is_generic(n["norm_name"] or "")) else "NON-GENERIC"
                lbls = [l for l in n["labels"] if l != "Entity"]
                print(f"    {idx:2d}. [{gen_flag:11s}] {n['name']!r:35s} (papers={n['paper_count']:2d}, labels={lbls})")
            print("=" * 70 + "\n")

    finally:
        await driver.close()


def main():
    asyncio.run(generate_report(config_id="default"))


if __name__ == "__main__":
    main()
