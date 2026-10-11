"""CLI script to clean empty ('[]') extractions from sqlite cache."""

import argparse
import sqlite3
from pathlib import Path
from eval.cache import DEFAULT_DB_PATH


def clean_empty_cache(profiles: list[str], apply: bool = False, db_path: Path | str | None = None) -> dict:
    target_path = Path(db_path) if db_path is not None else DEFAULT_DB_PATH
    if not target_path.exists():
        print(f"Database not found at {target_path}")
        return {}

    conn = sqlite3.connect(str(target_path))
    cur = conn.cursor()
    results = {}

    print("=" * 65)
    print(f"CLEAN EMPTY CACHE ({'APPLY MODE' if apply else 'DRY RUN'})")
    print(f"Database: {target_path}")
    print("=" * 65)

    try:
        for prof in profiles:
            cur.execute("SELECT COUNT(*) FROM extractions WHERE prompt_profile = ?", (prof,))
            total_before = cur.fetchone()[0]

            cur.execute(
                "SELECT COUNT(*) FROM extractions WHERE prompt_profile = ? AND TRIM(raw_json) = '[]'",
                (prof,)
            )
            empty_count = cur.fetchone()[0]

            deleted = 0
            if apply and empty_count > 0:
                cur.execute(
                    "DELETE FROM extractions WHERE prompt_profile = ? AND TRIM(raw_json) = '[]'",
                    (prof,)
                )
                conn.commit()
                deleted = cur.rowcount

            cur.execute("SELECT COUNT(*) FROM extractions WHERE prompt_profile = ?", (prof,))
            total_after = cur.fetchone()[0]

            results[prof] = {
                "total_before": total_before,
                "empty_found": empty_count,
                "deleted": deleted,
                "total_after": total_after,
            }

            print(f"Profile: {prof}")
            print(f"  Total before:   {total_before}")
            print(f"  Empty rows:     {empty_count}")
            if apply:
                print(f"  Deleted:        {deleted}")
                print(f"  Total after:    {total_after}")
            else:
                print(f"  Action:         Dry run (0 rows deleted)")
            print("-" * 65)

        return results

    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Clean empty extraction rows from SQLite cache.")
    parser.add_argument(
        "--profiles",
        nargs="+",
        required=True,
        help="One or more prompt profiles to clean (e.g. R3 R10)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply deletions (default is dry-run)",
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default=None,
        help="Path to SQLite database file",
    )

    args = parser.parse_args()
    clean_empty_cache(profiles=args.profiles, apply=args.apply, db_path=args.db_path)


if __name__ == "__main__":
    main()
