
from pathlib import Path
from contextlib import asynccontextmanager

import joblib
import pandas as pd

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


# Project paths
BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent

DATA_PATH = ROOT_DIR / "dataset" / "delhi_heat_data.csv"
MODEL_PATH = ROOT_DIR / "models" / "heat_risk_model.joblib"

# Model input features
FEATURES = [
    "lst_c",
    "ndvi",
    "built_up_pct",
    "population_density"
]

RISK_LABELS = {
    0: "Low",
    1: "Moderate",
    2: "High"
}


# Load model when backend starts
@asynccontextmanager
async def lifespan(app: FastAPI):

    app.state.model = None

    print("\nStarting HeatSafe AI backend...")
    print(f"Looking for model at: {MODEL_PATH}")

    if MODEL_PATH.exists():
        try:
            app.state.model = joblib.load(MODEL_PATH)
            print("Model loaded successfully!")
        except Exception as error:
            print(f"Model loading failed: {error}")
    else:
        print("Model file not found. Train the model first.")

    yield

    print("HeatSafe AI backend stopped.")


# Create FastAPI application
app = FastAPI(
    title="HeatSafe AI API",
    description="Urban Heat Risk Mapping API for Delhi",
    version="1.0.0",
    lifespan=lifespan
)


# Allow React frontend to access backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


# Prediction input validation
class HeatPredictionInput(BaseModel):

    lst_c: float = Field(ge=15, le=65)
    ndvi: float = Field(ge=-1, le=1)
    built_up_pct: float = Field(ge=0, le=100)
    population_density: float = Field(
        ge=0, le=100000
    )


# Home route
@app.get("/")
def home():

    return {
        "message": "Welcome to HeatSafe AI",
        "status": "Backend is running"
    }


# Health check
@app.get("/api/health")
def health_check():

    return {
        "status": "online",
        "model_loaded": app.state.model is not None,
        "model_file_exists": MODEL_PATH.exists(),
        "model_path": str(MODEL_PATH)
    }


# Get Delhi location data
@app.get("/api/locations")
def get_locations():

    if not DATA_PATH.exists():
        raise HTTPException(
            status_code=404,
            detail="Delhi heat dataset not found"
        )

    try:
        df = pd.read_csv(DATA_PATH)

        records = df.where(
            pd.notnull(df), None
        ).to_dict(orient="records")

        return {
            "total_locations": len(records),
            "locations": records,
            "data_status": "Illustrative demo dataset"
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


# Predict heat risk
@app.post("/api/predict")
def predict_risk(data: HeatPredictionInput):

    model = app.state.model

    if model is None:
        raise HTTPException(
            status_code=503,
            detail="Model not loaded. Run train_model.py first."
        )

    try:

        input_data = pd.DataFrame(
            [{
                "lst_c": data.lst_c,
                "ndvi": data.ndvi,
                "built_up_pct": data.built_up_pct,
                "population_density": data.population_density
            }],
            columns=FEATURES
        )

        prediction = int(model.predict(input_data)[0])

        probabilities = model.predict_proba(input_data)[0]

        confidence = round(
            float(max(probabilities)) * 100, 2
        )

        return {
            "risk_class": prediction,
            "risk_level": RISK_LABELS.get(
                prediction, "Unknown"
            ),
            "confidence": confidence,
            "input": data.model_dump(),
            "data_status": "Illustrative demo dataset"
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Prediction failed: {str(error)}"
        )
