
from pathlib import Path

import geopandas as gpd
import numpy as np
import planetary_computer
import rasterio
from rasterio.mask import mask
from pystac_client import Client

# Project paths
ROOT = Path(__file__).resolve().parent.parent
BOUNDARY_FILE = ROOT / "data" / "city_boundaries" / "delhi_boundary.geojson"
OUTPUT_DIR = ROOT / "data" / "satellite"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SCENE_ID = "LC09_L2SP_146040_20261101_02_T1"

print("Loading Delhi boundary...")

delhi = gpd.read_file(BOUNDARY_FILE)

if delhi.crs is None:
    raise ValueError("Delhi boundary has no CRS.")

# Connect to Planetary Computer
print("Connecting to satellite catalogue...")

catalog = Client.open(
    "https://planetarycomputer.microsoft.com/api/stac/v1",
    modifier=planetary_computer.sign_inplace
)

# Retrieve exact scene
search = catalog.search(
    collections=["landsat-c2-l2"],
    ids=[SCENE_ID]
)

items = list(search.items())

if not items:
    raise ValueError("Selected Landsat scene not found.")

item = items[0]

print("Selected:", item.id)

# Bands to download
assets = {
    "temperature": "lwir11",
    "red": "red",
    "nir": "nir08",
    "swir": "swir16",
    "quality": "qa_pixel"
}

# Download and clip each band
for output_name, asset_name in assets.items():

    print(f"\nProcessing {output_name}...")

    if asset_name not in item.assets:
        raise ValueError(f"Missing asset: {asset_name}")

    signed_href = planetary_computer.sign(
        item.assets[asset_name].href
    )

    with rasterio.open(signed_href) as src:

        # Reproject Delhi boundary to raster CRS
        boundary = delhi.to_crs(src.crs)

        # Clip raster to Delhi
        clipped, transform = mask(
            src,
            boundary.geometry,
            crop=True,
            filled=False
        )

        profile = src.profile.copy()
        profile.update(
            driver="GTiff",
            height=clipped.shape[1],
            width=clipped.shape[2],
            transform=transform,
            count=1,
            compress="deflate"
        )

        output_file = OUTPUT_DIR / f"delhi_{output_name}.tif"

        # Preserve invalid pixels as NoData
        profile.update(
            nodata=-9999,
            dtype="float32"
        )

        data = clipped[0].astype("float32").filled(-9999)

        with rasterio.open(output_file, "w", **profile) as dst:
            dst.write(data, 1)

    print("Saved:", output_file)

print("\nAll satellite bands downloaded and clipped!")
print("Output directory:", OUTPUT_DIR)
