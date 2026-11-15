
from pathlib import Path

import numpy as np
import rasterio
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm


# Project directories
PROJECT_DIR = Path(__file__).resolve().parent.parent
SATELLITE_DIR = PROJECT_DIR / "data" / "satellite" / "multidate"
OUTPUT_DIR = PROJECT_DIR / "outputs" / "satellite_maps"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_risk_map(path):
    """Read a heat-risk raster and preserve its valid-data mask."""

    with rasterio.open(path) as src:
        data = src.read(1, masked=True)
        profile = src.profile.copy()

    array = data.filled(np.nan).astype("float32")

    valid = (
        ~np.ma.getmaskarray(data)
        & np.isfinite(array)
    )

    return array, valid, profile


def main():

    # Find all processed observation folders
    date_folders = sorted(
        folder for folder in SATELLITE_DIR.iterdir()
        if folder.is_dir()
        and (folder / "processed" / "delhi_heat_risk.tif").exists()
    )

    if len(date_folders) < 2:
        print("At least two processed observations are required.")
        return

    print(f"Found {len(date_folders)} heat-risk observations.")

    risk_arrays = []
    valid_masks = []
    dates = []

    reference_profile = None
    reference_shape = None

    # Load and verify all risk rasters
    for folder in date_folders:

        date = folder.name
        risk_path = folder / "processed" / "delhi_heat_risk.tif"

        print(f"\nLoading: {date}")

        risk, valid, profile = load_risk_map(risk_path)

        if reference_profile is None:
            reference_profile = profile
            reference_shape = risk.shape

        else:
            if risk.shape != reference_shape:
                raise ValueError(
                    f"Raster shape mismatch for {date}."
                )

            if profile["transform"] != reference_profile["transform"]:
                raise ValueError(
                    f"Raster transform mismatch for {date}."
                )

            if profile["crs"] != reference_profile["crs"]:
                raise ValueError(
                    f"CRS mismatch for {date}."
                )

        risk_arrays.append(risk)
        valid_masks.append(valid)
        dates.append(date)

        print(f"Valid pixels: {np.count_nonzero(valid):,}")

    # Stack all observations
    risks = np.stack(risk_arrays)
    valid_stack = np.stack(valid_masks)

    # A pixel must have valid data in every observation
    common_valid = np.all(valid_stack, axis=0)

    if not np.any(common_valid):
        print("No common valid pixels across observations.")
        return

    # High risk means score >= 50
    high_risk = (risks >= 50) & valid_stack

    # Count how many observations classify each pixel as high risk
    hotspot_count = np.sum(high_risk, axis=0).astype("uint8")

    # Exclude pixels without complete observations
    hotspot_count[~common_valid] = 255

    # Save persistence GeoTIFF
    output_tif = OUTPUT_DIR / "delhi_persistent_heat_hotspots.tif"

    profile = reference_profile.copy()
    profile.update(
        dtype="uint8",
        count=1,
        nodata=255,
        compress="lzw"
    )

    with rasterio.open(output_tif, "w", **profile) as dst:
        dst.write(hotspot_count, 1)
        dst.write_mask(common_valid.astype("uint8") * 255)

    # Calculate statistics
    total = np.count_nonzero(common_valid)

    print("\n" + "=" * 55)
    print("PERSISTENT HEAT HOTSPOT ANALYSIS")
    print("=" * 55)

    print(f"Observations: {len(dates)}")
    print(f"Common valid pixels: {total:,}")

    for count in range(len(dates) + 1):

        pixels = np.count_nonzero(
            common_valid & (hotspot_count == count)
        )

        percentage = pixels / total * 100

        if count == 0:
            label = "Never high risk"
        elif count == 1:
            label = "High risk in 1 observation"
        elif count == len(dates):
            label = "High risk in ALL observations"
        else:
            label = f"High risk in {count} observations"

        print(f"{label}: {pixels:,} pixels ({percentage:.2f}%)")

    # Generate persistence map
    colors = [
        "#2ca25f",  # 0 observations
        "#ffff66",  # 1 observation
        "#fd8d3c",  # 2 observations
        "#bd0026"   # 3 observations
    ]

    cmap = ListedColormap(colors)
    cmap.set_bad("white")

    boundaries = np.arange(-0.5, len(dates) + 1.5, 1)
    norm = BoundaryNorm(boundaries, cmap.N)

    display_data = np.ma.masked_where(
        ~common_valid,
        hotspot_count
    )

    fig, ax = plt.subplots(figsize=(10, 8))

    image = ax.imshow(
        display_data,
        cmap=cmap,
        norm=norm
    )

    colorbar = plt.colorbar(
        image,
        ax=ax,
        ticks=list(range(len(dates) + 1))
    )

    labels = [
        "0 observations",
        "1 observation",
        "2 observations",
        "3 observations"
    ]

    colorbar.ax.set_yticklabels(labels[:len(dates) + 1])
    colorbar.set_label("Number of observations with high relative risk")

    ax.set_title("Delhi Persistent Heat Hotspot Map")
    ax.set_xlabel("Raster column")
    ax.set_ylabel("Raster row")

    plt.tight_layout()

    output_png = OUTPUT_DIR / "delhi_persistent_heat_hotspots.png"

    plt.savefig(
        output_png,
        dpi=300,
        bbox_inches="tight"
    )

    plt.close()

    print("\nFiles saved successfully:")
    print(output_tif)
    print(output_png)

    print("\n" + "=" * 55)
    print("HISTORICAL HOTSPOT ANALYSIS COMPLETED!")
    print("=" * 55)


if __name__ == "__main__":
    main()
