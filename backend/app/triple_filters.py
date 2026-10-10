import math


def min_votes(n_runs: int, fraction: float) -> int:
    return max(1, math.ceil(fraction * n_runs - 1e-9))


def graph_metrics(total_nodes: int, total_edges: int) -> tuple[float, float]:
    """Compute (avg_degree, density) for a directed graph."""
    avg_degree = round(total_edges * 2.0 / total_nodes, 2) if total_nodes > 0 else 0.0
    if total_nodes > 1:
        max_edges = total_nodes * (total_nodes - 1)
        density = round(total_edges / max_edges, 6) if max_edges > 0 else 0.0
    else:
        density = 0.0
    return avg_degree, density
