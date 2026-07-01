import { useEffect, useState } from 'react'
import { apiFetch } from '../api.js'

export default function StudentSessionsPage() {
  const [sessions, setSessions] = useState([])
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const load = () => {
    apiFetch('/api/sessions/open/')
      .then(setSessions)
      .catch((err) => setError(err.message))
  }

  useEffect(load, [])

  const book = async (sessionId) => {
    setError('')
    setMessage('')
    try {
      await apiFetch('/api/bookings/create/', {
        method: 'POST',
        body: JSON.stringify({ session_id: sessionId }),
      })
      setMessage('Booked!')
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div>
      <h1>Open sessions</h1>
      <p className="page-intro">Browse and book upcoming sessions.</p>
      {message && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}
      {sessions.map((session) => (
        <div key={session.id} className="card">
          <div className="card-row">
            <div>
              <div className="card-title">{session.title}</div>
              <div className="card-meta">
                {new Date(session.start_time).toLocaleString()} · Seats {session.confirmed_count}/{session.capacity}
                {session.class_type_name ? ` · ${session.class_type_name}` : ''}
              </div>
              {session.meeting_url && (
                <div className="card-meta">
                  <a href={session.meeting_url} target="_blank" rel="noreferrer">Meeting link</a>
                </div>
              )}
            </div>
            <button type="button" onClick={() => book(session.id)}>Book</button>
          </div>
        </div>
      ))}
      {!sessions.length && !error && <div className="empty">No open sessions right now.</div>}
    </div>
  )
}
