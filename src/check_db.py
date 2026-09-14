"""Sanity check of the loaded DuckDB database.

Prints row counts per table and per variable, confirms there are no NULL
values, and shows the actual temporal/spatial extent and the load log.
Run after ``load.py``.
"""
from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "ard_biendong.duckdb"

con = duckdb.connect(str(DB_PATH), read_only=True)

print("=== Row count per table ===")
for table in ["measurements", "load_log", "dataset_metadata", "variable_reference"]:
    n = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    print(f"{table}: {n}")

print()
print("=== Row count per variable in measurements ===")
print(con.execute("SELECT variable, COUNT(*) FROM measurements GROUP BY variable").fetchdf())

print()
print("=== Any NaN/NULL left in value? ===")
n_null = con.execute("SELECT COUNT(*) FROM measurements WHERE value IS NULL").fetchone()[0]
print(f"Rows with NULL value: {n_null}  (expected: 0)")

print()
print("=== Actual temporal and spatial extent ===")
print(con.execute("""
    SELECT MIN(time), MAX(time), MIN(latitude), MAX(latitude), MIN(longitude), MAX(longitude)
    FROM measurements
""").fetchdf())

print()
print("=== load_log: files loaded ===")
print(con.execute("SELECT file_name, inserted_line FROM load_log ORDER BY file_name").fetchdf())

print()
print("=== variable_reference ===")
print(con.execute("SELECT * FROM variable_reference").fetchdf())

print()
print("=== dataset_metadata ===")
print(con.execute("SELECT * FROM dataset_metadata").fetchdf())

con.close()
