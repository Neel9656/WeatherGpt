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

    recognition.onend = () => setListening(false)
    recognition.onerror = () => setListening(false)

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
    recognitionRef.current.start()
    setListening(true)
    setUnsupportedMessage('')
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
