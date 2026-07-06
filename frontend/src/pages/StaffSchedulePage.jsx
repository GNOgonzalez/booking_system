import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch } from '../api.js'
import SessionCalendar from '../components/SessionCalendar.jsx'
import { staffPathsForTeacher } from '../hooks/useTeacherScope.js'

export default function StaffSchedulePage() {
  const [sessions, setSessions] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    apiFetch('/api/staff/schedule/')
      .then(setSessions)
      .catch((err) => setError(err.message))
  }, [])

  return (
    <div className="page-calendar">
      <p className="card-meta"><Link to="/staff">← Staff dashboard</Link></p>
      <h1>Studio schedule</h1>
      <p className="page-intro">
        All teachers on one calendar. Click a session for details, or open a teacher&apos;s schedule to manage it.
      </p>
      {error && <div className="error">{error}</div>}
      {!error && (
        <SessionCalendar
          sessions={sessions}
          showTeacher
          showNewSession={false}
          showManageSession
          resolveApiPaths={(session) => staffPathsForTeacher(session.teacher)}
          onSessionChanged={(updated) => {
            setSessions((rows) => rows.map((s) => (s.id === updated.id ? updated : s)))
          }}
        />
      )}
    </div>
  )
}
