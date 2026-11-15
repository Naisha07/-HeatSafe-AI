# 🌍 HeatSafe AI – Urban Heat Risk Mapping

**Satellite-Based Urban Heat Monitoring for Delhi, India**

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Vercel-black?logo=vercel)](https://heat-safe-ai-xi.vercel.app/)
[![Backend](https://img.shields.io/badge/Backend-Render-purple)](https://heatsafe-ai.onrender.com)

## 📌 Overview

HeatSafe AI is a geospatial platform that analyses satellite data to identify urban heat patterns across the National Capital Territory (NCT) of Delhi.

It uses Landsat 8 and 9 satellite observations to study land surface temperature, vegetation density and built-up areas, providing interactive heat-risk maps and location-based environmental insights.

## ✨ Key Features

- **Interactive Heat Map:** Visualise heat-risk patterns across Delhi.
- **Satellite Analysis:** Explore multiple observation dates.
- **Location Intelligence:** View environmental information for selected locations.
- **Environmental Insights:** Get rule-based recommendations based on local conditions.
- **Risk Distribution:** View Low, Moderate, High and Very High risk categories.
- **Multi-Date Analysis:** Compare satellite-derived environmental indicators.

## 🛰️ Data and Methodology

**Data Source:** Landsat 8/9 Collection 2 Level-2 via Microsoft Planetary Computer.

Environmental indicators:
- Land Surface Temperature (LST)
- Normalized Difference Vegetation Index (NDVI)
- Normalized Difference Built-up Index (NDBI)

An experimental relative heat-risk index combines:
- LST – 50%
- Inverse NDVI – 25%
- NDBI – 25%

*The index is experimental and is not an official heat warning or validated health-risk prediction.*

## 🛠️ Tech Stack

| Component | Technologies |
|---|---|
| Frontend | React.js, Vite, CSS |
| Mapping | Leaflet, React-Leaflet |
| Backend | Python, FastAPI |
| Data Processing | NumPy, Pandas, Rasterio |
| Satellite Data | Landsat 8/9 |
| Deployment | Vercel, Render |
| Version Control | Git, GitHub |

## 📂 Project Structure

```text
URBAN HEAT MAP/
├── Backend/
│   ├── main.py
│   └── requirements.txt
├── Frontend/
│   ├── src/
│   └── package.json
├── data/
│   ├── city_boundaries/
│   └── satellite/
├── satellite/
│   └── processing scripts
└── outputs/
    └── satellite_maps/
```

## 🚀 Live Deployment

- **Frontend:** https://heat-safe-ai-xi.vercel.app/
- **Backend:** https://heatsafe-ai.onrender.com
- **GitHub:** https://github.com/Naisha07/-HeatSafe-AI

## 🔮 Future Scope

- Integration of real-time air-quality data.
- Advanced machine-learning-based heat analysis.
- Historical heat trend monitoring.
- Population vulnerability analysis.
- Expansion to other Indian cities.

## 📚 Resources

- [USGS Landsat](https://www.usgs.gov/landsat-missions)
- [Microsoft Planetary Computer](https://planetarycomputer.microsoft.com/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [React](https://react.dev/)
- [Leaflet](https://leafletjs.com/)

---

**HeatSafe AI – Making Urban Heat Patterns Visible Through Satellite Data and Environmental Intelligence.**