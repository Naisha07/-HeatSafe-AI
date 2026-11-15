
from pathlib import Path
from contextlib import asynccontextmanager
from io import BytesIO
from datetime import datetime

import joblib
import numpy as np
import pandas as pd
import rasterio

from PIL import Image
from rasterio.warp import transform
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field


# ==========================================
# PROJECT PATHS
# ==========================================

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent

SATELLITE_DIR = (
    ROOT_DIR / "data" / "satellite" / "multidate"
)

MODEL_PATH = ROOT_DIR / "models" / "heat_risk_model.joblib"

RISK_COLORS = [
    (44, 162, 95),    # Low
    (255, 255, 102), # Moderate
    (253, 141, 60),  # High
    (189, 0, 38)     # Very High
]


# ==========================================
# AVAILABLE SATELLITE DATES
# ==========================================

def get_available_dates():

    if not SATELLITE_DIR.exists():
        return []

    dates = []

    for folder in SATELLITE_DIR.iterdir():

        if not folder.is_dir():
            continue

        processed = folder / "processed"

        required_files = [
            "delhi_lst_celsius.tif",
            "delhi_ndvi.tif",
            "delhi_ndbi.tif",
            "delhi_heat_risk.tif"
        ]

        if all((processed / name).exists() for name in required_files):
            dates.append(folder.name)

    return sorted(dates)


def validate_date(date):

    available = get_available_dates()

    if date not in available:
        raise HTTPException(
            status_code=404,
            detail=f"Satellite data not available for {date}"
        )

    return SATELLITE_DIR / date / "processed"


def get_selected_date(date=None):

    available = get_available_dates()

    if not available:
        raise HTTPException(
            status_code=503,
            detail="No processed satellite observations found."
        )

    if date is None:
        return available[-1]

    if date not in available:
        raise HTTPException(
            status_code=404,
            detail=f"Date unavailable. Available dates: {available}"
        )

    return date


# ==========================================
# READ SATELLITE RASTERS
# ==========================================

def read_raster(path):

    with rasterio.open(path) as src:

        data = src.read(1, masked=True)

        array = data.filled(np.nan).astype("float32")

        valid = (
            ~np.ma.getmaskarray(data)
            & np.isfinite(array)
        )

        profile = src.profile.copy()

    return array, valid, profile


def load_satellite_data(date):

    folder = validate_date(date)

    lst, lst_valid, profile = read_raster(
        folder / "delhi_lst_celsius.tif"
    )

    ndvi, ndvi_valid, _ = read_raster(
        folder / "delhi_ndvi.tif"
    )

    ndbi, ndbi_valid, _ = read_raster(
        folder / "delhi_ndbi.tif"
    )

    risk, risk_valid, _ = read_raster(
        folder / "delhi_heat_risk.tif"
    )

    if not (
        lst.shape == ndvi.shape == ndbi.shape == risk.shape
    ):
        raise HTTPException(
            status_code=500,
            detail="Satellite raster dimensions do not match."
        )

    valid = (
        lst_valid
        & ndvi_valid
        & ndbi_valid
        & risk_valid
    )

    if not np.any(valid):
        raise HTTPException(
            status_code=500,
            detail="No valid satellite pixels found."
        )

    return {
        "lst": lst,
        "ndvi": ndvi,
        "ndbi": ndbi,
        "risk": risk,
        "valid": valid,
        "profile": profile
    }


# ==========================================
# RISK CLASSIFICATION
# ==========================================

def classify_risk(score):

    if score < 25:
        return 0, "Low"

    elif score < 50:
        return 1, "Moderate"

    elif score < 75:
        return 2, "High"

    return 3, "Very High"


# ==========================================
# LOAD ML MODEL
# ==========================================

@asynccontextmanager
async def lifespan(app: FastAPI):

    app.state.model = None

    print("\nStarting HeatSafe AI backend...")

    print(f"Satellite directory: {SATELLITE_DIR}")

    print("Available observations:", get_available_dates())

    if MODEL_PATH.exists():

        try:
            app.state.model = joblib.load(MODEL_PATH)
            print("Existing ML model loaded.")

        except Exception as error:
            print(f"Model loading failed: {error}")

    else:
        print("ML model file not found.")

    yield

    print("HeatSafe AI backend stopped.")


