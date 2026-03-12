#!/usr/bin/env python3
import argparse
import sqlite3
from pathlib import Path


def has_column(cur: sqlite3.Cursor, table_name: str, column_name: str) -> bool:
    cur.execute(f"PRAGMA table_info({table_name})")
    return any(row[1] == column_name for row in cur.fetchall())


def main() -> None:
    parser = argparse.ArgumentParser(description="Additive data backfill for WireGuard GUI v0.4.")
    parser.add_argument("--db-path", required=True, help="Path to sqlite database file.")
    args = parser.parse_args()

    db_path = Path(args.db_path)
    if not db_path.exists():
        raise SystemExit(f"Database not found: {db_path}")

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    # Additive schema safety: only add missing columns.
    if not has_column(cur, "peer", "network_id"):
        cur.execute("ALTER TABLE peer ADD COLUMN network_id INTEGER DEFAULT 0")
        print("Added peer.network_id")

    # Normalize nullable text fields to empty strings for simpler runtime logic.
    cur.execute("UPDATE network SET allowed_ips = '' WHERE allowed_ips IS NULL")
    cur.execute("UPDATE network SET adapter_name = 'wg0' WHERE adapter_name IS NULL OR adapter_name = ''")
    cur.execute("UPDATE peer SET network_id = 0 WHERE network_id IS NULL")

    conn.commit()
    conn.close()
    print("Backfill complete.")


if __name__ == "__main__":
    main()
