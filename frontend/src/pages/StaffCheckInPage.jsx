import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch } from '../api.js'

export default function StaffCheckInPage() {
  const [form, setForm] = useState({
    check_in_opens_hours_before: 24,
    reminder_hours_before: 3,
  })
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    apiFetch('/api/staff/check-in/')
      .then((data) => setForm({
        check_in_opens_hours_before: data.check_in_opens_hours_before,
        reminder_hours_before: data.reminder_hours_before,
      }))
      .catch((err) => setError(err.message))
  }, [])

  const save = async (e) => {
    e.preventDefault()
    setSaving(true)
    setError('')
    setMessage('')
    try {
      const updated = await apiFetch('/api/staff/check-in/', {
        method: 'PATCH',
        body: JSON.stringify({
          check_in_opens_hours_before: Number(form.check_in_opens_hours_before),
          reminder_hours_before: Number(form.reminder_hours_before),
        }),
      })
      setForm({
        check_in_opens_hours_before: updated.check_in_opens_hours_before,
        reminder_hours_before: updated.reminder_hours_before,
      })
      setMessage('Check-in settings saved.')
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <p className="card-meta"><Link to="/staff">← Staff dashboard</Link></p>
      <div className="page-header">
        <div>
          <h1>Lesson check-in</h1>
          <p className="page-intro">
            Teachers and booked students can check in on the app. Choose when that button appears
            and when a reminder email goes out if they have not checked in.
          </p>
        </div>
      </div>
      {message && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}
      <form onSubmit={save} className="card">
        <div className="field">
          <label htmlFor="checkin-opens">Check-in opens (hours before start)</label>
          <input
            id="checkin-opens"
            type="number"
            min="1"
            max="168"
            value={form.check_in_opens_hours_before}
            onChange={(e) => setForm({ ...form, check_in_opens_hours_before: e.target.value })}
            required
          />
          <p className="card-meta">Default 24. The button stays available until the lesson ends.</p>
        </div>
        <div className="field">
          <label htmlFor="checkin-reminder">Reminder email (hours before start)</label>
          <input
            id="checkin-reminder"
            type="number"
            min="0"
            max="168"
            value={form.reminder_hours_before}
            onChange={(e) => setForm({ ...form, reminder_hours_before: e.target.value })}
            required
          />
          <p className="card-meta">
            Must be the same or fewer hours than check-in opens, so people have time to tap Check in
            first. 0 means remind at start time.
          </p>
        </div>
        <button type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save'}</button>
      </form>
    </div>
  )
}
