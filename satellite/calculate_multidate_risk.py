
from pathlib import Path

import numpy as np
import rasterio
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm


# Project folders
PROJECT_DIR = Path(__file__).resolve().parent.parent
SATELLITE_DIR = PROJECT_DIR / "data" / "satellite" / "multidate"
OUTPUT_DIR = PROJECT_DIR / "outputs" / "satellite_maps"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def normalize(array, valid_mask):
    """Normalize valid values using the 2nd and 98th percentiles."""

    values = array[valid_mask]

    low = np.percentile(values, 2)
    high = np.percentile(values, 98)

    if high == low:
        return np.zeros_like(array, dtype="float32")

    result = (array - low) / (high - low)

    return np.clip(result, 0, 1)


def process_date(date_folder):

    date = date_folder.name
    processed_folder = date_folder / "processed"

    lst_path = processed_folder / "delhi_lst_celsius.tif"
    ndvi_path = processed_folder / "delhi_ndvi.tif"
    ndbi_path = processed_folder / "delhi_ndbi.tif"

    if not all(path.exists() for path in [lst_path, ndvi_path, ndbi_path]):
        print(f"Skipping {date}: processed files missing.")
        return

    print("\n" + "=" * 55)
    print(f"Calculating heat risk for: {date}")
    print("=" * 55)

    # Read satellite indices
    with rasterio.open(lst_path) as src:
        lst_data = src.read(1, masked=True)
        profile = src.profile.copy()

    with rasterio.open(ndvi_path) as src:
        ndvi_data = src.read(1, masked=True)

    with rasterio.open(ndbi_path) as src:
        ndbi_data = src.read(1, masked=True)

    # Convert masked arrays to floating-point arrays
    lst = lst_data.filled(np.nan).astype("float32")
    ndvi = ndvi_data.filled(np.nan).astype("float32")
    ndbi = ndbi_data.filled(np.nan).astype("float32")

    # Keep only pixels valid in all three datasets
    valid = (
        ~np.ma.getmaskarray(lst_data)
        & ~np.ma.getmaskarray(ndvi_data)
        & ~np.ma.getmaskarray(ndbi_data)
        & np.isfinite(lst)
        & np.isfinite(ndvi)
        & np.isfinite(ndbi)
    )

    if np.count_nonzero(valid) == 0:
        print(f"No valid pixels found for {date}.")
        return

    # Normalize the three indicators
    lst_normalized = normalize(lst, valid)
    vegetation_risk = normalize(-ndvi, valid)
    builtup_risk = normalize(ndbi, valid)

    # Weighted exploratory heat-risk index
    risk = (
        0.50 * lst_normalized
        + 0.25 * vegetation_risk
        + 0.25 * builtup_risk
    ) * 100

    risk = risk.astype("float32")
    risk[~valid] = np.nan

    # Classify risk
    # 0-25: Low, 25-50: Moderate,
    # 50-75: High, 75-100: Very High
    risk_classes = np.full(risk.shape, 255, dtype="uint8")

    risk_classes[valid & (risk < 25)] = 1
    risk_classes[valid & (risk >= 25) & (risk < 50)] = 2
    risk_classes[valid & (risk >= 50) & (risk < 75)] = 3
    risk_classes[valid & (risk >= 75)] = 4

    # Save heat-risk GeoTIFF
    risk_path = processed_folder / "delhi_heat_risk.tif"

    profile.update(
        dtype="float32",
        count=1,
        nodata=-9999.0,
        compress="lzw"
    )

    with rasterio.open(risk_path, "w", **profile) as dst:
        dst.write(np.where(valid, risk, -9999).astype("float32"), 1)
        dst.write_mask(valid.astype("uint8") * 255)

    # Generate heat-risk map
    colors = ["#2ca25f", "#ffff66", "#fd8d3c", "#bd0026"]
    cmap = ListedColormap(colors)
    norm = BoundaryNorm([0, 25, 50, 75, 100], cmap.N)

    fig, ax = plt.subplots(figsize=(10, 8))

    image = ax.imshow(
        np.ma.masked_invalid(risk),
        cmap=cmap,
        norm=norm
    )

    colorbar = plt.colorbar(image, ax=ax, ticks=[12.5, 37.5, 62.5, 87.5])
    colorbar.ax.set_yticklabels(
        ["Low", "Moderate", "High", "Very High"]
    )
    colorbar.set_label("Relative Heat Risk")

    ax.set_title(f"Delhi Urban Heat Risk Map - {date}")
    ax.set_xlabel("Raster column")
    ax.set_ylabel("Raster row")

    plt.tight_layout()

    map_path = OUTPUT_DIR / f"delhi_heat_risk_{date}.png"
    plt.savefig(map_path, dpi=300, bbox_inches="tight")
    plt.close()

    # Print statistics
    print(f"Valid pixels: {np.count_nonzero(valid):,}")
    print(f"Mean risk score: {np.nanmean(risk):.2f}")
    print(f"Minimum risk: {np.nanmin(risk):.2f}")
    print(f"Maximum risk: {np.nanmax(risk):.2f}")

    print("\nRisk distribution:")

    labels = {
        1: "Low",
        2: "Moderate",
        3: "High",
        4: "Very High"
    }

    for class_id, label in labels.items():
        count = np.count_nonzero(risk_classes == class_id)
        percentage = count / np.count_nonzero(valid) * 100

        print(f"{label}: {count:,} pixels ({percentage:.2f}%)")

    print(f"\nGeoTIFF saved: {risk_path}")
    print(f"Map saved: {map_path}")


# Process every date folder
date_folders = sorted(
    folder for folder in SATELLITE_DIR.iterdir()
    if folder.is_dir() and (folder / "processed").exists()
)

print(f"Found {len(date_folders)} satellite observations.")

for folder in date_folders:
    process_date(folder)

print("\n" + "=" * 55)
print("ALL MULTI-DATE HEAT-RISK MAPS GENERATED!")
print("=" * 55)
