#!/usr/bin/env python3
import argparse
import sqlite3
from pathlib import Path


def table_exists(cur: sqlite3.Cursor, table_name: str) -> bool:
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    )
    return cur.fetchone() is not None


def count_rows(cur: sqlite3.Cursor, table_name: str) -> int:
    cur.execute(f"SELECT COUNT(*) FROM {table_name}")
    return int(cur.fetchone()[0])


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate WireGuard GUI database invariants.")
    parser.add_argument("--db-path", required=True, help="Path to sqlite database file.")
    args = parser.parse_args()

    db_path = Path(args.db_path)
    if not db_path.exists():
        raise SystemExit(f"Database not found: {db_path}")

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    required_tables = ["user", "network", "peer", "lighthouses"]
    missing = [table for table in required_tables if not table_exists(cur, table)]
    if missing:
        raise SystemExit(f"Missing required tables: {', '.join(missing)}")

    counts = {table: count_rows(cur, table) for table in required_tables}
    print("Validation succeeded.")
    for table, count in counts.items():
        print(f"{table}: {count}")

    conn.close()


if __name__ == "__main__":
    main()
