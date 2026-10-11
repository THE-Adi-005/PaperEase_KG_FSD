from eval.scoring import (bootstrap_ci, evidence_hit, extract_numbers,
                          is_abstain, is_correct, normalize)


def test_numeric_tolerance():
    assert is_correct("It scored 92.38%", ["92.4"], True)
    assert not is_correct("It scored 80.1", ["92.4"], True)


def test_percent_scaling():
    assert is_correct("The F1 is 92.4", ["0.924"], True)
    assert is_correct("The F1 is 0.924", ["92.4"], True)


def test_abstain_detection():
    assert is_abstain("Not found in the papers.")
    assert is_abstain("I can't find this information")
    assert not is_abstain("The answer is RACE")


def test_unanswerable_correct_only_when_abstaining():
    assert is_correct("Not found in the papers.", [], False)
    assert not is_correct("The answer is 5", [], False)


def test_substring_match_and_numbers():
    assert is_correct("The model was evaluated on RACE and GLUE", ["race"], True)
    assert extract_numbers("1,000 and 92.4%") == [1000.0, 92.4]
    assert normalize("  A  b ") == "a b"


def test_evidence_hit():
    assert evidence_hit("f1 = 92.4 on squad", ["92.4"])


def test_bootstrap_ci():
    m, lo, hi = bootstrap_ci([1, 0, 1, 1, 0, 1])
    assert lo <= m <= hi
