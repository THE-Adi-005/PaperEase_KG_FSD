"""Demo endpoints for seeding data and preset questions."""

from fastapi import APIRouter
from app.services.demo_seeder import seed_demo_data

router = APIRouter()

@router.post("/seed")
async def seed_demo():
    """Seed Neo4j with 3 demo papers and their KG."""
    paper_ids = await seed_demo_data()
    return {"status": "success", "paper_ids": paper_ids, "message": "3 papers injected into Neo4j."}

@router.get("/questions")
async def get_demo_questions():
    """Return a list of curated questions that highlight KG advantages."""
    return [
        {
            "id": 1,
            "text": "What F1 score did BERT achieve on SQuAD?",
            "highlights": "Precise Retrieval",
            "mode": "single",
        },
        {
            "id": 2,
            "text": "What datasets were used across all these papers?",
            "highlights": "Multi-hop reasoning",
            "mode": "compare",
        },
        {
            "id": 3,
            "text": "How does BERT extend the Transformer architecture compared to GPT-3?",
            "highlights": "Relationship traversal",
            "mode": "compare",
        }
    ]

@router.get("/stats")
async def get_demo_stats():
    """Get live graph stats (nodes, edges, papers)."""
    from app.services.neo4j_client import neo4j_service
    
    async with neo4j_service.driver.session() as session:
        # Get counts
        node_result = await session.run("MATCH (n) RETURN count(n) as count")
        node_record = await node_result.single()
        node_count = node_record["count"] if node_record else 0
        
        edge_result = await session.run("MATCH ()-[r]->() RETURN count(r) as count")
        edge_record = await edge_result.single()
        edge_count = edge_record["count"] if edge_record else 0
        
        paper_result = await session.run("MATCH (p:Paper) RETURN count(p) as count")
        paper_record = await paper_result.single()
        paper_count = paper_record["count"] if paper_record else 0
        
    return {
        "nodes": node_count,
        "edges": edge_count,
        "papers": paper_count
    }
