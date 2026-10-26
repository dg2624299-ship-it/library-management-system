"""View the library SQLite database as pretty tables.

Usage:
    python view_db.py            # show all tables
    python view_db.py books      # show one table
    python view_db.py users loans
"""
import sys
import sqlite3

import pandas as pd

DB_FILE = "library.db"


def bordered(df):
    """Render a DataFrame as a bordered grid table (no extra deps)."""
    if df.empty:
        return "(empty)"
    cols = [str(c) for c in df.columns]
    rows = [[str(v) for v in r] for r in df.itertuples(index=False, name=None)]
    width = [max(len(cols[i]), max((len(r[i]) for r in rows), default=0)) for i in range(len(cols))]

    def line(left, mid, right):
        return left + mid.join("-" * (w + 2) for w in width) + right

    out = [line("+", "+", "+")]
    out.append("| " + " | ".join(c.ljust(width[i]) for i, c in enumerate(cols)) + " |")
    out.append(line("+", "+", "+"))
    for r in rows:
        out.append("| " + " | ".join(r[i].ljust(width[i]) for i in range(len(cols))) + " |")
    out.append(line("+", "+", "+"))
    return "\n".join(out)


def show_table(conn, table):
    df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
    print(f"\n=== {table} ({len(df)} rows) ===")
    print(bordered(df))


def main():
    conn = sqlite3.connect(DB_FILE)
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name"
    )]

    if len(sys.argv) > 1:
        wanted = sys.argv[1:]
        missing = [t for t in wanted if t not in tables]
        if missing:
            print(f"Unknown table(s): {', '.join(missing)}")
            print(f"Available tables: {', '.join(tables)}")
            sys.exit(1)
        for t in wanted:
            show_table(conn, t)
    else:
        for t in tables:
            show_table(conn, t)

    conn.close()


if __name__ == "__main__":
    main()