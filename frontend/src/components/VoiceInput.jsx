import { useEffect, useRef, useState } from 'react'

export default function VoiceInput({ value, onChange, language = 'en-IN' }) {
  const [listening, setListening] = useState(false)
  const [unsupportedMessage, setUnsupportedMessage] = useState('')
  const recognitionRef = useRef(null)
  const startingRef = useRef(false)
  const receivedResultRef = useRef(false)

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
      receivedResultRef.current = true
      const transcript = Array.from(event.results)
        .map((result) => result[0]?.transcript ?? '')
        .join(' ')
        .trim()

      if (transcript) {
        onChange((currentValue) => `${(currentValue || '').trim()} ${transcript}`.trim())
      }
    }

    recognition.onstart = () => {
      setListening(true)
      setUnsupportedMessage('')
      startingRef.current = false
    }

    recognition.onend = () => {
      setListening(false)
      startingRef.current = false
      if (!receivedResultRef.current) {
        setUnsupportedMessage('No speech was detected. Please try again.')
      }
    }

    recognition.onerror = (event) => {
      setListening(false)
      startingRef.current = false
      const messages = {
        'not-allowed': 'Microphone permission was denied. Allow access and try again.',
        'service-not-allowed': 'Microphone permission was denied. Allow access and try again.',
        'audio-capture': 'No microphone was found. Check your device and try again.',
        'no-speech': 'No speech was detected. Please try again.',
        network: 'Speech recognition service is unavailable. Check your internet connection and try again.',
      }
      setUnsupportedMessage(messages[event.error] || 'Voice input could not start. Please try again.')
    }

    recognitionRef.current = recognition
    return () => {
      recognition.stop()
      recognition.onresult = null
      recognition.onerror = null
      recognition.onend = null
      recognition.onstart = null
      recognitionRef.current = null
    }
  }, [language, onChange])

  function stopListening() {
    if (!recognitionRef.current) return
    receivedResultRef.current = false
    recognitionRef.current.stop()
    setListening(false)
    startingRef.current = false
  }

  async function toggleListening() {
    if (!recognitionRef.current) {
      setUnsupportedMessage('Voice input is not supported by this browser. Try Chrome or Edge.')
      return
    }

    if (listening || startingRef.current) {
      stopListening()
      return
    }

    try {
      if (navigator.mediaDevices?.getUserMedia) {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
        stream.getTracks().forEach((track) => track.stop())
      }

      recognitionRef.current.lang = language
      receivedResultRef.current = false
      startingRef.current = true
      recognitionRef.current.start()
    } catch (error) {
      startingRef.current = false
      setListening(false)

      if (error && error.name === 'NotAllowedError') {
        setUnsupportedMessage('Microphone permission was denied. Allow access and try again.')
        return
      }

      if (error && error.name === 'NotFoundError') {
        setUnsupportedMessage('No microphone was found. Check your device and try again.')
        return
      }

      setUnsupportedMessage('Voice input could not start. Please try again.')
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
