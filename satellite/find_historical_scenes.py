
from pathlib import Path
from collections import defaultdict

import geopandas as gpd
import pandas as pd

from pystac_client import Client
from shapely.geometry import shape
from shapely.ops import transform, unary_union
from pyproj import Transformer

# Project paths
ROOT = Path(__file__).resolve().parents[1]

BOUNDARY_FILE = (
    ROOT / "data" / "city_boundaries" / "delhi_boundary.geojson"
)

OUTPUT_DIR = ROOT / "data" / "satellite"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_CSV = OUTPUT_DIR / "historical_scene_inventory.csv"

# Load Delhi boundary
print("Loading Delhi boundary...")

delhi = gpd.read_file(BOUNDARY_FILE).to_crs("EPSG:4326")
delhi_geometry = unary_union(delhi.geometry)

# Convert geographic coordinates to an equal-area projection
project = Transformer.from_crs(
    "EPSG:4326",
    "EPSG:6933",
    always_xy=True
).transform

delhi_projected = transform(project, delhi_geometry)
delhi_area = delhi_projected.area

# Connect to Microsoft Planetary Computer
print("Connecting to satellite catalogue...")

catalog = Client.open(
    "https://planetarycomputer.microsoft.com/api/stac/v1"
)

# Search historical Landsat observations
print("Searching Landsat observations from 2024 to 2026...")

search = catalog.search(
    collections=["landsat-c2-l2"],
    intersects=delhi_geometry.__geo_interface__,
    datetime="2024-01-01T00:00:00Z/2026-11-15T23:59:59Z",
    query={
        "eo:cloud_cover": {
            "lt": 60
        }
    }
)

items = list(search.items())

print(f"Total candidate scenes found: {len(items)}")

# Calculate how much of Delhi each scene covers
records = []

for item in items:

    if not item.geometry:
        continue

    scene_geometry = shape(item.geometry)

    if not scene_geometry.is_valid:
        scene_geometry = scene_geometry.buffer(0)

    intersection = delhi_geometry.intersection(scene_geometry)

    if intersection.is_empty:
        continue

    intersection_projected = transform(project, intersection)

    coverage = (
        intersection_projected.area / delhi_area
    ) * 100

    observation_date = item.properties["datetime"]

    records.append({
        "scene_id": item.id,
        "date": observation_date,
        "month": observation_date[:7],
        "satellite": item.properties.get("platform", "Unknown"),
        "cloud_cover": item.properties.get("eo:cloud_cover"),
        "delhi_coverage_percent": round(coverage, 2)
    })

# Save complete inventory
df = pd.DataFrame(records)

if df.empty:
    print("No suitable scenes found. Check the catalogue query.")
    raise SystemExit

df = df.sort_values(
    ["month", "delhi_coverage_percent", "cloud_cover"],
    ascending=[True, False, True]
)

df.to_csv(OUTPUT_CSV, index=False)

print(f"\nInventory saved to: {OUTPUT_CSV}")

# Display the best two candidates per month
print("\nBEST CANDIDATE SCENES BY MONTH")
print("=" * 75)

for month, group in df.groupby("month"):

    print(f"\n{month}")

    best = group.head(2)

    for _, scene in best.iterrows():

        print(f"Scene: {scene['scene_id']}")
        print(f"Satellite: {scene['satellite']}")
        print(f"Cloud cover: {scene['cloud_cover']}%")
        print(
            f"Delhi coverage: "
            f"{scene['delhi_coverage_percent']}%"
        )
        print("-" * 45)

print("\nHistorical scene inventory completed!")
