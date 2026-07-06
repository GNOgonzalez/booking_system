import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { apiFetch } from '../api.js'

export default function StaffTeacherPermissionsPage() {
  const { teacherId } = useParams()
  const [items, setItems] = useState([])
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [saving, setSaving] = useState(false)

  const load = () => {
    apiFetch(`/api/staff/teachers/${teacherId}/permissions/`)
      .then(setItems)
      .catch((err) => setError(err.message))
  }

  useEffect(load, [teacherId])

  const toggle = (key) => {
    setItems((rows) => rows.map((r) => (r.key === key ? { ...r, is_enabled: !r.is_enabled } : r)))
  }

  const save = async () => {
    setSaving(true)
    setError('')
    setMessage('')
    try {
      const permissions = Object.fromEntries(items.map((r) => [r.key, r.is_enabled]))
      const updated = await apiFetch(`/api/staff/teachers/${teacherId}/permissions/`, {
        method: 'PATCH',
        body: JSON.stringify({ permissions }),
      })
      setItems(updated)
      setMessage('Permissions saved.')
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <h2>Permissions</h2>
      <p className="page-intro">
        Control what this teacher can do in the app. Staff always has full access.
      </p>
      {message && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}

      {items.map((item) => (
        <label key={item.key} className="card permission-row">
          <input
            type="checkbox"
            checked={item.is_enabled}
            onChange={() => toggle(item.key)}
          />
          <div>
            <div className="card-title">{item.label}</div>
            <div className="card-meta">{item.description}</div>
          </div>
        </label>
      ))}

      <div className="form-actions">
        <button type="button" onClick={save} disabled={saving || !items.length}>
          {saving ? 'Saving…' : 'Save permissions'}
        </button>
      </div>
      <p className="card-meta">
        Disabled teachers can still <Link to="../sessions">view their schedule</Link> but cannot make changes.
      </p>
    </div>
  )
}
