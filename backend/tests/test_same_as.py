import asyncio
from app.services.embeddings import EmbeddingService
from app.config import settings


def test_same_as_disabled_returns_zero(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_SAME_AS", False)
    svc = EmbeddingService()
    res = asyncio.run(svc.link_cross_paper_entities("paper_123", config_id="test_cfg"))
    assert res == 0


def test_same_as_settings_defaults():
    assert settings.ENABLE_SAME_AS is True
    assert settings.CONFIG_ID == "default"