# ==========================================
# FASTAPI APPLICATION
# ==========================================

app = FastAPI(
    title="HeatSafe AI API",
    description="Delhi satellite-based urban heat analysis API",
    version="2.0.0",
    lifespan=lifespan
)


# ==========================================
# CORS
# ==========================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://heat-safe-ai-xi.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


# ==========================================
# PREDICTION INPUT
# ==========================================

class HeatPredictionInput(BaseModel):

    lst_c: float = Field(ge=15, le=65)
    ndvi: float = Field(ge=-1, le=1)
    built_up_pct: float = Field(ge=0, le=100)
    population_density: float = Field(ge=0, le=100000)


# ==========================================
# HOME
# ==========================================

@app.get("/")
def home():

    return {
        "message": "Welcome to HeatSafe AI",
        "status": "Backend is running",
        "data_source": "Landsat Collection 2 Level 2"
    }


# ==========================================
# HEALTH CHECK
# ==========================================

@app.get("/api/health")
def health_check():

    dates = get_available_dates()

    return {
        "status": "online",
        "model_loaded": app.state.model is not None,
        "satellite_data_available": len(dates) > 0,
        "available_observations": dates,
        "data_source": "Landsat 8/9 Collection 2 Level 2"
    }


# ==========================================
# AVAILABLE SATELLITE DATES
# ==========================================

@app.get("/api/satellite/dates")
def satellite_dates():

    dates = get_available_dates()

    return {
        "total_observations": len(dates),
        "dates": dates,
        "default_date": dates[-1] if dates else None
    }


# ==========================================
# SATELLITE STATISTICS
# ==========================================

@app.get("/api/satellite/statistics")
def satellite_statistics(
    date: str | None = Query(default=None)
):

    selected_date = get_selected_date(date)
    data = load_satellite_data(selected_date)

    valid = data["valid"]

    lst = data["lst"][valid]
    ndvi = data["ndvi"][valid]
    ndbi = data["ndbi"][valid]
    risk = data["risk"][valid]

    total = len(risk)

    distribution = {}

    categories = [
        (0, "Low"),
        (1, "Moderate"),
        (2, "High"),
        (3, "Very High")
    ]

    for class_id, label in categories:

        count = int(np.count_nonzero(
            (risk >= class_id * 25)
            & (
                risk < (class_id + 1) * 25
                if class_id < 3
                else risk <= 100
            )
        ))

        distribution[label] = {
            "pixels": count,
            "percentage": round(count / total * 100, 2)
        }

    return {
        "date": selected_date,
        "data_source": "Landsat 8/9 Collection 2 Level 2",
        "measurement": "Land Surface Temperature, not air temperature",
        "valid_pixels": total,
        "lst_c": {
            "mean": round(float(np.mean(lst)), 2),
            "min": round(float(np.min(lst)), 2),
            "max": round(float(np.max(lst)), 2)
        },
        "ndvi": {
            "mean": round(float(np.mean(ndvi)), 3),
            "min": round(float(np.min(ndvi)), 3),
            "max": round(float(np.max(ndvi)), 3)
        },
        "ndbi": {
            "mean": round(float(np.mean(ndbi)), 3),
            "min": round(float(np.min(ndbi)), 3),
            "max": round(float(np.max(ndbi)), 3)
        },
        "mean_heat_risk": round(float(np.mean(risk)), 2),
        "risk_distribution": distribution
    }


# ==========================================
# SATELLITE GRID LOCATIONS
# ==========================================

