
const API_BASE_URL = "https://heatsafe-ai.onrender.com";

// Common API request handler
async function apiRequest(endpoint, options = {}) {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(
      data.detail || `API Error: ${response.status}`
    );
  }

  return data;
}

// Check backend and ML model status
export async function getHealth() {
  return apiRequest("/api/health");
}

// Fetch all available Delhi locations
export async function getLocations() {
  const data = await apiRequest("/api/locations");

  if (Array.isArray(data)) {
    return data;
  }

  if (Array.isArray(data.locations)) {
    return data.locations;
  }

  throw new Error("Invalid location data received from backend.");
}

// Send environmental measurements to the ML model
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
