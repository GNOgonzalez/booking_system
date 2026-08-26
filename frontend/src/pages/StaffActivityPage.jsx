import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch } from '../api.js'
import { formatDateTime } from '../utils/datetime.js'

export default function StaffActivityPage() {
  const [actions, setActions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    apiFetch('/api/staff/activity/?limit=100')
      .then((data) => setActions(data.actions || []))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div>
      <p className="card-meta"><Link to="/staff">← Staff dashboard</Link></p>
      <h1>Staff activity</h1>
      <p className="page-intro">
        Every override staff makes — memberships, tickets, bookings, passwords, and new accounts.
        Read-only, newest first.
      </p>
      {error && <div className="error">{error}</div>}
      {loading && <p className="card-meta">Loading activity…</p>}

      {!loading && !actions.length && !error && (
        <p className="card-meta">No staff overrides recorded yet.</p>
      )}

      {actions.map((entry) => (
        <div key={entry.id} className="card">
          <div className="card-row">
            <div>
              <div className="card-title">{entry.summary}</div>
              <div className="card-meta">
                {entry.actor} · {formatDateTime(entry.created_at)}
              </div>
              {entry.note && <div className="card-meta">Reason: {entry.note}</div>}
            </div>
            <span className="badge badge--muted">{entry.action_label}</span>
          </div>
        </div>
      ))}
    </div>
  )
}
