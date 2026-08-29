import { useEffect, useRef, useState } from 'react'
import { searchLocations } from '../services/api'

export default function LocationSearch({ onSelect, geoError = '' }) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [error, setError] = useState('')
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

  return (
    <div className="search-wrap">
      <label htmlFor="location-search">Search a location</label>
      <div className="search-input-row">
        <span className="search-icon" aria-hidden="true">⌕</span>
        <input id="location-search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="City or place" />
        <button type="button" className="search-button" onClick={() => results[0] && onSelect(results[0])} aria-label="Select first location">Search</button>
      </div>
      {(error || geoError) && <p className="field-error">{error || geoError}</p>}
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