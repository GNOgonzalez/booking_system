import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch } from '../api.js'
import SessionCalendar from '../components/SessionCalendar.jsx'
import { staffPathsForTeacher } from '../hooks/useTeacherScope.js'

export default function StaffSchedulePage() {
  const [sessions, setSessions] = useState([])
  const [teachers, setTeachers] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([
      apiFetch('/api/staff/schedule/'),
      apiFetch('/api/staff/teachers/'),
    ])
      .then(([sessionRows, teacherRows]) => {
        setSessions(sessionRows)
        setTeachers(
          (teacherRows || []).map((teacher) => ({
            id: teacher.id,
            label: teacher.label || teacher.username,
            username: teacher.username,
          })),
        )
      })
      .catch((err) => setError(err.message))
  }, [])

  const resolveApiPaths = useCallback(
    (session) => staffPathsForTeacher(session.teacher),
    [],
  )

  return (
    <div className="page-calendar">
      <p className="card-meta"><Link to="/staff">← Staff dashboard</Link></p>
      <h1>Studio schedule</h1>
      <p className="page-intro">
        All teachers on one calendar. Filter by teacher, student, or class, switch to list view, or click a session for details.
      </p>
      {error && <div className="error">{error}</div>}
      {!error && (
        <SessionCalendar
          sessions={sessions}
          showTeacher
          alwaysShowTeacherFilter
          teacherFilterOptions={teachers}
          showNewSession={false}
          showManageSession
          resolveApiPaths={resolveApiPaths}
          onSessionChanged={(updated) => {
            setSessions((rows) => rows.map((s) => (
              s.id === updated.id
                ? { ...s, ...updated, students: updated.students || s.students }
                : s
            )))
          }}
        />
      )}
    </div>
  )
}
