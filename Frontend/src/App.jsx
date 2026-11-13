
import React, { useEffect, useMemo, useState } from "react";

import {
  MapContainer,
  TileLayer,
  CircleMarker,
  Popup,
} from "react-leaflet";

import {
  getHealth,
  getLocations,
  predictRisk,
} from "./api";

const RISK_COLORS = {
  Low: "#16a34a",
  Moderate: "#ca8a04",
  High: "#dc2626",
};

function getRiskLabel(value) {
  const labels = {
    0: "Low",
    1: "Moderate",
    2: "High",
  };

  return labels[value] || "Unknown";
}

function getRiskColor(risk) {
  return RISK_COLORS[risk] || "#64748b";
}

// Recommendations based on predicted ML risk
function getHeatRecommendations(riskLevel, location) {
  const heatReduction = [
    "Plant native trees and increase vegetation cover to provide shade and reduce surface heating.",
    "Promote cool roofs and reflective building materials to reduce heat absorption.",
    "Create shaded pedestrian pathways and shaded public spaces.",
    "Protect existing parks, green belts and urban water bodies.",
    "Encourage rooftop gardens and community plantation drives.",
  ];

  if (Number(location.ndvi) < 0.2) {
    heatReduction.push(
      "Vegetation levels in this sample are low. Prioritise tree plantation and the development of green spaces."
    );
  }

  if (Number(location.built_up_pct) >= 75) {
    heatReduction.push(
      "Built-up coverage is high. Prioritise cool roofs, shaded streets and reflective surfaces."
    );
  }

  if (Number(location.population_density) >= 20000) {
    heatReduction.push(
      "Prioritise public drinking-water points, shaded waiting areas and heat-awareness campaigns in densely populated areas."
    );
  }

  const healthAdvice = {
    Low: [
      "Stay hydrated throughout the day.",
      "Wear light-coloured, breathable clothing when outdoors.",
      "Use sunscreen, sunglasses and a hat in direct sunlight.",
      "Take breaks in shaded areas during hot afternoons.",
    ],

    Moderate: [
      "Drink water frequently, even before feeling thirsty.",
      "Limit strenuous outdoor activities during peak afternoon heat.",
      "Take regular breaks in shaded or cool places.",
      "Wear loose, light-coloured cotton clothing.",
      "Check on children, older adults and outdoor workers.",
      "Keep indoor spaces cool and ventilated.",
    ],

    High: [
      "Avoid unnecessary outdoor exposure during the hottest hours.",
      "Stay in a cool or air-conditioned place wherever possible.",
      "Drink water regularly and avoid strenuous physical activity.",
      "Check frequently on children, older adults and vulnerable people.",
      "Never leave children or pets inside parked vehicles.",
      "Seek urgent medical assistance for confusion, fainting or suspected heatstroke.",
    ],
  };

  return {
    heatReduction,
    healthAdvice: healthAdvice[riskLevel] || [],
  };
}

