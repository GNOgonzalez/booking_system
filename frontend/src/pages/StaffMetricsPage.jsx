import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch } from '../api.js'

const EMPTY_METRIC = { label: '', min_score: 0, max_score: 5 }

export default function StaffMetricsPage() {
  const [subjects, setSubjects] = useState([{ value: '', label: 'All subjects (default)' }])
  const [subject, setSubject] = useState('')
  const [dimensions, setDimensions] = useState([])
  const [meta, setMeta] = useState({ max: 10, active: 0, remaining: 10 })
  const [newMetric, setNewMetric] = useState(EMPTY_METRIC)
  const [dragIndex, setDragIndex] = useState(null)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const params = () => {
    const p = new URLSearchParams()
    if (subject) p.set('subject', subject)
    return p.toString()
  }

  const load = () => {
    const qs = params()
    const listUrl = qs
      ? `/api/progress/staff/score-dimensions/?${qs}&include_inactive=1`
      : '/api/progress/staff/score-dimensions/?include_inactive=1'
    const metaUrl = qs
      ? `/api/progress/staff/score-dimensions/meta/?${qs}`
      : '/api/progress/staff/score-dimensions/meta/'

    Promise.all([
      apiFetch(listUrl),
      apiFetch(metaUrl),
    ])
      .then(([rows, metaData]) => {
        setDimensions(rows.filter((d) => d.is_active))
        setMeta(metaData)
      })
      .catch((err) => setError(err.message))
  }

  useEffect(() => {
    apiFetch('/api/progress/staff/score-dimensions/subjects/')
      .then(setSubjects)
      .catch(() => {})
  }, [])

  useEffect(load, [subject])

  const updateDim = (id, patch) => {
    setDimensions((rows) => rows.map((r) => (r.id === id ? { ...r, ...patch } : r)))
  }

  const save = async (dim) => {
    setError('')
    setMessage('')
    try {
      await apiFetch(`/api/progress/staff/score-dimensions/${dim.id}/`, {
        method: 'PATCH',
        body: JSON.stringify({
          label: dim.label,
          min_score: Number(dim.min_score),
          max_score: Number(dim.max_score),
        }),
      })
      setMessage('Metric saved.')
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  const persistOrder = async (ordered) => {
    setError('')
    try {
      await apiFetch('/api/progress/staff/score-dimensions/reorder/', {
        method: 'POST',
        body: JSON.stringify({
          subject,
          order: ordered.map((d) => d.id),
        }),
      })
      setMessage('Order updated.')
    } catch (err) {
      setError(err.message)
      load()
    }
  }

  const onDrop = (targetIndex) => {
    if (dragIndex === null || dragIndex === targetIndex) {
      setDragIndex(null)
      return
    }
    const next = [...dimensions]
    const [moved] = next.splice(dragIndex, 1)
    next.splice(targetIndex, 0, moved)
    setDimensions(next)
    setDragIndex(null)
    persistOrder(next)
  }

  const addMetric = async (e) => {
    e.preventDefault()
    setError('')
    setMessage('')
    if (!newMetric.label.trim()) {
      setError('Enter a metric name.')
      return
    }
    try {
      await apiFetch('/api/progress/staff/score-dimensions/', {
        method: 'POST',
        body: JSON.stringify({
          label: newMetric.label.trim(),
          subject,
          min_score: Number(newMetric.min_score),
          max_score: Number(newMetric.max_score),
        }),
      })
      setNewMetric(EMPTY_METRIC)
      setMessage('Metric added.')
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  const removeMetric = async (dim) => {
    if (!window.confirm(`Delete "${dim.label}"? Historical reports keep their stored scores.`)) return
    setError('')
    try {
      await apiFetch(`/api/progress/staff/score-dimensions/${dim.id}/`, { method: 'DELETE' })
      setMessage('Metric removed.')
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  const subjectLabel = subjects.find((s) => s.value === subject)?.label || 'All subjects (default)'

  return (
    <div>
      <h1>Studio metrics</h1>
      <p className="page-intro">
        Define up to {meta.max} metrics per subject. Drag to reorder. Set min/max points per metric
        (e.g. 1–10 for rubrics, 0–5 for stars).
      </p>
      <p className="card-meta"><Link to="/staff">← Back to staff dashboard</Link></p>
      {message && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}

      <div className="card">
        <div className="field">
          <label>Subject scope</label>
          <select value={subject} onChange={(e) => setSubject(e.target.value)}>
            {subjects.map((s) => (
              <option key={s.value || 'default'} value={s.value}>{s.label}</option>
            ))}
          </select>
        </div>
        <p className="card-meta">
          {subjectLabel}: {meta.active} of {meta.max} metrics used
          {meta.remaining === 0 ? ' · remove one to add another' : ` · ${meta.remaining} slots left`}
        </p>
      </div>

      {meta.remaining > 0 && (
        <form onSubmit={addMetric} className="card">
          <h2>Add metric</h2>
          <div className="row">
            <div className="field grow">
              <label>Display name</label>
              <input
                value={newMetric.label}
                onChange={(e) => setNewMetric({ ...newMetric, label: e.target.value })}
                placeholder={subject ? 'e.g. Kanji recognition' : 'e.g. Grammar'}
                required
              />
            </div>
            <div className="field" style={{ maxWidth: '5.5rem' }}>
              <label>Min</label>
              <input
                type="number"
                value={newMetric.min_score}
                onChange={(e) => setNewMetric({ ...newMetric, min_score: e.target.value })}
              />
            </div>
            <div className="field" style={{ maxWidth: '5.5rem' }}>
              <label>Max</label>
              <input
                type="number"
                value={newMetric.max_score}
                onChange={(e) => setNewMetric({ ...newMetric, max_score: e.target.value })}
              />
            </div>
          </div>
          <button type="submit">Add metric</button>
        </form>
      )}

      {dimensions.length > 0 && (
        <p className="card-meta">Drag the handle on each row to change display order.</p>
      )}

      {dimensions.map((dim, index) => (
        <div
          key={dim.id}
          className={`card metric-row${dragIndex === index ? ' metric-row--dragging' : ''}`}
          onDragOver={(e) => e.preventDefault()}
          onDrop={() => onDrop(index)}
        >
          <button
            type="button"
            className="metric-drag-handle"
            draggable
            aria-label={`Reorder ${dim.label}`}
            onDragStart={() => setDragIndex(index)}
            onDragEnd={() => setDragIndex(null)}
          >
            ⠿
          </button>
          <form
            className="metric-row-body"
            onSubmit={(e) => {
              e.preventDefault()
              save(dim)
            }}
          >
            <div className="card-meta">Key: {dim.key}</div>
            <div className="row">
              <div className="field grow">
                <label>Display name</label>
                <input
                  value={dim.label}
                  onChange={(e) => updateDim(dim.id, { label: e.target.value })}
                  required
                />
              </div>
              <div className="field" style={{ maxWidth: '5.5rem' }}>
                <label>Min</label>
                <input
                  type="number"
                  value={dim.min_score}
                  onChange={(e) => updateDim(dim.id, { min_score: e.target.value })}
                />
              </div>
              <div className="field" style={{ maxWidth: '5.5rem' }}>
                <label>Max</label>
                <input
                  type="number"
                  value={dim.max_score}
                  onChange={(e) => updateDim(dim.id, { max_score: e.target.value })}
                />
              </div>
            </div>
            <div className="row-actions">
              <button type="submit">Save</button>
              <button type="button" className="danger" onClick={() => removeMetric(dim)}>Delete</button>
            </div>
          </form>
        </div>
      ))}
      {!dimensions.length && !error && (
        <p className="card-meta">No metrics for this scope yet — add one above.</p>
      )}
    </div>
  )
}
