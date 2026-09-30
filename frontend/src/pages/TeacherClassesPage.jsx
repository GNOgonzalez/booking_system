import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch } from '../api.js'
import { useTeacherScope } from '../hooks/useTeacherScope.js'
import { useTeacherPermissions } from '../hooks/useTeacherPermissions.js'
import { useGlossary } from '../hooks/useGlossary.jsx'

function lessonList(item) {
  const modules = item.modules?.length ? item.modules : (item.topics || [])
  const titles = modules.map((row) => row.title).filter(Boolean)
  return titles.length ? titles.join(' · ') : '—'
}

export default function TeacherClassesPage() {
  const { isStaff, paths } = useTeacherScope()
  const { can } = useTeacherPermissions()
  const { label, labels } = useGlossary()
  const canEdit = isStaff || can('manage_classes')
  const [classes, setClasses] = useState([])
  const [tracks, setTracks] = useState([])
  const [form, setForm] = useState({ track: '', default_capacity: 4, ticket_cost: 1 })
  const [editingId, setEditingId] = useState(null)
  const [editForm, setEditForm] = useState(null)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const load = () => {
    Promise.all([
      apiFetch(paths.classes),
      apiFetch('/api/curriculum/tracks/'),
    ])
      .then(([classRows, trackRows]) => {
        setClasses(classRows)
        setTracks(trackRows)
      })
      .catch((err) => setError(err.message))
  }

  useEffect(load, [paths.classes])

  const add = async (e) => {
    e.preventDefault()
    setError('')
    setMessage('')
    if (!form.track) {
      setError('Choose a curriculum.')
      return
    }
    try {
      await apiFetch(paths.classes, {
        method: 'POST',
        body: JSON.stringify({
          track: Number(form.track),
          default_capacity: Number(form.default_capacity),
          ticket_cost: Number(form.ticket_cost) || 1,
          is_active: true,
        }),
      })
      setForm({ track: '', default_capacity: 4, ticket_cost: 1 })
      setMessage(`${label('class')} added.`)
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  const startEdit = (item) => {
    setEditingId(item.id)
    setEditForm({
      track: item.track || '',
      default_capacity: item.default_capacity,
      ticket_cost: item.ticket_cost ?? 1,
    })
  }

  const saveEdit = async (e) => {
    e.preventDefault()
    setError('')
    setMessage('')
    try {
      await apiFetch(paths.classDetail(editingId), {
        method: 'PATCH',
        body: JSON.stringify({
          track: editForm.track ? Number(editForm.track) : undefined,
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

  const curriculumPage = isStaff ? '/staff/curriculum' : '/teacher/curriculum'

  return (
    <div>
      {!isStaff && <h1>{labels('class')}</h1>}
      <p className="page-intro">
        A class is you teaching a curriculum: seats and ticket cost. Open sessions use that path&apos;s modules.
        Personalized curricula only show to students enrolled on them.
        {' '}<Link to={curriculumPage}>Edit curricula</Link>.
      </p>
      {message && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}

      {canEdit ? (
        <form onSubmit={add} className="card">
          <div className="field">
            <label htmlFor="class-track">Curriculum</label>
            <select
              id="class-track"
              value={form.track}
              onChange={(e) => setForm({ ...form, track: e.target.value })}
            >
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
              <input
                type="number"
                min="1"
                value={form.default_capacity}
                onChange={(e) => setForm({ ...form, default_capacity: e.target.value })}
              />
            </div>
            <div className="field" style={{ maxWidth: '8rem' }}>
              <label>Ticket cost</label>
              <input
                type="number"
                min="1"
                value={form.ticket_cost}
                onChange={(e) => setForm({ ...form, ticket_cost: e.target.value })}
              />
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
              <div className="field">
                <label>Curriculum</label>
                <select
                  value={editForm.track}
                  onChange={(e) => setEditForm({ ...editForm, track: e.target.value })}
                >
                  {tracks.map((track) => (
                    <option key={track.id} value={track.id}>
                      {track.title}
                      {track.is_template ? '' : ' (personalized)'}
                    </option>
                  ))}
                </select>
              </div>
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
                  {item.is_personalized && <span className="badge">Personalized</span>}
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
                <div><dt>Lessons</dt><dd>{lessonList(item)}</dd></div>
                <div><dt>Tickets</dt><dd>{item.ticket_cost ?? 1}</dd></div>
                <div><dt>Seats</dt><dd>{item.default_capacity}</dd></div>
              </dl>
            </>
          )}
        </div>
      ))}
      {!classes.length && !error && <p className="card-meta">No {labels('class').toLowerCase()} yet — attach a curriculum above.</p>}
    </div>
  )
}
