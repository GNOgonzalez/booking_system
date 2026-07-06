import { useEffect, useMemo, useState } from 'react'
import { apiFetch } from '../api.js'
import SessionCalendar from '../components/SessionCalendar.jsx'

function bookingToSession(booking) {
  return {
    id: booking.session,
    bookingId: booking.id,
    title: booking.session_title,
    start_time: booking.session_start_time,
    end_time: booking.session_end_time,
    teacher_name: booking.teacher_name,
    meeting_url: booking.meeting_url,
    meeting_provider: booking.meeting_provider,
    meeting_provider_display: booking.meeting_provider_display,
    class_offering_label: booking.class_offering_label,
    class_subject: booking.class_subject,
    class_level: booking.class_level,
    class_focus: booking.class_focus,
    class_topic: booking.class_topic,
    status: booking.status,
    tickets_spent: booking.tickets_spent,
    no_ticket_refund: booking.no_ticket_refund,
  }
}

export default function StudentBookingsPage() {
  const [bookings, setBookings] = useState([])
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [cancelling, setCancelling] = useState(false)

  const load = () => {
    apiFetch('/api/bookings/')
      .then(setBookings)
      .catch((err) => setError(err.message))
  }

  useEffect(load, [])

  const sessions = useMemo(() => bookings.map(bookingToSession), [bookings])

  const cancel = async (bookingId) => {
    const booking = bookings.find((item) => item.id === bookingId)
    const msg = booking?.no_ticket_refund
      ? 'Cancel this booking? Your tickets will not be refunded because this lesson came from an approved class request.'
      : 'Cancel this booking?'
    if (!window.confirm(msg)) return
    setError('')
    setMessage('')
    setCancelling(true)
    try {
      await apiFetch(`/api/bookings/${bookingId}/cancel/`, { method: 'POST', body: '{}' })
      setMessage('Booking cancelled.')
      load()
    } catch (err) {
      setError(err.message)
    } finally {
      setCancelling(false)
    }
  }

  return (
    <div className="page-calendar">
      <h1>My bookings</h1>
      <p className="page-intro">Your upcoming lessons in calendar view. Click a session to see details or cancel.</p>
      {message && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}
      {!error && sessions.length > 0 && (
        <SessionCalendar
          sessions={sessions}
          showTeacher
          showNewSession={false}
          showWriteReport={false}
          onCancelBooking={cancel}
          cancelling={cancelling}
        />
      )}
      {!sessions.length && !error && (
        <div className="empty" style={{ marginTop: '1rem' }}>No bookings yet.</div>
      )}
    </div>
  )
}
