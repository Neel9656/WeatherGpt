import { useEffect, useRef, useState } from 'react'
import { resolveCoordinates, searchLocations } from '../services/api'

export default function LocationSearch({ onSelect }) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [error, setError] = useState('')
  const [geoLoading, setGeoLoading] = useState(false)
  const requestIdRef = useRef(0)

  useEffect(() => {
    if (query.trim().length < 2) {
      setResults([])
      return undefined
    }
    const timer = setTimeout(async () => {
      const requestId = ++requestIdRef.current
      try {
        setError('')
        const nextResults = await searchLocations(query.trim())
        if (requestId === requestIdRef.current) setResults(nextResults)
      } catch (searchError) {
        if (requestId === requestIdRef.current) {
          setError(searchError.message)
          setResults([])
        }
      }
    }, 350)
    return () => clearTimeout(timer)
  }, [query])

  function handleUseMyLocation() {
    if (!navigator.geolocation) {
      setError('Geolocation is not supported by this browser.')
      return
    }

    setGeoLoading(true)
    setError('')
    const requestId = ++requestIdRef.current

    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const { latitude, longitude } = position.coords
        try {
          const resolved = await resolveCoordinates(latitude, longitude)
          if (requestId === requestIdRef.current) {
            onSelect(resolved)
            setQuery(resolved.name || 'Your GPS location')
            setResults([])
          }
        } catch (error) {
          if (requestId === requestIdRef.current) setError(error.message)
        } finally {
          if (requestId === requestIdRef.current) setGeoLoading(false)
        }
      },
      () => {
        if (requestId === requestIdRef.current) {
          setGeoLoading(false)
          setError('Location access was denied. Try a city search instead.')
        }
      },
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
    )
  }

  return (
    <div className="search-wrap">
      <label htmlFor="location-search">Search a location</label>
      <div className="search-input-row">
        <span className="search-icon" aria-hidden="true">⌕</span>
        <input id="location-search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="City or place" />
        <button type="button" className="search-button" onClick={() => results[0] && onSelect(results[0])} aria-label="Select first location">Search</button>
      </div>
      <div className="search-actions">
        <button type="button" className="geo-button" onClick={handleUseMyLocation} disabled={geoLoading}>
          {geoLoading ? 'Locating…' : 'Use my location'}
        </button>
      </div>
      {error && <p className="field-error">{error}</p>}
      {results.length > 0 && (
        <div className="location-results">
          {results.map((result) => (
            <button type="button" key={`${result.id}-${result.latitude}`} onClick={() => { onSelect(result); setResults([]); setQuery(result.name) }}>
              <strong>{result.name}</strong><span>{[result.admin1, result.country].filter(Boolean).join(', ')}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}