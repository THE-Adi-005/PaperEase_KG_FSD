from app.schema_profiles import PROFILES, ENTITY_TYPES, get_active_profile


def test_profiles_relationships():
    r3 = PROFILES["R3"]
    r5 = PROFILES["R5"]
    r7 = PROFILES["R7"]
    r10 = PROFILES["R10"]
    s8 = PROFILES["S8"]

    # Length of llm_relations is 3/5/7/10
    assert len(r3.llm_relations) == 3
    assert len(r5.llm_relations) == 5
    assert len(r7.llm_relations) == 7
    assert len(r10.llm_relations) == 10

    # R3 ⊂ R5 ⊂ R7 ⊂ R10 on llm_relations
    set_r3 = set(r3.llm_relations)
    set_r5 = set(r5.llm_relations)
    set_r7 = set(r7.llm_relations)
    set_r10 = set(r10.llm_relations)

    assert set_r3 < set_r5
    assert set_r5 < set_r7
    assert set_r7 < set_r10

    # Identical entity_types across profiles
    for prof in (r3, r5, r7, r10, s8):
        assert prof.entity_types == ENTITY_TYPES

    # R7 == S8 alias
    assert s8 is r7
    assert s8.llm_relations == r7.llm_relations
    assert s8.type_signatures == r7.type_signatures
