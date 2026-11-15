
from pathlib import Path

import rasterio
import numpy as np

ROOT = Path(__file__).resolve().parents[1]

RASTER = ROOT / "data" / "satellite" / "delhi_heat_risk.tif"

categories = [
    ("Low", 0, 25),
    ("Moderate", 25, 50),
    ("High", 50, 75),
    ("Very High", 75, 100.0001)
]

with rasterio.open(RASTER) as src:

    risk = src.read(1, masked=True)
    values = risk.compressed()

    # Calculate pixel area in square metres
    pixel_area = abs(
        src.transform.a * src.transform.e
        - src.transform.b * src.transform.d
    )

    total_pixels = len(values)
    total_area = total_pixels * pixel_area

    print("\nDELHI HEAT RISK DISTRIBUTION")
    print("-" * 55)

    print(f"Valid pixels: {total_pixels:,}")
    print(f"Approximate valid area: {total_area / 1_000_000:.2f} km²")

    print("\nCategory-wise distribution")
    print("-" * 55)

    for name, lower, upper in categories:

        count = np.count_nonzero(
            (values >= lower) & (values < upper)
        )

        area_km2 = count * pixel_area / 1_000_000
        percentage = (count / total_pixels) * 100

        print(f"\n{name} Risk")
        print(f"Pixels: {count:,}")
        print(f"Area: {area_km2:.2f} km²")
        print(f"Percentage: {percentage:.2f}%")

    print("\nDistribution calculation completed!")
