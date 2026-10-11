from eval.extraction_eval import lenient_match, compute_prf, normalize_text


def test_normalize_text():
    assert normalize_text("  Transformer-XL (2019)  ") == "transformer xl 2019"
    assert normalize_text("GLUE Benchmark.") == "glue benchmark"


def test_lenient_match_exact():
    assert lenient_match("Transformer", "transformer")
    assert lenient_match("BERT", "bert")
    assert not lenient_match("", "bert")


def test_lenient_match_substring_and_jaccard():
    # "transformer model" (2 tokens) vs "transformer" (1 token):
    # intersection: 1, union: 2 -> jaccard = 0.5 -> matches
    assert lenient_match("transformer model", "transformer")
    assert lenient_match("transformer", "transformer model")

    # "12 layer decoder transformer model" (5 tokens) vs "transformer" (1 token):
    # intersection: 1, union: 5 -> jaccard = 0.2 < 0.5 -> does not match
    assert not lenient_match("12 layer decoder transformer model", "transformer")

    # Disjoint words do not match even if similar
    assert not lenient_match("recurrent neural network", "transformer")


def test_compute_prf():
    p, r, f1 = compute_prf(10, 0, 0)
    assert (p, r, f1) == (1.0, 1.0, 1.0)

    p, r, f1 = compute_prf(0, 5, 5)
    assert (p, r, f1) == (0.0, 0.0, 0.0)

    # tp=8, fp=2 (pred=10 -> p=0.8), fn=2 (gold=10 -> r=0.8)
    p, r, f1 = compute_prf(8, 2, 2)
    assert p == 0.8
    assert r == 0.8
    assert f1 == 0.8
