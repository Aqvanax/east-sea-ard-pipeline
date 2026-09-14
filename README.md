# East Sea (Biển Đông) Analysis-Ready Ocean Dataset

An ETL pipeline that turns Copernicus Marine **GLORYS12V1** reanalysis output
into an analysis-ready, tabular dataset of daily sea surface temperature,
salinity and currents for the East Sea / Biển Đông (South China Sea),
2023–2025.

**The dataset itself is published on Zenodo:**
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22069105.svg)](https://doi.org/10.5281/zenodo.22069105)

| | |
|---|---|
| Rows | 174,662,944 (long format) / 43,665,736 (wide format), zero NULLs |
| Variables | `thetao` (SST, °C), `so` (salinity, PSU), `uo` / `vo` (surface current, m/s) |
| Time | 2023-01-01 → 2025-12-31, daily (1,096 days) |
| Space | 39,841 grid points inside the IHO "Bien Dong" polygon, ~0.083° (~9 km) |
| Depth | surface only (0–1 m) |
| Format | Apache Parquet (zstd), ~724 MB total |

## Why

GLORYS12V1 is a global, gridded NetCDF product. Anyone who wants to study
just this sea has to redo the same chores: pick a bounding box, mask land
and neighbouring seas with a polygon, slice the depth axis, and reshape the
grid into something a dataframe or SQL engine can use. This project does
that once and publishes the result, so a student or analyst can go from
`pd.read_parquet(...)` to a plot in one step.

## Pipeline

```
Copernicus Marine API
        │  src/extract.py      12 quarters × 4 variables = 48 subsets (padded bbox, 0–1 m)
        ▼
data/raw/*.nc  (~800 MB)
        │  src/transform.py    one polygon mask, computed once and reused for all 48 files
        ▼
data/processed/*.nc  (~480 MB, zlib)
        │  src/load.py         NetCDF → long dataframe → DuckDB; SHA-256 idempotency log
        ▼
ard_biendong.duckdb  (~9.8 GB)
        │  src/export_parquet.py
        ▼
data/parquet/*.parquet  (~724 MB)  ──►  Zenodo
```

`src/check_db.py` prints row counts, NULL check, and the real spatial /
temporal extent after loading.

### Design decisions

- **Quarterly chunks** (`{variable}_{region}_{start}_{end}_v{n}.nc`) as the
  unit of work everywhere — small enough to retry a single failed download,
  large enough that 48 files cover the whole scope.
- **One shared mask.** Land / out-of-polygon cells are identical for every
  variable and every day, so the `regionmask` mask is built once and reused.
- **Padded fetch box, exact polygon mask.** The download bbox (100.0–122.5°E,
  −3.5–26.0°N) is deliberately wider than the polygon; the polygon (IHO Sea
  Areas v3, "Bien Dong") is what defines the dataset extent.
- **Long table + wide view.** `measurements` is long
  (`time, latitude, longitude, variable, value`) with a composite primary
  key; `measurements_wide` is a conditional-aggregation view on top. Long
  keeps the schema trivially extensible; wide is what most users want.
- **Content-hash idempotency.** `load.py` records the SHA-256 of every file
  it loads, so re-running the pipeline after a partial failure is safe.
- **Parquet, one file per variable, for distribution** instead of the DuckDB
  file: readable by pandas / DuckDB / Spark / R without any specific engine,
  and every file is independently named so it browses correctly on Zenodo.

### Validation

- 0 NULL values in 174.6 M rows after masking.
- `measurements_wide` rows × 4 == `measurements` rows exactly → all four
  variables share identical coverage.
- Parquet exports cross-checked against DuckDB (row counts and
  spot-checked values bit-identical).
- The masked minimum longitude (102.33°E) vs. the 100.0°E fetch box was
  investigated: the polygon's true western edge is 102.238°E, so this is
  the first grid cell inside it — expected, not a bug.

Full write-up: [`docs/data_descriptor.md`](docs/data_descriptor.md).
Schema of the Parquet files: [`data/parquet/README.md`](data/parquet/README.md).

## Using the data

You do not need to run the pipeline. Download the Parquet files from
[Zenodo](https://doi.org/10.5281/zenodo.22069105) and:

```python
import pandas as pd
df = pd.read_parquet("measurements_wide.parquet")
```

```sql
-- DuckDB
SELECT time, AVG(thetao) AS mean_sst
FROM 'measurements_wide.parquet'
GROUP BY time ORDER BY time;
```

Verify integrity with `sha256sum -c data/parquet/checksums.sha256`.

[`examples/quickstart.ipynb`](examples/quickstart.ipynb) does exactly this:
it downloads `measurements_wide.parquet` (or uses the local copy), and with
three `GROUP BY` queries produces the monthly basin-mean SST series and
maps of mean SST and mean surface current speed — no geospatial library
needed.

## Reproducing the pipeline

```bash
python -m venv pyvenv && source pyvenv/bin/activate   # fish: activate.fish
pip install -r requirements.txt
copernicusmarine login          # free Copernicus Marine account required

python src/extract.py           # ~800 MB download
python src/transform.py
python src/load.py              # writes ard_biendong.duckdb (~9.8 GB)
python src/check_db.py
python src/export_parquet.py
```

Every stage is idempotent: re-running skips work that is already done.

## Repository layout

```
src/                     pipeline scripts (extract → transform → load → export)
bien_dong_boundary.geojson   IHO Sea Areas v3 "Bien Dong" polygon used for masking
data/parquet/README.md   data card / schema for the published Parquet files
data/parquet/checksums.sha256
docs/data_descriptor.md  full description of the dataset and method
examples/quickstart.ipynb    read the published Parquet and plot it (3 queries, 3 figures)
```

Large artefacts (`data/raw`, `data/processed`, `*.duckdb`, `*.parquet`) are
git-ignored; the published files live on Zenodo.

## Attribution and licenses

- **Code:** MIT (see `LICENSE`).
- **Dataset (Zenodo):** CC-BY 4.0 for the derived tables. The underlying
  data is *E.U. Copernicus Marine Service Information*, distributed under
  the Copernicus Marine Service's own licence (free, perpetual, worldwide,
  non-exclusive, royalty-free). Any publication using it must state:
  *"This study has been conducted using E.U. Copernicus Marine Service
  Information."*
- **Source product:** `GLOBAL_MULTIYEAR_PHY_001_030`
  (`cmems_mod_glo_phy_my_0.083deg_P1D-m`), MERCATOR GLORYS12V1, retrieved
  with Copernicus Marine Toolbox 2.4.1.
- **Boundary polygon:** Flanders Marine Institute (2018). IHO Sea Areas,
  version 3. https://doi.org/10.14284/323

## Author

Tran Nguyen Le Quan — Independent Researcher —
[ORCID 0009-0002-8803-3079](https://orcid.org/0009-0002-8803-3079)

The pipeline design and code are my own work. Claude Code (Anthropic) was
used as a reviewer during development and to help write the documentation
(README, data card, data descriptor).

Possible future work: add `mlotst` (mixed layer depth), extend the time
range.
