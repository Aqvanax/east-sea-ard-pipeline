"""Export: write the DuckDB tables out as Parquet for distribution.

Produces ``measurements_wide.parquet``, one
``measurements_long_<variable>.parquet`` per variable, plus the two
reference tables, in ``data/parquet/``. These are the files deposited on
Zenodo.
"""
from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "ard_biendong.duckdb"
PARQUET_DIR = PROJECT_ROOT / "data" / "parquet"


def main() -> None:
    PARQUET_DIR.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB_PATH), read_only=True)

    con.execute(f"""
        COPY (SELECT * FROM measurements_wide)
        TO '{PARQUET_DIR / "measurements_wide.parquet"}'
        (FORMAT PARQUET, COMPRESSION ZSTD)
    """)

    variables = [row[0] for row in con.execute("SELECT variable_name FROM variable_reference").fetchall()]
    for var in variables:
        con.execute(f"""
            COPY (
                SELECT time, latitude, longitude, value
                FROM measurements
                WHERE variable = '{var}'
            )
            TO '{PARQUET_DIR / f"measurements_long_{var}.parquet"}'
            (FORMAT PARQUET, COMPRESSION ZSTD)
        """)

    con.execute(f"""
        COPY (SELECT * FROM variable_reference)
        TO '{PARQUET_DIR / "variable_reference.parquet"}'
        (FORMAT PARQUET)
    """)

    con.execute(f"""
        COPY (SELECT * FROM dataset_metadata)
        TO '{PARQUET_DIR / "dataset_metadata.parquet"}'
        (FORMAT PARQUET)
    """)

    print(f"Parquet files written to {PARQUET_DIR}")


if __name__ == "__main__":
    main()
