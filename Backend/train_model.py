
from pathlib import Path

import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier

# Project paths
BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent

DATA_PATH = ROOT_DIR / "dataset" / "delhi_heat_data.csv"
MODEL_DIR = ROOT_DIR / "models"
MODEL_PATH = MODEL_DIR / "heat_risk_model.joblib"

# Input features
FEATURES = [
    "lst_c",
    "ndvi",
    "built_up_pct",
    "population_density"
]

TARGET = "risk_class"


def train_model():

    print("===================================")
    print("   HEATSAFE AI - MODEL TRAINING")
    print("===================================")

    # Check dataset
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found at: {DATA_PATH}"
        )

    print("\nLoading Delhi heat dataset...")

    df = pd.read_csv(DATA_PATH)

    # Check required columns
    required_columns = FEATURES + [TARGET]

    for column in required_columns:
        if column not in df.columns:
            raise ValueError(
                f"Missing required column: {column}"
            )

    # Clean data
    df = df[required_columns].apply(
        pd.to_numeric, errors="coerce"
    )

    df = df.dropna()

    if len(df) == 0:
        raise ValueError("Dataset contains no valid records.")

    X = df[FEATURES]
    y = df[TARGET].astype(int)

    if not set(y.unique()).issubset({0, 1, 2}):
        raise ValueError(
            "Risk classes must be 0, 1, or 2."
        )

    if y.nunique() < 2:
        raise ValueError(
            "At least two different risk classes are required."
        )

    print(f"Records loaded: {len(df)}")
    print("Training Random Forest model...")

    # Create model
    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=5,
        random_state=42,
        class_weight="balanced"
    )

    # Train model
    model.fit(X, y)

    # Create models folder if it doesn't exist
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    # Save trained model
    joblib.dump(model, MODEL_PATH)

    print("\nModel training completed successfully!")
    print(f"Training records: {len(df)}")
    print(f"Risk classes: {sorted(y.unique())}")
    print(f"Model saved at: {MODEL_PATH}")
    print("===================================")


if __name__ == "__main__":
    train_model()
