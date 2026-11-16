
import React, { useEffect, useState } from "react";

import {
  MapContainer,
  TileLayer,
  ImageOverlay,
  CircleMarker,
  Popup,
  useMapEvents,
} from "react-leaflet";

import {
  getHealth,
  getSatelliteDates,
  getSatelliteStatistics,
  getLocations,
  getSatelliteBounds,
  getSatelliteMapUrl,
  getPlaceName,
  getAQIForecast,
} from "./api";

import "leaflet/dist/leaflet.css";
import "./App.css";

// ==========================================
// RISK COLOURS
// ==========================================

const COLORS = {
  Low: "#2ca25f",
  Moderate: "#e5a000",
  High: "#fd8d3c",
  "Very High": "#bd0026",
};

function getRiskColor(level) {
  return COLORS[level] || "#64748b";
}

// ==========================================
// MAP CLICK HANDLER
// ==========================================

function MapClickHandler({ locations, onSelect }) {
  useMapEvents({
    click(event) {
      if (!locations.length) return;

      let nearest = null;
      let minDistance = Infinity;

      locations.forEach((location) => {
        const distance =
          Math.pow(location.latitude - event.latlng.lat, 2) +
          Math.pow(
            (location.longitude - event.latlng.lng) *
              Math.cos((event.latlng.lat * Math.PI) / 180),
            2
          );

        if (distance < minDistance) {
          minDistance = distance;
          nearest = location;
        }
      });

      if (nearest) onSelect(nearest);
    },
  });

  return null;
}

// ==========================================
// STATISTICS CARD
// ==========================================

function StatCard({ title, value, subtitle, color, icon }) {
  return (
    <div className="stat-card">
      <div className="stat-top">
        <span>{title}</span>
        <span className={`stat-icon ${color}`}>{icon}</span>
      </div>

      <strong>{value}</strong>
      <small>{subtitle}</small>
    </div>
  );
}

// ==========================================
// ENVIRONMENTAL INSIGHTS
// ==========================================

function getEnvironmentalInsights(location) {
  if (!location) return [];

  const insights = [];

  const temperature = Number(location.lst_c);
  const ndvi = Number(location.ndvi);
  const ndbi = Number(location.ndbi);
  const risk = Number(location.heat_risk);

  // Heat exposure
  if (risk >= 75 || temperature >= 40) {
    insights.push({
      title: "High heat exposure",
      level: "High",
      type: "danger",
      description:
        "This location has a high relative heat-risk score or elevated land surface temperature.",
      suggestion:
        "Prioritise shade, drinking-water facilities, cool roofs and heat-safety awareness.",
    });
  } else if (risk >= 50 || temperature >= 35) {
    insights.push({
      title: "Elevated heat conditions",
      level: "Moderate",
      type: "warning",
      description:
        "The satellite measurements indicate comparatively elevated heat conditions.",
      suggestion:
        "Increase shaded spaces, vegetation and reflective roofing where feasible.",
    });
  } else {
    insights.push({
      title: "Lower relative heat risk",
      level: "Low",
      type: "good",
      description:
        "The relative heat-risk score is lower than in higher-risk sampled locations.",
      suggestion:
        "Maintain existing green cover and continue monitoring seasonal changes.",
    });
  }

  // Vegetation
  if (ndvi < 0.2) {
    insights.push({
      title: "Limited vegetation cover",
      level: "Needs attention",
      type: "warning",
      description:
        "The NDVI value indicates relatively low vegetation activity.",
      suggestion:
        "Consider tree plantation, green corridors and protection of existing vegetation.",
    });
  } else if (ndvi >= 0.5) {
    insights.push({
      title: "Good vegetation signal",
      level: "Positive",
      type: "good",
      description:
        "The NDVI value indicates comparatively stronger vegetation activity.",
      suggestion:
        "Protect existing trees and green spaces and prevent unnecessary vegetation loss.",
    });
  }

  // Built-up surface
  if (ndbi > 0.1) {
    insights.push({
      title: "Elevated built-up signal",
      level: "Elevated",
      type: "warning",
      description:
        "The NDBI value indicates a relatively strong built-up surface signal.",
      suggestion:
        "Consider cool roofs, permeable surfaces and shaded pedestrian areas.",
    });
  }

  // Pollution guidance
  insights.push({
    title: "Air pollution monitoring",
    level: "External data needed",
    type: "info",
    description:
      "Satellite LST, NDVI and NDBI do not measure ground-level PM2.5, PM10 or NO2.",
    suggestion:
      "Check current CPCB air-quality readings for this area. Follow official guidance during poor-air-quality periods.",
  });

  // Health guidance
  insights.push({
    title: "Heat and public health",
    level: "Preventive guidance",
    type: "info",
    description:
      "High outdoor heat exposure can increase the risk of heat-related illness, particularly for vulnerable groups.",
    suggestion:
      "Provide drinking water, shaded rest areas and heat-safety awareness for outdoor workers and residents.",
  });

  return insights;
}

