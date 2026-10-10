"""Embedding service — MiniLM entity resolution and SAME_AS cross-paper linking.

Uses sentence-transformers all-MiniLM-L6-v2 on CPU.
After each paper ingestion, embeds Concept/Method/Dataset node names
and creates SAME_AS edges for cross-paper matches above a cosine threshold.
"""

import logging
import numpy as np
from typing import Optional
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from app.config import settings
from app.schema_profiles import norm_name

logger = logging.getLogger(__name__)


class EmbeddingService:
    """CPU-only embedding service for entity resolution."""

    def __init__(self):
        self.model: Optional[SentenceTransformer] = None

    def load_model(self):
        """Load the embedding model (CPU only, ~90MB)."""
        logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
        self.model = SentenceTransformer(
            settings.EMBEDDING_MODEL,
            device="cpu",
        )
        logger.info("Embedding model loaded")

    def embed(self, texts: list[str]) -> np.ndarray:
        """Embed a list of texts. Returns (N, dim) array."""
        if not self.model:
            self.load_model()
        return self.model.encode(texts, show_progress_bar=False, convert_to_numpy=True)

    async def link_cross_paper_entities(self, paper_id: str,
                                        config_id: str = settings.CONFIG_ID,
                                        threshold: float | None = None) -> int:
        """Create SAME_AS edges between similar concepts across papers within the same config_id.
        
        Returns count of new SAME_AS edges created.
        """
        if not settings.ENABLE_SAME_AS:
            logger.info("SAME_AS linking disabled by ENABLE_SAME_AS setting")
            return 0

        cid = config_id if config_id is not None else settings.CONFIG_ID
        from app.services.neo4j_client import neo4j_service

        # Get all concept-like nodes from the new paper for this config_id
        new_nodes = await self._get_entity_nodes(paper_id, cid)
        if not new_nodes:
            return 0

        # Get concept-like nodes from OTHER papers for this config_id
        other_nodes = await self._get_other_entity_nodes(paper_id, cid)
        if not other_nodes:
            return 0

        # Embed both sets
        new_names = [n["name"] for n in new_nodes]
        other_names = [n["name"] for n in other_nodes]

        new_embeddings = self.embed(new_names)
        other_embeddings = self.embed(other_names)

        # Compute cosine similarity matrix
        sim_matrix = cosine_similarity(new_embeddings, other_embeddings)

        # Create SAME_AS edges above threshold
        thresh = threshold if threshold is not None else settings.SAME_AS_THRESHOLD
        link_count = 0

        async with neo4j_service.driver.session() as session:
            for i, new_node in enumerate(new_nodes):
                for j, other_node in enumerate(other_nodes):
                    if sim_matrix[i, j] >= thresh:
                        # Avoid self-links and exact duplicates
                        if new_node["name"].lower() == other_node["name"].lower():
                            sim = 1.0
                        else:
                            sim = float(sim_matrix[i, j])

                        try:
                            await session.run(
                                """MATCH (a:Entity {norm_name: $na, config_id: $cid}),
                                         (b:Entity {norm_name: $nb, config_id: $cid})
                                   WHERE a <> b
                                   MERGE (a)-[:SAME_AS {
                                       similarity: $sim,
                                       source_paper_id: $pid,
                                       config_id: $cid
                                   }]->(b)""",
                                na=new_node["norm_name"],
                                nb=other_node["norm_name"],
                                sim=sim,
                                pid=paper_id,
                                cid=cid,
                            )
                            link_count += 1
                        except Exception as e:
                            logger.debug(f"SAME_AS link failed: {e}")

        logger.info(
            f"Cross-paper linking for {paper_id} (config_id={cid}): "
            f"{link_count} SAME_AS edges created "
            f"(threshold={threshold})"
        )
        return link_count

    async def _get_entity_nodes(self, paper_id: str, config_id: str) -> list[dict]:
        """Get Concept/Method/Dataset nodes for a specific paper scoped to config_id."""
        from app.services.neo4j_client import neo4j_service
        async with neo4j_service.driver.session() as session:
            result = await session.run(
                """MATCH (n:Entity)
                   WHERE (n:Concept OR n:Method OR n:Dataset)
                     AND coalesce(n.config_id, 'default') = $cid
                     AND (
                         EXISTS {
                             MATCH ()-[r]->(n)
                             WHERE r.source_paper_id = $pid
                               AND coalesce(r.config_id, 'default') = $cid
                         } OR EXISTS {
                             MATCH (n)-[r]->()
                             WHERE r.source_paper_id = $pid
                               AND coalesce(r.config_id, 'default') = $cid
                         }
                     )
                   RETURN DISTINCT n.name as name, n.norm_name as norm_name, labels(n) as labels""",
                pid=paper_id,
                cid=config_id,
            )
            nodes = []
            async for record in result:
                raw_name = record["name"]
                if raw_name:
                    n_norm = record["norm_name"] or norm_name(raw_name)
                    nodes.append({
                        "name": raw_name,
                        "norm_name": n_norm,
                        "labels": record["labels"],
                    })
            return nodes

    async def _get_other_entity_nodes(self, paper_id: str, config_id: str) -> list[dict]:
        """Get Concept/Method/Dataset nodes from other papers scoped to config_id."""
        from app.services.neo4j_client import neo4j_service
        async with neo4j_service.driver.session() as session:
            result = await session.run(
                """MATCH (n:Entity)
                   WHERE (n:Concept OR n:Method OR n:Dataset)
                     AND coalesce(n.config_id, 'default') = $cid
                     AND (
                         EXISTS {
                             MATCH ()-[r]->(n)
                             WHERE r.source_paper_id <> $pid
                               AND coalesce(r.config_id, 'default') = $cid
                         } OR EXISTS {
                             MATCH (n)-[r]->()
                             WHERE r.source_paper_id <> $pid
                               AND coalesce(r.config_id, 'default') = $cid
                         }
                     )
                   RETURN DISTINCT n.name as name, n.norm_name as norm_name, labels(n) as labels""",
                pid=paper_id,
                cid=config_id,
            )
            nodes = []
            async for record in result:
                raw_name = record["name"]
                if raw_name:
                    n_norm = record["norm_name"] or norm_name(raw_name)
                    nodes.append({
                        "name": raw_name,
                        "norm_name": n_norm,
                        "labels": record["labels"],
                    })
            return nodes


# Singleton
embedding_service = EmbeddingService()
