import { useState } from 'react'

export default function VoiceOutput({ text }) {
  const [speaking, setSpeaking] = useState(false)
  const [notSupported, setNotSupported] = useState(false)

  function handleToggle() {
    if (!('speechSynthesis' in window)) {
      setNotSupported(true)
      return
    }

    if (speaking) {
      window.speechSynthesis.cancel()
      setSpeaking(false)
      return
    }

    const utterance = new SpeechSynthesisUtterance(text)
    utterance.onend = () => setSpeaking(false)
    utterance.onerror = () => setSpeaking(false)
    window.speechSynthesis.cancel()
    window.speechSynthesis.speak(utterance)
    setSpeaking(true)
    setNotSupported(false)
  }

  return (
    <div className="voice-output-wrap">
      <button type="button" className="voice-output" onClick={handleToggle} aria-label={speaking ? 'Stop reading' : 'Read response aloud'}>
        {speaking ? '■ Stop' : '🔊 Read aloud'}
      </button>
      {notSupported && <span className="voice-status">Speech output is not supported by this browser.</span>}
    </div>
  )
}
