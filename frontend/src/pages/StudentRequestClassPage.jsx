import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch } from '../api.js'

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

export default function StudentRequestClassPage() {
  const [teachers, setTeachers] = useState([])
  const [classes, setClasses] = useState([])
  const [availability, setAvailability] = useState({ windows: [], busy: [] })
  const [requests, setRequests] = useState([])
  const [ticketsRemaining, setTicketsRemaining] = useState(null)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState({
    teacher: '',
    classOffering: '',
    classTopic: '',
    start: '',
    end: '',
    tickets: '1',
  })

  const loadRequests = () => {
    apiFetch('/api/class-requests/')
      .then(setRequests)
      .catch(() => {})
  }

  useEffect(() => {
    Promise.all([
      apiFetch('/api/class-requests/teachers/'),
      apiFetch('/api/membership/'),
    ])
      .then(([teacherRows, membership]) => {
        setTeachers(teacherRows)
        setTicketsRemaining(membership?.active ? membership.tickets_remaining : 0)
      })
      .catch((err) => setError(err.message))
    loadRequests()
  }, [])

  useEffect(() => {
    if (!form.teacher) {
      setClasses([])
      setAvailability({ windows: [], busy: [] })
      return
    }
    const qs = `?teacher=${encodeURIComponent(form.teacher)}`
    Promise.all([
      apiFetch(`/api/class-requests/classes/${qs}`),
      apiFetch(`/api/class-requests/availability/${qs}`),
    ])
      .then(([classRows, snapshot]) => {
        setClasses(classRows)
        setAvailability(snapshot)
      })
      .catch((err) => setError(err.message))
  }, [form.teacher])

  const selectedClass = useMemo(
    () => classes.find((item) => String(item.id) === form.classOffering),
    [classes, form.classOffering],
  )

  const topicOptions = selectedClass?.topics || []
  const minTickets = selectedClass?.ticket_cost || 1

  const onClassChange = (classOffering) => {
    const picked = classes.find((item) => String(item.id) === classOffering)
    const firstTopic = picked?.topics?.[0]
    setForm((current) => ({
      ...current,
      classOffering,
      classTopic: firstTopic ? String(firstTopic.id) : '',
      tickets: String(Math.max(picked?.ticket_cost || 1, Number(current.tickets) || 1)),
    }))
  }

  const submit = async (e) => {
    e.preventDefault()
    setSaving(true)
    setError('')
    setMessage('')
    try {
      await apiFetch('/api/class-requests/', {
        method: 'POST',
        body: JSON.stringify({
          teacher: Number(form.teacher),
          class_offering: Number(form.classOffering),
          class_topic: form.classTopic ? Number(form.classTopic) : null,
          start_time: new Date(form.start).toISOString(),
          end_time: new Date(form.end).toISOString(),
          tickets_requested: Number(form.tickets),
        }),
      })
      setMessage('Request sent. Your teacher will review it.')
      setForm((current) => ({
        ...current,
        start: '',
        end: '',
      }))
      loadRequests()
      apiFetch('/api/membership/').then((membership) => {
        setTicketsRemaining(membership?.active ? membership.tickets_remaining : 0)
      })
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  const cancelRequest = async (id) => {
    if (!window.confirm('Cancel this pending request? Your tickets will be returned.')) return
    setError('')
    try {
      await apiFetch(`/api/class-requests/${id}/`, { method: 'DELETE' })
      setMessage('Request cancelled.')
      loadRequests()
      apiFetch('/api/membership/').then((membership) => {
        setTicketsRemaining(membership?.active ? membership.tickets_remaining : 0)
      })
    } catch (err) {
      setError(err.message)
    }
  }

  const pending = requests.filter((item) => item.status === 'pending')

  return (
    <div>
      <h1>Request a class</h1>
      <p className="page-intro">
        Pick a time inside a teacher&apos;s availability, choose the class and topic, and offer tickets.
        Tickets are held until your teacher approves or denies the request.
        {ticketsRemaining != null && (
          <> You have <strong>{ticketsRemaining}</strong> ticket{ticketsRemaining === 1 ? '' : 's'} available.</>
        )}
      </p>
      <p className="card-meta">
        <Link to="/sessions">← Browse scheduled sessions</Link>
      </p>

      {message && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}

      <form onSubmit={submit} className="card" style={{ marginBottom: '1.5rem' }}>
        <h2>New request</h2>
        <div className="field">
          <label>Teacher</label>
          <select
            value={form.teacher}
            onChange={(e) => setForm({ ...form, teacher: e.target.value, classOffering: '', classTopic: '', start: '', end: '' })}
            required
          >
            <option value="">Choose a teacher…</option>
            {teachers.map((teacher) => (
              <option key={teacher.id} value={teacher.id}>{teacher.label}</option>
            ))}
          </select>
          {!teachers.length && <p className="card-meta">No teachers with availability are bookable on your plan.</p>}
        </div>

        {form.teacher && (
          <>
            <div className="field">
              <label>Class</label>
              <select
                value={form.classOffering}
                onChange={(e) => onClassChange(e.target.value)}
                required
              >
                <option value="">Choose a class…</option>
                {classes.map((item) => (
                    <option key={item.id} value={item.id}>
                    {item.label || `${item.subject} · ${item.level} · ${item.focus}`} ({item.ticket_cost} ticket{item.ticket_cost === 1 ? '' : 's'})
                  </option>
                ))}
              </select>
            </div>

            {topicOptions.length > 0 && (
              <div className="field">
                <label>Topic</label>
                <select
                  value={form.classTopic}
                  onChange={(e) => setForm({ ...form, classTopic: e.target.value })}
                >
                  <option value="">No specific topic</option>
                  {topicOptions.map((topic) => (
                    <option key={topic.id} value={topic.id}>{topic.title}</option>
                  ))}
                </select>
              </div>
            )}

            <div className="field">
              <label>Tickets to offer</label>
              <input
                type="number"
                min={minTickets}
                max={ticketsRemaining ?? minTickets}
                value={form.tickets}
                onChange={(e) => setForm({ ...form, tickets: e.target.value })}
                required
              />
              <p className="card-meta">Minimum for this class: {minTickets}. Held until approved or denied.</p>
            </div>

            <div className="row">
              <div className="field grow">
                <label>Start</label>
                <input
                  type="datetime-local"
                  value={form.start}
                  onChange={(e) => setForm({ ...form, start: e.target.value })}
                  required
                />
              </div>
              <div className="field grow">
                <label>End</label>
                <input
                  type="datetime-local"
                  value={form.end}
                  onChange={(e) => setForm({ ...form, end: e.target.value })}
                  required
                />
              </div>
            </div>

            {availability.windows.length > 0 && (
              <details className="card-meta" style={{ marginBottom: '0.75rem' }}>
                <summary>Teacher availability windows (next 4 weeks)</summary>
                <ul className="availability-window-list">
                  {availability.windows.slice(0, 12).map((window) => (
                    <li key={`${window.kind}-${window.start}`}>
                      {window.date} · {window.start_time}–{window.end_time}
                      {window.note ? ` (${window.note})` : ''}
                    </li>
                  ))}
                </ul>
              </details>
            )}
          </>
        )}

        <button type="submit" disabled={saving || !form.teacher}>
          {saving ? 'Sending…' : 'Send request'}
        </button>
      </form>

      <h2>Your requests</h2>
      {pending.map((item) => (
        <div key={item.id} className="card class-request-item">
          <div className="card-title">{item.class_offering_label}</div>
          <div className="card-meta">
            {item.teacher_name} · {formatWhen(item.start_time)} – {formatWhen(item.end_time)}
            {item.class_topic_title && <> · {item.class_topic_title}</>}
          </div>
          <div className="card-meta">
            {item.tickets_requested} ticket{item.tickets_requested === 1 ? '' : 's'} held · Pending approval
          </div>
          <button type="button" className="secondary" onClick={() => cancelRequest(item.id)}>
            Cancel request
          </button>
        </div>
      ))}
      {!pending.length && <p className="card-meta">No pending requests.</p>}
    </div>
  )
}
