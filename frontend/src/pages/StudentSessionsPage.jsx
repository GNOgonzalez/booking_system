import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch } from '../api.js'
import BookingSuccessModal from '../components/BookingSuccessModal.jsx'
import PageHeader from '../components/PageHeader.jsx'
import SessionCalendar from '../components/SessionCalendar.jsx'
import StudentTodayBoard from '../components/StudentTodayBoard.jsx'

const TIME_BUCKETS = {
  morning: { label: 'Morning (before noon)', match: (hour) => hour < 12 },
  afternoon: { label: 'Afternoon (noon–5 pm)', match: (hour) => hour >= 12 && hour < 17 },
  evening: { label: 'Evening (after 5 pm)', match: (hour) => hour >= 17 },
}

export default function StudentSessionsPage() {
  const [sessions, setSessions] = useState([])
  const [error, setError] = useState('')
  const [bookingSuccess, setBookingSuccess] = useState(null)
  const [booking, setBooking] = useState(false)
  const [ticketsRemaining, setTicketsRemaining] = useState(null)
  const [memberships, setMemberships] = useState([])
  const [filters, setFilters] = useState({
    time: '',
  })
  const [loading, setLoading] = useState(true)
  const [todayKey, setTodayKey] = useState(0)

  const load = () => {
    setTodayKey((k) => k + 1)
    setLoading(true)
    Promise.all([
      apiFetch('/api/sessions/open/'),
      apiFetch('/api/membership/'),
    ])
      .then(([sessionRows, membership]) => {
        setSessions(sessionRows)
        setTicketsRemaining(membership?.active ? membership.tickets_remaining : 0)
        setMemberships(
          membership?.memberships?.length
            ? membership.memberships
            : membership?.active
              ? [membership]
              : [],
        )
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }

  useEffect(load, [])

  const filteredSessions = useMemo(() => {
    return sessions.filter((session) => {
      if (filters.time) {
        const hour = new Date(session.start_time).getHours()
        if (!TIME_BUCKETS[filters.time]?.match(hour)) return false
      }
      return true
    })
  }, [sessions, filters])

  const hasActiveFilters = Boolean(filters.time)

  const book = async (sessionId, sessionRow = null) => {
    setError('')
    setBookingSuccess(null)
    setBooking(true)
    const session = sessionRow || sessions.find((row) => row.id === sessionId)
    try {
      const result = await apiFetch('/api/bookings/create/', {
        method: 'POST',
        body: JSON.stringify({ session_id: sessionId }),
      })
      setBookingSuccess({ session, result })
      load()
    } catch (err) {
      setError(err.message)
    } finally {
      setBooking(false)
    }
  }

  const setFilter = (key, value) => {
    setFilters((current) => ({ ...current, [key]: value }))
  }

  const clearFilters = () => {
    setFilters({ time: '' })
  }

  return (
    <div className="page-calendar">
      <PageHeader
        title="Book a lesson"
        intro={
          <>
            Browse upcoming lessons, or <Link to="/sessions/request">request a custom time</Link>.
            {ticketsRemaining != null && (
              <> You have <strong>{ticketsRemaining}</strong>
              {ticketsRemaining === 1 ? ' ticket' : ' tickets'} left.</>
            )}
          </>
        }
      />
      {error && <div className="error">{error}</div>}
      {loading ? (
        <div className="empty" style={{ marginTop: '1rem' }}>Loading open sessions…</div>
      ) : (
        <>
      {bookingSuccess && (
        <BookingSuccessModal
          session={bookingSuccess.session}
          result={bookingSuccess.result}
          onClose={() => setBookingSuccess(null)}
        />
      )}
      <StudentTodayBoard
        onBook={(id, row) => book(id, row)}
        booking={booking}
        refreshKey={todayKey}
      />
      {!error && sessions.length > 0 && (
        <div className="card session-filters">
          <div className="row">
            <div className="field grow">
              <label htmlFor="filter-time">Time of day</label>
              <select
                id="filter-time"
                value={filters.time}
                onChange={(e) => setFilter('time', e.target.value)}
              >
                <option value="">Any time</option>
                {Object.entries(TIME_BUCKETS).map(([value, { label }]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            </div>
            {hasActiveFilters && (
              <button type="button" className="secondary" onClick={clearFilters}>
                Clear
              </button>
            )}
          </div>
        </div>
      )}
      {!error && filteredSessions.length > 0 && (
        <SessionCalendar
          sessions={filteredSessions}
          showTeacher
          showNewSession={false}
          showWriteReport={false}
          onBookSession={book}
          booking={booking}
          ticketsRemaining={ticketsRemaining}
          memberships={memberships}
        />
      )}
      {!sessions.length && !error && (
        <div className="empty" style={{ marginTop: '1rem' }}>
          No open sessions right now.{' '}
          <Link to="/sessions/request">Request a custom time</Link> instead.
        </div>
      )}
      {sessions.length > 0 && !filteredSessions.length && !error && (
        <div className="empty" style={{ marginTop: '1rem' }}>No sessions match these filters.</div>
      )}
        </>
      )}
    </div>
  )
}
