import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
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

function isUpcoming(booking) {
  if (!booking.session_start_time) return false
  return new Date(booking.session_start_time) >= new Date()
}

export default function StudentBookingsPage() {
  const [bookings, setBookings] = useState([])
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(true)
  const [cancelling, setCancelling] = useState(false)
  const [tab, setTab] = useState('upcoming')

  const load = () => {
    setLoading(true)
    apiFetch('/api/bookings/')
      .then(setBookings)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }

  useEffect(load, [])

  const upcomingBookings = useMemo(
    () => bookings.filter((b) => b.status === 'confirmed' && isUpcoming(b)),
    [bookings],
  )
  const pastBookings = useMemo(
    () => bookings.filter((b) => !isUpcoming(b) || b.status !== 'confirmed'),
    [bookings],
  )

  const visibleBookings = tab === 'upcoming' ? upcomingBookings : pastBookings
  const sessions = useMemo(() => visibleBookings.map(bookingToSession), [visibleBookings])

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
      <p className="page-intro">
        Your lessons in calendar view. Click a session to see details or cancel an upcoming booking.
      </p>
      {message && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}

      <div className="subject-tabs" role="tablist" aria-label="Booking time">
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'upcoming'}
          className={tab === 'upcoming' ? 'subject-tab active' : 'subject-tab'}
          onClick={() => setTab('upcoming')}
        >
          Upcoming
          <span className="subject-tab-count">{upcomingBookings.length}</span>
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'past'}
          className={tab === 'past' ? 'subject-tab active' : 'subject-tab'}
          onClick={() => setTab('past')}
        >
          Past
          <span className="subject-tab-count">{pastBookings.length}</span>
        </button>
      </div>

      {loading ? (
        <div className="empty" style={{ marginTop: '1rem' }}>Loading bookings…</div>
      ) : sessions.length > 0 ? (
        <SessionCalendar
          sessions={sessions}
          showTeacher
          showNewSession={false}
          showWriteReport={false}
          onCancelBooking={tab === 'upcoming' ? cancel : undefined}
          cancelling={cancelling}
        />
      ) : (
        <div className="empty" style={{ marginTop: '1rem' }}>
          {tab === 'upcoming' ? (
            <>
              No upcoming bookings.{' '}
              <Link to="/sessions">Browse open sessions</Link> to book a lesson.
            </>
          ) : (
            'No past bookings yet.'
          )}
        </div>
      )}
    </div>
  )
}
