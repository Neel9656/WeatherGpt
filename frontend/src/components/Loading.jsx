export default function Loading({ label = 'Loading weather data' }) {
  return <div className="loading-state"><span className="spinner" aria-hidden="true" />{label}</div>
}