# East Sea (Biển Đông) Analysis-Ready Dataset — Parquet Distribution

Daily surface temperature, salinity, and current fields for the East Sea /
Biển Đông (South China Sea), 2023–2025, derived from the Copernicus Marine
Service GLORYS12V1 reanalysis (`GLOBAL_MULTIYEAR_PHY_001_030`,
`cmems_mod_glo_phy_my_0.083deg_P1D-m`), masked to the exact maritime
boundary and reshaped into an analysis-ready format.

## Files

| File | Rows | Description |
|---|---|---|
| `measurements_wide.parquet` | 43,665,736 | One row per `(time, latitude, longitude)`, one column per variable. **Recommended starting point for most users.** |
| `measurements_long_thetao.parquet` | 43,665,736 | Long format, temperature only: `(time, latitude, longitude, value)`. |
| `measurements_long_so.parquet` | 43,665,736 | Long format, salinity only. |
| `measurements_long_uo.parquet` | 43,665,736 | Long format, eastward velocity only. |
| `measurements_long_vo.parquet` | 43,665,736 | Long format, northward velocity only. |
| `variable_reference.parquet` | 4 | Variable name → unit → long name lookup. |
| `dataset_metadata.parquet` | 1 | Provenance: product source, toolbox version, boundary polygon citation, license/attribution terms. |
| `checksums.sha256` | — | SHA-256 checksums for all `.parquet` files above, for integrity verification. |

One file per variable (rather than a single Hive-partitioned long table)
was chosen so every file is independently named and browsable in a flat
repository listing (e.g. Zenodo), consistent with this project's
`{variable}_{region}_...` naming convention used throughout the pipeline.

## Schema

**`measurements_wide.parquet`**

| Column | Type | Description |
|---|---|---|
| `time` | timestamp | Day (UTC) |
| `latitude` | double | Degrees north |
| `longitude` | double | Degrees east |
| `thetao` | double | Sea surface temperature, °C |
| `so` | double | Salinity, PSU |
| `uo` | double | Eastward velocity, m/s |
| `vo` | double | Northward velocity, m/s |

**`measurements_long_<variable>.parquet`**

| Column | Type | Description |
|---|---|---|
| `time` | timestamp | Day (UTC) |
| `latitude` | double | Degrees north |
| `longitude` | double | Degrees east |
| `value` | double | Value for the variable named in this file's filename (see `variable_reference.parquet` for units) |

## Coverage

- **Temporal:** 2023-01-01 to 2025-12-31, daily (1,096 distinct days)
- **Spatial:** masked to the IHO Sea Areas v3 "Bien Dong" polygon; effective
  extent approx. 102.33–122.08°E, −3.17–25.5°N; grid resolution ~0.0833°
  (native GLORYS12V1 grid, ~9 km); 39,841 distinct grid points
- **Depth:** surface only (0–1 m)
- Zero NULL values (points outside the maritime boundary or on land are
  excluded, not null-filled)

## Reading the data

Any of pandas, DuckDB, Spark, R (`arrow`), etc. work directly on these
files with no proprietary tooling required. For example, in DuckDB:

```sql
SELECT * FROM 'measurements_wide.parquet' LIMIT 10;
SELECT * FROM 'measurements_long_thetao.parquet';
```

or in pandas:

```python
import pandas as pd
df = pd.read_parquet("measurements_wide.parquet")
```

## Provenance / Citation

- **Source data:** E.U. Copernicus Marine Service Information —
  `GLOBAL_MULTIYEAR_PHY_001_030` (MERCATOR GLORYS12V1 reanalysis),
  retrieved via Copernicus Marine Toolbox v2.4.1.
- **Boundary polygon:** Flanders Marine Institute (2018). IHO Sea Areas,
  version 3. https://doi.org/10.14284/323 (feature "Bien Dong", `NAME_INTL`
  = "South China Sea").
- **License:** the underlying Copernicus Marine data is distributed under
  the Copernicus Marine Service's own "Licence to Use the Copernicus
  Marine Service Products" (free, perpetual, worldwide, non-exclusive,
  royalty-free — this is **not** CC-BY). Required attribution for any
  publication using this data: *"This study has been conducted using
  E.U. Copernicus Marine Service Information."*
- **Derived by:** Tran Nguyen Le Quan (Independent Researcher), as part of
  the ARD Pipeline for the East Sea project. See `docs/data_descriptor.md`
  in the project repository for full methodology.

## Regenerating this bundle

These files are produced from `ard_biendong.duckdb` by
`src/export_parquet.py`, which itself is populated by
`src/extract.py` → `src/transform.py` → `src/load.py` from the raw
Copernicus Marine subsets. See the project repository for the full
pipeline source.
