
from pathlib import Path
import pandas as pd
import geopandas as gpd
import planetary_computer
import rasterio

from pystac_client import Client
from rasterio.mask import mask

# Project paths
ROOT = Path(__file__).resolve().parents[1]

BOUNDARY_FILE = (
    ROOT / "data" / "city_boundaries"
    / "delhi_boundary.geojson"
)

CSV_FILE = (
    ROOT / "data" / "satellite"
    / "selected_scene_inventory.csv"
)

OUTPUT_DIR = (
    ROOT / "data" / "satellite" / "multidate"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Select three pilot months
PILOT_MONTHS = [
    "2024-02",
    "2025-06",
    "2026-11"
]

# Landsat assets
BANDS = [
    "lwir11",
    "red",
    "nir08",
    "swir16",
    "qa_pixel"
]

BAND_NAMES = {
    "lwir11": "temperature",
    "red": "red",
    "nir08": "nir",
    "swir16": "swir",
    "qa_pixel": "quality"
}

print("Loading selected satellite scenes...")

df = pd.read_csv(CSV_FILE)

selected = df[df["month"].isin(PILOT_MONTHS)]

if len(selected) != len(PILOT_MONTHS):
    raise ValueError(
        "One or more pilot months are missing from the selection CSV."
    )

# Load Delhi boundary
delhi = gpd.read_file(BOUNDARY_FILE)

# Connect to catalogue
catalog = Client.open(
    "https://planetarycomputer.microsoft.com/api/stac/v1"
)

# Download each scene
for _, row in selected.iterrows():

    scene_id = row["scene_id"]
    date = pd.to_datetime(row["date"]).strftime("%Y-%m-%d")

    print("\n" + "=" * 55)
    print(f"Processing: {scene_id}")
    print(f"Observation date: {date}")

    # Find exact scene
    search = catalog.search(
        collections=["landsat-c2-l2"],
        ids=[scene_id]
    )

    items = list(search.items())

    if not items:
        print("Scene not found. Skipping.")
        continue

    item = planetary_computer.sign(items[0])

    scene_folder = OUTPUT_DIR / date
    scene_folder.mkdir(parents=True, exist_ok=True)

    downloaded = 0

    for band in BANDS:

        if band not in item.assets:
            print(f"Missing asset: {band}")
            continue

        asset = item.assets[band]

        output_name = (
            f"delhi_{BAND_NAMES[band]}.tif"
        )

        output_path = scene_folder / output_name

        print(f"Downloading and clipping: {band}")

        try:
            with rasterio.open(asset.href) as src:

                # Convert boundary to raster CRS
                boundary = delhi.to_crs(src.crs)

                geometries = [
                    geom.__geo_interface__
                    for geom in boundary.geometry
                    if geom is not None and not geom.is_empty
                ]

                # Clip while retaining the pixel validity mask
                clipped, transform = mask(
                    src,
                    geometries,
                    crop=True,
                    filled=False
                )

                profile = src.profile.copy()

                profile.update(
                    height=clipped.shape[1],
                    width=clipped.shape[2],
                    transform=transform,
                    count=1,
                    compress="deflate"
                )

                # Preserve invalid pixels using an internal mask
                with rasterio.open(
                    output_path,
                    "w",
                    **profile
                ) as dst:

                    dst.write(clipped.filled(0))
                    dst.write_mask(
                        (~clipped.mask[0]).astype("uint8") * 255
                    )

                downloaded += 1

                print(f"Saved: {output_path}")

        except Exception as error:
            print(f"Error processing {band}: {error}")

    print(f"Bands saved: {downloaded}/{len(BANDS)}")

print("\nPilot satellite download completed!")
