import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch } from '../api.js'
import { useGlossary } from '../hooks/useGlossary.jsx'

const EMPTY = {
  teacher: '',
  subject: '',
  level: '',
  focus: '',
  topics: [''],
  topics_ordered: false,
  default_capacity: 4,
  ticket_cost: 1,
}

function topicsPayload(topics) {
  return topics
    .map((title, index) => ({ title: title.trim(), sort_order: index }))
    .filter((topic) => topic.title)
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
  const onCheckbox = (key) => (e) => setForm({ ...form, [key]: e.target.checked })

  const setTopicAt = (topics, index, value) => topics.map((item, i) => (i === index ? value : item))
  const addTopicRow = (topics) => [...topics, '']
  const removeTopicRow = (topics, index) => (topics.length <= 1 ? [''] : topics.filter((_, i) => i !== index))

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setMessage('')
    if (!form.teacher) {
      setError('Choose a teacher.')
      return
    }
    const topics = topicsPayload(form.topics)
    if (!topics.length) {
      setError('Add at least one topic.')
      return
    }
    try {
      const created = await apiFetch('/api/staff/classes/', {
        method: 'POST',
        body: JSON.stringify({
          teacher: Number(form.teacher),
          subject: form.subject,
          level: form.level,
          focus: form.focus,
          topics_ordered: form.topics_ordered,
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
        Add a teachable {label('class').toLowerCase()} to any {label('teacher').toLowerCase()}&apos;s catalog — staff can always create {labels('class').toLowerCase()} regardless of {label('teacher').toLowerCase()} permissions.
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
        <div className="row">
          <div className="field grow">
            <label>Subject</label>
            <input value={form.subject} onChange={onField('subject')} placeholder="Japanese" required />
          </div>
          <div className="field grow">
            <label>Level</label>
            <input value={form.level} onChange={onField('level')} placeholder="Beginner" required />
          </div>
        </div>
        <div className="field">
          <label>Focus</label>
          <input value={form.focus} onChange={onField('focus')} placeholder="Grammar and Vocabulary" required />
        </div>
        <div className="field">
          <label>Topics</label>
          {form.topics.map((topic, index) => (
            <div key={index} className="row" style={{ marginBottom: '0.5rem' }}>
              <input
                className="grow"
                value={topic}
                onChange={(e) => setForm({ ...form, topics: setTopicAt(form.topics, index, e.target.value) })}
                placeholder={index === 0 ? 'Present Tense Verbs' : 'Another topic'}
                required={index === 0}
              />
              {form.topics.length > 1 && (
                <button
                  type="button"
                  className="secondary"
                  onClick={() => setForm({ ...form, topics: removeTopicRow(form.topics, index) })}
                >
                  Remove
                </button>
              )}
            </div>
          ))}
          <button
            type="button"
            className="secondary"
            onClick={() => setForm({ ...form, topics: addTopicRow(form.topics) })}
          >
            Add topic
          </button>
        </div>
        <label className="checkbox-row">
          <input type="checkbox" checked={form.topics_ordered} onChange={onCheckbox('topics_ordered')} />
          Teach topics in order
        </label>
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
