import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch } from '../api.js'
import {
  datetimeLocalToIso,
  formatDateTime,
  toDatetimeLocal,
} from '../utils/datetime.js'
import { useScoreDimensions, scoreValue } from '../hooks/useScoreDimensions.js'
import SessionReportForm from './SessionReportForm.jsx'

function formatDuration(startIso, endIso) {
  const mins = Math.round((new Date(endIso) - new Date(startIso)) / 60000)
  if (mins < 60) return `${mins} minutes`
  const h = Math.floor(mins / 60)
  const m = mins % 60
  return m ? `${h} hr ${m} min` : `${h} hour${h > 1 ? 's' : ''}`
}

export default function SessionDetailPanel({
  session,
  onClose,
  apiPaths,
  showTeacherLink = false,
  showWriteReport = true,
  showManageSession = false,
  onSessionChanged,
}) {
  const dimensions = useScoreDimensions(session?.class_subject || '')
  const [students, setStudents] = useState([])
  const [reports, setReports] = useState([])
  const [classes, setClasses] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [showReport, setShowReport] = useState(false)
  const [editing, setEditing] = useState(false)
  const [editForm, setEditForm] = useState(null)
  const [saving, setSaving] = useState(false)

  const studentsPath = session && apiPaths?.sessionStudents
    ? apiPaths.sessionStudents(session.id)
    : ''
  const feedbackPath = apiPaths?.feedback || ''
  const classesPath = showManageSession ? (apiPaths?.classes || '') : ''

  useEffect(() => {
    if (!session || !studentsPath || !feedbackPath) return undefined

    let cancelled = false
    setShowReport(false)
    setEditing(false)
    setLoading(true)
    setError('')
    setMessage('')

    Promise.all([
      apiFetch(studentsPath),
      apiFetch(feedbackPath),
      classesPath ? apiFetch(classesPath) : Promise.resolve([]),
    ])
      .then(([booked, allReports, classRows]) => {
        if (cancelled) return
        setStudents(booked)
        setReports(allReports.filter((r) => r.session === session.id))
        setClasses(classRows)
        setEditForm({
          class_offering: String(session.class_offering || ''),
          start_time: toDatetimeLocal(session.start_time),
          end_time: toDatetimeLocal(session.end_time),
          capacity: String(session.capacity),
        })
      })
      .catch((err) => {
        if (!cancelled) setError(err.message)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [session?.id, studentsPath, feedbackPath, classesPath])

  const saveSession = async (e) => {
    e.preventDefault()
    if (!apiPaths?.sessionDetail) return
    setSaving(true)
    setError('')
    setMessage('')
    try {
      const updated = await apiFetch(apiPaths.sessionDetail(session.id), {
        method: 'PATCH',
        body: JSON.stringify({
          class_offering: Number(editForm.class_offering),
          start_time: datetimeLocalToIso(editForm.start_time),
          end_time: datetimeLocalToIso(editForm.end_time),
          capacity: Number(editForm.capacity),
        }),
      })
      setMessage('Session updated.')
      setEditing(false)
      onSessionChanged?.(updated)
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  const cancelSession = async () => {
    if (!apiPaths?.sessionDetail || !window.confirm('Cancel this session? Students will no longer be able to book it.')) return
    setSaving(true)
    setError('')
    try {
      const updated = await apiFetch(apiPaths.sessionDetail(session.id), { method: 'DELETE' })
      setMessage('Session cancelled.')
      onSessionChanged?.(updated)
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  if (!session) {
    return (
      <aside className="session-panel session-panel--empty card">
        <h2>Session details</h2>
        <p className="card-meta">Click a session on the calendar to see its full details here.</p>
      </aside>
    )
  }

  const spotsLeft = Math.max(session.capacity - session.confirmed_count, 0)

  return (
    <aside className="session-panel card">
      <div className="session-panel-header">
        <div>
          <h2>{session.title}</h2>
          <div className="session-panel-badges">
            {session.teacher_name && (
              <span className="badge">{session.teacher_name}</span>
            )}
            <span className={`badge ${session.status === 'cancelled' ? 'badge--muted' : ''}`}>
              {session.status}
            </span>
          </div>
        </div>
        <button type="button" className="ghost session-panel-close" onClick={onClose} aria-label="Close">
          ✕
        </button>
      </div>

      {error && <div className="error">{error}</div>}
      {message && <div className="success">{message}</div>}

      {showTeacherLink && apiPaths?.staffTeacherSessions && (
        <p className="card-meta" style={{ marginBottom: '0.75rem' }}>
          <Link to={apiPaths.staffTeacherSessions}>Open this teacher&apos;s schedule →</Link>
        </p>
      )}

      <dl className="session-detail-list">
        <div className="session-detail-item">
          <dt>Starts</dt>
          <dd>{formatDateTime(session.start_time)}</dd>
        </div>
        <div className="session-detail-item">
          <dt>Ends</dt>
          <dd>{formatDateTime(session.end_time)}</dd>
        </div>
        <div className="session-detail-item">
          <dt>Duration</dt>
          <dd>{formatDuration(session.start_time, session.end_time)}</dd>
        </div>
        {session.class_subject && (
          <>
            <div className="session-detail-item">
              <dt>Subject</dt>
              <dd>{session.class_subject}</dd>
            </div>
            <div className="session-detail-item">
              <dt>Level</dt>
              <dd>{session.class_level}</dd>
            </div>
            <div className="session-detail-item">
              <dt>Focus</dt>
              <dd>{session.class_focus}</dd>
            </div>
            <div className="session-detail-item">
              <dt>Topic</dt>
              <dd>{session.class_topic}</dd>
            </div>
          </>
        )}
        <div className="session-detail-item">
          <dt>Capacity</dt>
          <dd>
            {session.confirmed_count} of {session.capacity} booked
            {spotsLeft > 0 ? ` · ${spotsLeft} spot${spotsLeft === 1 ? '' : 's'} left` : ' · Full'}
          </dd>
        </div>
        {session.meeting_url && (
          <div className="session-detail-item">
            <dt>{session.meeting_provider_display || 'Meeting'}</dt>
            <dd>
              <a href={session.meeting_url} target="_blank" rel="noreferrer" className="btn secondary">
                Open {session.meeting_provider === 'zoom' ? 'Zoom' : session.meeting_provider === 'google_meet' ? 'Meet' : 'meeting'} link
              </a>
            </dd>
          </div>
        )}
      </dl>

      {showManageSession && session.status !== 'cancelled' && editForm && (
        <div className="session-panel-section">
          {!editing ? (
            <div className="row-actions">
              <button type="button" className="secondary" onClick={() => setEditing(true)}>Edit session</button>
              <button type="button" className="danger" onClick={cancelSession} disabled={saving}>Cancel session</button>
            </div>
          ) : (
            <form onSubmit={saveSession}>
              <h3>Edit session</h3>
              <div className="field">
                <label>Class</label>
                <select
                  value={editForm.class_offering}
                  onChange={(e) => setEditForm({ ...editForm, class_offering: e.target.value })}
                  required
                >
                  <option value="">Choose a class…</option>
                  {classes.filter((c) => c.is_active).map((item) => (
                    <option key={item.id} value={item.id}>{item.label}</option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label>Start</label>
                <input
                  type="datetime-local"
                  value={editForm.start_time}
                  onChange={(e) => setEditForm({ ...editForm, start_time: e.target.value })}
                  required
                />
              </div>
              <div className="field">
                <label>End</label>
                <input
                  type="datetime-local"
                  value={editForm.end_time}
                  onChange={(e) => setEditForm({ ...editForm, end_time: e.target.value })}
                  required
                />
              </div>
              <div className="field">
                <label>Capacity</label>
                <input
                  type="number"
                  min="1"
                  value={editForm.capacity}
                  onChange={(e) => setEditForm({ ...editForm, capacity: e.target.value })}
                />
              </div>
              <div className="row-actions">
                <button type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save'}</button>
                <button type="button" className="secondary" onClick={() => setEditing(false)}>Discard</button>
              </div>
            </form>
          )}
        </div>
      )}

      <div className="session-panel-section">
        <h3>Booked students</h3>
        {loading ? (
          <p className="card-meta">Loading…</p>
        ) : students.length ? (
          <ul className="session-student-list">
            {students.map((student) => (
              <li key={student.id}>{student.label}</li>
            ))}
          </ul>
        ) : (
          <p className="card-meta">No confirmed bookings yet.</p>
        )}
      </div>

      {reports.length > 0 && (
        <div className="session-panel-section">
          <h3>Reports on file</h3>
          {reports.map((report) => (
            <div key={report.id} className="session-report-summary">
              <div className="card-title">{report.student_name}</div>
              <div className="card-meta">
                {dimensions.map((d) => `${d.label[0]}${scoreValue(report, d)}`).join(' · ')}
              </div>
              {report.class_notes && <div className="card-meta">{report.class_notes}</div>}
            </div>
          ))}
        </div>
      )}

      {showWriteReport && (
      <div className="session-panel-section">
        {!showReport ? (
          <button type="button" className="btn-block" onClick={() => setShowReport(true)}>
            Write student report
          </button>
        ) : (
          <SessionReportForm
            session={session}
            apiPaths={apiPaths}
            onCancel={() => setShowReport(false)}
            onSaved={() => {
              setShowReport(false)
              apiFetch(apiPaths.feedback)
                .then((allReports) => setReports(allReports.filter((r) => r.session === session.id)))
                .catch(() => {})
            }}
          />
        )}
      </div>
      )}
    </aside>
  )
}
