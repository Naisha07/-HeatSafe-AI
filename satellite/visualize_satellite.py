
from pathlib import Path

import rasterio
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np

# Project folders
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "satellite"
BOUNDARY = ROOT / "data" / "city_boundaries" / "delhi_boundary.geojson"

OUTPUT = ROOT / "outputs" / "satellite_maps"
OUTPUT.mkdir(parents=True, exist_ok=True)

# Read Delhi boundary
delhi = gpd.read_file(BOUNDARY)

# Map configuration
maps = [
    {
        "file": "delhi_lst_celsius.tif",
        "title": "Delhi Land Surface Temperature",
        "color": "inferno",
        "label": "Temperature (°C)",
        "output": "delhi_temperature_map.png"
    },
    {
        "file": "delhi_ndvi.tif",
        "title": "Delhi Vegetation Index (NDVI)",
        "color": "YlGn",
        "label": "NDVI",
        "output": "delhi_ndvi_map.png"
    },
    {
        "file": "delhi_ndbi.tif",
        "title": "Delhi Built-up Index (NDBI)",
        "color": "coolwarm",
        "label": "NDBI",
        "output": "delhi_ndbi_map.png"
    }
]

for item in maps:

    raster_path = DATA / item["file"]

    with rasterio.open(raster_path) as src:

        # Read raster and convert invalid pixels to NaN
        image = src.read(1, masked=True).astype("float32")
        image = image.filled(np.nan)

        # Get map coordinates
        bounds = src.bounds
        extent = [
            bounds.left,
            bounds.right,
            bounds.bottom,
            bounds.top
        ]

        # Match boundary CRS with raster CRS
        boundary = delhi.to_crs(src.crs)

        # Display raster
        fig, ax = plt.subplots(figsize=(10, 8))

        valid = image[np.isfinite(image)]

        vmin = np.percentile(valid, 2)
        vmax = np.percentile(valid, 98)

        plot = ax.imshow(
            image,
            cmap=item["color"],
            extent=extent,
            origin="upper",
            vmin=vmin,
            vmax=vmax
        )

        # Add Delhi boundary
        boundary.boundary.plot(
            ax=ax,
            color="cyan",
            linewidth=1.2
        )

        # Add title and labels
        ax.set_title(item["title"], fontsize=15, fontweight="bold")
        ax.set_xlabel("Longitude / Easting")
        ax.set_ylabel("Latitude / Northing")

        plt.colorbar(
            plot,
            ax=ax,
            label=item["label"],
            shrink=0.75
        )

        plt.tight_layout()

        # Save map
        output_path = OUTPUT / item["output"]
        plt.savefig(output_path, dpi=300, bbox_inches="tight")

        plt.close()

        print(f"Map saved: {output_path}")

print("\nAll Delhi satellite maps generated successfully!")
