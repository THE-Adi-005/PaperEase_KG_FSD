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


GENERIC_ENTITIES = {
    "method", "methods", "approach", "our approach", "our method",
    "proposed method", "the proposed method", "proposed approach",
    "framework", "our framework", "model", "models", "our model", "our models",
    "the model", "the models", "system", "our system", "technique", "algorithm",
    "baseline", "baselines", "this paper", "this work", "this study", "this section",
    "the section", "paper", "results", "experiments", "task", "tasks",
    "data", "dataset", "datasets", "metric", "metrics", "ours", "we", "it",
}


def is_generic(name: str) -> bool:
    """Check if an entity name is a generic placeholder."""
    if not name:
        return False
    collapsed = " ".join(name.strip().lower().split())
    return collapsed in GENERIC_ENTITIES
