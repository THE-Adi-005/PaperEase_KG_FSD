from app.triple_filters import min_votes


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
