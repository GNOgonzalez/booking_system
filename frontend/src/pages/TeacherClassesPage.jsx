import { useEffect, useState } from 'react'
import { apiFetch } from '../api.js'
import { useTeacherScope } from '../hooks/useTeacherScope.js'
import { useTeacherPermissions } from '../hooks/useTeacherPermissions.js'
import { useGlossary } from '../hooks/useGlossary.jsx'

const EMPTY = {
  subject: '',
  level: '',
  focus: '',
  topics: [{ title: '' }],
  topics_ordered: false,
  default_capacity: 4,
  ticket_cost: 1,
}

function formatTopics(item) {
  const titles = (item.topics || []).map((topic) => topic.title).filter(Boolean)
  if (!titles.length) return '—'
  const suffix = item.topics_ordered ? ' (in order)' : ''
  return `${titles.join(' · ')}${suffix}`
}

function topicsPayload(topics) {
  return topics
    .map((topic, index) => ({
      id: topic.id,
      title: (topic.title || '').trim(),
      sort_order: index,
    }))
    .filter((topic) => topic.title)
}

export default function TeacherClassesPage() {
  const { isStaff, paths } = useTeacherScope()
  const { can } = useTeacherPermissions()
  const { label, labels } = useGlossary()
  const canEdit = isStaff || can('manage_classes')
  const [classes, setClasses] = useState([])
  const [form, setForm] = useState(EMPTY)
  const [editingId, setEditingId] = useState(null)
  const [editForm, setEditForm] = useState(null)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const load = () => {
    apiFetch(paths.classes)
      .then(setClasses)
      .catch((err) => setError(err.message))
  }

  useEffect(load, [paths.classes])

  const onField = (key) => (e) => setForm({ ...form, [key]: e.target.value })
  const onCheckbox = (key) => (e) => setForm({ ...form, [key]: e.target.checked })

  const setTopicAt = (topics, index, value) =>
    topics.map((item, i) => (i === index ? { ...item, title: value } : item))
  const addTopicRow = (topics) => [...topics, { title: '' }]
  const removeTopicRow = (topics, index) =>
    (topics.length <= 1 ? [{ title: '' }] : topics.filter((_, i) => i !== index))

  const add = async (e) => {
    e.preventDefault()
    setError('')
    setMessage('')
    const topics = topicsPayload(form.topics)
    if (!topics.length) {
      setError('Add at least one topic.')
      return
    }
    try {
      await apiFetch(paths.classes, {
        method: 'POST',
        body: JSON.stringify({
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
      setForm(EMPTY)
      setMessage(`${label('class')} added.`)
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  const startEdit = (item) => {
    setEditingId(item.id)
    setEditForm({
      subject: item.subject,
      level: item.level,
      focus: item.focus,
      topics: (item.topics || []).length
        ? item.topics.map((topic) => ({ id: topic.id, title: topic.title }))
        : [{ title: '' }],
      topics_ordered: Boolean(item.topics_ordered),
      default_capacity: item.default_capacity,
      ticket_cost: item.ticket_cost ?? 1,
    })
  }

  const saveEdit = async (e) => {
    e.preventDefault()
    setError('')
    setMessage('')
    const topics = topicsPayload(editForm.topics)
    if (!topics.length) {
      setError('Add at least one topic.')
      return
    }
    try {
      await apiFetch(paths.classDetail(editingId), {
        method: 'PATCH',
        body: JSON.stringify({
          subject: editForm.subject,
          level: editForm.level,
          focus: editForm.focus,
          topics_ordered: editForm.topics_ordered,
          topics,
          default_capacity: Number(editForm.default_capacity),
          ticket_cost: Number(editForm.ticket_cost) || 1,
        }),
      })
      setEditingId(null)
      setMessage('Class updated.')
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  const deactivate = async (id) => {
    if (!window.confirm('Deactivate this class? It will no longer appear when scheduling sessions.')) return
    setError('')
    try {
      await apiFetch(paths.classDetail(id), { method: 'DELETE' })
      setMessage('Class deactivated.')
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  const reactivate = async (id) => {
    setError('')
    try {
      await apiFetch(paths.classDetail(id), {
        method: 'PATCH',
        body: JSON.stringify({ is_active: true }),
      })
      setMessage('Class reactivated.')
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  const renderTopicFields = (topics, onChange, ordered, onOrderedChange) => (
    <>
      <div className="field">
        <label>Topics</label>
        {topics.map((topic, index) => (
          <div key={topic.id || `new-${index}`} className="row" style={{ marginBottom: '0.5rem' }}>
            <input
              className="grow"
              value={topic.title}
              onChange={(e) => onChange(setTopicAt(topics, index, e.target.value))}
              placeholder={index === 0 ? 'Present Tense Verbs' : 'Another topic'}
              required={index === 0}
            />
            {topics.length > 1 && (
              <button
                type="button"
                className="secondary"
                onClick={() => onChange(removeTopicRow(topics, index))}
              >
                Remove
              </button>
            )}
          </div>
        ))}
        <button type="button" className="secondary" onClick={() => onChange(addTopicRow(topics))}>
          Add topic
        </button>
      </div>
      <label className="checkbox-row">
        <input type="checkbox" checked={ordered} onChange={onOrderedChange} />
        Teach topics in order
      </label>
    </>
  )

  return (
    <div>
      {!isStaff && <h1>{labels('class')}</h1>}
      <p className="page-intro">
        Teachable catalog — each class has subject, level, focus, and one or more topics (optional order).
      </p>
      {message && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}

      {canEdit ? (
      <form onSubmit={add} className="card">
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
        {renderTopicFields(
          form.topics,
          (topics) => setForm({ ...form, topics }),
          form.topics_ordered,
          onCheckbox('topics_ordered'),
        )}
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
      ) : (
        <div className="card card-meta">You do not have permission to create {labels('class').toLowerCase()}. Contact staff.</div>
      )}

      {classes.map((item) => (
        <div key={item.id} className={`card class-catalog-row${item.is_active ? '' : ' card--inactive'}`}>
          {editingId === item.id ? (
            <form onSubmit={saveEdit}>
              <div className="row">
                <div className="field grow">
                  <label>Subject</label>
                  <input
                    value={editForm.subject}
                    onChange={(e) => setEditForm({ ...editForm, subject: e.target.value })}
                    required
                  />
                </div>
                <div className="field grow">
                  <label>Level</label>
                  <input
                    value={editForm.level}
                    onChange={(e) => setEditForm({ ...editForm, level: e.target.value })}
                    required
                  />
                </div>
              </div>
              <div className="field">
                <label>Focus</label>
                <input
                  value={editForm.focus}
                  onChange={(e) => setEditForm({ ...editForm, focus: e.target.value })}
                  required
                />
              </div>
              {renderTopicFields(
                editForm.topics,
                (topics) => setEditForm({ ...editForm, topics }),
                editForm.topics_ordered,
                (e) => setEditForm({ ...editForm, topics_ordered: e.target.checked }),
              )}
              <div className="row">
                <div className="field" style={{ maxWidth: '8rem' }}>
                  <label>Default capacity</label>
                  <input
                    type="number"
                    min="1"
                    value={editForm.default_capacity}
                    onChange={(e) => setEditForm({ ...editForm, default_capacity: e.target.value })}
                  />
                </div>
                <div className="field" style={{ maxWidth: '8rem' }}>
                  <label>Ticket cost</label>
                  <input
                    type="number"
                    min="1"
                    value={editForm.ticket_cost}
                    onChange={(e) => setEditForm({ ...editForm, ticket_cost: e.target.value })}
                  />
                </div>
              </div>
              <div className="row-actions">
                <button type="submit">Save</button>
                <button type="button" className="secondary" onClick={() => setEditingId(null)}>Cancel</button>
              </div>
            </form>
          ) : (
            <>
              <div className="card-row">
                <div className="card-title">
                  {item.label}
                  {!item.is_active && <span className="badge badge--muted">Inactive</span>}
                </div>
                {canEdit && (
                  <div className="row-actions">
                    <button type="button" className="secondary" onClick={() => startEdit(item)}>Edit</button>
                    {item.is_active ? (
                      <button type="button" className="danger" onClick={() => deactivate(item.id)}>Deactivate</button>
                    ) : (
                      <button type="button" onClick={() => reactivate(item.id)}>Reactivate</button>
                    )}
                  </div>
                )}
              </div>
              <dl className="class-catalog-meta">
                <div><dt>Subject</dt><dd>{item.subject}</dd></div>
                <div><dt>Level</dt><dd>{item.level}</dd></div>
                <div><dt>Focus</dt><dd>{item.focus}</dd></div>
                <div><dt>Topics</dt><dd>{formatTopics(item)}</dd></div>
                <div><dt>Tickets</dt><dd>{item.ticket_cost ?? 1}</dd></div>
              </dl>
            </>
          )}
        </div>
      ))}
      {!classes.length && !error && <p className="card-meta">No {labels('class').toLowerCase()} yet — add your first one above.</p>}
    </div>
  )
}
