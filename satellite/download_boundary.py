
import requests
import geopandas as gpd
from pathlib import Path

# GeoBoundaries API: India administrative level 1
api_url = "https://www.geoboundaries.org/api/current/gbOpen/IND/ADM1/"

print("Fetching Indian administrative boundaries...")

response = requests.get(api_url, timeout=60)
response.raise_for_status()

metadata = response.json()

geojson_url = metadata["gjDownloadURL"]

print("Downloading boundary data...")

output_dir = Path("data/city_boundaries")
output_dir.mkdir(parents=True, exist_ok=True)

output_file = output_dir / "india_states.geojson"

geo_response = requests.get(geojson_url, timeout=120)
geo_response.raise_for_status()

output_file.write_bytes(geo_response.content)

gdf = gpd.read_file(output_file)

print("\nAvailable state names:")
print(gdf["shapeName"].tolist())

# Find Delhi
delhi = gdf[
    gdf["shapeName"].str.contains("Delhi", case=False, na=False)
]

if delhi.empty:
    raise ValueError("Delhi boundary was not found.")

delhi_file = output_dir / "delhi_boundary.geojson"
delhi.to_file(delhi_file, driver="GeoJSON")

print("\nDelhi boundary saved successfully!")
print("File:", delhi_file)
print("Features:", len(delhi))
print("CRS:", delhi.crs)
print("Area (sq km):", round(delhi.to_crs("EPSG:32643").area.sum() / 1e6, 2))
