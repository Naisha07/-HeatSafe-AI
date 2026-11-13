# 🌡️ HeatSafe AI – Urban Heat Risk Mapping & Prediction

**An AI-powered platform to identify urban heat risk across Delhi and provide recommendations for reducing heat exposure.**

🔗 **Live Demo:** https://heat-safe-ai-xi.vercel.app/  
🔗 **API Documentation:** https://heatsafe-ai.onrender.com/docs

## 📌 Overview

Rapid urbanisation, increasing built-up areas and declining vegetation contribute to rising urban temperatures. HeatSafe AI aims to make urban heat patterns easier to explore through an interactive dashboard and Machine Learning-based risk prediction.

Users can explore selected Delhi locations, view environmental indicators and predict heat risk as **Low, Moderate or High**.

## ✨ Key Features

- Interactive Delhi heat-risk dashboard.
- Location search and map visualisation.
- Environmental indicators: LST, NDVI, built-up percentage and population density.
- Random Forest-based heat-risk prediction.
- Risk-based recommendations to reduce heat trapping.
- Health and safety suggestions based on predicted risk.

## 🧠 Machine Learning

**Algorithm:** Random Forest Classifier

**Input Features:**
- Land Surface Temperature (LST)
- Normalized Difference Vegetation Index (NDVI)
- Built-up Area Percentage
- Population Density

**Output:** Low, Moderate or High heat risk.

## 🛠️ Tech Stack

| Component | Technologies |
|---|---|
| Frontend | React.js, Vite, CSS |
| Maps | React Leaflet, OpenStreetMap |
| Backend | Python, FastAPI |
| Machine Learning | Scikit-learn, Random Forest |
| Data Processing | Pandas, NumPy |
| Deployment | Vercel, Render |
| Version Control | Git, GitHub |

## 🏗️ Project Structure

```text
-HeatSafe-AI/
├── Backend/
│   ├── main.py
│   ├── requirements.txt
│   └── train_model.py
├── Frontend/
│   ├── src/
│   ├── package.json
│   └── vite.config.js
├── dataset/
│   └── delhi_heat_data.csv
├── models/
│   └── heat_risk_model.joblib
├── .gitignore
└── README.md
```

## ⚙️ Run Locally

**1. Clone the repository**

```bash
git clone https://github.com/Naisha07/-HeatSafe-AI.git
cd -HeatSafe-AI
```

**2. Start the backend**

```bash
cd Backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

**3. Start the frontend** in a separate terminal:

```bash
cd Frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser. For local development, configure the frontend API URL to `http://127.0.0.1:8000`.

## ☁️ Deployment

- **Frontend:** [Vercel](https://heat-safe-ai-xi.vercel.app/)
- **Backend:** [Render](https://heatsafe-ai.onrender.com/)
- **API Docs:** [FastAPI Documentation](https://heatsafe-ai.onrender.com/docs)

## ⚠️ Dataset Disclaimer

The current project uses a small illustrative dataset of 12 Delhi locations. Predictions are intended for demonstration and educational purposes, not validated real-world heat-risk assessments. Model confidence should not be interpreted as real-world accuracy.

## 🚀 Future Scope

- Integration of real satellite and weather data.
- Expanded neighbourhood-level heat mapping.
- Improved model training and validation.
- Heat-risk forecasting and alerts.

---

**🌍 Building cooler and safer cities with AI.**