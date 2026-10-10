import pytest
import asyncio
from app.services.neo4j_client import neo4j_service


def test_delete_config_refuses_default():
    with pytest.raises(ValueError, match="protected or empty"):
        asyncio.run(neo4j_service.delete_config("default"))


def test_delete_config_refuses_empty():
    with pytest.raises(ValueError, match="protected or empty"):
        asyncio.run(neo4j_service.delete_config(""))
