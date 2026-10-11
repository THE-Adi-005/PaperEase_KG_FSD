import csv
from pathlib import Path
from eval.make_tables import (
    load_csv, _f, _ci, _pct, _booktabs_table,
    table_main, table_schema, table_voting, table_cap,
)


def test_format_helpers():
    assert _f("0.12345", ".3f") == "0.123"
    assert _f(None) == "--"
    assert _f("", fallback="N/A") == "N/A"
    assert _f("nan") == "--"
    assert _f("invalid") == "--"

    assert _pct("0.852") == "85.2\\%"
    assert _pct(None) == "--"

    row = {"acc": "0.75", "acc_lo": "0.65", "acc_hi": "0.85"}
    assert _ci(row) == "0.750 [0.650,0.850]"

    empty_row = {}
    assert _ci(empty_row) == "--"


def test_load_csv(tmp_path):
    csv_file = tmp_path / "test_runs.csv"
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["system_id", "acc", "total_nodes"])
        writer.writeheader()
        writer.writerow({"system_id": "rag", "acc": "0.80", "total_nodes": ""})
        writer.writerow({"system_id": "kg_cfg_base_nolazy", "acc": "0.85", "total_nodes": "100"})

    data = load_csv(csv_file)
    assert len(data) == 2
    assert "rag" in data
    assert data["rag"]["acc"] == "0.80"
    assert data["kg_cfg_base_nolazy"]["total_nodes"] == "100"


def test_table_generators():
    mock_data = {
        "rag": {"acc": "0.70", "acc_lo": "0.60", "acc_hi": "0.80", "mean_steps": "1.0", "mean_latency": "2.5"},
        "kg_cfg_base_nolazy": {"acc": "0.82", "total_nodes": "250", "total_edges": "350"},
    }
    main_latex = table_main(mock_data)
    assert "\\begin{table}" in main_latex
    assert "Vector RAG" in main_latex
    assert "\\bottomrule" in main_latex

    schema_latex = table_schema(mock_data)
    assert "\\begin{table}" in schema_latex
    assert "cfg_base" in schema_latex
