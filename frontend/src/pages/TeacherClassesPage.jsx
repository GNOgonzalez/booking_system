import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch } from '../api.js'
import { useTeacherScope } from '../hooks/useTeacherScope.js'
import { useTeacherPermissions } from '../hooks/useTeacherPermissions.js'
import { useGlossary } from '../hooks/useGlossary.jsx'
import ClassCatalogPicker, {
  catalogSelectionToTopics,
  EMPTY_CATALOG_SELECTION,
} from '../components/ClassCatalogPicker.jsx'

function formatTopics(item) {
  const titles = (item.topics || []).map((topic) => topic.title).filter(Boolean)
  if (!titles.length) return '—'
  const suffix = item.topics_ordered ? ' (in order)' : ''
  return `${titles.join(' · ')}${suffix}`
}

function catalogFromClass(item) {
  return {
    subject: item.subject || '',
    level: item.level || '',
    focus: item.focus || '',
    topicTitles: (item.topics || []).map((topic) => topic.title),
    topics_ordered: Boolean(item.topics_ordered),
  }
}

export default function TeacherClassesPage() {
  const { isStaff, paths } = useTeacherScope()
  const { can } = useTeacherPermissions()
  const { label, labels } = useGlossary()
  const canEdit = isStaff || can('manage_classes')
  const [classes, setClasses] = useState([])
  const [form, setForm] = useState({
    catalog: { ...EMPTY_CATALOG_SELECTION },
    default_capacity: 4,
    ticket_cost: 1,
  })
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

  const add = async (e) => {
    e.preventDefault()
    setError('')
    setMessage('')
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
      await apiFetch(paths.classes, {
        method: 'POST',
        body: JSON.stringify({
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
      setForm({
        catalog: { ...EMPTY_CATALOG_SELECTION },
        default_capacity: 4,
        ticket_cost: 1,
      })
      setMessage(`${label('class')} added.`)
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  const startEdit = (item) => {
    setEditingId(item.id)
    setEditForm({
      catalog: catalogFromClass(item),
      default_capacity: item.default_capacity,
      ticket_cost: item.ticket_cost ?? 1,
    })
  }

  const saveEdit = async (e) => {
    e.preventDefault()
    setError('')
    setMessage('')
    const { catalog } = editForm
    const topics = catalogSelectionToTopics(catalog.topicTitles)
    if (!topics.length) {
      setError('Select at least one topic.')
      return
    }
    try {
      await apiFetch(paths.classDetail(editingId), {
        method: 'PATCH',
        body: JSON.stringify({
          subject: catalog.subject,
          level: catalog.level,
          focus: catalog.focus,
          topics_ordered: catalog.topics_ordered,
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

  return (
    <div>
      {!isStaff && <h1>{labels('class')}</h1>}
      <p className="page-intro">
        Teachable catalog — pick subject, level, focus, and topics from the studio roadmap.
        {isStaff && (
          <> <Link to="/staff/class-catalog">Manage roadmap</Link>.</>
        )}
      </p>
      {message && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}

      {canEdit ? (
        <form onSubmit={add} className="card">
          <ClassCatalogPicker
            value={form.catalog}
            onChange={(catalog) => setForm({ ...form, catalog })}
            showStaffCatalogLink={isStaff}
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
      ) : (
        <div className="card card-meta">You do not have permission to create {labels('class').toLowerCase()}. Contact staff.</div>
      )}

      {classes.map((item) => (
        <div key={item.id} className={`card class-catalog-row${item.is_active ? '' : ' card--inactive'}`}>
          {editingId === item.id ? (
            <form onSubmit={saveEdit}>
              <ClassCatalogPicker
                value={editForm.catalog}
                onChange={(catalog) => setEditForm({ ...editForm, catalog })}
                showStaffCatalogLink={isStaff}
              />
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
