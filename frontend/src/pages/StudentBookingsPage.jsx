import { useEffect, useState } from 'react'
import { apiFetch } from '../api.js'

export default function StudentBookingsPage() {
  const [bookings, setBookings] = useState([])
  const [error, setError] = useState('')

  const load = () => {
    apiFetch('/api/bookings/')
      .then(setBookings)
      .catch((err) => setError(err.message))
  }

  useEffect(load, [])

  const cancel = async (bookingId) => {
    setError('')
    try {
      await apiFetch(`/api/bookings/${bookingId}/cancel/`, { method: 'POST', body: '{}' })
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div>
      <h1>My bookings</h1>
      {error && <p className="error">{error}</p>}
      {bookings.map((booking) => (
        <div key={booking.id} className="card">
          <strong>{booking.session_title}</strong>
          <p>{booking.session_start_time}</p>
          <button type="button" onClick={() => cancel(booking.id)}>Cancel</button>
        </div>
      ))}
      {!bookings.length && !error && <p>No bookings yet.</p>}
    </div>
  )
}
