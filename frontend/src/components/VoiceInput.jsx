import { useEffect, useRef, useState } from 'react'

export default function VoiceInput({ value, onChange, language = 'en-IN' }) {
  const [listening, setListening] = useState(false)
  const [unsupportedMessage, setUnsupportedMessage] = useState('')
  const recognitionRef = useRef(null)

  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SpeechRecognition) {
      setUnsupportedMessage('Voice input is not supported by this browser. Try Chrome or Edge.')
      return undefined
    }

    const recognition = new SpeechRecognition()
    recognition.lang = language
    recognition.continuous = false
    recognition.interimResults = false

    recognition.onresult = (event) => {
      const transcript = Array.from(event.results)
        .map((result) => result[0]?.transcript ?? '')
        .join(' ')
        .trim()
      if (transcript) {
        onChange((currentValue) => `${currentValue.trim()} ${transcript}`.trim())
      }
    }

    recognition.onstart = () => {
      setListening(true)
      setUnsupportedMessage('')
    }
    recognition.onend = () => setListening(false)
    recognition.onerror = (event) => {
      setListening(false)
      const messages = {
        'not-allowed': 'Microphone permission was denied. Allow access and try again.',
        'service-not-allowed': 'Microphone permission was denied. Allow access and try again.',
        'audio-capture': 'No microphone was found. Check your device and try again.',
        network: 'Voice recognition is unavailable right now. Please try again.',
      }
      setUnsupportedMessage(messages[event.error] || 'Voice input could not start. Please try again.')
    }

    recognitionRef.current = recognition
    return () => {
      recognition.stop()
    }
  }, [language, onChange])

  function toggleListening() {
    if (!recognitionRef.current) {
      setUnsupportedMessage('Voice input is not supported by this browser. Try Chrome or Edge.')
      return
    }

    if (listening) {
      recognitionRef.current.stop()
      setListening(false)
      return
    }

    recognitionRef.current.lang = language
    try {
      recognitionRef.current.start()
    } catch (error) {
      if (error.name !== 'InvalidStateError') {
        setUnsupportedMessage('Voice input could not start. Please try again.')
      }
    }
  }

  return (
    <div className="voice-input-wrap">
      <button
        type="button"
        className={`voice-toggle ${listening ? 'is-listening' : ''}`}
        aria-label={listening ? 'Stop voice input' : 'Start voice input'}
        onClick={toggleListening}
      >
        {listening ? '🎤 Listening...' : '🎤'}
      </button>
      {unsupportedMessage && <p className="voice-status">{unsupportedMessage}</p>}
      {value && <span className="voice-preview">{value}</span>}
    </div>
  )
}