@app.get("/api/locations")
def get_locations(
    date: str | None = Query(default=None),
    max_points: int = Query(default=2500, ge=100, le=10000)
):

    selected_date = get_selected_date(date)
    data = load_satellite_data(selected_date)

    lst = data["lst"]
    ndvi = data["ndvi"]
    ndbi = data["ndbi"]
    risk = data["risk"]
    valid = data["valid"]

    profile = data["profile"]

    height, width = lst.shape

    step = max(
        1,
        int(np.sqrt((height * width) / max_points))
    )

    rows = np.arange(0, height, step)
    cols = np.arange(0, width, step)

    row_grid, col_grid = np.meshgrid(rows, cols, indexing="ij")

    sampled_valid = valid[row_grid, col_grid]

    selected_rows = row_grid[sampled_valid]
    selected_cols = col_grid[sampled_valid]

    x_coords, y_coords = rasterio.transform.xy(
        profile["transform"],
        selected_rows,
        selected_cols,
        offset="center"
    )

    longitude, latitude = transform(
        profile["crs"],
        "EPSG:4326",
        list(x_coords),
        list(y_coords)
    )

    records = []

    for index, (row, col) in enumerate(
        zip(selected_rows, selected_cols)
    ):

        score = float(risk[row, col])
        risk_class, risk_level = classify_risk(score)

        records.append({
            "location": f"Delhi grid cell {index + 1}",
            "latitude": round(latitude[index], 6),
            "longitude": round(longitude[index], 6),
            "lst_c": round(float(lst[row, col]), 2),
            "ndvi": round(float(ndvi[row, col]), 3),
            "ndbi": round(float(ndbi[row, col]), 3),
            "heat_risk": round(score, 2),
            "risk_class": risk_class,
            "risk_level": risk_level
        })

    return {
        "date": selected_date,
        "total_grid_points": len(records),
        "data_source": "Actual processed Landsat satellite rasters",
        "locations": records
    }


# ==========================================
# HEAT-RISK MAP IMAGE
# ==========================================

@app.get("/api/satellite/map")
def satellite_map(
    date: str | None = Query(default=None)
):

    selected_date = get_selected_date(date)
    data = load_satellite_data(selected_date)

    risk = data["risk"]
    valid = data["valid"]

    height, width = risk.shape

    rgba = np.zeros((height, width, 4), dtype=np.uint8)

    for class_id, color in enumerate(RISK_COLORS):

        lower = class_id * 25
        upper = (class_id + 1) * 25

        if class_id == 3:
            mask = valid & (risk >= lower) & (risk <= 100)
        else:
            mask = valid & (risk >= lower) & (risk < upper)

        rgba[mask, :3] = color
        rgba[mask, 3] = 255

    image = Image.fromarray(rgba, mode="RGBA")

    image_bytes = BytesIO()
    image.save(image_bytes, format="PNG")
    image_bytes.seek(0)

    return StreamingResponse(
        image_bytes,
        media_type="image/png",
        headers={
            "Cache-Control": "public, max-age=3600",
            "X-Observation-Date": selected_date
        }
    )


# ==========================================
# MAP BOUNDARIES
# ==========================================

@app.get("/api/satellite/bounds")
def satellite_bounds(
    date: str | None = Query(default=None)
):

    selected_date = get_selected_date(date)
    data = load_satellite_data(selected_date)

    profile = data["profile"]

    left, bottom, right, top = rasterio.transform.array_bounds(
        data["risk"].shape[0],
        data["risk"].shape[1],
        profile["transform"]
    )

    xs, ys = transform(
        profile["crs"],
        "EPSG:4326",
        [left, right, right, left],
        [bottom, bottom, top, top]
    )

    return {
        "date": selected_date,
        "bounds": [
            [min(ys), min(xs)],
            [max(ys), max(xs)]
        ]
    }


# ==========================================
# EXISTING ML PREDICTION ENDPOINT
# ==========================================

@app.post("/api/predict")
def predict_risk(data: HeatPredictionInput):

    model = app.state.model

    if model is None:
        raise HTTPException(
            status_code=503,
            detail="ML model not loaded."
        )

    try:

        features = [
            "lst_c",
            "ndvi",
            "built_up_pct",
            "population_density"
        ]

        input_data = pd.DataFrame(
            [[
                data.lst_c,
                data.ndvi,
                data.built_up_pct,
                data.population_density
            ]],
            columns=features
        )

        prediction = int(model.predict(input_data)[0])

        probabilities = model.predict_proba(input_data)[0]

        confidence = round(
            float(max(probabilities)) * 100,
            2
        )

        labels = {
            0: "Low",
            1: "Moderate",
            2: "High"
        }

        return {
            "risk_class": prediction,
            "risk_level": labels.get(prediction, "Unknown"),
            "confidence": confidence,
            "input": data.model_dump(),
            "data_status": "Legacy model trained on illustrative data; not a validated satellite prediction."
        }

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=f"Prediction failed: {str(error)}"
        )
