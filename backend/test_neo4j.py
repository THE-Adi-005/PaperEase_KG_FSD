import asyncio
import traceback
from app.services.neo4j_client import neo4j_service

async def _test():
    try:
        await neo4j_service.connect()
        papers = await neo4j_service.list_papers()
        print("Success:", papers)
    except Exception as e:
        traceback.print_exc()
    finally:
        await neo4j_service.close()

def test_neo4j_connection():
    asyncio.run(_test())

if __name__ == "__main__":
    asyncio.run(_test())
