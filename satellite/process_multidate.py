
from pathlib import Path

import numpy as np
import rasterio

# ==========================================
# 1. PROJECT PATHS
# ==========================================

ROOT = Path(__file__).resolve().parents[1]

MULTIDATE = ROOT / "data" / "satellite" / "multidate"

# Landsat Collection 2 Level-2 scaling factors
THERMAL_SCALE = 0.00341802
THERMAL_OFFSET = 149.0

REFLECTANCE_SCALE = 0.0000275
REFLECTANCE_OFFSET = -0.2


# ==========================================
# 2. SAVE PROCESSED RASTER
# ==========================================

def save_raster(path, array, profile, description):

    output_profile = profile.copy()

    output_profile.update(
        dtype="float32",
        count=1,
        nodata=-9999,
        compress="lzw"
    )

    output = np.where(
        np.isfinite(array),
        array,
        -9999
    ).astype("float32")

    with rasterio.open(path, "w", **output_profile) as dst:

        dst.write(output, 1)

        dst.set_band_description(
            1,
            description
        )


# ==========================================
# 3. PROCESS ONE SATELLITE DATE
# ==========================================

def process_date(folder):

    print("\n" + "=" * 55)
    print(f"Processing date: {folder.name}")

    files = {
        "temperature": folder / "delhi_temperature.tif",
        "red": folder / "delhi_red.tif",
        "nir": folder / "delhi_nir.tif",
        "swir": folder / "delhi_swir.tif",
        "quality": folder / "delhi_quality.tif"
    }

    # Check all required files
    for name, path in files.items():

        if not path.exists():
            raise FileNotFoundError(
                f"Missing {name} file: {path}"
            )

    # ======================================
    # 4. READ THERMAL RASTER
    # ======================================

    with rasterio.open(files["temperature"]) as src:

        thermal_ma = src.read(1, masked=True)

        profile = src.profile.copy()

        reference = (
            src.shape,
            src.transform,
            src.crs
        )

    # ======================================
    # 5. READ REMAINING RASTERS
    # ======================================

    bands = {}

    for name in ["red", "nir", "swir", "quality"]:

        with rasterio.open(files[name]) as src:

            current = (
                src.shape,
                src.transform,
                src.crs
            )

            if current != reference:
                raise ValueError(
                    f"{name} raster is not aligned with temperature."
                )

            bands[name] = src.read(1, masked=True)

    # ======================================
    # 6. CONVERT DATA TYPES SAFELY
    # ======================================

    thermal = (
        thermal_ma
        .astype("float32")
        .filled(np.nan)
    )

    red_dn = (
        bands["red"]
        .astype("float32")
        .filled(np.nan)
    )

    nir_dn = (
        bands["nir"]
        .astype("float32")
        .filled(np.nan)
    )

    swir_dn = (
        bands["swir"]
        .astype("float32")
        .filled(np.nan)
    )

    # Preserve the QA mask before filling missing values
    qa_valid = ~np.ma.getmaskarray(bands["quality"])

    qa = (
        bands["quality"]
        .filled(0)
        .astype("uint16")
    )

    # ======================================
    # 7. CLOUD AND INVALID PIXEL MASKING
    # ======================================

    # QA_PIXEL bits:
    # 0 = Fill
    # 1 = Dilated cloud
    # 2 = Cirrus
    # 3 = Cloud
    # 4 = Cloud shadow
    # 5 = Snow

    bad_pixels = (
        ((qa & (1 << 0)) != 0)
        | ((qa & (1 << 1)) != 0)
        | ((qa & (1 << 2)) != 0)
        | ((qa & (1 << 3)) != 0)
        | ((qa & (1 << 4)) != 0)
        | ((qa & (1 << 5)) != 0)
    )

    # ======================================
    # 8. CALCULATE LAND SURFACE TEMPERATURE
    # ======================================

    lst_kelvin = (
        thermal * THERMAL_SCALE
        + THERMAL_OFFSET
    )

    lst_celsius = lst_kelvin - 273.15

    # ======================================
    # 9. CONVERT SURFACE REFLECTANCE
    # ======================================

    red = (
        red_dn * REFLECTANCE_SCALE
        + REFLECTANCE_OFFSET
    )

    nir = (
        nir_dn * REFLECTANCE_SCALE
        + REFLECTANCE_OFFSET
    )

    swir = (
        swir_dn * REFLECTANCE_SCALE
        + REFLECTANCE_OFFSET
    )

    # ======================================
    # 10. CALCULATE NDVI
    # ======================================

    ndvi_denominator = nir + red

    ndvi = np.divide(
        nir - red,
        ndvi_denominator,
        out=np.full(
            red.shape,
            np.nan,
            dtype="float32"
        ),
        where=np.abs(ndvi_denominator) > 1e-6
    )

    # ======================================
    # 11. CALCULATE NDBI
    # ======================================

    ndbi_denominator = swir + nir

    ndbi = np.divide(
        swir - nir,
        ndbi_denominator,
        out=np.full(
            red.shape,
            np.nan,
            dtype="float32"
        ),
        where=np.abs(ndbi_denominator) > 1e-6
    )

    # ======================================
    # 12. FINAL VALID PIXEL MASK
    # ======================================

    valid = (
        qa_valid
        & ~bad_pixels
        & np.isfinite(thermal)
        & np.isfinite(red)
        & np.isfinite(nir)
        & np.isfinite(swir)
        & np.isfinite(lst_celsius)
        & np.isfinite(ndvi)
        & np.isfinite(ndbi)
        & (red > 0)
        & (nir > 0)
        & (swir > 0)
        & (lst_celsius > -100)
        & (lst_celsius < 100)
    )

    lst_output = np.where(
        valid,
        lst_celsius,
        np.nan
    )

    ndvi_output = np.where(
        valid,
        ndvi,
        np.nan
    )

    ndbi_output = np.where(
        valid,
        ndbi,
        np.nan
    )

    # ======================================
    # 13. SAVE PROCESSED RASTERS
    # ======================================

    output_folder = folder / "processed"

    output_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    save_raster(
        output_folder / "delhi_lst_celsius.tif",
        lst_output,
        profile,
        "Land Surface Temperature in Celsius"
    )

    save_raster(
        output_folder / "delhi_ndvi.tif",
        ndvi_output,
        profile,
        "Normalized Difference Vegetation Index"
    )

    save_raster(
        output_folder / "delhi_ndbi.tif",
        ndbi_output,
        profile,
        "Normalized Difference Built-up Index"
    )

    # ======================================
    # 14. DISPLAY STATISTICS
    # ======================================

    print(f"Valid pixels: {valid.sum():,}")

    print(
        f"Invalid/cloud-masked pixels: "
        f"{(~valid).sum():,}"
    )

    statistics = [
        ("LST (Celsius)", lst_output),
        ("NDVI", ndvi_output),
        ("NDBI", ndbi_output)
    ]

    for name, values in statistics:

        valid_values = values[np.isfinite(values)]

        if len(valid_values) == 0:
            raise ValueError(
                f"No valid pixels found for {name} on {folder.name}"
            )

        print(
            f"{name}: "
            f"Min={valid_values.min():.3f}, "
            f"Max={valid_values.max():.3f}, "
            f"Mean={valid_values.mean():.3f}"
        )

    print("Processed files saved successfully!")


# ==========================================
# 15. PROCESS ALL SATELLITE DATES
# ==========================================

def main():

    folders = sorted(
        folder
        for folder in MULTIDATE.iterdir()
        if folder.is_dir()
        and (folder / "delhi_quality.tif").exists()
    )

    if not folders:
        raise RuntimeError(
            "No downloaded satellite date folders found."
        )

    print(
        f"Found {len(folders)} satellite observations."
    )

    for folder in folders:
        process_date(folder)

    print("\n" + "=" * 55)
    print("ALL MULTI-DATE PROCESSING COMPLETED!")
    print("=" * 55)


if __name__ == "__main__":
    main()
