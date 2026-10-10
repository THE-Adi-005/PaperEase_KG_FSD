import pytest
from app.config import settings
from app.schema_profiles import PROFILES, ENTITY_TYPES
from app.services.kg_builder import _is_triple_valid, sanitize_type
from app.models.neo4j_schema import RELATION_TYPES


def test_unknown_type_becomes_concept():
    # Valid types in ENTITY_TYPES whitelist stay unchanged
    for et in ENTITY_TYPES:
        assert sanitize_type(et) == et

    # Types outside ENTITY_TYPES (like Paper, Section, or arbitrary strings) become Concept
    assert sanitize_type("Paper") == "Concept"
    assert sanitize_type("Section") == "Concept"
    assert sanitize_type("UnknownEntity") == "Concept"
    assert sanitize_type("") == "Concept"


def test_dynamic_relation_rejected_when_not_allowed(monkeypatch):
    r3 = PROFILES["R3"]
    # COMPARES_TO is in RELATION_TYPES but NOT in R3.llm_relations
    assert "COMPARES_TO" in RELATION_TYPES
    assert "COMPARES_TO" not in r3.llm_relations

    # When ALLOW_DYNAMIC_RELATIONS=False, it must be rejected even if in RELATION_TYPES
    monkeypatch.setattr(settings, "ALLOW_DYNAMIC_RELATIONS", False)
    assert not _is_triple_valid("COMPARES_TO", "Method", "Method", r3)

    # When ALLOW_DYNAMIC_RELATIONS=True, it is accepted
    monkeypatch.setattr(settings, "ALLOW_DYNAMIC_RELATIONS", True)
    assert _is_triple_valid("COMPARES_TO", "Method", "Method", r3)


def test_signature_rejection_only_when_enforced(monkeypatch):
    r7 = PROFILES["R7"]
    # ACHIEVES has signature [("Method", "Metric")]
    # ("Dataset", "Dataset") violates this signature

    # When ENFORCE_TYPE_SIGNATURES=False, invalid signature is accepted
    monkeypatch.setattr(settings, "ENFORCE_TYPE_SIGNATURES", False)
    assert _is_triple_valid("ACHIEVES", "Dataset", "Dataset", r7)

    # When ENFORCE_TYPE_SIGNATURES=True, invalid signature is rejected
    monkeypatch.setattr(settings, "ENFORCE_TYPE_SIGNATURES", True)
    assert not _is_triple_valid("ACHIEVES", "Dataset", "Dataset", r7)
    # Valid signature passes
    assert _is_triple_valid("ACHIEVES", "Method", "Metric", r7)
