"""Read-only helper to inspect extraction and table cache status."""

import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "results" / "cache.sqlite"


def print_cache_status():
    if not DB_PATH.exists():
        print(f"Database file not found: {DB_PATH}")
        return

    conn = sqlite3.connect(str(DB_PATH))
    try:
        cursor = conn.cursor()

        # Check extractions table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='extractions'")
        if cursor.fetchone():
            cursor.execute("""
                SELECT
                    prompt_profile,
                    COUNT(*) as total_rows,
                    COUNT(DISTINCT paper_id || '::' || section_id) as distinct_sections,
                    MAX(run_idx) as max_run_idx
                FROM extractions
                GROUP BY prompt_profile
                ORDER BY prompt_profile
            """)
            profiles = cursor.fetchall()
            print("=" * 60)
            print("EXTRACTION CACHE STATUS")
            print("=" * 60)
            if profiles:
                print(f"{'Profile':<10} {'Rows':<10} {'Distinct Secs':<16} {'Max run_idx':<12}")
                print("-" * 60)
                for profile, count, distinct_secs, max_run in profiles:
                    print(f"{profile:<10} {count:<10} {distinct_secs:<16} {max_run:<12}")
            else:
                print("No extraction rows found.")
        else:
            print("Table 'extractions' does not exist.")

        # Check table_triples table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='table_triples'")
        if cursor.fetchone():
            cursor.execute("SELECT COUNT(*) FROM table_triples")
            table_count = cursor.fetchone()[0]
            print("\n" + "=" * 60)
            print(f"Table triples row count: {table_count}")
            print("=" * 60)
        else:
            print("Table 'table_triples' does not exist.")

    finally:
        conn.close()


if __name__ == "__main__":
    print_cache_status()
