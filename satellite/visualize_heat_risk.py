
from pathlib import Path

import rasterio
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap, BoundaryNorm

ROOT = Path(__file__).resolve().parents[1]

RASTER = ROOT / "data" / "satellite" / "delhi_heat_risk.tif"
BOUNDARY = ROOT / "data" / "city_boundaries" / "delhi_boundary.geojson"

OUTPUT = ROOT / "outputs" / "satellite_maps"
OUTPUT.mkdir(parents=True, exist_ok=True)

# Read Delhi boundary
delhi = gpd.read_file(BOUNDARY)

# Risk categories
colors = ["#2E9D63", "#E4C542", "#E88A32", "#D94A43"]

cmap = ListedColormap(colors)
bounds = [0, 25, 50, 75, 100]
norm = BoundaryNorm(bounds, cmap.N)

# Read heat risk raster
with rasterio.open(RASTER) as src:

    risk = src.read(1, masked=True).astype("float32")
    risk = risk.filled(np.nan)

    extent = [
        src.bounds.left,
        src.bounds.right,
        src.bounds.bottom,
        src.bounds.top
    ]

    boundary = delhi.to_crs(src.crs)

# Plot map
fig, ax = plt.subplots(figsize=(11, 9))

image = ax.imshow(
    risk,
    cmap=cmap,
    norm=norm,
    extent=extent,
    origin="upper"
)

# Delhi boundary
boundary.boundary.plot(
    ax=ax,
    color="black",
    linewidth=1
)

# Legend
colorbar = plt.colorbar(
    image,
    ax=ax,
    boundaries=bounds,
    ticks=[12.5, 37.5, 62.5, 87.5],
    shrink=0.75
)

colorbar.ax.set_yticklabels([
    "Low",
    "Moderate",
    "High",
    "Very High"
])

colorbar.set_label("Relative Heat Risk")

ax.set_title(
    "HeatSafe AI - Delhi Heat Risk Map",
    fontsize=16,
    fontweight="bold"
)

ax.set_xlabel("Easting (metres)")
ax.set_ylabel("Northing (metres)")

plt.tight_layout()

output_file = OUTPUT / "delhi_heat_risk_map.png"

plt.savefig(
    output_file,
    dpi=300,
    bbox_inches="tight"
)

plt.close()

print("Delhi Heat Risk Map generated!")
print(f"Saved at: {output_file}")
