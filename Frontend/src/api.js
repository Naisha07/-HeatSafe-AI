
const API_BASE_URL = "https://heatsafe-ai.onrender.com";

// Local backend during development; Render after deployment.
export const API_URL = import.meta.env.DEV
  ? "http://127.0.0.1:8000"
  : API_BASE_URL;


// ==========================================
// COMMON API REQUEST
// ==========================================

async function apiRequest(endpoint, options = {}) {
  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (!response.ok) {
    let message = `API Error: ${response.status}`;

    try {
      const data = await response.json();
      message = data.detail || message;
    } catch {
      // Keep default error.
    }

    throw new Error(message);
  }

  return response.json();
}


// ==========================================
// BACKEND HEALTH
// ==========================================

export async function getHealth() {
  return apiRequest("/api/health");
}


// ==========================================
// AVAILABLE SATELLITE DATES
// ==========================================

export async function getSatelliteDates() {
  return apiRequest("/api/satellite/dates");
}


// ==========================================
// SATELLITE STATISTICS
// ==========================================

export async function getSatelliteStatistics(date) {
  return apiRequest(
    `/api/satellite/statistics?date=${encodeURIComponent(date)}`
  );
}


// ==========================================
// SATELLITE GRID LOCATIONS
// ==========================================

export async function getLocations(date) {
  const data = await apiRequest(
    `/api/locations?date=${encodeURIComponent(date)}&max_points=10000`
  );

  if (!Array.isArray(data.locations)) {
    throw new Error("Invalid satellite location data received.");
  }

  return data.locations;
}


// ==========================================
// SATELLITE MAP BOUNDARIES
// ==========================================

export async function getSatelliteBounds(date) {
  return apiRequest(
    `/api/satellite/bounds?date=${encodeURIComponent(date)}`
  );
}


// ==========================================
// SATELLITE MAP IMAGE
// ==========================================

export function getSatelliteMapUrl(date) {
  return `${API_URL}/api/satellite/map?date=${encodeURIComponent(date)}`;
}


// ==========================================
// LOCALITY NAME FROM COORDINATES
// ==========================================

export async function getPlaceName(latitude, longitude) {
  const url = new URL(
    "https://nominatim.openstreetmap.org/reverse"
  );

  url.searchParams.set("format", "jsonv2");
  url.searchParams.set("lat", latitude);
  url.searchParams.set("lon", longitude);
  url.searchParams.set("zoom", "14");
  url.searchParams.set("addressdetails", "1");

  const response = await fetch(url.toString(), {
    headers: {
      "Accept-Language": "en",
    },
  });

  if (!response.ok) {
    throw new Error("Locality lookup unavailable.");
  }

  const data = await response.json();
  const address = data.address || {};

  const locality =
    address.suburb ||
    address.neighbourhood ||
    address.quarter ||
    address.residential ||
    address.city_district ||
    address.town ||
    address.city ||
    address.village;

  return {
    name: locality || "Delhi area",
    fullAddress: data.display_name || "Delhi, India",
  };
}


// ==========================================
// LEGACY ML PREDICTION ENDPOINT
// ==========================================

export async function predictRisk(input) {
  return apiRequest("/api/predict", {
    method: "POST",
    body: JSON.stringify({
      lst_c: Number(input.lst_c),
      ndvi: Number(input.ndvi),
      built_up_pct: Number(input.built_up_pct),
      population_density: Number(input.population_density),
    }),
  });
}
