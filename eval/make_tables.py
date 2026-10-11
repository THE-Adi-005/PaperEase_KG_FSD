"""eval/make_tables.py — generate LaTeX tables and PNG plots from results/all_runs.csv.

Outputs to paper_assets/:
  table_main.tex         — main comparison: RAG vs KG nolazy vs KG lazy
  table_schema.tex       — schema sweep (cfg_r3/r5/r7/r10 vs base)
  table_voting.tex       — voting sweep (cfg_v_run1/union/base/unan)
  table_cap.tex          — cap sweep (cfg_k5/k10/k20/base)
  table_sameas.tex       — SAME_AS sweep (cfg_sa_off/070/base/090)
  table_constraints.tex  — constraint ablations (sig_on, dyn_on, nogeneric)
  plot_acc_vs_relations.png
  plot_acc_vs_cap.png
  plot_acc_vs_vote.png
  plot_nodes_vs_acc.png
  plot_sameas_vs_acc.png

Usage:
    python -m eval.make_tables
    python -m eval.make_tables --csv results/all_runs.csv --out paper_assets
"""

import argparse
import csv
import io
import math
import sys
from pathlib import Path
from typing import Optional

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_CSV = _REPO_ROOT / "results" / "all_runs.csv"
_DEFAULT_OUT = _REPO_ROOT / "paper_assets"

# ── Schema relation counts for the schema sweep ──────────────────────────────
_SCHEMA_RELATIONS = {
    "cfg_r3": 3, "cfg_r5": 5, "cfg_base": 7,
    "cfg_r7": 7, "cfg_r10": 10,
}
_CAP_K = {
    "cfg_k5": 5, "cfg_k10": 10, "cfg_base": 20, "cfg_k20": 20,
}
_VOTE_LABEL = {
    "cfg_v_run1": "Run×1 (union)", "cfg_v_union": "50% vote",
    "cfg_base": "50% vote (base)", "cfg_v_unan": "Unanimous",
}
_SA_THRESH = {
    "cfg_sa_off": "off", "cfg_sa_070": "0.70",
    "cfg_base": "0.85", "cfg_sa_090": "0.90",
}


# ── CSV helpers ───────────────────────────────────────────────────────────────

def load_csv(path: Path) -> dict[str, dict]:
    """Load all_runs.csv keyed by system_id. Missing cells become ''."""
    if not path.exists():
        return {}
    rows: dict[str, dict] = {}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            rows[row["system_id"]] = row
    return rows


def _f(val, fmt=".3f", fallback="--") -> str:
    """Format a numeric cell; return fallback on missing/empty."""
    if val is None or str(val).strip() in ("", "nan", "None"):
        return fallback
    try:
        return format(float(val), fmt)
    except (ValueError, TypeError):
        return fallback


def _ci(row: dict, col: str = "acc") -> str:
    """Format acc with CI as 'val [lo, hi]'."""
    v = _f(row.get(col))
    lo = _f(row.get(f"{col}_lo"))
    hi = _f(row.get(f"{col}_hi"))
    if v == "--":
        return "--"
    if lo == "--" or hi == "--":
        return v
    return f"{v} [{lo},{hi}]"


def _pct(val, fallback="--") -> str:
    """Format as percentage string."""
    if val is None or str(val).strip() in ("", "nan"):
        return fallback
    try:
        return f"{float(val)*100:.1f}\\%"
    except (ValueError, TypeError):
        return fallback


# ── LaTeX helpers ─────────────────────────────────────────────────────────────

def _booktabs_table(caption: str, label: str, header: list[str],
                    rows: list[list[str]], col_spec: Optional[str] = None) -> str:
    n = len(header)
    spec = col_spec or ("l" + "c" * (n - 1))
    lines = [
        "\\begin{table}[t]",
        "\\centering",
        f"\\caption{{{caption}}}",
        f"\\label{{tab:{label}}}",
        f"\\begin{{tabular}}{{{spec}}}",
        "\\toprule",
        " & ".join(header) + " \\\\",
        "\\midrule",
    ]
    for row in rows:
        lines.append(" & ".join(str(c) for c in row) + " \\\\")
    lines += ["\\bottomrule", "\\end{tabular}", "\\end{table}"]
    return "\n".join(lines)


# ── Table generators ─────────────────────────────────────────────────────────

def table_main(data: dict) -> str:
    """Main comparison: RAG vs KG-base-nolazy vs KG-base-lazy."""
    systems = [
        ("rag", "Vector RAG"),
        ("kg_cfg_base_nolazy", "KG agent (no lazy)"),
        ("kg_cfg_base_lazy", "KG agent (lazy)"),
    ]
    header = ["System", "Acc. (95\\% CI)", "Cross-paper", "Abstain unans.", "Ev. hit", "Steps", "Lat. (s)"]
    rows = []
    for sid, label in systems:
        r = data.get(sid, {})
        rows.append([
            label,
            _ci(r),
            _f(r.get("acc_cross_paper")),
            _pct(r.get("abstain_rate_unanswerable")),
            _f(r.get("evidence_hit")),
            _f(r.get("mean_steps"), ".1f"),
            _f(r.get("mean_latency"), ".1f"),
        ])
    return _booktabs_table(
        "Main QA comparison. All systems use Qwen~2.5~7B. "
        "Acc.~= exact-match accuracy with 95\\% bootstrap CI.",
        "main",
        header, rows,
        col_spec="lcccccc",
    )


