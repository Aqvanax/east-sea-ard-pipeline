"""Load: insert the masked NetCDF files into a DuckDB database.

Each file is converted to a long-format dataframe (surface level only,
NaN rows dropped) and appended to ``measurements``. A SHA-256 hash of the
file content is recorded in ``load_log`` so re-running the script never
loads the same file twice. Also creates the ``measurements_wide`` view and
the two small reference tables.
"""
import hashlib
import re
from datetime import datetime
from pathlib import Path

import duckdb
import xarray as xr

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
DB_PATH = PROJECT_ROOT / "ard_biendong.duckdb"

FILENAME_PATTERN = re.compile(r"^(thetao|so|uo|vo)_biendong_\d{8}_\d{8}_v\d+\.nc$")


def list_valid_processed_files() -> list[Path]:
    valid = []
    for f in PROCESSED_DIR.glob("*.nc"):
        if FILENAME_PATTERN.match(f.name):
            valid.append(f)
        else:
            print(f"{f} does not match the filename convention")
    return valid


def compute_file_hash(file_path: Path) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
        return h.hexdigest()

def extract_variable_name(file_path: Path) -> str:
    return FILENAME_PATTERN.match(file_path.name).group(1)


def is_already_loaded(con: duckdb.DuckDBPyConnection, file_hash: str) -> bool:
    con.execute("SELECT COUNT(*) FROM load_log WHERE hash = ?", [file_hash])
    row = con.fetchone()
    return row[0] > 0


def netcdf_to_long_dataframe(file_path: Path, variable_name: str):
    ds = xr.open_dataset(file_path)
    ds = ds.isel(depth=0)
    df = ds[variable_name].to_dataframe().reset_index()
    df = df.drop(columns=["depth"])
    df = df.rename(columns={variable_name: "value"})
    df["variable"] = variable_name
    df = df.dropna(subset=["value"])
    return df


def insert_measurements(con: duckdb.DuckDBPyConnection, df) -> int:
    con.execute("""
        INSERT INTO measurements (time, latitude, longitude, variable, value)
        SELECT time, latitude, longitude, variable, value FROM df
    """)
    return len(df)


def log_loaded_file(con, file_name: str, file_hash: str, n_rows: int) -> None:
    con.execute(
        "INSERT INTO load_log VALUES (?, ?, ?, ?)",
        [file_name, file_hash, datetime.now(), n_rows]
    )


def main():
    con = duckdb.connect(str(DB_PATH))

    con.execute("""
    CREATE TABLE IF NOT EXISTS measurements (
    time TIMESTAMP,
    latitude    DOUBLE,
    longitude   DOUBLE,
    variable    VARCHAR,
    value       DOUBLE,
    PRIMARY KEY (time, latitude, longitude, variable)
    )
    """)
    con.execute("""
    CREATE TABLE IF NOT EXISTS load_log (
    file_name       VARCHAR,
    hash            VARCHAR,
    load_time       TIMESTAMP,
    inserted_line   INTEGER,
    PRIMARY KEY (hash)
    )
    """)
    con.execute("""
    CREATE TABLE IF NOT EXISTS dataset_metadata (
    product_source       VARCHAR,
    toolbox_version      VARCHAR,
    polygon_description  VARCHAR,
    license              VARCHAR,
    PRIMARY KEY (product_source)
    )
    """)
    con.execute("""
    CREATE TABLE IF NOT EXISTS variable_reference (
    variable_name  VARCHAR,
    unit           VARCHAR,
    long_name      VARCHAR,
    PRIMARY KEY (variable_name)
    )
    """)

    con.execute("""
    CREATE OR REPLACE VIEW measurements_wide AS
    SELECT
        time,
        latitude,
        longitude,
        MAX(CASE WHEN variable = 'thetao' THEN value END) AS thetao,
        MAX(CASE WHEN variable = 'so'     THEN value END) AS so,
        MAX(CASE WHEN variable = 'uo'     THEN value END) AS uo,
        MAX(CASE WHEN variable = 'vo'     THEN value END) AS vo
    FROM measurements
    GROUP BY time, latitude, longitude
    """)

    con.execute("INSERT OR IGNORE INTO variable_reference VALUES ('thetao', 'degrees_C', 'Temperature')")
    con.execute("INSERT OR IGNORE INTO variable_reference VALUES ('so', 'PSU', 'Salinity')")
    con.execute("INSERT OR IGNORE INTO variable_reference VALUES ('uo', 'm/s', 'Eastward velocity')")
    con.execute("INSERT OR IGNORE INTO variable_reference VALUES ('vo', 'm/s', 'Northward velocity')")
    con.execute(
        "INSERT OR IGNORE INTO dataset_metadata VALUES (?, ?, ?, ?)",
        [
            "MERCATOR GLORYS12V1",
            "2.4.1",
            "Flanders Marine Institute (2018). IHO Sea Areas, version 3, feature: "
            "Bien Dong / South China Sea. https://doi.org/10.14284/323",
            "Licence to Use the Copernicus Marine Service Products (free, perpetual, "
            "worldwide, non-exclusive, royalty-free; NOT CC-BY). Required attribution "
            "for publications: \"This study has been conducted using E.U. Copernicus "
            "Marine Service Information\"",
        ],
    )

    for file in list_valid_processed_files():
        h = compute_file_hash(file)
        if is_already_loaded(con, h):
            print(f"Skipping {file.name} (already loaded)")
            continue
        var = extract_variable_name(file)
        df = netcdf_to_long_dataframe(file, var)
        n = insert_measurements(con, df)
        log_loaded_file(con, file.name, h, n)
        print(f"Loaded {file.name}: {n} rows")


if __name__ == "__main__":
    main()
