import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch } from '../api.js'
import { useGlossary } from '../hooks/useGlossary.jsx'

const EMPTY = {
  teacher: '',
  track: '',
  default_capacity: 4,
  ticket_cost: 1,
}

export default function StaffCreateClassPage() {
  const { label, labels } = useGlossary()
  const [teachers, setTeachers] = useState([])
  const [tracks, setTracks] = useState([])
  const [form, setForm] = useState(EMPTY)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  useEffect(() => {
    Promise.all([
      apiFetch('/api/staff/teachers/'),
      apiFetch('/api/curriculum/tracks/'),
    ])
      .then(([teacherRows, trackRows]) => {
        setTeachers(teacherRows)
        setTracks(trackRows)
      })
      .catch((err) => setError(err.message))
  }, [])

  const onField = (key) => (e) => setForm({ ...form, [key]: e.target.value })

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setMessage('')
    if (!form.teacher) {
      setError('Choose a teacher.')
      return
    }
    if (!form.track) {
      setError('Choose a curriculum.')
      return
    }
    try {
      await apiFetch('/api/staff/classes/', {
        method: 'POST',
        body: JSON.stringify({
          teacher: Number(form.teacher),
          track: Number(form.track),
          default_capacity: Number(form.default_capacity),
          ticket_cost: Number(form.ticket_cost) || 1,
          is_active: true,
        }),
      })
      setMessage(`Class added for ${teachers.find((t) => String(t.id) === form.teacher)?.label || 'teacher'}.`)
      setForm({ ...EMPTY, teacher: form.teacher })
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div>
      <p className="card-meta"><Link to="/staff">← Staff dashboard</Link></p>
      <h1>Create {label('class').toLowerCase()}</h1>
      <p className="page-intro">
        Attach a curriculum to a {label('teacher').toLowerCase()} — studio path or a personalized one.
        {' '}<Link to="/staff/curriculum">Manage curricula</Link>.
      </p>
      {message && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}
      <form onSubmit={submit} className="card">
        <div className="field">
          <label htmlFor="staff-class-teacher">{label('teacher')}</label>
          <select id="staff-class-teacher" value={form.teacher} onChange={onField('teacher')}>
            <option value="">Choose…</option>
            {teachers.map((t) => (
              <option key={t.id} value={t.id}>{t.label || t.username}</option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="staff-class-track">Curriculum</label>
          <select id="staff-class-track" value={form.track} onChange={onField('track')}>
            <option value="">Choose a path…</option>
            {tracks.map((track) => (
              <option key={track.id} value={track.id}>
                {track.title}
                {track.is_template ? '' : ' (personalized)'}
                {` · ${track.module_count} modules`}
              </option>
            ))}
          </select>
        </div>
        <div className="row">
          <div className="field" style={{ maxWidth: '8rem' }}>
            <label>Default capacity</label>
            <input type="number" min="1" value={form.default_capacity} onChange={onField('default_capacity')} />
          </div>
          <div className="field" style={{ maxWidth: '8rem' }}>
            <label>Ticket cost</label>
            <input type="number" min="1" value={form.ticket_cost} onChange={onField('ticket_cost')} />
          </div>
        </div>
        <button type="submit">Add {label('class').toLowerCase()}</button>
      </form>
    </div>
  )
}
