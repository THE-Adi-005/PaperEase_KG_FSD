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


def test_self_consistency_filter_n1_applies_validity_rules(monkeypatch):
    from app.services.kg_builder import _self_consistency_filter
    monkeypatch.setattr(settings, "SCHEMA_PROFILE", "R3")
    monkeypatch.setattr(settings, "ALLOW_DYNAMIC_RELATIONS", False)

    # Run with N=1 containing an invalid dynamic relation not in R3
    raw_triples = [
        {"head": "BERT", "head_type": "Paper", "relation": "COMPARES_TO", "tail": "RoBERTa", "tail_type": "Paper"},
        {"head": "BERT", "head_type": "Paper", "relation": "USES_METHOD", "tail": "Attention", "tail_type": "InvalidType"},
    ]
    # For N=1
    res1 = _self_consistency_filter([raw_triples], paper_id="p1", section_id="s1", num_runs=1)
    # COMPARES_TO should be rejected by ALLOW_DYNAMIC_RELATIONS=False
    assert len(res1) == 1
    assert res1[0].relation == "USES_METHOD"
    # Types should be sanitized from "Paper" and "InvalidType" to "Concept"
    assert res1[0].head_type == "Concept"
    assert res1[0].tail_type == "Concept"
    assert res1[0].confidence == 1.0

    # For N=2 with identical raw_triples
    res2 = _self_consistency_filter([raw_triples, raw_triples], paper_id="p1", section_id="s1", num_runs=2)
    assert len(res2) == 1
    assert res2[0].relation == res1[0].relation
    assert res2[0].head_type == res1[0].head_type
    assert res2[0].tail_type == res1[0].tail_type

