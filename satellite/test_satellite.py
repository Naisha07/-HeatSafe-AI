
from pystac_client import Client
import planetary_computer

DELHI_BBOX = [76.84, 28.40, 77.35, 28.88]

catalog = Client.open(
    "https://planetarycomputer.microsoft.com/api/stac/v1",
    modifier=planetary_computer.sign_inplace
)

search = catalog.search(
    collections=["landsat-c2-l2"],
    bbox=DELHI_BBOX,
    datetime="2026-01-01/2026-11-15",
    query={"eo:cloud_cover": {"lt": 20}},
    max_items=100
)

items = list(search.items())

print("Total scenes found:", len(items))

for item in items[:15]:
    print("\n------------------------------")
    print("Scene:", item.id)
    print("Date:", item.datetime.date())
    print("Satellite:", item.properties.get("platform"))
    print("Cloud cover:", item.properties.get("eo:cloud_cover"))

    print("Scene footprint:", item.bbox)

    print("Temperature available:", "lwir11" in item.assets)
    print("Temperature band:", item.assets.get("lwir11").href[:100]
          if "lwir11" in item.assets else "Not available")

    print("Available assets:", list(item.assets.keys()))

print("\nScene inspection completed!")
