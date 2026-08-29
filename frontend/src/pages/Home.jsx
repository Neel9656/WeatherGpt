import { useEffect, useRef, useState } from 'react'
import AlertCard from '../components/AlertCard'
import ChatWindow from '../components/ChatWindow'
import { DailyCards, HourlyCards } from '../components/ForecastCard'
import Loading from '../components/Loading'
import LocationSearch from '../components/LocationSearch'
import WeatherCard from '../components/WeatherCard'
import { getWeatherOverview, resolveCoordinates } from '../services/api'

export default function Home() {
  const [location, setLocation] = useState(null)
  const [weather, setWeather] = useState(null)
  const [hourly, setHourly] = useState([])
  const [daily, setDaily] = useState([])
  const [alerts, setAlerts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [geoError, setGeoError] = useState('')
  const geoAttemptedRef = useRef(false)

  function handleLocationSelect(nextLocation) {
    if (!nextLocation || !Number.isFinite(Number(nextLocation.latitude)) || !Number.isFinite(Number(nextLocation.longitude))) return
    setLocation({ ...nextLocation, latitude: Number(nextLocation.latitude), longitude: Number(nextLocation.longitude), name: nextLocation.name || 'Your GPS location' })
  }

  useEffect(() => {
    if (geoAttemptedRef.current || location) return
    geoAttemptedRef.current = true

    if (!navigator.geolocation) {
      setGeoError('Location access is unavailable in this browser. You can still search manually.')
      setLoading(false)
      return
    }

    navigator.geolocation.getCurrentPosition(
      async (position) => {
        try {
          const { latitude, longitude } = position.coords
          const resolved = await resolveCoordinates(latitude, longitude)
          handleLocationSelect(resolved)
          setGeoError('')
        } catch {
          setGeoError('Location access could not be obtained. You can still search for a city manually.')
          setLoading(false)
        }
      },
      () => {
        setGeoError('Location access could not be obtained. You can still search for a city manually.')
        setLoading(false)
      },
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 600000 }
    )
  }, [location])

  useEffect(() => {
    let cancelled = false
    if (!location) {
      setLoading(false)
      return () => { cancelled = true }
    }
    async function loadWeather() {
      setLoading(true)
      setError('')
      setWeather(null)
      setHourly([])
      setDaily([])
      setAlerts([])
      try {
        const overview = await getWeatherOverview(location.latitude, location.longitude)
        if (!cancelled) {
          setWeather({ current: overview.current })
          setHourly(Array.isArray(overview.hourly) ? overview.hourly : [])
          setDaily(Array.isArray(overview.daily) ? overview.daily : [])
          setAlerts(Array.isArray(overview.alerts) ? overview.alerts : [])
        }
      } catch (loadError) {
        if (!cancelled) setError(loadError.message)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    loadWeather()
    return () => { cancelled = true }
  }, [location])

  const coordinates = location ? `${Number(location.latitude).toFixed(3)}, ${Number(location.longitude).toFixed(3)}` : 'Select a location to load weather'
  return <main className="app-shell">
    <header className="topbar"><a className="brand" href="/"><span className="brand-symbol">W</span><span>Weather<span className="brand-light">GPT</span></span></a><div className="topbar-status"><span className="status-dot" />Live data <span className="divider" />{alerts.length ? `${alerts.length} alerts` : 'No active alerts'}</div></header>
    <section className="hero"><div className="hero-copy"><div className="kicker">Intelligence for changing skies</div><h1>Know the weather<br /><em>before it changes.</em></h1><p>Real-time conditions and forecasts, grounded in live meteorological data.</p></div><LocationSearch onSelect={handleLocationSelect} geoError={geoError} /></section>
    <div className="content-grid"><div className="dashboard-column"><div className="location-heading"><div><span className="eyebrow">Your location</span><h2>{location?.name || 'Choose a location'}</h2><p>{location?.country || 'Search or use GPS'} · {coordinates}</p></div><span className="coordinates">⌖</span></div>
      {loading && <Loading />}{error && <div className="error-panel"><strong>Could not load weather</strong><p>{error}</p><button type="button" onClick={() => setLocation({ ...location })}>Try again</button></div>}{weather && !loading && <WeatherCard weather={weather} location={location} />}
      <section className="forecast-section"><div className="section-heading"><div><div className="eyebrow">Next 24 hours</div><h2>Hourly forecast</h2></div><span className="section-unit">°C</span></div>{loading ? <Loading label="Updating hourly forecast" /> : <HourlyCards forecast={hourly} />}</section>
      <section className="forecast-section"><div className="section-heading"><div><div className="eyebrow">Plan ahead</div><h2>7-day forecast</h2></div><span className="section-unit">°C</span></div>{loading ? <Loading label="Updating daily forecast" /> : <DailyCards forecast={daily} />}</section><AlertCard alerts={alerts} loading={loading} />
    </div><aside className="assistant-column"><ChatWindow location={location} currentWeather={weather} forecast={daily} alerts={alerts} /><div className="trust-note"><span>◎</span><p><strong>Grounded in real data</strong><br />Weather values come directly from Open-Meteo. AI responses use this context.</p></div></aside></div><footer>WEATHERGPT <span>·</span> A weather intelligence prototype <span>·</span> Data by Open-Meteo</footer>
  </main>
}
