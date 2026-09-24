import { useEffect, useState } from 'react'
import { NavLink } from 'react-router-dom'
import { apiFetch } from '../api.js'
import { useGlossary } from '../hooks/useGlossary.jsx'

function formatLessonTime(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString(undefined, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

export default function TeacherHomeDashboard({ canWriteReports = true }) {
  const { label, labels } = useGlossary()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    apiFetch('/api/teacher/home/')
      .then(setData)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="card card-meta">Loading your lessons…</div>
  if (error) return <div className="error">{error}</div>
  if (!data) return null

  const recent = data.recent_sessions || []
  const missing = data.missing_reports || []
  const hiddenCount = (data.missing_reports_total || 0) - missing.length

  const reportLink = (sessionId, studentId) =>
    `/teacher/progress?session=${sessionId}&student=${studentId}`

  return (
    <>
      <div className="card">
        <div className="card-title">
          {labels('report')} to write
          {missing.length > 0 && <span className="badge"> {data.missing_reports_total}</span>}
        </div>
        {missing.length === 0 ? (
          <p className="card-meta">
            Every finished {label('session').toLowerCase()} has a {label('report').toLowerCase()}.
          </p>
        ) : (
          <>
            <p className="card-meta">
              {label('student')}s from finished {labels('session').toLowerCase()} who are still waiting.
            </p>
            <ul className="teacher-queue-list">
              {missing.map((row) => (
                <li key={`${row.session.id}-${row.student_id}`} className="card-row">
                  <div>
                    <strong>{row.student_name}</strong>
                    <div className="card-meta">
                      {row.session.title} · {formatLessonTime(row.session.end_time)}
                    </div>
                  </div>
                  {canWriteReports && (
                    <NavLink
                      to={reportLink(row.session.id, row.student_id)}
                      className="btn secondary"
                    >
                      Write {label('report').toLowerCase()}
                    </NavLink>
                  )}
                </li>
              ))}
            </ul>
            {hiddenCount > 0 && (
              <p className="card-meta">And {hiddenCount} more older than this list.</p>
            )}
          </>
        )}
      </div>

      <div className="card">
        <div className="card-title">Recently finished</div>
        {recent.length === 0 ? (
          <p className="card-meta">
            No {labels('session').toLowerCase()} finished in the last {data.recent_days} days.
          </p>
        ) : (
          <ul className="teacher-queue-list">
            {recent.map((session) => (
              <li key={session.id} className="card-row">
                <div>
                  <strong>{session.title}</strong>
                  <div className="card-meta">
                    {formatLessonTime(session.end_time)}
                    {session.subject ? ` · ${session.subject}` : ''}
                    {session.students.length ? ` · ${session.students.join(', ')}` : ''}
                  </div>
                </div>
                <div className="card-meta">
                  {session.student_count === 0
                    ? 'No bookings'
                    : `${session.reported_count}/${session.student_count} reported`}
                </div>
              </li>
            ))}
          </ul>
        )}
        <div className="row" style={{ marginTop: '1rem' }}>
          <NavLink to="/teacher/sessions" className="btn secondary">
            My {labels('session').toLowerCase()}
          </NavLink>
          <NavLink to="/teacher/progress" className="btn secondary">
            {label('student')} {labels('report').toLowerCase()}
          </NavLink>
        </div>
      </div>
    </>
  )
}
