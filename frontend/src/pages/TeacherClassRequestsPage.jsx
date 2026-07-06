import { useEffect, useState } from 'react'
import { apiFetch } from '../api.js'
import { useTeacherScope } from '../hooks/useTeacherScope.js'

function toLocalInputValue(iso) {
  if (!iso) return ''
  const date = new Date(iso)
  const pad = (n) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

function formatWhen(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

export default function TeacherClassRequestsPage() {
  const { isStaff, paths, teacherId } = useTeacherScope()
  const [requests, setRequests] = useState([])
  const [classes, setClasses] = useState([])
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [savingId, setSavingId] = useState(null)
  const [edits, setEdits] = useState({})

  const requestBase = isStaff
    ? `/api/staff/teachers/${teacherId}/class-requests`
    : '/api/teacher/class-requests'

  const load = () => {
    apiFetch(`${requestBase}/`)
      .then((rows) => {
        setRequests(rows)
        const next = {}
        rows.forEach((item) => {
          next[item.id] = {
            classOffering: String(item.class_offering),
            classTopic: item.class_topic ? String(item.class_topic) : '',
            start: toLocalInputValue(item.start_time),
            end: toLocalInputValue(item.end_time),
            capacity: '',
          }
        })
        setEdits(next)
      })
      .catch((err) => setError(err.message))
  }

  useEffect(() => {
    load()
    apiFetch(paths.classes)
      .then((rows) => setClasses(rows.filter((item) => item.is_active)))
      .catch(() => setClasses([]))
  }, [requestBase, paths.classes])

  const updateEdit = (id, patch) => {
    setEdits((current) => ({ ...current, [id]: { ...current[id], ...patch } }))
  }

  const saveEdits = async (id) => {
    const edit = edits[id]
    if (!edit) return
    setSavingId(id)
    setError('')
    try {
      await apiFetch(`${requestBase}/${id}/`, {
        method: 'PATCH',
        body: JSON.stringify({
          class_offering: Number(edit.classOffering),
          class_topic: edit.classTopic ? Number(edit.classTopic) : null,
          start_time: new Date(edit.start).toISOString(),
          end_time: new Date(edit.end).toISOString(),
        }),
      })
      setMessage('Request updated.')
      load()
    } catch (err) {
      setError(err.message)
    } finally {
      setSavingId(null)
    }
  }

  const approve = async (id) => {
    const edit = edits[id]
    setSavingId(id)
    setError('')
    try {
      const body = {}
      if (edit?.capacity) body.capacity = Number(edit.capacity)
      await apiFetch(`${requestBase}/${id}/approve/`, {
        method: 'POST',
        body: JSON.stringify(body),
      })
      setMessage('Class approved and scheduled.')
      load()
    } catch (err) {
      setError(err.message)
    } finally {
      setSavingId(null)
    }
  }

  const deny = async (id) => {
    if (!window.confirm('Deny this request? Tickets will be returned to the student.')) return
    setSavingId(id)
    setError('')
    try {
      await apiFetch(`${requestBase}/${id}/deny/`, { method: 'POST', body: '{}' })
      setMessage('Request denied.')
      load()
    } catch (err) {
      setError(err.message)
    } finally {
      setSavingId(null)
    }
  }

  const remove = async (id) => {
    if (!window.confirm('Delete this request?')) return
    setSavingId(id)
    setError('')
    try {
      await apiFetch(`${requestBase}/${id}/delete/`, { method: 'DELETE' })
      setMessage('Request removed.')
      load()
    } catch (err) {
      setError(err.message)
    } finally {
      setSavingId(null)
    }
  }

  return (
    <div>
      <h1>Class requests</h1>
      <p className="page-intro">
        Review student requests for times inside your availability. Edit the class, topic, or time before approving.
        Approved requests spend the student&apos;s held tickets. Denied or deleted requests return them.
      </p>
      {message && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}

      {requests.map((item) => {
        const edit = edits[item.id] || {}
        const pickedClass = classes.find((row) => String(row.id) === edit.classOffering)
        const topics = pickedClass?.topics || []
        const busy = savingId === item.id
        return (
          <div key={item.id} className="card class-request-review">
            <div className="card-title">{item.student_name}</div>
            <div className="card-meta">
              Requested {formatWhen(item.created_at)} · {item.tickets_requested} ticket{item.tickets_requested === 1 ? '' : 's'}
            </div>

            <div className="field">
              <label>Class</label>
              <select
                value={edit.classOffering || ''}
                onChange={(e) => updateEdit(item.id, { classOffering: e.target.value, classTopic: '' })}
              >
                {classes.map((row) => (
                  <option key={row.id} value={row.id}>{row.label || row.subject}</option>
                ))}
              </select>
            </div>

            {topics.length > 0 && (
              <div className="field">
                <label>Topic</label>
                <select
                  value={edit.classTopic || ''}
                  onChange={(e) => updateEdit(item.id, { classTopic: e.target.value })}
                >
                  <option value="">No specific topic</option>
                  {topics.map((topic) => (
                    <option key={topic.id} value={topic.id}>{topic.title}</option>
                  ))}
                </select>
              </div>
            )}

            <div className="row">
              <div className="field grow">
                <label>Start</label>
                <input
                  type="datetime-local"
                  value={edit.start || ''}
                  onChange={(e) => updateEdit(item.id, { start: e.target.value })}
                />
              </div>
              <div className="field grow">
                <label>End</label>
                <input
                  type="datetime-local"
                  value={edit.end || ''}
                  onChange={(e) => updateEdit(item.id, { end: e.target.value })}
                />
              </div>
            </div>

            <div className="field">
              <label>Session capacity (optional)</label>
              <input
                type="number"
                min="1"
                placeholder={pickedClass ? String(pickedClass.default_capacity) : '4'}
                value={edit.capacity || ''}
                onChange={(e) => updateEdit(item.id, { capacity: e.target.value })}
              />
            </div>

            <div className="form-actions">
              <button type="button" disabled={busy} onClick={() => saveEdits(item.id)}>
                {busy ? 'Saving…' : 'Save edits'}
              </button>
              <button type="button" className="secondary" disabled={busy} onClick={() => approve(item.id)}>
                Approve
              </button>
              <button type="button" className="ghost" disabled={busy} onClick={() => deny(item.id)}>
                Deny
              </button>
              <button type="button" className="ghost" disabled={busy} onClick={() => remove(item.id)}>
                Delete
              </button>
            </div>
          </div>
        )
      })}

      {!requests.length && !error && <p className="card-meta">No pending requests.</p>}
    </div>
  )
}
