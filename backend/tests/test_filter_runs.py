import pytest
from app.config import settings
from app.triple_filters import is_generic
from app.schema_profiles import PROFILES, get_active_profile
from app.services.kg_builder import filter_runs, _self_consistency_filter


@pytest.fixture
def three_runs():
    t_3v = {"head": "BERT", "head_type": "Method", "relation": "USES_METHOD", "tail": "Transformer", "tail_type": "Concept"}
    t_2v = {"head": "ResNet", "head_type": "Method", "relation": "ACHIEVES", "tail": "Accuracy", "tail_type": "Metric"}
    t_1v = {"head": "GPT", "head_type": "Method", "relation": "DISCUSSES_CONCEPT", "tail": "Attention", "tail_type": "Concept"}
    t_dyn = {"head": "ModelA", "head_type": "Method", "relation": "CUSTOM_DYNAMIC_REL", "tail": "ModelB", "tail_type": "Concept"}

    run1 = [t_3v, t_2v, t_1v, t_dyn]
    run2 = [t_3v, t_2v, t_dyn]
    run3 = [t_3v, t_dyn]
    return [run1, run2, run3]


def test_wrapper_equals_filter_runs_default(three_runs):
    wrapper_res = _self_consistency_filter(three_runs, "p1", "s1")
    direct_res = filter_runs(
        three_runs,
        "p1",
        "s1",
        vote_fraction=settings.VOTE_FRACTION,
        profile=get_active_profile(),
        allow_dynamic=settings.ALLOW_DYNAMIC_RELATIONS,
        enforce_signatures=settings.ENFORCE_TYPE_SIGNATURES,
        cap=settings.MAX_TRIPLES_PER_SECTION,
    )
    assert wrapper_res == direct_res


def test_vote_fraction_thresholds(three_runs):
    profile = PROFILES["R7"]
    # vote_fraction 0.0 -> min_votes 1 (keeps all 4: 1, 2, and 3 votes)
    res_00 = filter_runs(
        three_runs, "p1", "s1",
        vote_fraction=0.0, profile=profile,
        allow_dynamic=True, enforce_signatures=False, cap=0
    )
    assert len(res_00) == 4

    # vote_fraction 0.5 -> min_votes 2 (keeps 3: 2 and 3 votes, drops 1-vote triple)
    res_05 = filter_runs(
        three_runs, "p1", "s1",
        vote_fraction=0.5, profile=profile,
        allow_dynamic=True, enforce_signatures=False, cap=0
    )
    assert len(res_05) == 3
    rels_05 = {t.relation for t in res_05}
    assert "DISCUSSES_CONCEPT" not in rels_05  # the 1-vote triple was dropped

    # vote_fraction 1.0 -> min_votes 3 (keeps 2: only 3 votes, drops 1 and 2 votes)
    res_10 = filter_runs(
        three_runs, "p1", "s1",
        vote_fraction=1.0, profile=profile,
        allow_dynamic=True, enforce_signatures=False, cap=0
    )
    assert len(res_10) == 2
    rels_10 = {t.relation for t in res_10}
    assert rels_10 == {"USES_METHOD", "CUSTOM_DYNAMIC_REL"}


def test_cap_keeps_highest_confidence_deterministically(three_runs):
    profile = PROFILES["R7"]
    # With cap=1, allow_dynamic=False drops CUSTOM_DYNAMIC_REL, so USES_METHOD (conf 1.0) is the only top triple
    res = filter_runs(
        three_runs, "p1", "s1",
        vote_fraction=0.0, profile=profile,
        allow_dynamic=False, enforce_signatures=False, cap=1
    )
    assert len(res) == 1
    assert res[0].relation == "USES_METHOD"
    assert res[0].confidence == 1.0


def test_allow_dynamic_false_drops_dynamic_relation(three_runs):
    profile = PROFILES["R7"]
    assert "CUSTOM_DYNAMIC_REL" not in profile.llm_relations

    # allow_dynamic=False drops CUSTOM_DYNAMIC_REL
    res_no_dyn = filter_runs(
        three_runs, "p1", "s1",
        vote_fraction=0.0, profile=profile,
        allow_dynamic=False, enforce_signatures=False, cap=0
    )
    rels_no_dyn = [t.relation for t in res_no_dyn]
    assert "CUSTOM_DYNAMIC_REL" not in rels_no_dyn

    # allow_dynamic=True keeps CUSTOM_DYNAMIC_REL
    res_with_dyn = filter_runs(
        three_runs, "p1", "s1",
        vote_fraction=0.0, profile=profile,
        allow_dynamic=True, enforce_signatures=False, cap=0
    )
    rels_with_dyn = [t.relation for t in res_with_dyn]
    assert "CUSTOM_DYNAMIC_REL" in rels_with_dyn


def test_is_generic_detection():
    assert is_generic("Our approach") is True
    assert is_generic("  our   approach  ") is True
    assert is_generic("models") is True
    assert is_generic("the models") is True
    assert is_generic("our models") is True
    assert is_generic("BERT") is False
    assert is_generic("Transformer") is False


def test_filter_runs_drop_generic():
    profile = PROFILES["R7"]
    runs = [
        [
            {"head": "our approach", "head_type": "Method", "relation": "USES_METHOD", "tail": "Transformer", "tail_type": "Concept"},
            {"head": "BERT", "head_type": "Method", "relation": "USES_METHOD", "tail": "Transformer", "tail_type": "Concept"},
        ]
    ]

    # When drop_generic=False: keeps "our approach"
    res_keep = filter_runs(
        runs, "p1", "s1",
        vote_fraction=0.5, profile=profile,
        allow_dynamic=True, enforce_signatures=False, cap=0,
        drop_generic=False,
    )
    heads_keep = [t.head for t in res_keep]
    assert "our approach" in heads_keep
    assert "BERT" in heads_keep

    # When drop_generic=True: drops "our approach", keeps "BERT"
    res_drop = filter_runs(
        runs, "p1", "s1",
        vote_fraction=0.5, profile=profile,
        allow_dynamic=True, enforce_signatures=False, cap=0,
        drop_generic=True,
    )
    heads_drop = [t.head for t in res_drop]
    assert "our approach" not in heads_drop
    assert "BERT" in heads_drop

