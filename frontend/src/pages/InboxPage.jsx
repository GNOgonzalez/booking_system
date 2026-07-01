import { useEffect, useState } from 'react'
import { apiFetch } from '../api.js'

export default function InboxPage() {
  const [messages, setMessages] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    apiFetch('/api/messages/')
      .then(setMessages)
      .catch((err) => setError(err.message))
  }, [])

  return (
    <div>
      <h1>Inbox</h1>
      {error && <p className="error">{error}</p>}
      {messages.map((msg) => (
        <div key={msg.id} className="card">
          <strong>{msg.subject}</strong>
          <p>From {msg.sender_name}</p>
          <p>{msg.body}</p>
        </div>
      ))}
      {!messages.length && !error && <p>No messages.</p>}
    </div>
  )
}
