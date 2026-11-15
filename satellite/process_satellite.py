
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "satellite"

# Input files
temperature_file = DATA / "delhi_temperature.tif"
red_file = DATA / "delhi_red.tif"
nir_file = DATA / "delhi_nir.tif"
swir_file = DATA / "delhi_swir.tif"
quality_file = DATA / "delhi_quality.tif"

# Output files
outputs = {
    "lst": DATA / "delhi_lst_celsius.tif",
    "ndvi": DATA / "delhi_ndvi.tif",
    "ndbi": DATA / "delhi_ndbi.tif"
}

NODATA = -9999.0

print("Loading downloaded Landsat bands...")

def read_band(path):
    with rasterio.open(path) as src:
        data = src.read(1).astype("float32")
        profile = src.profile.copy()
        return data, profile

temp_dn, profile = read_band(temperature_file)
red_dn, red_profile = read_band(red_file)
nir_dn, nir_profile = read_band(nir_file)
swir_dn, swir_profile = read_band(swir_file)
qa, qa_profile = read_band(quality_file)

# Ensure all rasters are aligned
for name, other in [
    ("red", red_profile),
    ("nir", nir_profile),
    ("swir", swir_profile),
    ("quality", qa_profile)
]:
    if (
        profile["width"] != other["width"]
        or profile["height"] != other["height"]
        or profile["transform"] != other["transform"]
        or profile["crs"] != other["crs"]
    ):
        raise ValueError(f"{name} raster is not aligned with temperature.")

print("All raster bands are aligned.")

# Mask invalid pixels and cloud-related QA flags.
# QA_PIXEL bits:
# 0 fill, 1 dilated cloud, 2 cirrus,
# 3 cloud, 4 cloud shadow, 5 snow.

qa_integer = np.where(
    np.isfinite(qa) & (qa >= 0),
    qa,
    65535
).astype("uint16")

bad_bits = (1 << 0) | (1 << 1) | (1 << 2) | \
           (1 << 3) | (1 << 4) | (1 << 5)

valid = (
    np.isfinite(temp_dn) &
    np.isfinite(red_dn) &
    np.isfinite(nir_dn) &
    np.isfinite(swir_dn) &
    ((qa_integer & bad_bits) == 0) &
    (temp_dn > 0) &
    (red_dn > 0) &
    (nir_dn > 0) &
    (swir_dn > 0)
)

print("Valid pixels:", int(valid.sum()))
print("Invalid/cloud-masked pixels:", int((~valid).sum()))

# Landsat Collection 2 Level-2 temperature scaling
# ST_B10 = DN * 0.00341802 + 149.0 Kelvin
lst_kelvin = temp_dn * 0.00341802 + 149.0
lst_celsius = lst_kelvin - 273.15

# Surface reflectance scaling
# SR = DN * 0.0000275 - 0.2
red = red_dn * 0.0000275 - 0.2
nir = nir_dn * 0.0000275 - 0.2
swir = swir_dn * 0.0000275 - 0.2

# Calculate NDVI
ndvi_denominator = nir + red

ndvi = np.divide(
    nir - red,
    ndvi_denominator,
    out=np.full_like(nir, np.nan),
    where=np.abs(ndvi_denominator) > 1e-6
)

# Calculate NDBI
ndbi_denominator = swir + nir

ndbi = np.divide(
    swir - nir,
    ndbi_denominator,
    out=np.full_like(swir, np.nan),
    where=np.abs(ndbi_denominator) > 1e-6
)

# Exclude invalid and physically unusable values
valid_lst = valid & np.isfinite(lst_celsius) & \
            (lst_celsius >= -50) & (lst_celsius <= 100)

valid_ndvi = valid & np.isfinite(ndvi) & \
             (ndvi >= -1) & (ndvi <= 1)

valid_ndbi = valid & np.isfinite(ndbi) & \
             (ndbi >= -1) & (ndbi <= 1)

results = [
    ("lst", lst_celsius, valid_lst),
    ("ndvi", ndvi, valid_ndvi),
    ("ndbi", ndbi, valid_ndbi)
]

# Save derived rasters
profile.update(
    driver="GTiff",
    dtype="float32",
    count=1,
    nodata=NODATA,
    compress="deflate"
)

for name, values, mask_valid in results:

    output = np.where(mask_valid, values, NODATA).astype("float32")

    with rasterio.open(outputs[name], "w", **profile) as dst:
        dst.write(output, 1)

    print("\nSaved:", outputs[name])

    if mask_valid.any():
        print("Minimum:", round(float(values[mask_valid].min()), 3))
        print("Maximum:", round(float(values[mask_valid].max()), 3))
        print("Mean:", round(float(values[mask_valid].mean()), 3))
    else:
        print("WARNING: No valid pixels found.")

print("\nDelhi satellite processing completed!")
