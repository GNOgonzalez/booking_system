import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { apiFetch } from '../api.js'

export default function StaffTeacherPermissionsPage() {
  const { teacherId } = useParams()
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [savingKey, setSavingKey] = useState('')

  const load = () => {
    setLoading(true)
    setError('')
    apiFetch(`/api/staff/teachers/${teacherId}/permissions/`)
      .then((rows) => {
        setItems(rows)
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }

  useEffect(load, [teacherId])

  const savePermissions = async (rows) => {
    const permissions = Object.fromEntries(rows.map((r) => [r.key, r.is_enabled]))
    const updated = await apiFetch(`/api/staff/teachers/${teacherId}/permissions/`, {
      method: 'PATCH',
      body: JSON.stringify({ permissions }),
    })
    setItems(updated)
    setMessage('Permissions saved.')
  }

  const toggle = async (key) => {
    const previous = items
    const next = items.map((r) => (r.key === key ? { ...r, is_enabled: !r.is_enabled } : r))
    setItems(next)
    setError('')
    setMessage('')
    setSavingKey(key)
    try {
      await savePermissions(next)
    } catch (err) {
      setItems(previous)
      setError(err.message)
    } finally {
      setSavingKey('')
    }
  }

  return (
    <div>
      <h2>Permissions</h2>
      <p className="page-intro">
        Control what this teacher can do in the app. Changes save immediately when you toggle a checkbox.
        Staff always has full access.
      </p>
      {message && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}

      {loading && <p className="page-intro">Loading permissions…</p>}

      {!loading && !items.length && !error && (
        <p className="empty">No permissions found for this teacher.</p>
      )}

      {items.map((item) => (
        <label key={item.key} className="card permission-row">
          <input
            type="checkbox"
            checked={item.is_enabled}
            onChange={() => toggle(item.key)}
            disabled={Boolean(savingKey)}
          />
          <div>
            <div className="card-title">
              {item.label}
              {savingKey === item.key && <span className="card-meta"> · Saving…</span>}
            </div>
            <div className="card-meta">{item.description}</div>
          </div>
        </label>
      ))}

      <p className="card-meta">
        Disabled teachers can still <Link to="../sessions">view their schedule</Link> but cannot make changes.
      </p>
    </div>
  )
}
