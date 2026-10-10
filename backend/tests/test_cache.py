import pytest
from pathlib import Path
from eval.cache import has_run, put_run, get_runs, put_table_triple, get_table_triples


@pytest.fixture
def tmp_db(tmp_path):
    return tmp_path / "test_cache.sqlite"


def test_cache_put_has_get(tmp_db):
    assert not has_run("p1", "s1", 0, "R7", 3000, 0.6, "m1", db_path=tmp_db)

    triples = [{"head": "BERT", "relation": "USES_METHOD", "tail": "Transformer"}]
    put_run("p1", "s1", 0, "R7", 3000, 0.6, "m1", triples, db_path=tmp_db)

    assert has_run("p1", "s1", 0, "R7", 3000, 0.6, "m1", db_path=tmp_db)

    runs = get_runs("p1", "s1", "R7", 3000, 0.6, "m1", db_path=tmp_db)
    assert len(runs) == 1
    assert runs[0] == triples

    # Second run
    triples_r2 = [{"head": "GPT", "relation": "ACHIEVES", "tail": "Score"}]
    put_run("p1", "s1", 1, "R7", 3000, 0.6, "m1", triples_r2, db_path=tmp_db)

    runs_all = get_runs("p1", "s1", "R7", 3000, 0.6, "m1", db_path=tmp_db)
    assert len(runs_all) == 2
    assert runs_all[0] == triples
    assert runs_all[1] == triples_r2

    # max_runs=1
    runs_limited = get_runs("p1", "s1", "R7", 3000, 0.6, "m1", max_runs=1, db_path=tmp_db)
    assert len(runs_limited) == 1
    assert runs_limited[0] == triples


def test_table_triples_cache(tmp_db):
    put_table_triple("p1", "s1", "BERT", "EVALUATED_ON", "GLUE", db_path=tmp_db)
    triples = get_table_triples("p1", db_path=tmp_db)
    assert len(triples) == 1
    assert triples[0]["head"] == "BERT"
    assert triples[0]["relation"] == "EVALUATED_ON"
    assert triples[0]["tail"] == "GLUE"


def test_parse_json_array():
    from app.services.llm_client import llm_client

    # Valid empty list
    assert llm_client._parse_json_array("[]") == []
    assert llm_client._parse_json_array("```json\n[]\n```") == []
    assert llm_client._parse_json_array("Here are the triples: []") == []

    # Valid non-empty list
    parsed = llm_client._parse_json_array('[{"head": "BERT", "relation": "ACHIEVES", "tail": "F1=92.4"}]')
    assert len(parsed) == 1
    assert parsed[0]["head"] == "BERT"

    # Unparseable output raises ValueError
    with pytest.raises(ValueError, match="No valid JSON array or objects found"):
        llm_client._parse_json_array("This section describes the dataset but contains no triples.")

    with pytest.raises(ValueError, match="No valid JSON array or objects found"):
        llm_client._parse_json_array("")

