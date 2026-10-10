"""SQLite extraction and table triple cache."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "results" / "cache.sqlite"


def get_connection(db_path: Path | str | None = None) -> sqlite3.Connection:
    target_path = Path(db_path) if db_path is not None else DEFAULT_DB_PATH
    target_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target_path))
    init_db(conn)
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS extractions (
                paper_id TEXT,
                section_id TEXT,
                run_idx INT,
                prompt_profile TEXT,
                trunc INT,
                temperature REAL,
                model TEXT,
                raw_json TEXT,
                created TEXT,
                PRIMARY KEY(paper_id, section_id, run_idx, prompt_profile, trunc, temperature, model)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS table_triples (
                paper_id TEXT,
                section_id TEXT,
                head TEXT,
                relation TEXT,
                tail TEXT,
                PRIMARY KEY(paper_id, section_id, head, relation, tail)
            )
        """)


def has_run(
    paper_id: str,
    section_id: str,
    run_idx: int,
    prompt_profile: str,
    trunc: int,
    temperature: float,
    model: str,
    db_path: Path | str | None = None,
) -> bool:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT 1 FROM extractions
            WHERE paper_id = ?
              AND section_id = ?
              AND run_idx = ?
              AND prompt_profile = ?
              AND trunc = ?
              AND ABS(temperature - ?) < 1e-6
              AND model = ?
            LIMIT 1
            """,
            (paper_id, section_id, run_idx, prompt_profile, trunc, temperature, model),
        )
        return cursor.fetchone() is not None


def put_run(
    paper_id: str,
    section_id: str,
    run_idx: int,
    prompt_profile: str,
    trunc: int,
    temperature: float,
    model: str,
    raw_triples: list[dict],
    created: str | None = None,
    db_path: Path | str | None = None,
) -> None:
    created_ts = created or datetime.now(timezone.utc).isoformat()
    raw_json = json.dumps(raw_triples)
    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO extractions (
                paper_id, section_id, run_idx, prompt_profile, trunc, temperature, model, raw_json, created
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (paper_id, section_id, run_idx, prompt_profile, trunc, temperature, model, raw_json, created_ts),
        )


def get_runs(
    paper_id: str,
    section_id: str,
    prompt_profile: str,
    trunc: int,
    temperature: float,
    model: str,
    max_runs: int | None = None,
    db_path: Path | str | None = None,
) -> list[list[dict]]:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        query = """
            SELECT raw_json FROM extractions
            WHERE paper_id = ?
              AND section_id = ?
              AND prompt_profile = ?
              AND trunc = ?
              AND ABS(temperature - ?) < 1e-6
              AND model = ?
            ORDER BY run_idx ASC
        """
        params: list[Any] = [paper_id, section_id, prompt_profile, trunc, temperature, model]
        if max_runs is not None:
            query += " LIMIT ?"
            params.append(max_runs)

        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        return [json.loads(row[0]) for row in rows]


def put_table_triple(
    paper_id: str,
    section_id: str,
    head: str,
    relation: str,
    tail: str,
    db_path: Path | str | None = None,
) -> None:
    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO table_triples (
                paper_id, section_id, head, relation, tail
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (paper_id, section_id, head, relation, tail),
        )


def get_table_triples(
    paper_id: str | None = None,
    section_id: str | None = None,
    db_path: Path | str | None = None,
) -> list[dict]:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        query = "SELECT paper_id, section_id, head, relation, tail FROM table_triples WHERE 1=1"
        params: list[Any] = []
        if paper_id is not None:
            query += " AND paper_id = ?"
            params.append(paper_id)
        if section_id is not None:
            query += " AND section_id = ?"
            params.append(section_id)
        query += " ORDER BY paper_id, section_id, head, relation, tail"

        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        return [
            {
                "paper_id": row[0],
                "section_id": row[1],
                "head": row[2],
                "relation": row[3],
                "tail": row[4],
            }
            for row in rows
        ]
