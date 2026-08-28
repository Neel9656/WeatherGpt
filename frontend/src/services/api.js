const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

async function request(path, options = {}) {
  let response
  try {
    response = await fetch(`${API_URL}${path}`, options)
  } catch {
    throw new Error('Weather service is unreachable. Check that the backend is running.')
  }

  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    if (import.meta.env.DEV) console.error('WeatherGPT API error', response.status, data)
    throw new Error(data.detail || data.error?.message || 'The weather service returned an error.')
  }
  return data
}

export function searchLocations(query) {
  return request(`/location?query=${encodeURIComponent(query)}`)
}

export function resolveCoordinates(latitude, longitude) {
  return request(`/location/reverse?latitude=${latitude}&longitude=${longitude}`)
}

export function getCurrentWeather(latitude, longitude) {
  return request(`/weather?latitude=${latitude}&longitude=${longitude}`)
}

export function getForecast(latitude, longitude, forecastType = 'daily') {
  return request(`/forecast?latitude=${latitude}&longitude=${longitude}&forecast_type=${forecastType}`)
}

export function sendChat(message, language = 'en', location = null, conversationHistory = [], audience = 'general') {
  return request('/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message: String(message || '').trim(),
      selected_location: location || null,
      location: location?.name || null,
      latitude: location?.latitude ?? null,
      longitude: location?.longitude ?? null,
      language,
      audience,
      conversation_history: conversationHistory,
    }),
  })
}

export function getAlerts(latitude, longitude) {
  return request(`/alerts?latitude=${latitude}&longitude=${longitude}`).then((payload) => (
    Array.isArray(payload) ? payload : payload.alerts || []
  ))
}
