"""Transform: mask each raw NetCDF file to the exact East Sea polygon.

The land / out-of-polygon mask is identical for all four variables and for
every day inside a file, so it is computed once (from the first raw file)
and reused for all 48 files. Output: masked, zlib-compressed NetCDF files
in ``data/processed/``. Re-runs skip files that already exist.
"""
import re
from pathlib import Path

import geopandas as gpd
import regionmask
import xarray as xr

# CONFIG (same layout as extract.py)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
BOUNDARY_GEOJSON = PROJECT_ROOT / "bien_dong_boundary.geojson"

# Agreed filename convention: {variable}_{region}_{YYYYMMDD}_{YYYYMMDD}_v{n}.nc
FILENAME_PATTERN = re.compile(r"^(thetao|so|uo|vo)_biendong_\d{8}_\d{8}_v\d+\.nc$")


# VALIDATE INPUT
def list_valid_raw_files() -> list[Path]:
    valid = []
    for f in RAW_DIR.glob("*.nc"):
        if FILENAME_PATTERN.match(f.name):
            valid.append(f)
        else:
            print(f"{f} does not match the filename convention")
    return valid


# BUILD MASK (computed once, reused for every file)
def build_mask(sample_file: Path) -> xr.DataArray:
    gdf = gpd.read_file(BOUNDARY_GEOJSON)
    ds = xr.open_dataset(sample_file)
    return regionmask.mask_geopandas(gdf, ds.longitude, ds.latitude)


# TRANSFORM (one file)
def mask_one_file(input_path: Path, output_path: Path, mask: xr.DataArray) -> bool:
    if output_path.exists():
        print(f"{output_path} already exists, skipping")
        return True
    try:
        ds = xr.open_dataset(input_path)
        ds_mask = ds.where(mask.notnull())
        encoding = {var: {"zlib": True, "complevel": 4} for var in ds_mask.data_vars}
        ds_mask.to_netcdf(output_path, encoding=encoding)
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False


# ORCHESTRATION
def run_transform_all() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    raw_files = list_valid_raw_files()
    if not raw_files:
        print("No valid raw files found, stopping")
        return
    mask = build_mask(raw_files[0])
    success = []
    fail = []
    for input_path in raw_files:
        output_path = PROCESSED_DIR / input_path.name
        ok = mask_one_file(input_path, output_path, mask)
        if ok:
            success.append(input_path.name)
        else:
            fail.append(input_path.name)

    print(f"Succeeded: {len(success)}/{len(success) + len(fail)}")
    if fail:
        print("Failed files:")
        for f in fail:
            print(f" {f}")


if __name__ == "__main__":
    run_transform_all()
