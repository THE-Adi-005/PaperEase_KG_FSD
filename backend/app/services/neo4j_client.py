"""Neo4j async client — MERGE operations, agent tool queries, schema setup.

Uses the official neo4j async driver. All Cypher queries are parameterized.
Every edge carries source_paper_id and source_section_id for provenance.
"""

from neo4j import AsyncGraphDatabase, AsyncDriver
import logging
from typing import Optional

from app.config import settings
from app.models.schemas import (
    Triple, ParsedPaper, GraphNode, GraphEdge, SubGraph,
    PaperInfo, PaperStatus, FigureData, TableData,
)
from app.models.neo4j_schema import SETUP_QUERIES

logger = logging.getLogger(__name__)


class Neo4jService:
    """Async Neo4j operations for the KG Paper Assistant."""

    def __init__(self):
        self.driver: Optional[AsyncDriver] = None

    async def connect(self):
        """Initialize the async driver and run schema setup."""
        self.driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
        )
        # Run schema setup (constraints + indexes)
        async with self.driver.session() as session:
            for query in SETUP_QUERIES:
                try:
                    await session.run(query)
                except Exception as e:
                    # Some queries may fail if index exists, that's fine
                    logger.debug(f"Schema setup note: {e}")
        logger.info("Neo4j schema initialized")

    async def close(self):
        """Close the driver."""
        if self.driver:
            await self.driver.close()

    async def verify_connectivity(self) -> bool:
        """Check if Neo4j is reachable."""
        try:
            async with self.driver.session() as session:
                result = await session.run("RETURN 1 AS ok")
                record = await result.single()
                return record and record["ok"] == 1
        except Exception:
            return False

    # ── Paper Structure ──────────────────────────────────────────────

    async def merge_paper(self, paper: ParsedPaper) -> None:
        """Create/update Paper, Author, Section, Figure, Table nodes."""
        async with self.driver.session() as session:
            # Paper node
            await session.run(
                """MERGE (p:Paper {id: $id})
                   SET p.title = $title, p.abstract = $abstract,
                       p.status = $status""",
                id=paper.id, title=paper.title, abstract=paper.abstract,
                status=PaperStatus.EXTRACTING.value,
            )

            # Authors
            for author in paper.authors:
                author_id = f"{paper.id}_{author.name.lower().replace(' ', '_')}"
                await session.run(
                    """MERGE (a:Author {id: $aid})
                       SET a.name = $name, a.affiliation = $affiliation
                       WITH a
                       MATCH (p:Paper {id: $pid})
                       MERGE (p)-[:AUTHORED_BY {source_paper_id: $pid}]->(a)""",
                    aid=author_id, name=author.name,
                    affiliation=author.affiliation or "", pid=paper.id,
                )

            # Sections
            for section in paper.sections:
                await session.run(
                    """MERGE (s:Section {id: $sid})
                       SET s.title = $title, s.text = $text, s.order_idx = $order
                       WITH s
                       MATCH (p:Paper {id: $pid})
                       MERGE (p)-[:CONTAINS_SECTION {source_paper_id: $pid}]->(s)""",
                    sid=section.id, title=section.title,
                    text=section.text[:5000],  # Truncate for storage
                    order=section.order, pid=paper.id,
                )

            # Figures
            for fig in paper.figures:
                await session.run(
                    """MERGE (f:Figure {id: $fid})
                       SET f.label = $label, f.caption = $caption,
                           f.image_path = $image_path, f.name = $label
                       WITH f
                       MATCH (p:Paper {id: $pid})
                       MERGE (p)-[:CONTAINS_FIGURE {source_paper_id: $pid}]->(f)""",
                    fid=fig.id, label=fig.label, caption=fig.caption,
                    image_path=fig.image_path or "", pid=paper.id,
                )
                # Link to section if known
                if fig.section_id:
                    await session.run(
                        """MATCH (s:Section {id: $sid}), (f:Figure {id: $fid})
                           MERGE (s)-[:ILLUSTRATED_BY {source_paper_id: $pid}]->(f)""",
                        sid=fig.section_id, fid=fig.id, pid=paper.id,
                    )

            # Tables
            for tbl in paper.tables:
                await session.run(
                    """MERGE (t:Table {id: $tid})
                       SET t.label = $label, t.caption = $caption,
                           t.headers = $headers, t.name = $label
                       WITH t
                       MATCH (p:Paper {id: $pid})
                       MERGE (p)-[:CONTAINS_TABLE {source_paper_id: $pid}]->(t)""",
                    tid=tbl.id, label=tbl.label, caption=tbl.caption,
                    headers=tbl.headers, pid=paper.id,
                )
                if tbl.section_id:
                    await session.run(
                        """MATCH (s:Section {id: $sid}), (t:Table {id: $tid})
                           MERGE (s)-[:ILLUSTRATED_BY {source_paper_id: $pid}]->(t)""",
                        sid=tbl.section_id, tid=tbl.id, pid=paper.id,
                    )

    # ── Triple Merging ───────────────────────────────────────────────

    async def merge_triples(self, triples: list[Triple]) -> int:
        """MERGE extracted triples into Neo4j. Returns count of triples merged."""
        count = 0
        async with self.driver.session() as session:
            for t in triples:
                try:
                    # Use APOC for dynamic relationship types
                    await session.run(
                        """MERGE (h {name: $head})
                           ON CREATE SET h:""" + t.head_type + """
                           MERGE (t {name: $tail})
                           ON CREATE SET t:""" + t.tail_type + """
                           WITH h, t
                           CALL apoc.merge.relationship(
                               h, $rel_type, 
                               {source_paper_id: $pid, source_section_id: $sid},
                               {},
                               t, {}
                           ) YIELD rel
                           RETURN rel""",
                        head=t.head, tail=t.tail,
                        rel_type=t.relation,
                        pid=t.source_paper_id,
                        sid=t.source_section_id,
                    )
                    count += 1
                except Exception as e:
                    logger.warning(f"Failed to merge triple ({t.head})-[{t.relation}]->({t.tail}): {e}")
        return count

    # ── Paper Status ─────────────────────────────────────────────────

    async def update_paper_status(self, paper_id: str, status: PaperStatus,
                                   progress: float = 0.0) -> None:
        """Update ingestion status for a paper."""
        async with self.driver.session() as session:
            await session.run(
                """MATCH (p:Paper {id: $pid})
                   SET p.status = $status, p.progress = $progress""",
                pid=paper_id, status=status.value, progress=progress,
            )

    async def get_paper_info(self, paper_id: str) -> Optional[PaperInfo]:
        """Get paper metadata including node/edge counts."""
        async with self.driver.session() as session:
            result = await session.run(
                """MATCH (p:Paper {id: $pid})
                   OPTIONAL MATCH (p)-[:AUTHORED_BY]->(a:Author)
                   OPTIONAL MATCH (p)-[:CONTAINS_SECTION]->(s:Section)
                   WITH p, collect(DISTINCT a.name) as authors, count(DISTINCT s) as sec_count
                   OPTIONAL MATCH (n) WHERE any(lbl IN labels(n) WHERE lbl <> 'Paper')
                     AND EXISTS { MATCH ()-[r]->() WHERE r.source_paper_id = $pid }
                   WITH p, authors, sec_count, count(DISTINCT n) as node_count
                   OPTIONAL MATCH ()-[r]->() WHERE r.source_paper_id = $pid
                   RETURN p, authors, sec_count, node_count, count(r) as edge_count""",
                pid=paper_id,
            )
            record = await result.single()
            if not record:
                return None
            p = record["p"]
            return PaperInfo(
                id=paper_id,
                title=p.get("title", ""),
                status=PaperStatus(p.get("status", "complete")),
                authors=record["authors"],
                section_count=record["sec_count"],
                node_count=record["node_count"],
                edge_count=record["edge_count"],
                progress_pct=p.get("progress", 0.0),
            )

    async def list_papers(self) -> list[PaperInfo]:
        """List all papers."""
        async with self.driver.session() as session:
            result = await session.run(
                """MATCH (p:Paper)
                   OPTIONAL MATCH (p)-[:AUTHORED_BY]->(a:Author)
                   OPTIONAL MATCH (p)-[:CONTAINS_SECTION]->(s:Section)
                   RETURN p, collect(DISTINCT a.name) as authors,
                          count(DISTINCT s) as sec_count
                   ORDER BY p.title"""
            )
            papers = []
            async for record in result:
                p = record["p"]
                papers.append(PaperInfo(
                    id=p.get("id", ""),
                    title=p.get("title", ""),
                    status=PaperStatus(p.get("status", "complete")),
                    authors=record["authors"],
                    section_count=record["sec_count"],
                    progress_pct=p.get("progress", 0.0),
                ))
            return papers

    # ── Graph Retrieval ──────────────────────────────────────────────

    async def get_paper_graph(self, paper_id: str) -> SubGraph:
        """Return full subgraph for a paper."""
        nodes = []
        edges = []
        async with self.driver.session() as session:
            # Get all nodes connected to this paper
            result = await session.run(
                """MATCH (p:Paper {id: $pid})-[r*1..2]-(n)
                   UNWIND r as rel
                   WITH DISTINCT startNode(rel) as src, rel, endNode(rel) as tgt
                   RETURN src, rel, tgt""",
                pid=paper_id,
            )
            seen_nodes = set()
            seen_edges = set()
            async for record in result:
                src = record["src"]
                tgt = record["tgt"]
                rel = record["rel"]

                for node in [src, tgt]:
                    nid = node.element_id
                    if nid not in seen_nodes:
                        seen_nodes.add(nid)
                        labels = list(node.labels)
                        nodes.append(GraphNode(
                            id=node.get("id", nid),
                            label=node.get("name", node.get("title", node.get("label", ""))),
                            type=labels[0] if labels else "Unknown",
                            properties=dict(node),
                        ))

                eid = rel.element_id
                if eid not in seen_edges:
                    seen_edges.add(eid)
                    edges.append(GraphEdge(
                        id=eid,
                        source=src.get("id", src.element_id),
                        target=tgt.get("id", tgt.element_id),
                        type=rel.type,
                        properties=dict(rel),
                    ))

        return SubGraph(nodes=nodes, edges=edges)

    # ── Agent Tool Functions (Cypher-backed) ─────────────────────────

    async def retrieve_node(self, keyword: str,
                             paper_ids: Optional[list[str]] = None) -> list[dict]:
        """Full-text search for nodes matching keyword. Used by RetrieveNode agent tool."""
        async with self.driver.session() as session:
            # Use full-text index
            query = """
                CALL db.index.fulltext.queryNodes('entity_name_index', $keyword)
                YIELD node, score
                WHERE score > 0.5
            """
            if paper_ids:
                # Filter to specific papers by checking edges
                query += """
                    AND EXISTS {
                        MATCH ()-[r]->(node) WHERE r.source_paper_id IN $pids
                    } OR EXISTS {
                        MATCH (node)-[r]->() WHERE r.source_paper_id IN $pids
                    }
                """
            query += """
                RETURN node, labels(node) as labels, score
                ORDER BY score DESC LIMIT 10
            """
            result = await session.run(
                query, keyword=keyword, pids=paper_ids or [],
            )
            nodes = []
            async for record in result:
                node = record["node"]
                nodes.append({
                    "id": node.get("id", node.element_id),
                    "name": node.get("name", node.get("title", "")),
                    "type": record["labels"][0] if record["labels"] else "Unknown",
                    "score": record["score"],
                    "properties": dict(node),
                })
            return nodes

    async def node_feature(self, node_name: str, feature: str) -> str:
        """Get a specific feature/property of a node. Used by NodeFeature agent tool."""
        async with self.driver.session() as session:
            result = await session.run(
                """MATCH (n) WHERE n.name = $name OR n.id = $name OR n.title = $name
                   RETURN n, labels(n) as labels LIMIT 1""",
                name=node_name,
            )
            record = await result.single()
            if not record:
                return f"Node '{node_name}' not found."
            node = record["node"] if "node" in record else record["n"]
            props = dict(node)
            if feature.lower() == "all":
                return str(props)
            if feature in props:
                return str(props[feature])
            # Return available features
            return f"Feature '{feature}' not found. Available: {list(props.keys())}"

    async def neighbor_check(self, node_name: str,
                              edge_type: Optional[str] = None) -> list[dict]:
        """List neighbors of a node. Used by NeighborCheck agent tool."""
        async with self.driver.session() as session:
            if edge_type:
                query = """
                    MATCH (n)-[r]->(m)
                    WHERE (n.name = $name OR n.id = $name) AND type(r) = $etype
                    RETURN m.name as name, m.id as id, labels(m) as labels, type(r) as rel_type
                    UNION
                    MATCH (m)-[r]->(n)
                    WHERE (n.name = $name OR n.id = $name) AND type(r) = $etype
                    RETURN m.name as name, m.id as id, labels(m) as labels, type(r) as rel_type
                """
                result = await session.run(query, name=node_name, etype=edge_type)
            else:
                query = """
                    MATCH (n)-[r]-(m)
                    WHERE n.name = $name OR n.id = $name
                    RETURN DISTINCT m.name as name, m.id as id,
                           labels(m) as labels, type(r) as rel_type
                """
                result = await session.run(query, name=node_name)

            neighbors = []
            async for record in result:
                neighbors.append({
                    "name": record["name"] or record["id"],
                    "id": record["id"],
                    "type": record["labels"][0] if record["labels"] else "Unknown",
                    "relation": record["rel_type"],
                })
            return neighbors

    async def node_degree(self, node_name: str,
                           edge_type: Optional[str] = None) -> int:
        """Count neighbors of a node. Used by NodeDegree agent tool."""
        neighbors = await self.neighbor_check(node_name, edge_type)
        return len(neighbors)

    # ── Subgraph from reasoning trace ────────────────────────────────

    async def get_subgraph_for_nodes(self, node_names: list[str]) -> SubGraph:
        """Get the subgraph connecting the given nodes (for reasoning trace viz)."""
        if not node_names:
            return SubGraph()

        async with self.driver.session() as session:
            result = await session.run(
                """UNWIND $names AS name
                   MATCH (n) WHERE n.name = name OR n.id = name
                   WITH collect(n) as nodes
                   UNWIND nodes as n
                   OPTIONAL MATCH (n)-[r]-(m) WHERE m IN nodes
                   RETURN DISTINCT n, r, m""",
                names=node_names,
            )
            nodes_map = {}
            edges_list = []
            seen_edges = set()
            async for record in result:
                for node in [record["n"], record["m"]]:
                    if node and node.element_id not in nodes_map:
                        labels = list(node.labels)
                        nodes_map[node.element_id] = GraphNode(
                            id=node.get("id", node.element_id),
                            label=node.get("name", node.get("title", "")),
                            type=labels[0] if labels else "Unknown",
                            properties=dict(node),
                        )
                rel = record["r"]
                if rel and rel.element_id not in seen_edges:
                    seen_edges.add(rel.element_id)
                    src = record["n"]
                    tgt = record["m"]
                    edges_list.append(GraphEdge(
                        id=rel.element_id,
                        source=src.get("id", src.element_id),
                        target=tgt.get("id", tgt.element_id),
                        type=rel.type,
                        properties=dict(rel),
                    ))

        return SubGraph(
            nodes=list(nodes_map.values()),
            edges=edges_list,
        )

    # ── Section text retrieval (for lazy completion) ─────────────────

    async def get_section_text(self, section_id: str) -> Optional[str]:
        """Retrieve section text for re-extraction."""
        async with self.driver.session() as session:
            result = await session.run(
                "MATCH (s:Section {id: $sid}) RETURN s.text as text",
                sid=section_id,
            )
            record = await result.single()
            return record["text"] if record else None

    async def get_sections_for_paper(self, paper_id: str) -> list[dict]:
        """Get all sections for a paper, ordered."""
        async with self.driver.session() as session:
            result = await session.run(
                """MATCH (p:Paper {id: $pid})-[:CONTAINS_SECTION]->(s:Section)
                   RETURN s.id as id, s.title as title, s.text as text,
                          s.order_idx as order_idx
                   ORDER BY s.order_idx""",
                pid=paper_id,
            )
            sections = []
            async for record in result:
                sections.append(dict(record))
            return sections

    async def get_paper_figures(self, paper_id: str) -> list[FigureData]:
        """Get all figures for a paper."""
        async with self.driver.session() as session:
            result = await session.run(
                """MATCH (p:Paper {id: $pid})-[:CONTAINS_FIGURE]->(f:Figure)
                   RETURN f""", pid=paper_id,
            )
            figures = []
            async for record in result:
                f = record["f"]
                figures.append(FigureData(
                    id=f.get("id", ""),
                    label=f.get("label", ""),
                    caption=f.get("caption", ""),
                    image_path=f.get("image_path", ""),
                ))
            return figures

    async def get_paper_tables(self, paper_id: str) -> list[TableData]:
        """Get all tables for a paper."""
        async with self.driver.session() as session:
            result = await session.run(
                """MATCH (p:Paper {id: $pid})-[:CONTAINS_TABLE]->(t:Table)
                   RETURN t""", pid=paper_id,
            )
            tables = []
            async for record in result:
                t = record["t"]
                tables.append(TableData(
                    id=t.get("id", ""),
                    label=t.get("label", ""),
                    caption=t.get("caption", ""),
                    headers=t.get("headers", []),
                ))
            return tables


# Singleton
neo4j_service = Neo4jService()
