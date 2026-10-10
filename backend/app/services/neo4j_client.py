"""Neo4j async client — MERGE operations, agent tool queries, schema setup.

Uses the official neo4j async driver. All Cypher queries are parameterized.
Every semantic edge carries source_paper_id, source_section_id, config_id,
and confidence for provenance and ablation isolation.
Entity nodes are MERGED on (norm_name, config_id) with a shared :Entity base
label so the Entity(norm_name, config_id) composite index is used.
"""

from neo4j import AsyncGraphDatabase, AsyncDriver
import logging
import json
import re
from typing import Optional

from app.config import settings
from app.models.schemas import (
    Triple, ParsedPaper, GraphNode, GraphEdge, SubGraph,
    PaperInfo, PaperStatus, FigureData, TableData,
)
from app.models.neo4j_schema import SETUP_QUERIES, GRAPH_STATS_EXCLUDE_RELATIONS
from app.schema_profiles import norm_name as _norm
from app.triple_filters import graph_metrics

logger = logging.getLogger(__name__)


def _parse_metric_tail(tail: str) -> dict:
    """Parse a metric tail string into structured properties.

    Examples::

        _parse_metric_tail("F1=92.4")          -> {metric_name: 'F1',   value: 92.4,  is_percent: False}
        _parse_metric_tail("accuracy=88.1%")   -> {metric_name: 'acc.', value: 88.1,  is_percent: True}
        _parse_metric_tail("BLEU")             -> {metric_name: 'BLEU', value: None,  is_percent: False}

    Name is kept unchanged; value is parsed as float without rescaling.
    """
    m = re.match(r'^(.+?)=(.+)$', tail.strip())
    if m:
        metric_name = m.group(1).strip()
        value_str = m.group(2).strip()
        is_percent = value_str.endswith('%')
        if is_percent:
            value_str = value_str[:-1].strip()
        try:
            value = float(value_str)
            return {'metric_name': metric_name, 'value': value, 'is_percent': is_percent}
        except ValueError:
            pass
    return {'metric_name': tail, 'value': None, 'is_percent': False}


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

        # APOC startup check (required for merge_triples)
        async with self.driver.session() as session:
            try:
                result = await session.run("RETURN apoc.version() AS ver")
                rec = await result.single()
                logger.info(f"APOC version: {rec['ver']}")
            except Exception as e:
                logger.warning(
                    f"APOC not detected: {e}. "
                    "merge_triples will fail without APOC. "
                    "Ensure NEO4J_PLUGINS=[\"apoc\"] in docker-compose."
                )

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
                rows_json = json.dumps(tbl.rows or [])
                await session.run(
                    """MERGE (t:Table {id: $tid})
                       SET t.label = $label, t.caption = $caption,
                           t.headers = $headers, t.rows = $rows_json, t.name = $label
                       WITH t
                       MATCH (p:Paper {id: $pid})
                       MERGE (p)-[:CONTAINS_TABLE {source_paper_id: $pid}]->(t)""",
                    tid=tbl.id, label=tbl.label, caption=tbl.caption,
                    headers=tbl.headers, rows_json=rows_json, pid=paper.id,
                )
                if tbl.section_id:
                    await session.run(
                        """MATCH (s:Section {id: $sid}), (t:Table {id: $tid})
                           MERGE (s)-[:ILLUSTRATED_BY {source_paper_id: $pid}]->(t)""",
                        sid=tbl.section_id, tid=tbl.id, pid=paper.id,
                    )

    # ── Triple Merging ───────────────────────────────────────────────

    async def merge_triples(self, triples: list[Triple],
                             config_id: str = "default") -> int:
        """MERGE extracted triples into Neo4j. Returns count of triples merged.

        Entity nodes are keyed on (norm_name, config_id) using the :Entity base
        label so the composite index is hit. Type-specific labels (e.g. :Method)
        are added on every merge — not only on creation — via APOC so a node
        can accumulate labels if different extractions disagree on type.
        Confidence is written to the edge on creation.
        Metric tail nodes get extra metric_name / value / is_percent properties.
        """
        count = 0
        async with self.driver.session() as session:
            for t in triples:
                head_norm = _norm(t.head)
                tail_norm = _norm(t.tail)

                # Parse metric properties for Metric tail nodes
                if t.tail_type == "Metric":
                    mp = _parse_metric_tail(t.tail)
                else:
                    mp = {"metric_name": None, "value": None, "is_percent": None}

                try:
                    await session.run(
                        """
                        // ── Head node: MERGE on (norm_name, config_id) ──
                        MERGE (h:Entity {norm_name: $head_norm, config_id: $cid})
                        ON CREATE SET h.name = $head,
                                      h.norm_name = $head_norm,
                                      h.config_id = $cid
                        WITH h
                        CALL apoc.create.addLabels(h, [$head_type]) YIELD node AS h_node

                        // ── Tail node: MERGE on (norm_name, config_id) ──
                        MERGE (t:Entity {norm_name: $tail_norm, config_id: $cid})
                        ON CREATE SET t.name = $tail,
                                      t.norm_name = $tail_norm,
                                      t.config_id = $cid,
                                      t.metric_name = $metric_name,
                                      t.value = $metric_value,
                                      t.is_percent = $is_percent
                        ON MATCH SET
                            t.metric_name = CASE WHEN t.metric_name IS NULL
                                                 THEN $metric_name ELSE t.metric_name END,
                            t.value       = CASE WHEN t.value IS NULL
                                                 THEN $metric_value ELSE t.value END,
                            t.is_percent  = CASE WHEN t.is_percent IS NULL
                                                 THEN $is_percent  ELSE t.is_percent  END
                        WITH h_node, t
                        CALL apoc.create.addLabels(t, [$tail_type]) YIELD node AS t_node

                        // ── Semantic edge with provenance + confidence ──
                        WITH h_node, t_node
                        CALL apoc.merge.relationship(
                            h_node, $rel_type,
                            {source_paper_id: $pid, source_section_id: $sid,
                             config_id: $cid},
                            {confidence: $confidence},
                            t_node, {}
                        ) YIELD rel
                        RETURN rel
                        """,
                        head=t.head,
                        head_norm=head_norm,
                        head_type=t.head_type,
                        tail=t.tail,
                        tail_norm=tail_norm,
                        tail_type=t.tail_type,
                        rel_type=t.relation,
                        pid=t.source_paper_id,
                        sid=t.source_section_id,
                        cid=config_id,
                        confidence=t.confidence,
                        metric_name=mp["metric_name"],
                        metric_value=mp["value"],
                        is_percent=mp["is_percent"],
                    )
                    count += 1
                except Exception as e:
                    logger.warning(
                        f"Failed to merge triple "
                        f"({t.head})-[{t.relation}]->({t.tail}): {e}"
                    )
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
                             paper_ids: Optional[list[str]] = None,
                             config_id: Optional[str] = None) -> list[dict]:
        """Full-text search for nodes matching keyword. Used by RetrieveNode agent tool."""
        async with self.driver.session() as session:
            # Use full-text index
            query = """
                CALL db.index.fulltext.queryNodes('entity_name_index', $keyword)
                YIELD node, score
                WHERE score > 0.5
                  AND (NOT 'Entity' IN labels(node) OR $cid IS NULL OR coalesce(node.config_id, 'default') = $cid)
            """
            if paper_ids:
                # Filter to specific papers by checking edges
                query += """
                    AND (
                        EXISTS {
                            MATCH ()-[r]->(node)
                            WHERE r.source_paper_id IN $pids
                              AND ($cid IS NULL OR coalesce(r.config_id, 'default') = $cid)
                        } OR EXISTS {
                            MATCH (node)-[r]->()
                            WHERE r.source_paper_id IN $pids
                              AND ($cid IS NULL OR coalesce(r.config_id, 'default') = $cid)
                        }
                    )
                """
            query += """
                RETURN node, labels(node) as labels, score
                ORDER BY score DESC LIMIT 10
            """
            result = await session.run(
                query, keyword=keyword, pids=paper_ids or [], cid=config_id,
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

    async def node_feature(self, node_name: str, feature: str,
                           config_id: Optional[str] = None) -> str:
        """Get a specific feature/property of a node. Used by NodeFeature agent tool."""
        async with self.driver.session() as session:
            norm = _norm(node_name)
            result = await session.run(
                """MATCH (n)
                   WHERE (n.name = $name OR n.id = $name OR n.title = $name OR n.norm_name = $norm)
                     AND (NOT 'Entity' IN labels(n) OR $cid IS NULL OR coalesce(n.config_id, 'default') = $cid)
                   RETURN n, labels(n) as labels LIMIT 1""",
                name=node_name, norm=norm, cid=config_id,
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
                              edge_type: Optional[str] = None,
                              paper_ids: Optional[list[str]] = None,
                              config_id: Optional[str] = None) -> list[dict]:
        """List neighbors of a node. Used by NeighborCheck agent tool.

        Optional filters:
          paper_ids  — restrict to edges whose source_paper_id is in this list
          config_id  — restrict to edges whose config_id matches (or is missing,
                       treated as 'default' via coalesce)
        """
        async with self.driver.session() as session:
            query = """
                MATCH (n)-[r]->(m)
                WHERE (n.name = $name OR n.id = $name OR n.norm_name = $norm_name)
                  AND ($etype IS NULL OR type(r) = $etype)
                  AND ($pids IS NULL OR r.source_paper_id IN $pids)
                  AND ($cid IS NULL OR coalesce(r.config_id, 'default') = $cid)
                OPTIONAL MATCH (p:Paper {id: r.source_paper_id})
                RETURN m.name as name, m.id as id, labels(m)[0] as type,
                       type(r) as rel_type,
                       coalesce(p.title, r.source_paper_id, 'Shared') as source_paper
                UNION
                MATCH (m)-[r]->(n)
                WHERE (n.name = $name OR n.id = $name OR n.norm_name = $norm_name)
                  AND ($etype IS NULL OR type(r) = $etype)
                  AND ($pids IS NULL OR r.source_paper_id IN $pids)
                  AND ($cid IS NULL OR coalesce(r.config_id, 'default') = $cid)
                OPTIONAL MATCH (p:Paper {id: r.source_paper_id})
                RETURN m.name as name, m.id as id, labels(m)[0] as type,
                       type(r) as rel_type,
                       coalesce(p.title, r.source_paper_id, 'Shared') as source_paper
                LIMIT 25
            """
            norm = _norm(node_name)
            result = await session.run(
                query,
                name=node_name,
                norm_name=norm,
                etype=edge_type,
                pids=paper_ids,
                cid=config_id,
            )
            neighbors = []
            async for record in result:
                neighbors.append({
                    "name": record["name"] or record["id"],
                    "id": record["id"],
                    "type": record["type"] or "Unknown",
                    "relation": record["rel_type"],
                    "source_paper": record["source_paper"] or "Shared",
                })
            return neighbors

    async def node_degree(self, node_name: str,
                           edge_type: Optional[str] = None,
                           paper_ids: Optional[list[str]] = None,
                           config_id: Optional[str] = None) -> int:
        """Count neighbors of a node. Used by NodeDegree agent tool."""
        neighbors = await self.neighbor_check(
            node_name, edge_type, paper_ids=paper_ids, config_id=config_id
        )
        return len(neighbors)

    # ── Subgraph from reasoning trace ────────────────────────────────

    async def get_subgraph_for_nodes(self, node_names: list[str],
                                     config_id: Optional[str] = None) -> SubGraph:
        """Get the subgraph connecting the given nodes (for reasoning trace viz)."""
        if not node_names:
            return SubGraph()

        async with self.driver.session() as session:
            result = await session.run(
                """UNWIND $names AS name
                   MATCH (n)
                   WHERE (n.name = name OR n.id = name OR n.norm_name = toLower(trim(name)))
                     AND (NOT 'Entity' IN labels(n) OR $cid IS NULL OR coalesce(n.config_id, 'default') = $cid)
                   WITH collect(n) as nodes
                   UNWIND nodes as n
                   OPTIONAL MATCH (n)-[r]-(m)
                   WHERE m IN nodes
                     AND ($cid IS NULL OR coalesce(r.config_id, 'default') = $cid)
                   RETURN DISTINCT n, r, m""",
                names=node_names, cid=config_id,
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

    async def inspect_section(self, paper_keyword: str, topic_keyword: str) -> str:
        """Fetch matching section text for deep factual grounding."""
        async with self.driver.session() as session:
            result = await session.run(
                """MATCH (p:Paper)-[:CONTAINS_SECTION]->(s:Section)
                   WHERE (toLower(p.title) CONTAINS toLower($pkw) OR toLower(p.id) CONTAINS toLower($pkw))
                     AND (toLower(s.title) CONTAINS toLower($tkw) OR toLower(s.text) CONTAINS toLower($tkw))
                   RETURN p.title as paper, s.title as section, s.text as text
                   LIMIT 1""",
                pkw=paper_keyword, tkw=topic_keyword,
            )
            record = await result.single()
            if record:
                snippet = record["text"][:1000].replace('\n', ' ')
                return f"[{record['paper']} - Section: {record['section']}]:\n\"{snippet}...\""
            return f"No section found matching paper '{paper_keyword}' with topic '{topic_keyword}'."

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
                rows_raw = t.get("rows", "[]")
                try:
                    rows = json.loads(rows_raw) if isinstance(rows_raw, str) else (rows_raw or [])
                except Exception:
                    rows = []
                tables.append(TableData(
                    id=t.get("id", ""),
                    label=t.get("label", ""),
                    caption=t.get("caption", ""),
                    headers=t.get("headers", []),
                    rows=rows,
                ))
            return tables

    async def get_semantic_graph_stats(
        self,
        paper_id: Optional[str] = None,
        config_id: Optional[str] = None,
    ) -> dict:
        """Return graph topology stats for semantic entities and edges only.

        Excludes structural relations (AUTHORED_BY, CONTAINS_SECTION, CONTAINS_FIGURE,
        CONTAINS_TABLE, ILLUSTRATED_BY) and SAME_AS from total_edges and relation_type_counts.
        SAME_AS stays only in same_as_edges.
        Filters by paper_id and/or config_id if provided.
        """
        async with self.driver.session() as session:
            # Semantic nodes count (either incoming or outgoing edge from paper_id)
            node_query = """
                MATCH (n:Entity)
                WHERE ($cid IS NULL OR coalesce(n.config_id, 'default') = $cid)
            """
            if paper_id:
                node_query += """
                    AND (
                        EXISTS {
                            MATCH ()-[r]->(n)
                            WHERE r.source_paper_id = $pid
                              AND ($cid IS NULL OR coalesce(r.config_id, 'default') = $cid)
                        } OR EXISTS {
                            MATCH (n)-[r]->()
                            WHERE r.source_paper_id = $pid
                              AND ($cid IS NULL OR coalesce(r.config_id, 'default') = $cid)
                        }
                    )
                """
            node_query += " RETURN count(DISTINCT n) as count"
            res = await session.run(node_query, cid=config_id, pid=paper_id)
            rec = await res.single()
            total_nodes = rec["count"] if rec else 0

            # Semantic edges count (exclude structural list AND SAME_AS)
            exclude_list = list(GRAPH_STATS_EXCLUDE_RELATIONS | {"SAME_AS"})
            edge_query = """
                MATCH (h:Entity)-[r]->(t:Entity)
                WHERE NOT type(r) IN $exclude
                  AND ($cid IS NULL OR coalesce(r.config_id, 'default') = $cid)
                  AND ($pid IS NULL OR r.source_paper_id = $pid)
                RETURN count(r) as count
            """
            res = await session.run(edge_query, exclude=exclude_list, cid=config_id, pid=paper_id)
            rec = await res.single()
            total_edges = rec["count"] if rec else 0

            # Node counts by semantic label
            node_type_query = """
                MATCH (n:Entity)
                WHERE ($cid IS NULL OR coalesce(n.config_id, 'default') = $cid)
            """
            if paper_id:
                node_type_query += """
                    AND (
                        EXISTS {
                            MATCH ()-[r]->(n)
                            WHERE r.source_paper_id = $pid
                              AND ($cid IS NULL OR coalesce(r.config_id, 'default') = $cid)
                        } OR EXISTS {
                            MATCH (n)-[r]->()
                            WHERE r.source_paper_id = $pid
                              AND ($cid IS NULL OR coalesce(r.config_id, 'default') = $cid)
                        }
                    )
                """
            node_type_query += """
                UNWIND [lbl IN labels(n) WHERE lbl <> 'Entity'] as lbl
                RETURN lbl, count(DISTINCT n) as count ORDER BY count DESC
            """
            res = await session.run(node_type_query, cid=config_id, pid=paper_id)
            node_type_counts = {}
            async for record in res:
                node_type_counts[record["lbl"]] = record["count"]

            # Relation counts (exclude structural list AND SAME_AS)
            rel_query = """
                MATCH (h:Entity)-[r]->(t:Entity)
                WHERE NOT type(r) IN $exclude
                  AND ($cid IS NULL OR coalesce(r.config_id, 'default') = $cid)
                  AND ($pid IS NULL OR r.source_paper_id = $pid)
                RETURN type(r) as rel, count(r) as count ORDER BY count DESC
            """
            res = await session.run(rel_query, exclude=exclude_list, cid=config_id, pid=paper_id)
            relation_type_counts = {}
            async for record in res:
                relation_type_counts[record["rel"]] = record["count"]

            # SAME_AS edges count
            same_as_query = """
                MATCH ()-[r:SAME_AS]->()
                WHERE ($cid IS NULL OR coalesce(r.config_id, 'default') = $cid)
                  AND ($pid IS NULL OR r.source_paper_id = $pid)
                RETURN count(r) as count
            """
            res = await session.run(same_as_query, cid=config_id, pid=paper_id)
            rec = await res.single()
            same_as_edges = rec["count"] if rec else 0

            avg_degree, graph_density = graph_metrics(total_nodes, total_edges)

            return {
                "total_nodes": total_nodes,
                "total_edges": total_edges,
                "avg_degree": avg_degree,
                "node_type_counts": node_type_counts,
                "relation_type_counts": relation_type_counts,
                "same_as_edges": same_as_edges,
                "graph_density": graph_density,
            }


# Singleton
neo4j_service = Neo4jService()

