function finiteNumber(value) {
  const number = Number(value)
  return Number.isFinite(number) ? number : null
}

function ForecastSnapshot({ forecast, timePeriod }) {
  if (!forecast) return null
  const weekendLabel = timePeriod === 'weekend' && forecast.date
    ? new Date(`${forecast.date}T12:00:00`).toLocaleDateString([], { weekday: 'long' })
    : null
  const label = weekendLabel || (timePeriod === 'day_after_tomorrow' ? 'Day after tomorrow' : timePeriod === 'tomorrow' ? 'Tomorrow' : 'Today')
  return <div className="inline-current-weather">
    <strong>{label}</strong><small>{forecast.date}</small>
    <div className="weather-details"><span>High {finiteNumber(forecast.temperature_max) ?? '—'}°C</span><span>Low {finiteNumber(forecast.temperature_min) ?? '—'}°C</span></div>
    <div className="weather-desc">{forecast.description || 'Conditions unavailable'}</div>
    <div className="weather-details"><span>Rain {finiteNumber(forecast.precipitation_probability) ?? '—'}%</span><span>{finiteNumber(forecast.precipitation_sum) ?? '—'} mm · {finiteNumber(forecast.wind_speed_max) ?? '—'} km/h wind</span></div>
  </div>
}

function CurrentSnapshot({ current }) {
  if (!current) return null
  return <div className="inline-current-weather">
    <strong>Current weather</strong>
    <div className="temp-main">{finiteNumber(current.temperature) === null ? '—' : `${Math.round(finiteNumber(current.temperature))}°`}</div>
    <div className="weather-desc">{current.description || 'Conditions unavailable'}</div>
    <div className="weather-details"><span>Humidity {finiteNumber(current.humidity) ?? '—'}%</span><span>Wind {finiteNumber(current.wind_speed) ?? '—'} km/h</span></div>
  </div>
}

export default function ChatMessage({ message, risks = [] }) {
  const text = typeof message.text === 'string' ? message.text : 'WeatherGPT could not provide a readable response.'
  if (message.role === 'assistant' && message.agricultureAdvisory) {
    const window = message.agricultureAdvisory.window || {}
    return <div className="chat-message assistant">
      <span className="message-label">WeatherGPT</span>
      {message.location?.name && <small className="resolved-location">Weather for: {message.location.name}</small>}
      <p>{text}</p>
      <div className="farm-advisory-card"><div className="farm-advisory-title">Farm weather advisory</div><strong>{window.suitable ? 'Weather conditions appear suitable' : 'Not recommended'}</strong><div className="farm-advisory-metrics"><span>Rain probability <b>{finiteNumber(window.rain_probability) ?? '—'}%</b></span><span>Expected rain <b>{finiteNumber(window.expected_precipitation_mm) ?? '—'} mm</b></span><span>Wind <b>{finiteNumber(window.wind_speed_kmh) ?? '—'} km/h</b></span><span>Temperature <b>{finiteNumber(window.temperature_c) ?? '—'}°C</b></span></div><small>Best weather window: {window.best_window ? `${window.best_window.start} to ${window.best_window.end}` : 'None identified'}</small><small>Follow the pesticide label for product-specific requirements.</small></div>
    </div>
  }
  const weather = message.weather || {}
  const forecast = weather.selected_forecast || message.selectedForecast
  const weekendForecasts = weather.weekend_forecasts || message.weekendForecasts || []
  return <div className={`chat-message ${message.role}`}>
    <span className="message-label">{message.role === 'user' ? 'You' : 'WeatherGPT'}</span>
    {message.role === 'assistant' && message.location?.name && <small className="resolved-location">Weather for: {message.location.name}</small>}
    <p>{text}</p>
    {message.role === 'assistant' && message.timePeriod === 'current' ? <CurrentSnapshot current={weather.current} /> : message.role === 'assistant' && message.timePeriod === 'weekend' ? weekendForecasts.map((item) => <ForecastSnapshot key={item.date} forecast={item} timePeriod="weekend" />) : message.role === 'assistant' && <ForecastSnapshot forecast={forecast} timePeriod={message.timePeriod} />}
    {message.role === 'assistant' && risks.length > 0 && <div className="message-risks">{risks.map((risk, index) => <div key={risk.id || `${risk.type}-${index}`} className={`risk-badge risk-${risk.severity}`}><strong>{risk.title || risk.type?.replaceAll('_', ' ') || 'Forecast risk'}</strong><br />{risk.message || 'WeatherGPT identified a forecast risk.'}</div>)}</div>}
  </div>
}
