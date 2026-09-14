"""Extract: download quarterly surface subsets from Copernicus Marine.

For each variable, the 2023-2025 period is split into quarterly chunks and
each (variable, chunk) pair is fetched independently via
``copernicusmarine.subset()``. Output: 12 quarters x 4 variables = 48
NetCDF files in ``data/raw/``. Re-runs skip files that already exist.
"""
import copernicusmarine
from pathlib import Path
from datetime import date
from dateutil.relativedelta import relativedelta

# CONFIG
DATASET_ID = "cmems_mod_glo_phy_my_0.083deg_P1D-m"  # all 4 variables live in this dataset
REGION = "biendong"
VARIABLES = ["thetao", "so", "uo", "vo"]  # surface variables: no depth range needed

# Outer bounding box around the East Sea polygon (slightly wider than the
# polygon's true bbox so the mask step never runs out of data at the edges)
BBOX = {
    "minimum_longitude": 100.0,
    "maximum_longitude": 122.5,
    "minimum_latitude": -3.5,
    "maximum_latitude": 26.0,
}

SURFACE_DEPTH = {
    "minimum_depth": 0.0,
    "maximum_depth": 1.0,
}

TIME_START = date(2023, 1, 1)
TIME_END = date(2025, 12, 31)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
BOUNDARY_GEOJSON = PROJECT_ROOT / "bien_dong_boundary.geojson"

VERSION = 1


# CHUNKING
def generate_quarterly_chunks(start: date, end: date) -> list[tuple[date, date]]:
    chunks = []
    current = start
    while current <= end:
        chunk_end = current + relativedelta(months=3) - relativedelta(days=1)
        if chunk_end > end:
            chunk_end = end
        chunks.append((current, chunk_end))
        current = current + relativedelta(months=3)
    return chunks


# NAMING
def build_output_filename(variable: str, region: str, chunk_start: date, chunk_end: date, version: int = VERSION) -> str:
    d_start = chunk_start.strftime("%Y%m%d")
    d_end = chunk_end.strftime("%Y%m%d")
    return f"{variable}_{region}_{d_start}_{d_end}_v{version}.nc"


# EXTRACT (one chunk)
def subset_one_chunk(variable: str, chunk_start: date, chunk_end: date, output_path: Path) -> bool:
    if output_path.exists():
        print(f"Already exists: {output_path}, skipping")
        return True
    try:
        copernicusmarine.subset(
            dataset_id = DATASET_ID,
            variables = [variable],
            **BBOX,
            **SURFACE_DEPTH,
            start_datetime = chunk_start.isoformat(),
            end_datetime = chunk_end.isoformat(),
            output_filename = output_path.name,
            output_directory = output_path.parent,
        )
        return True
    except Exception as e:
        print(f"Error downloading {variable} ({chunk_start} - {chunk_end}): {e}")
        return False


# ORCHESTRATION (plain Python loop, no workflow engine)
def run_extract_all() -> None:
    region = REGION
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    chunks = generate_quarterly_chunks(TIME_START, TIME_END)
    success = []
    fail = []
    for variable in VARIABLES:
        for (c_start, c_end) in chunks:
            filename = build_output_filename(variable, region, c_start, c_end)
            output_path = RAW_DIR / filename
            ok = subset_one_chunk(variable, c_start, c_end, output_path)
            if ok:
                success.append((variable, c_start, c_end))
            else:
                fail.append((variable, c_start, c_end))
    print(f"Succeeded: {len(success)}/{len(success) + len(fail)}")
    if fail:
        print("Failed chunks:")
        for f in fail:
            print(f"  {f}")


if __name__ == "__main__":
    run_extract_all()
