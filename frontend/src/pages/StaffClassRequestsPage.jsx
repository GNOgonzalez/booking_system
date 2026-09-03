import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch } from '../api.js'
import { staffPathsForTeacher } from '../hooks/useTeacherScope.js'

function when(value) {
  if (!value) return ''
  return new Date(value).toLocaleString([], {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

export default function StaffClassRequestsPage() {
  const [requests, setRequests] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [busyId, setBusyId] = useState(null)
  const [notice, setNotice] = useState('')
  // Open-pool rows have no teacher until staff picks one.
  const [chosenTeacher, setChosenTeacher] = useState({})

  const load = () => {
    setLoading(true)
    apiFetch('/api/staff/class-requests/')
      .then((data) => setRequests(data.requests || []))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }

  useEffect(load, [])

  const act = async (request, action) => {
    const teacherId = request.teacher || chosenTeacher[request.id]
    if (!teacherId) {
      setError('Pick a teacher first — an open request needs an owner before it can be approved.')
      return
    }
    setError('')
    setNotice('')
    setBusyId(request.id)
    const paths = staffPathsForTeacher(teacherId)
    const url =
      action === 'approve'
        ? paths.classRequestApprove(request.id)
        : paths.classRequestDeny(request.id)
    try {
      await apiFetch(url, { method: 'POST', body: {} })
      setNotice(
        action === 'approve'
          ? `Approved ${request.student_name}'s request — the lesson is on the calendar.`
          : `Denied ${request.student_name}'s request and returned their tickets.`,
      )
      load()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div>
      <p className="card-meta"><Link to="/staff">← Staff dashboard</Link></p>
      <h1>Pending class requests</h1>
      <p className="page-intro">
        Every request waiting on a decision, across all teachers. Requests open to any teacher need
        one assigned before you can approve them.
      </p>

      {error && <div className="error">{error}</div>}
      {notice && <div className="success">{notice}</div>}

      {loading && <div className="empty">Loading requests…</div>}

      {!loading && !requests.length && (
        <div className="empty">
          Nothing pending. New student requests will appear here.
        </div>
      )}

      {requests.map((request) => {
        const isOpenPool = !request.teacher
        const candidates = request.candidate_teachers || []
        return (
          <div key={request.id} className="card">
            <div className="card-row">
              <div>
                <div className="card-title">
                  {request.student_name}
                  {isOpenPool && <span className="badge badge--muted">any teacher</span>}
                </div>
                <div className="card-meta">
                  {request.class_offering_label || request.class_profile_label}
                  {request.class_topic_title ? ` · ${request.class_topic_title}` : ''}
                </div>
                <div className="card-meta">
                  {when(request.start_time)} – {when(request.end_time)} ·{' '}
                  {request.tickets_requested} ticket(s)
                </div>
                <div className="card-meta">Teacher: {request.teacher_name}</div>
              </div>
            </div>

            {isOpenPool && (
              <div className="field">
                <label htmlFor={`teacher-${request.id}`}>Assign to</label>
                <select
                  id={`teacher-${request.id}`}
                  value={chosenTeacher[request.id] || ''}
                  onChange={(e) =>
                    setChosenTeacher((prev) => ({ ...prev, [request.id]: e.target.value }))
                  }
                >
                  <option value="">Choose a teacher…</option>
                  {candidates.map((teacher) => (
                    <option key={teacher.id} value={teacher.id}>
                      {teacher.username}
                    </option>
                  ))}
                </select>
                {!candidates.length && (
                  <p className="card-meta">
                    No teacher has this class in their catalog yet. Add it to a teacher&apos;s
                    classes first.
                  </p>
                )}
              </div>
            )}

            <div className="form-actions">
              <button
                type="button"
                onClick={() => act(request, 'approve')}
                disabled={busyId === request.id}
              >
                {busyId === request.id ? 'Working…' : 'Approve'}
              </button>
              <button
                type="button"
                className="secondary"
                onClick={() => act(request, 'deny')}
                disabled={busyId === request.id}
              >
                Deny
              </button>
              {request.teacher && (
                <Link className="btn secondary" to={`/staff/teachers/${request.teacher}/requests`}>
                  Open teacher view
                </Link>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}
