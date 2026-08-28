import { useEffect, useRef, useState } from 'react'
import ChatMessage from './ChatMessage'
import VoiceInput from './VoiceInput'
import VoiceOutput from './VoiceOutput'
import { sendChat } from '../services/api'

const historyLimit = 10

export default function ChatWindow({ location, currentWeather, forecast, onLocationResolved }) {
  const chatLogRef = useRef(null)
  const [message, setMessage] = useState('')
  const [messages, setMessages] = useState(() => [{ id: crypto.randomUUID(), role: 'assistant', text: `Hi! I can help with weather in ${location?.name || 'your location'}. Ask about rain, travel, heat, or what to expect later today.`, risks: [] }])
  const [activeLocation, setActiveLocation] = useState(location)
  const [error, setError] = useState('')
  const [language, setLanguage] = useState('en')
  const [sending, setSending] = useState(false)
  const [promptSuggestions, setPromptSuggestions] = useState([])

  const liveCurrent = currentWeather?.current || null
  const weatherSnapshot = liveCurrent ? {
    temperature: Number.isFinite(Number(liveCurrent.temperature)) ? Number(liveCurrent.temperature) : null,
    description: liveCurrent.description || 'Conditions unavailable',
    humidity: Number.isFinite(Number(liveCurrent.humidity)) ? Number(liveCurrent.humidity) : null,
    wind: Number.isFinite(Number(liveCurrent.wind_speed)) ? Number(liveCurrent.wind_speed) : null,
  } : null

  function buildSuggestions(weather = liveCurrent, question = '') {
    const normalized = question.toLowerCase()
    if (normalized.includes('rain') || normalized.includes('umbrella') || normalized.includes('storm')) return ['How strong is the rain likely to be later?', 'Should I carry an umbrella today?', 'What is the weekend forecast?']
    if (normalized.includes('travel') || normalized.includes('trip') || normalized.includes('going out')) return ['Is it a good day for travel?', 'What is the next 3-day forecast?', 'Should I plan around the wind today?']
    if (normalized.includes('heat') || normalized.includes('hot') || normalized.includes('temperature')) return ['Is it safe to stay outside in this heat?', 'How hot will it be tomorrow?', 'Should I drink more water outside today?']
    if (weather) return weather.temperature >= 30 ? ['Is it safe to go out in this heat?', 'Will it rain this afternoon?', 'What is the weekend forecast?'] : ['Will it rain today?', 'How hot will it be tomorrow?', 'Should I plan travel around the weather this week?']
    return ['Will it rain today?', 'How hot will it be tomorrow?', 'Should I carry an umbrella tonight?', 'What is the weekend forecast?']
  }

  useEffect(() => setPromptSuggestions(buildSuggestions()), [currentWeather])
  useEffect(() => setActiveLocation(location), [location])

  useEffect(() => {
    chatLogRef.current?.scrollTo({ top: chatLogRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, sending])

  async function submitQuestion(question) {
    const trimmedQuestion = question.trim()
    if (!trimmedQuestion || sending) return
    const previousMessages = messages
      .filter((item) => (item.role === 'user' || item.role === 'assistant') && typeof item.text === 'string' && item.text.trim())
      .slice(-historyLimit)
    const nextMessages = [...messages, { id: crypto.randomUUID(), role: 'user', text: trimmedQuestion, risks: [] }]
    setMessages(nextMessages)
    setMessage('')
    setError('')
    setSending(true)
    try {
      const history = previousMessages.map((item) => ({
        role: item.role,
        content: item.role === 'assistant' && item.location?.name
          ? `Weather for: ${item.location.name}\n${item.text}`
          : item.text,
      }))
      const response = await sendChat(trimmedQuestion, language, activeLocation, history)
      const answer = typeof response.answer === 'string' && response.answer.trim() ? response.answer : 'WeatherGPT returned an invalid answer. Please try again.'
      const risks = Array.isArray(response.alerts) ? response.alerts : (Array.isArray(response.risks) ? response.risks : [])
      setMessages([...nextMessages, {
        id: crypto.randomUUID(), role: 'assistant', text: answer, risks,
        location: response.resolved_location || response.location,
        weather: response.weather || null,
        timePeriod: response.time_period || 'current',
        agricultureAdvisory: response.agriculture_advisory,
        fallback: !response.llm_available,
      }])
      if (response.resolved_location) setActiveLocation(response.resolved_location)
      if (response.resolved_location) onLocationResolved?.(response.resolved_location)
      setPromptSuggestions(buildSuggestions(liveCurrent, trimmedQuestion))
    } catch (requestError) {
      setError(requestError.message || 'The weather service returned an error.')
    } finally {
      setSending(false)
    }
  }

  function handleSuggestion(suggestion) {
    setMessage(suggestion)
    void submitQuestion(suggestion)
  }

  async function handleSubmit(event) {
    event.preventDefault()
    await submitQuestion(message)
  }

  const voiceLanguage = { en: 'en-IN', hinglish: 'hi-IN', hi: 'hi-IN', bn: 'bn-IN', or: 'or-IN', ta: 'ta-IN' }[language] || 'en-IN'

  return <section className="chat-panel">
    <div className="section-heading">
      <div><div className="eyebrow">Ask the atmosphere</div><h2>WeatherGPT chat</h2></div>
      <label className="language-select">Language<select value={language} onChange={(event) => setLanguage(event.target.value)} aria-label="Response language">
        <option value="en">English</option><option value="hinglish">Hinglish</option><option value="hi">हिन्दी</option><option value="bn">বাংলা</option><option value="or">ଓଡ଼ିଆ</option>
      </select></label>
    </div>
    {weatherSnapshot && <div className="weather-glance"><div className="weather-glance-header">Live snapshot</div><div className="weather-glance-content"><div className="weather-glance-temp">{weatherSnapshot.temperature ?? '—'}°</div><div className="weather-glance-copy"><strong>{location?.name || 'Your location'}</strong><span>{weatherSnapshot.description}</span><small>{weatherSnapshot.humidity ?? '—'}% humidity · {weatherSnapshot.wind ?? '—'} km/h wind</small></div></div></div>}
    <div className="chat-log" ref={chatLogRef} aria-live="polite">
      {messages.map((item, index) => <ChatMessage key={item.id || `${item.role}-${index}`} message={item} risks={item.risks || []} />)}
      {sending && <div className="chat-message assistant"><span className="message-label">WeatherGPT</span><div className="chat-thinking" aria-label="WeatherGPT is thinking"><span /><span /><span /></div></div>}
    </div>
    {error && <p className="chat-error">{error}</p>}
    <div className="chat-controls"><VoiceInput value={message} onChange={setMessage} language={voiceLanguage} /><VoiceOutput text={messages[messages.length - 1]?.text || ''} /></div>
    <div className="suggestion-row">{promptSuggestions.map((suggestion) => <button key={suggestion} type="button" className="suggestion-chip" onClick={() => handleSuggestion(suggestion)}>{suggestion}</button>)}</div>
    <form className="chat-form" onSubmit={handleSubmit}><input value={message} onChange={(event) => setMessage(event.target.value)} placeholder="Will it rain tomorrow?" aria-label="Ask WeatherGPT" disabled={sending} /><button type="submit" aria-label="Send message" disabled={sending}>{sending ? 'Thinking' : 'Send'} <span aria-hidden="true">↗</span></button></form>
  </section>
}