import asyncio
import traceback
from app.services.neo4j_client import neo4j_service

async def test():
    try:
        await neo4j_service.connect()
        papers = await neo4j_service.list_papers()
        print("Success:", papers)
    except Exception as e:
        traceback.print_exc()
    finally:
        await neo4j_service.close()

if __name__ == "__main__":
    asyncio.run(test())
