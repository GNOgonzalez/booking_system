import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch } from '../api.js'
import { useGlossary } from '../hooks/useGlossary.jsx'
import ClassCatalogPicker, {
  catalogSelectionToTopics,
  EMPTY_CATALOG_SELECTION,
} from '../components/ClassCatalogPicker.jsx'

const EMPTY = {
  teacher: '',
  catalog: { ...EMPTY_CATALOG_SELECTION },
  default_capacity: 4,
  ticket_cost: 1,
}

export default function StaffCreateClassPage() {
  const { label, labels } = useGlossary()
  const [teachers, setTeachers] = useState([])
  const [form, setForm] = useState(EMPTY)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  useEffect(() => {
    apiFetch('/api/staff/teachers/')
      .then(setTeachers)
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
    const { catalog } = form
    const topics = catalogSelectionToTopics(catalog.topicTitles)
    if (!catalog.subject || !catalog.level || !catalog.focus) {
      setError('Choose subject, level, and focus.')
      return
    }
    if (!topics.length) {
      setError('Select at least one topic.')
      return
    }
    try {
      const created = await apiFetch('/api/staff/classes/', {
        method: 'POST',
        body: JSON.stringify({
          teacher: Number(form.teacher),
          subject: catalog.subject,
          level: catalog.level,
          focus: catalog.focus,
          topics_ordered: catalog.topics_ordered,
          topics,
          default_capacity: Number(form.default_capacity),
          ticket_cost: Number(form.ticket_cost) || 1,
          is_active: true,
        }),
      })
      setMessage(`Class added for ${teachers.find((t) => String(t.id) === form.teacher)?.label || 'teacher'}.`)
      setForm({ ...EMPTY, teacher: form.teacher })
      void created
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div>
      <p className="card-meta"><Link to="/staff">← Staff dashboard</Link></p>
      <h1>Create {label('class').toLowerCase()}</h1>
      <p className="page-intro">
        Add a teachable {label('class').toLowerCase()} to any {label('teacher').toLowerCase()}&apos;s catalog.
        Pick from the studio roadmap, or{' '}
        <Link to="/staff/class-catalog">edit subjects, levels, and topics</Link>.
      </p>
      {message && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}

      <form onSubmit={submit} className="card">
        <div className="field">
          <label>{label('teacher')}</label>
          <select value={form.teacher} onChange={onField('teacher')} required>
            <option value="">Choose a {label('teacher').toLowerCase()}…</option>
            {teachers.map((t) => (
              <option key={t.id} value={t.id}>{t.label}</option>
            ))}
          </select>
        </div>
        <ClassCatalogPicker
          value={form.catalog}
          onChange={(catalog) => setForm({ ...form, catalog })}
          showStaffCatalogLink
        />
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