function App() {
  const [locations, setLocations] = useState([]);
  const [health, setHealth] = useState(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [searchText, setSearchText] = useState("");
  const [selectedLocation, setSelectedLocation] = useState(null);

  const [prediction, setPrediction] = useState(null);
  const [predicting, setPredicting] = useState(false);
  const [predictionError, setPredictionError] = useState("");

  // Load backend data
  useEffect(() => {
    async function loadDashboard() {
      setLoading(true);
      setError("");

      try {
        const [healthData, locationData] = await Promise.all([
          getHealth(),
          getLocations(),
        ]);

        setHealth(healthData);
        setLocations(
          Array.isArray(locationData) ? locationData : []
        );
      } catch (err) {
        console.error("Dashboard loading error:", err);
        setError(err.message || "Unable to load dashboard.");
      } finally {
        setLoading(false);
      }
    }

    loadDashboard();
  }, []);

  // Dashboard statistics
  const statistics = useMemo(() => {
    const counts = {
      Low: 0,
      Moderate: 0,
      High: 0,
    };

    let totalTemperature = 0;
    let temperatureCount = 0;

    locations.forEach((location) => {
      const risk = getRiskLabel(location.risk_class);

      if (counts[risk] !== undefined) {
        counts[risk]++;
      }

      const temperature = Number(location.lst_c);

      if (Number.isFinite(temperature)) {
        totalTemperature += temperature;
        temperatureCount++;
      }
    });

    return {
      total: locations.length,
      low: counts.Low,
      moderate: counts.Moderate,
      high: counts.High,
      averageTemperature:
        temperatureCount > 0
          ? (totalTemperature / temperatureCount).toFixed(1)
          : "—",
    };
  }, [locations]);

  // Search location
  function handleLocationSearch(event) {
    const value = event.target.value;

    setSearchText(value);

    // Clear previous prediction when location changes
    setPrediction(null);
    setPredictionError("");

    const found = locations.find(
      (location) =>
        location.location.toLowerCase() ===
        value.trim().toLowerCase()
    );

    setSelectedLocation(found || null);
  }

  // Predict heat risk
  async function handlePrediction(event) {
    event.preventDefault();

    setPrediction(null);
    setPredictionError("");

    if (!selectedLocation) {
      setPredictionError(
        "Please select a valid location from the suggestions."
      );
      return;
    }

    if (!health?.model_loaded) {
      setPredictionError(
        "ML model is not loaded. Please restart the backend."
      );
      return;
    }

    setPredicting(true);

    try {
      const result = await predictRisk({
        lst_c: selectedLocation.lst_c,
        ndvi: selectedLocation.ndvi,
        built_up_pct: selectedLocation.built_up_pct,
        population_density: selectedLocation.population_density,
      });

      setPrediction(result);
    } catch (err) {
      console.error("Prediction error:", err);

      setPredictionError(
        err.message || "Unable to generate prediction."
      );
    } finally {
      setPredicting(false);
    }
  }

  const modelReady = health?.model_loaded === true;

  // Recommendations appear only after successful prediction
  const recommendations = prediction
    ? getHeatRecommendations(
        prediction.risk_level,
        selectedLocation
      )
    : null;

  return (
    <div style={styles.app}>

      {/* HEADER */}
      <header style={styles.header}>
        <div>
          <div style={styles.brand}>HEATSAFE AI</div>

          <h1 style={styles.heading}>
            Delhi Urban Heat Risk Dashboard
          </h1>

          <p style={styles.subtitle}>
            Explore urban heat patterns and predict heat risk across Delhi.
          </p>
        </div>

        <div style={styles.status}>
          <span
            style={{
              ...styles.statusDot,
              background: modelReady ? "#22c55e" : "#ef4444",
            }}
          />

          {modelReady ? "ML Model Online" : "Model Offline"}
        </div>
      </header>

      <main style={styles.main}>

        {loading && (
          <div style={styles.message}>
            Loading HeatSafe AI dashboard...
          </div>
        )}

        {error && (
          <div style={styles.error}>
            {error}
            <p>
              Make sure your FastAPI backend is running at
              http://127.0.0.1:8000.
            </p>
          </div>
        )}

        {!loading && !error && (
          <>

            {/* DASHBOARD STATISTICS */}
            <section style={styles.statsGrid}>
              <StatCard
                title="Total Locations"
                value={statistics.total}
                color="#2563eb"
              />

              <StatCard
                title="Average LST"
                value={`${statistics.averageTemperature}°C`}
                color="#ea580c"
              />

              <StatCard
                title="High Risk Locations"
                value={statistics.high}
                color="#dc2626"
              />

              <StatCard
                title="Moderate Risk Locations"
                value={statistics.moderate}
                color="#ca8a04"
              />
            </section>

            {/* HEAT MAP */}
            <section style={styles.section}>
              <h2 style={styles.sectionTitle}>
                Delhi Heat Risk Map
              </h2>

              <p style={styles.sectionDescription}>
                Explore heat-risk categories across the available sample
                locations. Click a marker to view its details.
              </p>

              <div style={styles.legend}>
                {["Low", "Moderate", "High"].map((risk) => (
                  <span key={risk} style={styles.legendItem}>
                    <span
                      style={{
                        ...styles.legendDot,
                        background: getRiskColor(risk),
                      }}
                    />
                    {risk} Risk
                  </span>
                ))}
              </div>

              <div style={styles.mapWrapper}>
                <MapContainer
                  center={[28.6139, 77.2090]}
                  zoom={10}
                  scrollWheelZoom={true}
                  style={styles.map}
                >
                  <TileLayer
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  />

                  {locations.map((location, index) => {
                    const latitude = Number(location.latitude);
                    const longitude = Number(location.longitude);

                    const risk = getRiskLabel(location.risk_class);

                    if (
                      !Number.isFinite(latitude) ||
                      !Number.isFinite(longitude)
                    ) {
                      return null;
                    }

                    return (
                      <CircleMarker
                        key={`${location.location}-${index}`}
                        center={[latitude, longitude]}
                        radius={10}
                        pathOptions={{
                          color: getRiskColor(risk),
                          fillColor: getRiskColor(risk),
                          fillOpacity: 0.75,
                        }}
                      >
                        <Popup>
                          <strong>{location.location}</strong>
                          <br />
                          Risk: {risk}
                          <br />
                          LST: {location.lst_c}°C
                          <br />
                          NDVI: {location.ndvi}
                          <br />
                          Built-up: {location.built_up_pct}%
                        </Popup>
                      </CircleMarker>
                    );
                  })}
                </MapContainer>
              </div>
            </section>

            {/* LOCATION SEARCH */}
            <section style={styles.section}>
              <h2 style={styles.sectionTitle}>
                Location-Based Heat Risk Prediction
              </h2>

              <p style={styles.sectionDescription}>
                Search for a Delhi location. HeatSafe AI automatically
                retrieves its environmental measurements and predicts
                its heat-risk category.
              </p>

              <form onSubmit={handlePrediction}>
                <label style={styles.field}>
                  <span style={styles.fieldLabel}>
                    Search Delhi Location
                  </span>

                  <input
                    type="text"
                    list="delhi-locations"
                    placeholder="Type Connaught Place, Rohini, Saket..."
                    value={searchText}
                    onChange={handleLocationSearch}
                    style={styles.input}
                  />

                  <datalist id="delhi-locations">
                    {locations.map((location) => (
                      <option
                        key={location.location}
                        value={location.location}
                      />
                    ))}
                  </datalist>
                </label>

                {!selectedLocation && searchText.trim() !== "" && (
                  <p style={styles.warning}>
                    Select an exact location from the suggestions.
                    Currently, only the 12 locations in your dataset
                    are supported.
                  </p>
                )}

                {/* SELECTED LOCATION DETAILS */}
                {selectedLocation && (
                  <div style={styles.locationCard}>
                    <h3 style={styles.locationTitle}>
                      {selectedLocation.location}
                    </h3>

                    <p style={styles.sectionDescription}>
                      Environmental measurements retrieved from the dataset.
                    </p>

                    <div style={styles.valueGrid}>
                      <ValueCard
                        label="Land Surface Temperature"
                        value={`${selectedLocation.lst_c}°C`}
                      />

                      <ValueCard
                        label="NDVI"
                        value={selectedLocation.ndvi}
                      />

                      <ValueCard
                        label="Built-up Area"
                        value={`${selectedLocation.built_up_pct}%`}
                      />

                      <ValueCard
                        label="Population Density"
                        value={Number(
                          selectedLocation.population_density
                        ).toLocaleString("en-IN")}
                      />
                    </div>

                    {/* PREDICTION BUTTON */}
                    <button
                      type="submit"
                      disabled={predicting || !modelReady}
                      style={{
                        ...styles.button,
                        opacity:
                          predicting || !modelReady ? 0.6 : 1,
                      }}
                    >
                      {predicting
                        ? "Predicting..."
                        : "Predict Heat Risk"}
                    </button>
                  </div>
                )}
              </form>

              {predictionError && (
                <div style={styles.error}>
                  {predictionError}
                </div>
              )}

              {/* ML PREDICTION RESULT */}
              {prediction && (
                <div style={styles.predictionResult}>
                  <h3 style={styles.resultTitle}>
                    AI Heat Risk Prediction
                  </h3>

                  <p style={styles.resultLocation}>
                    Location: {selectedLocation.location}
                  </p>

                  <div
                    style={{
                      ...styles.resultRisk,
                      color: getRiskColor(prediction.risk_level),
                    }}
                  >
                    {prediction.risk_level} Risk
                  </div>

                  <p>
                    Risk Class: {prediction.risk_class}
                  </p>

                  <p>
                    Model Confidence: {prediction.confidence}%
                  </p>

                  <p style={styles.dataNote}>
                    {prediction.data_status}
                  </p>
                </div>
              )}

              {/* RECOMMENDATIONS AFTER PREDICTION */}
              {prediction && recommendations && (
                <div
                  style={{
                    ...styles.adviceCard,
                    borderTop: `5px solid ${getRiskColor(
                      prediction.risk_level
                    )}`,
                  }}
                >
                  <h2 style={styles.sectionTitle}>
                    Heat Reduction and Health Recommendations
                  </h2>

                  <p style={styles.sectionDescription}>
                    Recommended actions for {selectedLocation.location},
                    based on the predicted {prediction.risk_level} heat-risk category.
                  </p>

                  {/* HEAT REDUCTION */}
                  <div style={styles.recommendationBlock}>
                    <h3 style={styles.recommendationHeading}>
                      🌳 Reduce Urban Heat Trapping
                    </h3>

                    <p style={styles.recommendationDescription}>
                      Measures to reduce heat absorption, improve vegetation
                      and make the surrounding environment cooler.
                    </p>

                    <ul style={styles.recommendationList}>
                      {recommendations.heatReduction.map(
                        (item, index) => (
                          <li key={index}>{item}</li>
                        )
                      )}
                    </ul>
                  </div>

                  {/* HEALTH ADVICE */}
                  <div style={styles.recommendationBlock}>
                    <h3 style={styles.recommendationHeading}>
                      ❤️ Maintain Health and Prevent Heat Illness
                    </h3>

                    <p style={styles.recommendationDescription}>
                      Personal safety measures to reduce heat exposure
                      and prevent heat-related illnesses.
                    </p>

                    <ul style={styles.recommendationList}>
                      {recommendations.healthAdvice.map(
                        (item, index) => (
                          <li key={index}>{item}</li>
                        )
                      )}
                    </ul>
                  </div>

                  <p style={styles.adviceFooter}>
                    These are general educational recommendations.
                    Follow local public-health advisories during heatwaves.
                  </p>
                </div>
              )}
            </section>

            {/* FOOTER */}
            <footer style={styles.footer}>
              <strong>HEATSAFE AI</strong>
              <br />
              Urban Heat Risk Mapping – Delhi
              <br />
              <span>
                Demonstration project using an illustrative sample dataset.
                Predictions are not validated real-world heat-risk assessments.
              </span>
            </footer>

          </>
        )}
      </main>
    </div>
  );
}


// STATISTICS CARD
function StatCard({ title, value, color }) {
  return (
    <div style={styles.statCard}>
      <p style={styles.statTitle}>{title}</p>

      <h2 style={{ ...styles.statValue, color }}>
        {value}
      </h2>
    </div>
  );
}


// ENVIRONMENTAL VALUE CARD
function ValueCard({ label, value }) {
  return (
    <div style={styles.valueCard}>
      <p style={styles.valueLabel}>{label}</p>

      <h3 style={styles.valueNumber}>
        {value}
      </h3>
    </div>
  );
}


// DASHBOARD STYLES
const styles = {
  app: {
    minHeight: "100vh",
    background: "#f1f5f9",
    color: "#1e293b",
    fontFamily: "Arial, sans-serif",
  },

  header: {
    background: "#0f172a",
    color: "white",
    padding: "28px 5%",
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: "20px",
    flexWrap: "wrap",
  },

  brand: {
    color: "#38bdf8",
    fontWeight: "bold",
    letterSpacing: "2px",
    fontSize: "13px",
  },

  heading: {
    fontSize: "clamp(24px, 4vw, 34px)",
    margin: "10px 0",
  },

  subtitle: {
    color: "#cbd5e1",
    margin: 0,
    lineHeight: 1.6,
  },

  status: {
    background: "#1e293b",
    padding: "12px 18px",
    borderRadius: "30px",
    display: "flex",
    alignItems: "center",
    gap: "9px",
    fontSize: "14px",
  },

  statusDot: {
    height: "10px",
    width: "10px",
    borderRadius: "50%",
  },

  main: {
    width: "90%",
    maxWidth: "1250px",
    margin: "30px auto",
  },

  statsGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))",
    gap: "18px",
    marginBottom: "25px",
  },

  statCard: {
    background: "white",
    borderRadius: "14px",
    padding: "22px",
    boxShadow: "0 2px 10px rgba(15,23,42,0.05)",
  },

  statTitle: {
    color: "#64748b",
    fontSize: "14px",
    margin: 0,
  },

  statValue: {
    fontSize: "30px",
    margin: "12px 0 0",
  },

  section: {
    background: "white",
    padding: "25px",
    borderRadius: "14px",
    marginBottom: "25px",
    boxShadow: "0 2px 10px rgba(15,23,42,0.05)",
  },

  sectionTitle: {
    fontSize: "22px",
    margin: "0 0 10px",
  },

  sectionDescription: {
    color: "#64748b",
    fontSize: "14px",
    lineHeight: 1.6,
  },

  legend: {
    display: "flex",
    gap: "20px",
    flexWrap: "wrap",
    margin: "18px 0",
  },

  legendItem: {
    display: "flex",
    alignItems: "center",
    gap: "7px",
    fontSize: "13px",
  },

  legendDot: {
    height: "11px",
    width: "11px",
    borderRadius: "50%",
  },

  mapWrapper: {
    height: "430px",
    width: "100%",
    borderRadius: "12px",
    overflow: "hidden",
    border: "1px solid #e2e8f0",
  },

  map: {
    height: "100%",
    width: "100%",
  },

  field: {
    display: "flex",
    flexDirection: "column",
    gap: "9px",
    marginTop: "20px",
    maxWidth: "600px",
  },

  fieldLabel: {
    fontSize: "14px",
    fontWeight: "bold",
  },

  input: {
    padding: "14px",
    border: "1px solid #cbd5e1",
    borderRadius: "8px",
    fontSize: "15px",
    width: "100%",
    boxSizing: "border-box",
  },

  locationCard: {
    background: "#f8fafc",
    border: "1px solid #e2e8f0",
    padding: "22px",
    borderRadius: "12px",
    marginTop: "22px",
  },

  locationTitle: {
    fontSize: "21px",
    margin: "0 0 5px",
  },

  valueGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
    gap: "12px",
    marginTop: "20px",
  },

  valueCard: {
    background: "white",
    border: "1px solid #e2e8f0",
    borderRadius: "9px",
    padding: "15px",
  },

  valueLabel: {
    fontSize: "12px",
    color: "#64748b",
    margin: 0,
  },

  valueNumber: {
    fontSize: "20px",
    margin: "9px 0 0",
  },

  button: {
    background: "#2563eb",
    color: "white",
    border: "none",
    borderRadius: "8px",
    padding: "13px 22px",
    fontSize: "15px",
    fontWeight: "bold",
    cursor: "pointer",
    marginTop: "20px",
  },

  warning: {
    padding: "12px",
    background: "#fef3c7",
    color: "#92400e",
    borderRadius: "8px",
    marginTop: "15px",
    fontSize: "14px",
  },

  predictionResult: {
    background: "#f8fafc",
    border: "1px solid #cbd5e1",
    padding: "22px",
    borderRadius: "12px",
    marginTop: "22px",
  },

  resultTitle: {
    marginTop: 0,
  },

  resultLocation: {
    color: "#64748b",
    fontSize: "14px",
  },

  resultRisk: {
    fontSize: "30px",
    fontWeight: "bold",
    margin: "15px 0",
  },

  dataNote: {
    color: "#64748b",
    fontSize: "13px",
  },

  adviceCard: {
    background: "#ffffff",
    border: "1px solid #e2e8f0",
    borderRadius: "14px",
    padding: "25px",
    marginTop: "25px",
    boxShadow: "0 2px 10px rgba(15,23,42,0.05)",
  },

  recommendationBlock: {
    background: "#f8fafc",
    border: "1px solid #e2e8f0",
    padding: "20px",
    borderRadius: "10px",
    marginTop: "18px",
    lineHeight: 1.8,
    color: "#334155",
  },

  recommendationHeading: {
    fontSize: "18px",
    marginTop: 0,
    color: "#0f172a",
  },

  recommendationDescription: {
    fontSize: "13px",
    color: "#64748b",
  },

  recommendationList: {
    paddingLeft: "22px",
    lineHeight: 2,
    fontSize: "14px",
  },

  adviceFooter: {
    color: "#64748b",
    fontSize: "12px",
    marginTop: "20px",
    lineHeight: 1.6,
  },

  error: {
    background: "#fee2e2",
    color: "#991b1b",
    padding: "15px",
    borderRadius: "8px",
    marginTop: "15px",
  },

  message: {
    padding: "25px",
    background: "white",
    borderRadius: "10px",
  },

  footer: {
    textAlign: "center",
    color: "#64748b",
    fontSize: "13px",
    lineHeight: 1.8,
    padding: "20px",
  },
};

export default App;
