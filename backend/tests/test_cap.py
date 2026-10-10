from app.models.schemas import Triple


def test_triple_cap_sorting_and_determinism():
    t1 = Triple(head="GPT", relation="USES_METHOD", tail="Transformer", confidence=0.5)
    t2 = Triple(head="BERT", relation="ACHIEVES", tail="Score2", confidence=1.0)
    t3 = Triple(head="BERT", relation="ACHIEVES", tail="Score1", confidence=1.0)
    t4 = Triple(head="Albert", relation="ACHIEVES", tail="Score1", confidence=1.0)
    t5 = Triple(head="BERT", relation="USES_METHOD", tail="Transformer", confidence=0.5)

    triples = [t1, t2, t3, t4, t5]

    # Key function used in kg_builder
    sort_key = lambda t: (-t.confidence, t.relation, t.head.lower(), t.tail.lower())
    triples.sort(key=sort_key)

    # 1. Higher confidence (1.0) comes first: t4 (Albert, ACHIEVES), t3 (BERT, ACHIEVES, Score1), t2 (BERT, ACHIEVES, Score2)
    assert triples[0] == t4  # conf 1.0, ACHIEVES, albert
    assert triples[1] == t3  # conf 1.0, ACHIEVES, bert, score1
    assert triples[2] == t2  # conf 1.0, ACHIEVES, bert, score2

    # 2. Lower confidence (0.5): t5 (BERT, USES_METHOD) before t1 (GPT, USES_METHOD)
    assert triples[3] == t5
    assert triples[4] == t1

    # Cap slicing
    cap = 2
    capped = triples[:cap]
    assert len(capped) == 2
    assert capped == [t4, t3]
