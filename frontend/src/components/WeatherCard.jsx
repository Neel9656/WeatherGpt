export default function WeatherCard({ weather, location }) {
  const current = weather?.current
  const value = (candidate, format = (item) => item) => {
    const number = Number(candidate)
    return Number.isFinite(number) ? format(number) : '—'
  }
  if (!current) return <section className="current-panel"><p>Live weather is unavailable for this location.</p></section>
  return (
    <section className="current-panel panel-grid-accent">
      <div className="eyebrow">Live conditions</div>
      <div className="temperature-line"><span>{value(current.temperature, Math.round)}°</span><small>C</small></div>
      <p className="weather-description">{current.description || 'Conditions unavailable'}</p>
      <p className="updated">Observed at {new Date(current.time).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}</p>
      <div className="metric-grid">
        <div><span>Humidity</span><strong>{value(current.humidity, Math.round)}{Number.isFinite(Number(current.humidity)) ? '%' : ''}</strong></div>
        <div><span>Wind</span><strong>{value(current.wind_speed, Math.round)}{Number.isFinite(Number(current.wind_speed)) ? ' km/h' : ''}</strong></div>
        <div><span>Rain now</span><strong>{value(current.precipitation)}{Number.isFinite(Number(current.precipitation)) ? ' mm' : ''}</strong></div>
        <div><span>Pressure</span><strong>{value(current.pressure, Math.round)}{Number.isFinite(Number(current.pressure)) ? ' hPa' : ''}</strong></div>
      </div>
      <div className="source-note">Open-Meteo · {location.timezone}</div>
    </section>
  )
}