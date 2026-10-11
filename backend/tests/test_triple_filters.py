from app.triple_filters import min_votes, graph_metrics, is_generic


def test_min_votes():
    assert min_votes(1, 0.5) == 1
    assert min_votes(2, 0.5) == 1
    assert min_votes(3, 0.5) == 2
    assert min_votes(5, 0.5) == 3
    assert min_votes(5, 0.0) == 1
    assert min_votes(5, 1.0) == 5
    assert min_votes(5, 0.6) == 3
    assert min_votes(5, 0.2) == 1
    assert min_votes(10, 0.7) == 7


def test_graph_metrics():
    assert graph_metrics(4, 6) == (3.0, 0.5)
    assert graph_metrics(0, 0) == (0.0, 0.0)
    assert graph_metrics(1, 0) == (0.0, 0.0)


def test_is_generic():
    assert is_generic("models") is True
    assert is_generic("the models") is True
    assert is_generic("our models") is True
    assert is_generic("BERT") is False
