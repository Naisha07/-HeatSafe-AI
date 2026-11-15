
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

INPUT = (
    ROOT / "data" / "satellite"
    / "historical_scene_inventory.csv"
)

OUTPUT = (
    ROOT / "data" / "satellite"
    / "selected_scene_inventory.csv"
)

# Read historical scene inventory
df = pd.read_csv(INPUT)

# Ensure numerical columns are numeric
df["cloud_cover"] = pd.to_numeric(
    df["cloud_cover"], errors="coerce"
)

df["delhi_coverage_percent"] = pd.to_numeric(
    df["delhi_coverage_percent"], errors="coerce"
)

# Initial quality criteria
eligible = df[
    (df["cloud_cover"] < 20)
    & (df["delhi_coverage_percent"] >= 95)
].copy()

# Select the clearest scene in each month
selected = (
    eligible
    .sort_values(
        ["month", "cloud_cover", "delhi_coverage_percent"],
        ascending=[True, True, False]
    )
    .drop_duplicates(subset="month")
    .sort_values("date")
)

# Identify months without a qualifying scene
all_months = pd.period_range(
    "2024-01",
    "2026-11",
    freq="M"
).astype(str)

selected_months = set(selected["month"])

missing_months = [
    month for month in all_months
    if month not in selected_months
]

# Save selected observations
selected.to_csv(OUTPUT, index=False)

print("\nHISTORICAL SCENE SELECTION")
print("=" * 55)

print(f"Total candidate scenes: {len(df)}")
print(f"Eligible scenes: {len(eligible)}")
print(f"Selected monthly scenes: {len(selected)}")

print("\nSELECTED SCENES")
print("-" * 55)

for _, scene in selected.iterrows():

    print(
        f"{scene['month']} | "
        f"{scene['scene_id']} | "
        f"Cloud: {scene['cloud_cover']}% | "
        f"Coverage: {scene['delhi_coverage_percent']}%"
    )

print("\nMONTHS WITHOUT QUALIFYING SCENES")
print("-" * 55)

for month in missing_months:
    print(month)

print(f"\nSaved selection: {OUTPUT}")
