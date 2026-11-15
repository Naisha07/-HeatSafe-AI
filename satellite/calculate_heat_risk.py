
from pathlib import Path

import numpy as np
import rasterio

# Project paths
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "satellite"

LST_FILE = DATA / "delhi_lst_celsius.tif"
NDVI_FILE = DATA / "delhi_ndvi.tif"
NDBI_FILE = DATA / "delhi_ndbi.tif"

OUTPUT_FILE = DATA / "delhi_heat_risk.tif"


def normalize(array, low, high):
    """Normalize values to a range of 0 to 1."""
    if high <= low:
        raise ValueError("Invalid normalization range.")

    result = (array - low) / (high - low)
    return np.clip(result, 0, 1)


print("Loading satellite indicators...")

with rasterio.open(LST_FILE) as lst_src, \
     rasterio.open(NDVI_FILE) as ndvi_src, \
     rasterio.open(NDBI_FILE) as ndbi_src:

    # Check that all rasters match
    if not (
        lst_src.shape == ndvi_src.shape == ndbi_src.shape
        and lst_src.transform == ndvi_src.transform == ndbi_src.transform
        and lst_src.crs == ndvi_src.crs == ndbi_src.crs
    ):
        raise ValueError("Satellite rasters are not aligned.")

    # Read data and identify NoData pixels
    lst = lst_src.read(1, masked=True).filled(np.nan).astype("float32")
    ndvi = ndvi_src.read(1, masked=True).filled(np.nan).astype("float32")
    ndbi = ndbi_src.read(1, masked=True).filled(np.nan).astype("float32")

    profile = lst_src.profile.copy()

print("Preparing valid pixels...")

# Use only pixels where all three indicators are available
valid = (
    np.isfinite(lst)
    & np.isfinite(ndvi)
    & np.isfinite(ndbi)
)

if not np.any(valid):
    raise ValueError("No common valid pixels found.")

lst_values = lst[valid]
ndvi_values = ndvi[valid]
ndbi_values = ndbi[valid]

print(f"Valid pixels: {len(lst_values)}")

# Normalize indicators using Delhi's 2nd and 98th percentiles
lst_low, lst_high = np.percentile(lst_values, [2, 98])
ndvi_low, ndvi_high = np.percentile(ndvi_values, [2, 98])
ndbi_low, ndbi_high = np.percentile(ndbi_values, [2, 98])

lst_risk = normalize(lst_values, lst_low, lst_high)

# Less vegetation means a higher potential heat-risk contribution
vegetation_risk = 1 - normalize(
    ndvi_values, ndvi_low, ndvi_high
)

# Higher built-up index means a higher potential heat-risk contribution
builtup_risk = normalize(
    ndbi_values, ndbi_low, ndbi_high
)

# Transparent weighted index
# Temperature: 50%
# Vegetation: 25%
# Built-up indicator: 25%
heat_risk = (
    0.50 * lst_risk
    + 0.25 * vegetation_risk
    + 0.25 * builtup_risk
) * 100

# Create output raster
result = np.full(lst.shape, -9999, dtype="float32")
result[valid] = heat_risk.astype("float32")

profile.update(
    dtype="float32",
    count=1,
    nodata=-9999,
    compress="lzw"
)

with rasterio.open(OUTPUT_FILE, "w", **profile) as dst:
    dst.write(result, 1)

    dst.set_band_description(
        1, "Relative Satellite-Based Heat Risk Index (0-100)"
    )

    dst.update_tags(
        formula="50% LST + 25% inverse NDVI + 25% NDBI",
        date="2026-11-01",
        interpretation="Exploratory relative index, not a validated health-risk prediction"
    )

print("\nHeat Risk Index generated successfully!")
print(f"Saved to: {OUTPUT_FILE}")
print(f"Minimum risk: {heat_risk.min():.2f}")
print(f"Maximum risk: {heat_risk.max():.2f}")
print(f"Mean risk: {heat_risk.mean():.2f}")
