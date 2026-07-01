import { useEffect, useState } from 'react'
import { apiFetch } from '../api.js'

export default function TeacherSessionsPage() {
  const [sessions, setSessions] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    apiFetch('/api/teacher/sessions/')
      .then(setSessions)
      .catch((err) => setError(err.message))
  }, [])

  return (
    <div>
      <h1>Teacher sessions</h1>
      {error && <p className="error">{error}</p>}
      {sessions.map((session) => (
        <div key={session.id} className="card">
          <strong>{session.title}</strong>
          <p>{session.start_time}</p>
          <p>Status: {session.status}</p>
        </div>
      ))}
      {!sessions.length && !error && <p>No sessions yet.</p>}
    </div>
  )
}
