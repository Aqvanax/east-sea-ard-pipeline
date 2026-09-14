# Data Descriptor

**An Analysis-Ready Dataset of Daily Sea Surface Temperature, Salinity, and
Currents for the East Sea (Biển Đông), 2023–2025, Derived from CMEMS
GLORYS12V1 Reanalysis**

Tran Nguyen Le Quan — Independent Researcher —
[ORCID 0009-0002-8803-3079](https://orcid.org/0009-0002-8803-3079)

Dataset DOI: [10.5281/zenodo.22069105](https://doi.org/10.5281/zenodo.22069105)

> The boundary polygon's own metadata (IHO Sea Areas v3) labels this region
> `NAME_INTL = "South China Sea"`. That name is kept here as a keyword so the
> dataset can be found under either name.

## Specifications

|---|---|
| Subject | Earth and Planetary Sciences; Oceanography |
| Specific subject area | Regional oceanographic reanalysis subset for the East Sea / Biển Đông (South China Sea), structured as analysis-ready tabular data |
| Type of data | Tabular (long-format and pivoted wide-format), derived from gridded NetCDF |
| Data collection | Subset via the Copernicus Marine Toolbox (v2.4.1) Python API from the CMEMS product `GLOBAL_MULTIYEAR_PHY_001_030` (dataset `cmems_mod_glo_phy_my_0.083deg_P1D-m`), MERCATOR GLORYS12V1 reanalysis. Surface-level (0–1 m) daily fields for 4 variables, retrieved in 12 quarterly chunks per variable (48 files) over a padded bounding box, then masked to the exact East Sea / Biển Đông polygon and loaded into a structured database |
| Data source location | Copernicus Marine Service (MERCATOR OCEAN INTERNATIONAL). Region: East Sea / Biển Đông (South China Sea). Masked extent: approx. 102.33–122.08°E, −3.17–25.5°N |
| Data accessibility | Zenodo, Apache Parquet: `measurements_wide.parquet` plus one `measurements_long_<variable>.parquet` per variable, `variable_reference.parquet`, `dataset_metadata.parquet`, `checksums.sha256`. DOI [10.5281/zenodo.22069105](https://doi.org/10.5281/zenodo.22069105) |

## Value of the data

- Lowers the barrier to working with GLORYS12V1 for East Sea / Biển
  Đông-focused research: the region mask, depth slicing and NetCDF → table
  reshaping are already done, and the result is a queryable long- and
  wide-format schema.
- Useful to regional oceanographers, marine spatial planners, and students
  studying sea surface temperature, salinity or current variability in
  this region, and to anyone building downstream tools (dashboards, ML
  models, teaching material) who wants a ready-to-query dataset rather
  than raw model output.
- Supports time-series analysis (seasonal / interannual SST or salinity
  trends), spatial analysis (current patterns via `uo`/`vo`), and can
  serve as a comparison baseline against in-situ or satellite observations.
- The open-source ETL pipeline (`src/extract.py`, `transform.py`,
  `load.py`, `export_parquet.py`) is reusable as-is for other CMEMS
  products or other maritime regions: chunked extraction, shared-mask
  transform, idempotent hash-based load.

## Data description

- **Region:** East Sea / Biển Đông, boundary defined by the IHO Sea Areas
  v3 polygon (Flanders Marine Institute, 2018;
  https://doi.org/10.14284/323), feature "Bien Dong"
  (`NAME_INTL` = "South China Sea").
- **Variables (surface only, 0–1 m):**

  | Variable | Long name | Unit |
  |---|---|---|
  | `thetao` | Temperature | degrees_C |
  | `so` | Salinity | PSU |
  | `uo` | Eastward velocity | m/s |
  | `vo` | Northward velocity | m/s |

- **Temporal coverage:** 2023-01-01 to 2025-12-31, daily (1,096 days).
- **Spatial resolution:** ~0.0833° (native GLORYS12V1 grid, ~9 km);
  39,841 grid points inside the masked polygon.
- **Volume:** 174,662,944 long-format rows
  (`time, latitude, longitude, variable, value`), zero NULL values.
- **Formats:**
  - **Parquet (distribution format, on Zenodo):** `measurements_wide.parquet`
    (43,665,736 rows, one column per variable) and four
    `measurements_long_<variable>.parquet` files (43,665,736 rows each),
    all zstd-compressed, ~724 MB total. Chosen over the DuckDB file for
    portability (pandas, DuckDB, Spark, R). One file per variable rather
    than a Hive-partitioned tree so every file is independently named and
    browsable in a flat repository listing.
  - **Intermediate NetCDF4** (masked, zlib `complevel=4`): 48 files,
    ~480 MB, in `data/processed/` — pipeline-internal, not deposited.
  - **DuckDB database** (`ard_biendong.duckdb`, ~9.8 GB, mostly primary-key
    indexes over 174 M rows) — pipeline-internal, not deposited:
    - `measurements` — long format, `PRIMARY KEY (time, latitude, longitude, variable)`
    - `measurements_wide` — view pivoting `measurements` to one column per
      variable, keyed on `(time, latitude, longitude)`
    - `load_log` — SHA-256 content-hash idempotency registry
    - `dataset_metadata` — single-row provenance record
    - `variable_reference` — variable → unit / long-name lookup

## Method

Four-stage ETL pipeline in Python (see `src/`):

1. **Extract.** For each of the 4 variables the 2023–2025 period is split
   into 12 quarterly chunks (`generate_quarterly_chunks`) and each
   variable × chunk is retrieved independently with
   `copernicusmarine.subset()`, restricted to 0–1 m depth and a padded
   bounding box (100.0–122.5°E, −3.5–26.0°N — deliberately wider than the
   polygon to guarantee full coverage after masking). Output filenames
   follow `{variable}_{region}_{start}_{end}_v{n}.nc`. Re-runs skip
   existing files.
2. **Transform.** A single land / out-of-polygon mask is computed once
   (`regionmask.mask_geopandas` against the IHO polygon) and reused for all
   48 files — the mask is identical across variables and across all days
   in a file. Each file is clipped with `xr.Dataset.where()` and written
   back as NetCDF4 with zlib compression (`complevel=4`).
3. **Load.** Each masked file is converted to a long-format dataframe
   (surface level selected, NaN rows dropped), hashed (SHA-256) for
   idempotency, and inserted into `measurements`. The `measurements_wide`
   view is created via conditional aggregation
   (`MAX(CASE WHEN variable = '…' THEN value END) … GROUP BY time,
   latitude, longitude`) rather than DuckDB's `PIVOT`, for stability inside
   a view definition given the small fixed variable set.
4. **Export.** `measurements_wide` and the per-variable slices of
   `measurements` are exported from DuckDB to zstd-compressed Parquet
   (`src/export_parquet.py`).

## Validation

- Zero NULL values in `measurements.value` after the full 174.6 M-row load.
- `measurements_wide` row count = `measurements` / 4 exactly
  (43,665,736 × 4 = 174,662,944): all four variables share identical
  spatial / temporal coverage, as expected from a single shared mask.
- After adding NetCDF compression, regenerated values were spot-checked
  against already-loaded rows and matched exactly — compression changed
  on-disk encoding only.
- Parquet export row counts and sample values match the DuckDB source
  (bit-identical on spot checks).
- The masked minimum longitude (102.33°E) vs. the 100.0°E fetch box was
  investigated: the polygon's true western edge is 102.238°E, so 102.33°E
  is simply the first 0.0833° grid cell inside it. Not a processing error.

## Known limitations

- `mlotst` (mixed layer depth) is not included in this version.
- Surface layer only; no vertical profiles.
- The dataset is a reanalysis product, not observations; it inherits
  GLORYS12V1's own model and assimilation characteristics.

## Attribution

This study has been conducted using E.U. Copernicus Marine Service
Information. Source product: `GLOBAL_MULTIYEAR_PHY_001_030`, MERCATOR
GLORYS12V1, retrieved with Copernicus Marine Toolbox 2.4.1. The
underlying data is distributed under the Copernicus Marine Service's own
licence (free, perpetual, worldwide, non-exclusive, royalty-free — not
CC-BY); the attribution sentence above is required in any publication
using it.

Boundary polygon: Flanders Marine Institute (2018). IHO Sea Areas,
version 3. https://www.marineregions.org/ — https://doi.org/10.14284/323

This is an independent, unfunded project undertaken for skill development
and as an open scientific contribution.
