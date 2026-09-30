import { useState } from 'react'
import { apiFetch } from '../api.js'

function formatWhen(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString(undefined, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

export default function CheckInButton({ sessionId, checkIn, onCheckedIn }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  if (!checkIn || !checkIn.eligible) return null

  const checkInNow = async () => {
    setBusy(true)
    setError('')
    try {
      const updated = await apiFetch(`/api/sessions/${sessionId}/check-in/`, {
        method: 'POST',
        body: '{}',
      })
      onCheckedIn?.(updated)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  if (checkIn.checked_in) {
    return (
      <p className="card-meta">
        Checked in{checkIn.checked_in_at ? ` at ${formatWhen(checkIn.checked_in_at)}` : ''}.
      </p>
    )
  }

  if (!checkIn.window_open) {
    const now = Date.now()
    const opens = checkIn.opens_at ? new Date(checkIn.opens_at).getTime() : 0
    if (opens > now) {
      return <p className="card-meta">Check-in opens {formatWhen(checkIn.opens_at)}.</p>
    }
    return null
  }

  return (
    <div className="row-actions">
      {error && <div className="error">{error}</div>}
      <button type="button" onClick={checkInNow} disabled={busy}>
        {busy ? 'Checking in…' : 'Check in'}
      </button>
    </div>
  )
}
