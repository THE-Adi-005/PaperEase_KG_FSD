import math


def min_votes(n_runs: int, fraction: float) -> int:
    return max(1, math.ceil(fraction * n_runs - 1e-9))