// ==========================================
// ENVIRONMENTAL INSIGHTS COMPONENT
// ==========================================

function EnvironmentalInsights({ location }) {
  if (!location) {
    return (
      <section className="panel environmental-panel">
        <div className="panel-heading">
          <div>
            <h3>Environmental Insights</h3>
            <p>Location-based environmental observations and suggestions</p>
          </div>
        </div>

        <div className="insights-empty">
          Select a location on the map or use the random location button
          to view environmental insights.
        </div>
      </section>
    );
  }

  const insights = getEnvironmentalInsights(location);

  return (
    <section className="panel environmental-panel">
      <div className="panel-heading">
        <div>
          <h3>Environmental Insights</h3>
          <p>
            Environmental conditions and AI-assisted rule-based
            recommendations for the selected location.
          </p>
        </div>

        <span className="table-count">LOCATION ANALYSIS</span>
      </div>

      <div className="insights-grid">
        {insights.map((insight, index) => (
          <div
            className={`insight-card ${insight.type}`}
            key={index}
          >
            <div className="insight-heading">
              <strong>{insight.title}</strong>
              <span>{insight.level}</span>
            </div>

            <p>{insight.description}</p>

            <div className="insight-suggestion">
              <strong>Suggested action</strong>
              <p>{insight.suggestion}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

// ==========================================
// MAIN APPLICATION
// ==========================================

function App() {
  const [dates, setDates] = useState([]);
  const [selectedDate, setSelectedDate] = useState("");

  const [health, setHealth] = useState(null);
  const [statistics, setStatistics] = useState(null);
  const [locations, setLocations] = useState([]);
  const [bounds, setBounds] = useState(null);

  const [selectedLocation, setSelectedLocation] = useState(null);

  // AQI forecast state
  const [aqiForecast, setAqiForecast] = useState([]);
  const [aqiLoading, setAqiLoading] = useState(false);
  const [aqiError, setAqiError] = useState("");

  const [placeName, setPlaceName] = useState("");
  const [placeAddress, setPlaceAddress] = useState("");
  const [placeLoading, setPlaceLoading] = useState(false);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // ==========================================
  // INITIALIZE BACKEND
  // ==========================================

  useEffect(() => {
    let cancelled = false;

    async function initialize() {
      try {
        const [healthData, dateData] = await Promise.all([
          getHealth(),
          getSatelliteDates(),
        ]);

        if (cancelled) return;

        setHealth(healthData);
        setDates(dateData.dates || []);
        setSelectedDate(dateData.default_date || "");

        if (!dateData.default_date) {
          setError("No processed satellite observations are available.");
          setLoading(false);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message || "Unable to connect to backend.");
          setLoading(false);
        }
      }
    }

    initialize();

    return () => {
      cancelled = true;
    };
  }, []);

  // ==========================================
  // LOAD SELECTED DATE DATA
  // ==========================================

  useEffect(() => {
    if (!selectedDate) return;

    let cancelled = false;

    async function loadSatelliteData() {
      setLoading(true);
      setError("");

      setSelectedLocation(null);
      setPlaceName("");
      setPlaceAddress("");

      try {
        const [stats, points, mapBounds] = await Promise.all([
          getSatelliteStatistics(selectedDate),
          getLocations(selectedDate),
          getSatelliteBounds(selectedDate),
        ]);

        if (cancelled) return;

        setStatistics(stats);
        setLocations(points);
        setBounds(mapBounds.bounds);
      } catch (err) {
        if (!cancelled) {
          setError(err.message || "Unable to load satellite data.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadSatelliteData();

    return () => {
      cancelled = true;
    };
  }, [selectedDate]);

  // ==========================================
  // LOAD AQI FORECAST FOR SELECTED LOCATION
  // ==========================================

  useEffect(() => {
    const latitude = selectedLocation?.latitude;
    const longitude = selectedLocation?.longitude;

    if (
      latitude == null ||
      longitude == null ||
      !Number.isFinite(Number(latitude)) ||
      !Number.isFinite(Number(longitude))
    ) {
      setAqiForecast([]);
      setAqiError("");
      setAqiLoading(false);
      return;
    }

    let cancelled = false;

    async function loadAQI() {
      setAqiLoading(true);
      setAqiError("");
      setAqiForecast([]);

      try {
        const data = await getAQIForecast(latitude, longitude);

        if (!cancelled) {
          setAqiForecast(data);
        }
      } catch (err) {
        if (!cancelled) {
          setAqiError(err.message || "Unable to load AQI forecast.");
        }
      } finally {
        if (!cancelled) {
          setAqiLoading(false);
        }
      }
    }

    loadAQI();

    return () => {
      cancelled = true;
    };
  }, [
    selectedLocation?.latitude,
    selectedLocation?.longitude,
  ]);

  // ==========================================
  // SELECT LOCATION AND IDENTIFY LOCALITY
  // ==========================================

  async function identifyLocation(location) {
    setSelectedLocation(location);
    setPlaceName("");
    setPlaceAddress("");
    setPlaceLoading(true);

    try {
      const result = await getPlaceName(
        location.latitude,
        location.longitude
      );

      setPlaceName(result.name);
      setPlaceAddress(result.fullAddress);
    } catch (err) {
      setPlaceName("Delhi area");
      setPlaceAddress("Locality information unavailable.");
    } finally {
      setPlaceLoading(false);
    }
  }

  // ==========================================
  // RANDOM LOCATION
  // ==========================================

  function selectRandomLocation() {
    if (!locations.length) return;

    const randomIndex = Math.floor(Math.random() * locations.length);

    identifyLocation(locations[randomIndex]);
  }

  // ==========================================
  // CLEAR LOCATION
  // ==========================================

  function clearSelection() {
    setSelectedLocation(null);
    setPlaceName("");
    setPlaceAddress("");
  }

  // ==========================================
  // RISK DISTRIBUTION
  // ==========================================

  const riskDistribution = statistics?.risk_distribution || {};

  // ==========================================
  // UI
  // ==========================================

  return (
    <div className="app">

      {/* HEADER */}

      <header className="topbar">
        <div className="brand">
          <div className="brand-icon">H</div>

          <div>
            <h1>
              HEATSAFE <span>AI</span>
            </h1>
            <p>URBAN HEAT INTELLIGENCE · DELHI</p>
          </div>
        </div>

        <div className="connection">
          <span
            className={`status-dot ${
              health ? "online" : "offline"
            }`}
          />
          {health ? "Satellite API Connected" : "Connecting"}
        </div>
      </header>

      <main className="dashboard">

        {/* WELCOME */}

        <section className="welcome">
          <div>
            <p className="eyebrow">
              SATELLITE-BASED HEAT MONITORING
            </p>

            <h2>Delhi Urban Heat Dashboard</h2>

            <p>
              Explore actual satellite-derived temperature,
              vegetation and relative heat-risk patterns
              across Delhi.
            </p>
          </div>

          <label className="date-label">
            <span>SATELLITE OBSERVATION</span>

            <select
              value={selectedDate}
              onChange={(event) => setSelectedDate(event.target.value)}
              disabled={!dates.length}
            >
              {dates.map((date) => (
                <option key={date} value={date}>
                  {date}
                </option>
              ))}
            </select>
          </label>
        </section>

        {/* ERROR */}

        {error && (
          <div className="error-banner">
            {error}
          </div>
        )}

        {/* LOADING */}

        {loading && (
          <div className="panel loading-panel">
            Loading actual Delhi satellite observations...
          </div>
        )}

        {!loading && !error && statistics && (
          <>
            {/* STATISTICS */}

            <section className="stats-grid">
              <StatCard
                title="Average Surface Temperature"
                value={`${statistics.lst_c.mean}°C`}
                subtitle="Land surface temperature"
                color="red"
                icon="°C"
              />

              <StatCard
                title="Average Vegetation"
                value={statistics.ndvi.mean}
                subtitle="NDVI vegetation index"
                color="green"
                icon="ND"
              />

              <StatCard
                title="Average Built-up Index"
                value={statistics.ndbi.mean}
                subtitle="NDBI index"
                color="yellow"
                icon="BU"
              />

              <StatCard
                title="Mean Relative Heat Risk"
                value={`${statistics.mean_heat_risk}/100`}
                subtitle="Experimental satellite index"
                color="orange"
                icon="HR"
              />
            </section>

            {/* MAP AND LOCATION INTELLIGENCE */}

            <section className="main-grid">

              {/* MAP */}

              <div className="panel map-panel">
                <div className="panel-heading">
                  <div>
                    <h3>Delhi Heat Risk Map</h3>
                    <p>
                      Click anywhere on the map to inspect
                      the nearest sampled satellite location.
                    </p>
                  </div>

                  <span className="table-count">
                    REAL SATELLITE DATA
                  </span>
                </div>

                <div className="map-container">
                  {bounds && (
                    <MapContainer
                      key={selectedDate}
                      bounds={bounds}
                      boundsOptions={{ padding: [15, 15] }}
                      scrollWheelZoom={true}
                      className="leaflet-map"
                    >
                      <TileLayer
                        attribution="&copy; OpenStreetMap contributors"
                        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                      />

                      <ImageOverlay
                        url={getSatelliteMapUrl(selectedDate)}
                        bounds={bounds}
                        opacity={0.78}
                        zIndex={2}
                      />

                      <MapClickHandler
                        locations={locations}
                        onSelect={identifyLocation}
                      />

                      {selectedLocation && (
                        <CircleMarker
                          center={[
                            selectedLocation.latitude,
                            selectedLocation.longitude,
                          ]}
                          radius={9}
                          pathOptions={{
                            color: "#ffffff",
                            weight: 3,
                            fillColor: getRiskColor(
                              selectedLocation.risk_level
                            ),
                            fillOpacity: 1,
                          }}
                        >
                          <Popup>
                            <strong>
                              {placeName || "Selected location"}
                            </strong>
                            <br />
                            LST: {selectedLocation.lst_c}°C
                            <br />
                            Risk: {selectedLocation.risk_level}
                          </Popup>
                        </CircleMarker>
                      )}
                    </MapContainer>
                  )}
                </div>

                {/* MAP LEGEND */}

                <div className="map-legend">
                  {Object.entries(COLORS).map(([label, color]) => (
                    <span key={label}>
                      <i style={{ background: color }} />
                      {label}
                    </span>
                  ))}
                </div>

                <p className="map-note">
                  The raster displays the satellite-derived relative
                  heat-risk index. Selectable points represent sampled
                  valid satellite pixels.
                </p>
              </div>

              {/* LOCATION INTELLIGENCE */}

              <aside className="panel predictor">
                <div className="panel-heading">
                  <div>
                    <h3>Location Intelligence</h3>
                    <p>
                      Explore environmental conditions at
                      any sampled Delhi location.
                    </p>
                  </div>
                </div>

                <div className="model-status">
                  <span className="status-dot online" />
                  Actual satellite measurements available
                </div>

                <button
                  className="predict-button"
                  onClick={selectRandomLocation}
                  disabled={!locations.length}
                >
                  ↗ Select Random Delhi Location
                </button>

                <p className="model-help">
                  You can also click directly on the map.
                  Random selection chooses one of the available
                  sampled satellite grid points.
                </p>

                {selectedLocation ? (
                  <div className="location-result">

                    {/* LOCALITY */}

                    <div className="result-heading">
                      <div>
                        <small>SELECTED LOCALITY</small>

                        <strong>
                          {placeLoading
                            ? "Identifying locality..."
                            : placeName || "Delhi area"}
                        </strong>
                      </div>

                      <span
                        className="risk-badge"
                        style={{
                          background: `${getRiskColor(
                            selectedLocation.risk_level
                          )}22`,
                          color: getRiskColor(
                            selectedLocation.risk_level
                          ),
                        }}
                      >
                        {selectedLocation.risk_level}
                      </span>
                    </div>

                    <p className="place-address">
                      {placeAddress ||
                        `${selectedLocation.latitude.toFixed(5)}° N, ${selectedLocation.longitude.toFixed(5)}° E`}
                    </p>

                    {/* MEASUREMENTS */}

                    <div className="location-metrics">
                      <div>
                        <span>Surface temperature</span>
                        <strong>{selectedLocation.lst_c}°C</strong>
                      </div>

                      <div>
                        <span>Relative heat risk</span>
                        <strong>{selectedLocation.heat_risk}/100</strong>
                      </div>

                      <div>
                        <span>Vegetation (NDVI)</span>
                        <strong>{selectedLocation.ndvi}</strong>
                      </div>

                      <div>
                        <span>Built-up index (NDBI)</span>
                        <strong>{selectedLocation.ndbi}</strong>
                      </div>
                    </div>

                    <button
                      className="clear-button"
                      onClick={clearSelection}
                    >
                      Clear selection
                    </button>
                  </div>
                ) : (
                  <div className="empty-selection">
                    <div className="empty-icon">⌖</div>

                    <strong>No location selected</strong>

                    <p>
                      Click the map or select a random Delhi location
                      to see its satellite conditions and recommendations.
                    </p>
                  </div>
                )}

                {/* 24-HOUR AQI FORECAST */}

                {selectedLocation && (
                  <div className="aqi-panel">
                    <div className="panel-heading">
                      <div>
                        <h3>24-Hour AQI Forecast</h3>
                        <p>Air quality forecast for this location</p>
                      </div>
                    </div>

                    <div className="model-status">
                      <span className="status-dot online" />
                      Open-Meteo Forecast · US AQI
                    </div>

                    {aqiLoading && (
                      <p className="aqi-message">
                        Loading AQI forecast...
                      </p>
                    )}

                    {aqiError && (
                      <p className="aqi-error">
                        {aqiError}
                      </p>
                    )}

                    {!aqiLoading && !aqiError && aqiForecast.length > 0 && (
                      <>
                        <div className="aqi-current">
                          <small>FIRST FORECAST VALUE</small>
                          <strong>
                            {aqiForecast[0].aqi ?? "N/A"}
                          </strong>
                          <span>US AQI</span>
                        </div>

                        <div className="aqi-hourly-list">
                          {aqiForecast.map((item) => (
                            <div className="aqi-hour-row" key={item.time}>
                              <span>
                                {new Date(item.time).toLocaleTimeString(
                                  "en-IN",
                                  {
                                    hour: "2-digit",
                                    minute: "2-digit",
                                    hour12: true,
                                  }
                                )}
                              </span>

                              <strong>
                                {item.aqi ?? "N/A"}
                              </strong>

                              <small>
                                PM2.5: {item.pm25 ?? "N/A"} µg/m³
                              </small>

                              <small>
                                PM10: {item.pm10 ?? "N/A"} µg/m³
                              </small>
                            </div>
                          ))}
                        </div>

                        <p className="aqi-note">
                          Model-based US AQI forecast, not official CPCB AQI.
                          Forecast resolution and accuracy vary by location.
                        </p>
                      </>
                    )}
                  </div>
                )}

              </aside>
            </section>

            {/* ENVIRONMENTAL INSIGHTS - NOW BELOW MAP */}

            <EnvironmentalInsights location={selectedLocation} />

            {/* RISK DISTRIBUTION */}

            <section className="panel table-panel">
              <div className="panel-heading">
                <div>
                  <h3>Delhi Heat Risk Distribution</h3>

                  <p>
                    Based on{" "}
                    {statistics.valid_pixels?.toLocaleString("en-IN") || 0}
                    {" "}valid satellite pixels · {selectedDate}
                  </p>
                </div>
              </div>

              {Object.entries(COLORS).map(([label, color]) => {
                const item = riskDistribution[label] || {
                  pixels: 0,
                  percentage: 0,
                };

                return (
                  <div className="distribution-row" key={label}>
                    <div className="distribution-label">
                      <i style={{ background: color }} />
                      {label}
                    </div>

                    <div className="distribution-bar">
                      <div
                        style={{
                          width: `${item.percentage}%`,
                          background: color,
                        }}
                      />
                    </div>

                    <strong>{item.percentage}%</strong>

                    <small>
                      {item.pixels.toLocaleString("en-IN")} pixels
                    </small>
                  </div>
                );
              })}
            </section>

            {/* DATA INFORMATION */}

            <section className="panel data-panel">
              <div className="panel-heading">
                <div>
                  <h3>Satellite Data Information</h3>
                  <p>Observation and source details</p>
                </div>
              </div>

              <div className="data-grid">
                <div>
                  <span>Satellite</span>
                  <strong>Landsat 8/9</strong>
                </div>

                <div>
                  <span>Dataset</span>
                  <strong>Collection 2 Level 2</strong>
                </div>

                <div>
                  <span>Observation</span>
                  <strong>{selectedDate}</strong>
                </div>

                <div>
                  <span>Data provider</span>
                  <strong>Microsoft Planetary Computer</strong>
                </div>
              </div>

              <p className="model-help">
                LST is land surface temperature, not air temperature.
                The heat-risk score is an experimental relative indicator,
                not an official heat warning. Air pollution and disease
                incidence are not measured by these satellite layers.
              </p>
            </section>
          </>
        )}

        {/* FOOTER */}

        <footer className="footer">
          <strong>HEATSAFE AI</strong>

          <span>
            Satellite-Based Urban Heat Risk Mapping · Delhi
          </span>

          <span>
            Academic project · Experimental environmental analysis
          </span>
        </footer>
      </main>
    </div>
  );
}

export default App;
