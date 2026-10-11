import json
from pathlib import Path
from eval.qa_merge import validate_and_filter, merge


def test_qa_merge_validation(tmp_path):
    corpus_ids = {"paper1", "paper2"}
    items = [
        {
            "id": "q1",
            "type": "lookup",
            "source": "manual",
            "paper_ids": ["paper1"],
            "question": "What is the metric?",
            "gold_answers": ["92.4"],
            "answerable": True,
            "verified": True,
        },
        {
            "id": "q2",
            "type": "unanswerable",
            "source": "manual",
            "paper_ids": ["paper2"],
            "question": "Is something else tested?",
            "gold_answers": [],
            "answerable": False,
            "verified": True,
        },
        {
            "id": "q3_unverified",
            "type": "lookup",
            "source": "manual",
            "paper_ids": ["paper1"],
            "question": "Unverified question?",
            "gold_answers": ["42"],
            "answerable": True,
            "verified": False,
        },
        {
            "id": "q4_bad_answerable",
            "type": "lookup",
            "source": "manual",
            "paper_ids": ["paper1"],
            "question": "No gold answers?",
            "gold_answers": [],
            "answerable": True,
            "verified": True,
        },
    ]

    valid, errors = validate_and_filter(items, corpus_ids)
    assert len(valid) == 2
    assert [x["id"] for x in valid] == ["q1", "q2"]
    assert len(errors) == 2

    deduped, _ = merge([items[:2], items[:1]], corpus_ids)
    assert len(deduped) == 2
