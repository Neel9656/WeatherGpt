export default function InlineForecast({ forecast }) {
  if (!forecast || forecast.length === 0) return null
  
  return (
    <div className="inline-forecast">
      {forecast.slice(0, 3).map((day, idx) => (
        <div key={idx} className="forecast-day">
          <div className="forecast-date">{new Date(day.date).toLocaleDateString('en-US', { weekday: 'short' })}</div>
          <div className="forecast-temp">{Math.round(day.temperature_max)}°</div>
          <div className="forecast-condition">
            {day.precipitation_probability > 60 ? '🌧️' : day.temperature_max > 32 ? '☀️' : '⛅'}
          </div>
          {day.precipitation_probability > 30 && (
            <div className="forecast-precip">{day.precipitation_probability}% rain</div>
          )}
        </div>
      ))}
    </div>
  )
}
