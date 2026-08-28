function formatHour(value) {
  return new Date(value).toLocaleTimeString([], { hour: 'numeric' })
}

export function HourlyCards({ forecast }) {
  return <div className="forecast-strip">{forecast.slice(0, 8).map((item) => <article className="forecast-item" key={item.time}><span>{formatHour(item.time)}</span><strong>{Math.round(item.temperature)}°</strong><small>{item.description}</small><em>{Math.round(item.precipitation_probability)}% rain</em></article>)}</div>
}

export function DailyCards({ forecast }) {
  return <div className="daily-grid">{forecast.map((item) => <article className="daily-item" key={item.date}><span>{new Date(`${item.date}T12:00:00`).toLocaleDateString([], { weekday: 'short' })}</span><strong>{Math.round(item.temperature_max)}° <small>{Math.round(item.temperature_min)}°</small></strong><p>{item.description}</p><em>{Math.round(item.precipitation_probability)}% rain</em></article>)}</div>
}