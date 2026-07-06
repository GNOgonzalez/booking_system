import { useEffect, useState } from 'react'
import { apiFetch } from '../api.js'
import { useTeacherScope } from '../hooks/useTeacherScope.js'

function formatDateTime(value) {
  if (!value) return ''
  return new Date(value).toLocaleString(undefined, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

function hiddenByLabel(privacy) {
  if (!privacy) return ''
  if (privacy.hidden_by_student && privacy.hidden_by_teacher) return 'hidden by student and teacher'
  if (privacy.hidden_by_student) return 'hidden by student'
  if (privacy.hidden_by_teacher) return 'hidden by teacher'
  return ''
}

function HistorySessionRow({ session, isStaff, onTogglePrivacy, busy }) {
  const privacy = session.privacy || {}
  const hidden = privacy.hidden_from_peers
  const showStaffBadge = isStaff && hidden
  const canToggle = !isStaff && session.is_own_session && onTogglePrivacy

  return (
    <li className="session-history-item">
      <div>
        <strong>{session.title}</strong>
        <div className="card-meta">{formatDateTime(session.start_time)}</div>
        {session.feedback?.class_notes && (
          <div className="card-meta" style={{ marginTop: '0.35rem' }}>
            {session.feedback.class_notes}
          </div>
        )}
        {canToggle && (
          <label className="card-meta" style={{ display: 'block', marginTop: '0.35rem' }}>
            <input
              type="checkbox"
              checked={Boolean(privacy.hidden_by_teacher)}
              disabled={busy}
              onChange={(e) => onTogglePrivacy(session.id, e.target.checked)}
            />
            {' '}Hide from other teachers
          </label>
        )}
      </div>
      <div className="session-history-badges">
        {session.class_topic && <span className="badge">{session.class_topic}</span>}
        <span className="badge">{session.teacher_name}</span>
        {session.has_feedback ? (
          <span className="badge badge--success">Reported</span>
        ) : (
          <span className="badge badge--muted">No report yet</span>
        )}
        {showStaffBadge && (
          <span className="badge badge--muted" title="Visible to staff for oversight only">
            Hidden from teachers — {hiddenByLabel(privacy)}
          </span>
        )}
      </div>
    </li>
  )
}

/**
 * Cross-teacher past session history for one student (Phase 16).
 * Teachers see shared history minus hidden sessions; staff see everything with badges.
 */
export default function StudentHistoryPanel() {
  const { isStaff, paths } = useTeacherScope()
  const [students, setStudents] = useState([])
  const [studentId, setStudentId] = useState('')
  const [history, setHistory] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    apiFetch(paths.students)
      .then(setStudents)
      .catch((err) => setError(err.message))
  }, [paths.students])

  const loadHistory = (id) => {
    if (!id) {
      setHistory(null)
      return
    }
    setError('')
    apiFetch(paths.studentHistory(id))
      .then(setHistory)
      .catch((err) => {
        setHistory(null)
        setError(err.message)
      })
  }

  const onSelect = (e) => {
    const id = e.target.value
    setStudentId(id)
    loadHistory(id)
  }

  const togglePrivacy = async (sessionId, hidden) => {
    if (!paths.sessionHistoryPrivacy) return
    setBusy(true)
    try {
      await apiFetch(paths.sessionHistoryPrivacy(sessionId), {
        method: 'PATCH',
        body: JSON.stringify({ hidden_by_teacher: hidden }),
      })
      loadHistory(studentId)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const sections = history?.sections || []

  return (
    <div className="card">
      <h2>Student lesson history</h2>
      <p className="card-meta">
        {isStaff
          ? 'Full history including sessions hidden from other teachers (staff oversight).'
          : 'Past lessons this student took with you and other teachers you share them with.'}
      </p>
      {error && <div className="error">{error}</div>}

      <div className="field" style={{ maxWidth: '340px' }}>
        <label>Student</label>
        <select value={studentId} onChange={onSelect}>
          <option value="">Choose a student…</option>
          {students.map((student) => (
            <option key={student.id} value={student.id}>
              {student.label}
            </option>
          ))}
        </select>
      </div>

      {studentId && !sections.length && !error && (
        <p className="card-meta">No shared past lessons for this student yet.</p>
      )}

      {sections.map((section) => (
        <div key={section.subject} style={{ marginTop: '0.75rem' }}>
          <h2>{section.subject}</h2>
          {(section.classes || []).map((klass) => (
            <div key={klass.class_offering_id} style={{ marginBottom: '0.75rem' }}>
              <div className="card-title">{klass.label}</div>
              <div className="card-meta">
                {klass.level} · {klass.focus} · {klass.session_count} session{klass.session_count === 1 ? '' : 's'}
              </div>
              <ul className="session-history-list">
                {klass.sessions.map((session) => (
                  <HistorySessionRow
                    key={session.id}
                    session={session}
                    isStaff={isStaff}
                    onTogglePrivacy={togglePrivacy}
                    busy={busy}
                  />
                ))}
              </ul>
            </div>
          ))}
        </div>
      ))}

      {!isStaff && studentId && (
        <p className="card-meta" style={{ marginTop: '0.75rem' }}>
          Hiding a lesson removes it from other teachers&apos; view. Studio staff may still
          access records for safety and policy reasons.
        </p>
      )}
    </div>
  )
}