def table_schema(data: dict) -> str:
    """Schema sweep: relation-set size vs graph stats and QA."""
    configs = ["cfg_r3", "cfg_r5", "cfg_base", "cfg_r10"]
    header = ["Profile", "\\#Rel.", "Nodes", "Edges", "Density", "Acc."]
    rows = []
    for cfg in configs:
        sid = f"kg_{cfg}_nolazy"
        r = data.get(sid, {})
        rows.append([
            cfg,
            str(_SCHEMA_RELATIONS.get(cfg, "--")),
            _f(r.get("total_nodes"), ".0f"),
            _f(r.get("total_edges"), ".0f"),
            _f(r.get("graph_density"), ".4f"),
            _ci(r),
        ])
    return _booktabs_table(
        "Effect of relation-set size. Nested sets; same 5 entity types.",
        "schema", header, rows,
    )


def table_voting(data: dict) -> str:
    """Voting threshold sweep."""
    configs = ["cfg_v_run1", "cfg_v_union", "cfg_base", "cfg_v_unan"]
    header = ["Vote rule", "Nodes", "Edges", "Acc."]
    rows = []
    for cfg in configs:
        sid = f"kg_{cfg}_nolazy"
        r = data.get(sid, {})
        rows.append([
            _VOTE_LABEL.get(cfg, cfg),
            _f(r.get("total_nodes"), ".0f"),
            _f(r.get("total_edges"), ".0f"),
            _ci(r),
        ])
    return _booktabs_table(
        "Effect of self-consistency voting threshold.",
        "voting", header, rows,
    )


def table_cap(data: dict) -> str:
    """Per-section cap sweep."""
    configs = ["cfg_k5", "cfg_k10", "cfg_base", "cfg_k20"]
    header = ["Cap $K$", "Nodes", "Edges", "Acc."]
    rows = []
    for cfg in configs:
        sid = f"kg_{cfg}_nolazy"
        r = data.get(sid, {})
        rows.append([
            str(_CAP_K.get(cfg, "--")),
            _f(r.get("total_nodes"), ".0f"),
            _f(r.get("total_edges"), ".0f"),
            _ci(r),
        ])
    return _booktabs_table(
        "Effect of per-section triple cap $K$.",
        "cap", header, rows,
    )


def table_sameas(data: dict) -> str:
    """SAME_AS threshold sweep."""
    configs = ["cfg_sa_off", "cfg_sa_070", "cfg_base", "cfg_sa_090"]
    header = ["SA thresh.", "SAME\\_AS edges", "Cross-paper acc."]
    rows = []
    for cfg in configs:
        sid = f"kg_{cfg}_nolazy"
        r = data.get(sid, {})
        rows.append([
            _SA_THRESH.get(cfg, cfg),
            "--",  # same_as edge count not yet in CSV; placeholder
            _f(r.get("acc_cross_paper")),
        ])
    return _booktabs_table(
        "Effect of SAME\\_AS cosine similarity threshold on cross-paper accuracy.",
        "sameas", header, rows,
    )


def table_constraints(data: dict) -> str:
    """Constraint ablations."""
    systems = [
        ("kg_cfg_base_nolazy", "Base (R7, no constraints)"),
        ("kg_cfg_sig_on_nolazy", "+ Type-sig. filter"),
        ("kg_cfg_dyn_on_nolazy", "+ Dynamic relations"),
        ("kg_cfg_nogeneric_nolazy", "+ Drop generic"),
    ]
    header = ["System", "Nodes", "Edges", "Acc."]
    rows = []
    for sid, label in systems:
        r = data.get(sid, {})
        rows.append([
            label,
            _f(r.get("total_nodes"), ".0f"),
            _f(r.get("total_edges"), ".0f"),
            _ci(r),
        ])
    return _booktabs_table(
        "Effect of schema constraints (type-signature filter, dynamic relations, generic drop).",
        "constraints", header, rows,
    )


# ── Plots ─────────────────────────────────────────────────────────────────────

