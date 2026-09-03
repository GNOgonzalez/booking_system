import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch } from '../api.js'

const EMPTY_MODULE = { title: '', content: '' }

export default function StaffCurriculumPage() {
  const [tracks, setTracks] = useState([])
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [editingId, setEditingId] = useState(null)
  const [form, setForm] = useState({
    title: '',
    description: '',
    is_template: true,
    is_active: true,
    modules: [{ ...EMPTY_MODULE }],
  })
  const [saving, setSaving] = useState(false)

  const load = () => {
    apiFetch('/api/staff/curriculum/tracks/')
      .then(setTracks)
      .catch((err) => setError(err.message))
  }

  useEffect(load, [])

  const startNew = () => {
    setEditingId('new')
    setForm({
      title: '',
      description: '',
      is_template: true,
      is_active: true,
      modules: [{ ...EMPTY_MODULE }],
    })
  }

  const startEdit = (track) => {
    setEditingId(track.id)
    setForm({
      title: track.title,
      description: track.description || '',
      is_template: track.is_template,
      is_active: track.is_active,
      modules: track.modules?.length
        ? track.modules.map((module) => ({ title: module.title, content: module.content || '' }))
        : [{ ...EMPTY_MODULE }],
    })
  }

  const setModule = (index, key, value) => {
    setForm((current) => ({
      ...current,
      modules: current.modules.map((row, i) => (i === index ? { ...row, [key]: value } : row)),
    }))
  }

  const save = async (e) => {
    e.preventDefault()
    setSaving(true)
    setError('')
    setMessage('')
    const payload = {
      title: form.title,
      description: form.description,
      is_template: form.is_template,
      is_active: form.is_active,
      modules: form.modules
        .filter((row) => row.title.trim())
        .map((row, index) => ({ title: row.title.trim(), content: row.content, sort_order: index })),
    }
    try {
      if (editingId === 'new') {
        await apiFetch('/api/staff/curriculum/tracks/', {
          method: 'POST',
          body: JSON.stringify(payload),
        })
        setMessage('Curriculum saved.')
      } else {
        await apiFetch(`/api/staff/curriculum/tracks/${editingId}/`, {
          method: 'PATCH',
          body: JSON.stringify(payload),
        })
        setMessage('Curriculum updated.')
      }
      setEditingId(null)
      load()
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  const removeTrack = async (track) => {
    if (!window.confirm(`Delete “${track.title}”? Students on this plan will lose it.`)) return
    setError('')
    try {
      await apiFetch(`/api/staff/curriculum/tracks/${track.id}/`, { method: 'DELETE' })
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div>
      <p className="card-meta"><Link to="/staff">← Staff dashboard</Link></p>
      <h1>Curriculum templates</h1>
      <p className="page-intro">
        Premade paths students can pick, in order. Teachers can skip a module or build a custom path
        for assigned students.
      </p>
      {message && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}

      {!editingId && (
        <p>
          <button type="button" onClick={startNew}>New curriculum</button>
        </p>
      )}

      {editingId && (
        <form onSubmit={save} className="card">
          <h2>{editingId === 'new' ? 'New curriculum' : 'Edit curriculum'}</h2>
          <div className="field">
            <label>Title</label>
            <input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required />
          </div>
          <div className="field">
            <label>Description</label>
            <textarea
              rows={2}
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
          </div>
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={form.is_template}
              onChange={(e) => setForm({ ...form, is_template: e.target.checked })}
            />
            Students can pick this (premade)
          </label>
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={form.is_active}
              onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
            />
            Active
          </label>
          <h3>Modules (in order)</h3>
          {form.modules.map((module, index) => (
            <div key={index} className="card">
              <div className="field">
                <label>Module {index + 1} title</label>
                <input
                  value={module.title}
                  onChange={(e) => setModule(index, 'title', e.target.value)}
                />
              </div>
              <div className="field">
                <label>Notes</label>
                <textarea
                  rows={2}
                  value={module.content}
                  onChange={(e) => setModule(index, 'content', e.target.value)}
                />
              </div>
            </div>
          ))}
          <div className="form-actions">
            <button
              type="button"
              className="secondary"
              onClick={() => setForm({ ...form, modules: [...form.modules, { ...EMPTY_MODULE }] })}
            >
              Add module
            </button>
            <button type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save'}</button>
            <button type="button" className="secondary" onClick={() => setEditingId(null)}>Cancel</button>
          </div>
        </form>
      )}

      {tracks.map((track) => (
        <div key={track.id} className="card">
          <div className="card-row">
            <div>
              <div className="card-title">{track.title}</div>
              <div className="card-meta">
                {track.module_count} module{track.module_count === 1 ? '' : 's'}
                {track.is_template ? ' · Premade' : ' · Custom'}
                {track.is_active ? '' : ' · Hidden'}
              </div>
              {track.description && <p className="card-meta">{track.description}</p>}
            </div>
            <div className="row-actions">
              <button type="button" className="secondary" onClick={() => startEdit(track)}>Edit</button>
              <button type="button" className="danger" onClick={() => removeTrack(track)}>Delete</button>
            </div>
          </div>
        </div>
      ))}
      {!tracks.length && !error && <p className="empty">No curricula yet.</p>}
    </div>
  )
}
