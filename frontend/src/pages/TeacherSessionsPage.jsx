import { useEffect, useState } from 'react'
import { apiFetch } from '../api.js'
import { useTeacherScope } from '../hooks/useTeacherScope.js'
import { useTeacherPermissions } from '../hooks/useTeacherPermissions.js'
import SessionCalendar from '../components/SessionCalendar.jsx'

export default function TeacherSessionsPage() {
  const { isStaff, paths } = useTeacherScope()
  const { can } = useTeacherPermissions()
  const [sessions, setSessions] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    apiFetch(paths.sessions)
      .then(setSessions)
      .catch((err) => setError(err.message))
  }, [paths.sessions])

  const refreshSession = (updated) => {
    setSessions((rows) => rows.map((s) => (s.id === updated.id ? updated : s)))
  }

  return (
    <div className={isStaff ? '' : 'page-calendar'}>
      {!isStaff && <h1>My sessions</h1>}
      {!isStaff && (
        <p className="page-intro">Your teaching schedule in calendar view. Click a session to open its details.</p>
      )}
      {error && <div className="error">{error}</div>}
      {!error && (
        <SessionCalendar
          sessions={sessions}
          apiPaths={paths}
          showNewSession={isStaff || can('manage_schedule')}
          showWriteReport={isStaff || can('write_reports')}
          showManageSession={isStaff || can('manage_schedule')}
          onSessionChanged={refreshSession}
        />
      )}
    </div>
  )
}