def _safe_float(v) -> Optional[float]:
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def make_plots(data: dict, out_dir: Path):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed — skipping plots. Run: pip install matplotlib", file=sys.stderr)
        return

    def _errbar(ax, xs, ys, lows, highs, label, marker="o"):
        valid = [(x, y, lo, hi) for x, y, lo, hi in zip(xs, ys, lows, highs)
                 if y is not None]
        if not valid:
            return
        xs2, ys2, los, his = zip(*valid)
        yerr_lo = [y - lo for y, lo in zip(ys2, los)]
        yerr_hi = [hi - y for y, hi in zip(ys2, his)]
        ax.errorbar(xs2, ys2, yerr=[yerr_lo, yerr_hi],
                    fmt=f"-{marker}", label=label, capsize=4)

    # 1. Accuracy vs relation count
    configs = ["cfg_r3", "cfg_r5", "cfg_base", "cfg_r10"]
    x = [_SCHEMA_RELATIONS.get(c, None) for c in configs]
    rows = [data.get(f"kg_{c}_nolazy", {}) for c in configs]
    y = [_safe_float(r.get("acc")) for r in rows]
    lo = [_safe_float(r.get("acc_lo")) for r in rows]
    hi = [_safe_float(r.get("acc_hi")) for r in rows]
    fig, ax = plt.subplots()
    _errbar(ax, x, y, lo, hi, "KG no-lazy")
    ax.set_xlabel("Number of relation types")
    ax.set_ylabel("Accuracy")
    ax.set_title("Accuracy vs. relation-set size")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_dir / "plot_acc_vs_relations.png", dpi=150)
    plt.close(fig)

    # 2. Accuracy vs cap K
    configs_k = ["cfg_k5", "cfg_k10", "cfg_base", "cfg_k20"]
    x = [_CAP_K.get(c, None) for c in configs_k]
    rows = [data.get(f"kg_{c}_nolazy", {}) for c in configs_k]
    y = [_safe_float(r.get("acc")) for r in rows]
    lo = [_safe_float(r.get("acc_lo")) for r in rows]
    hi = [_safe_float(r.get("acc_hi")) for r in rows]
    fig, ax = plt.subplots()
    _errbar(ax, x, y, lo, hi, "KG no-lazy")
    ax.set_xlabel("Per-section cap K")
    ax.set_ylabel("Accuracy")
    ax.set_title("Accuracy vs. triple cap K")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_dir / "plot_acc_vs_cap.png", dpi=150)
    plt.close(fig)

    # 3. Nodes vs Accuracy (schema sweep scatter)
    fig, ax = plt.subplots()
    for cfg in ["cfg_r3", "cfg_r5", "cfg_base", "cfg_r10"]:
        r = data.get(f"kg_{cfg}_nolazy", {})
        n = _safe_float(r.get("total_nodes"))
        a = _safe_float(r.get("acc"))
        if n and a:
            ax.scatter(n, a, label=cfg, s=80)
    ax.set_xlabel("Total nodes")
    ax.set_ylabel("Accuracy")
    ax.set_title("Nodes vs. accuracy (schema sweep)")
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(out_dir / "plot_nodes_vs_acc.png", dpi=150)
    plt.close(fig)

    # 4. Extraction F1 vs vote threshold (placeholder until extraction_metrics.json)
    fig, ax = plt.subplots()
    vote_labels = ["Union", "50%", "67%", "Unan."]
    ax.set_xticks(range(len(vote_labels)))
    ax.set_xticklabels(vote_labels)
    ax.set_ylabel("Accuracy")
    ax.set_title("Accuracy vs. vote threshold")
    for i, cfg in enumerate(["cfg_v_run1", "cfg_v_union", "cfg_base", "cfg_v_unan"]):
        r = data.get(f"kg_{cfg}_nolazy", {})
        a = _safe_float(r.get("acc"))
        if a is not None:
            ax.scatter([i], [a], s=80)
    fig.tight_layout()
    fig.savefig(out_dir / "plot_acc_vs_vote.png", dpi=150)
    plt.close(fig)

    # 5. Cross-paper acc vs SAME_AS threshold
    thresh_labels = ["off", "0.70", "0.85", "0.90"]
    fig, ax = plt.subplots()
    for i, cfg in enumerate(["cfg_sa_off", "cfg_sa_070", "cfg_base", "cfg_sa_090"]):
        r = data.get(f"kg_{cfg}_nolazy", {})
        a = _safe_float(r.get("acc_cross_paper"))
        if a is not None:
            ax.scatter([i], [a], s=80)
    ax.set_xticks(range(len(thresh_labels)))
    ax.set_xticklabels(thresh_labels)
    ax.set_xlabel("SAME_AS threshold")
    ax.set_ylabel("Cross-paper accuracy")
    ax.set_title("Cross-paper accuracy vs. SAME_AS threshold")
    fig.tight_layout()
    fig.savefig(out_dir / "plot_sameas_vs_acc.png", dpi=150)
    plt.close(fig)

    print(f"Saved 5 plots to {out_dir}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate LaTeX tables and plots")
    parser.add_argument("--csv", default=str(_DEFAULT_CSV))
    parser.add_argument("--out", default=str(_DEFAULT_OUT))
    args = parser.parse_args()

    csv_path = Path(args.csv)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    data = load_csv(csv_path)
    if not data:
        print(f"Warning: {csv_path} not found or empty — tables will show '--' placeholders")

    tables = [
        ("table_main.tex", table_main(data)),
        ("table_schema.tex", table_schema(data)),
        ("table_voting.tex", table_voting(data)),
        ("table_cap.tex", table_cap(data)),
        ("table_sameas.tex", table_sameas(data)),
        ("table_constraints.tex", table_constraints(data)),
    ]
    for fname, tex in tables:
        p = out_dir / fname
        p.write_text(tex, encoding="utf-8")
        print(f"Wrote {p}")

    make_plots(data, out_dir)


if __name__ == "__main__":
    main()
