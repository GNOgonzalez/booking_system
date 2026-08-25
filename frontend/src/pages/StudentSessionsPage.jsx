import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch } from '../api.js'
import BookingSuccessModal from '../components/BookingSuccessModal.jsx'
import SessionCalendar from '../components/SessionCalendar.jsx'

const TIME_BUCKETS = {
  morning: { label: 'Morning (before noon)', match: (hour) => hour < 12 },
  afternoon: { label: 'Afternoon (noon–5 pm)', match: (hour) => hour >= 12 && hour < 17 },
  evening: { label: 'Evening (after 5 pm)', match: (hour) => hour >= 17 },
}

function uniqueOptions(sessions, idKey, labelKey) {
  const map = new Map()
  for (const session of sessions) {
    const id = session[idKey]
    const label = session[labelKey]
    if (id != null && label) map.set(id, label)
  }
  return [...map.entries()]
    .map(([id, label]) => ({ id: String(id), label }))
    .sort((a, b) => a.label.localeCompare(b.label))
}

export default function StudentSessionsPage() {
  const [sessions, setSessions] = useState([])
  const [error, setError] = useState('')
  const [bookingSuccess, setBookingSuccess] = useState(null)
  const [booking, setBooking] = useState(false)
  const [ticketsRemaining, setTicketsRemaining] = useState(null)
  const [memberships, setMemberships] = useState([])
  const [filters, setFilters] = useState({
    classOffering: '',
    teacher: '',
    time: '',
  })
  const [loading, setLoading] = useState(true)

  const load = () => {
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

  const classOptions = useMemo(
    () => uniqueOptions(sessions, 'class_offering', 'class_offering_label'),
    [sessions],
  )
  const teacherOptions = useMemo(
    () => uniqueOptions(sessions, 'teacher', 'teacher_name'),
    [sessions],
  )

  const filteredSessions = useMemo(() => {
    return sessions.filter((session) => {
      if (filters.classOffering && String(session.class_offering) !== filters.classOffering) {
        return false
      }
      if (filters.teacher && String(session.teacher) !== filters.teacher) {
        return false
      }
      if (filters.time) {
        const hour = new Date(session.start_time).getHours()
        if (!TIME_BUCKETS[filters.time]?.match(hour)) return false
      }
      return true
    })
  }, [sessions, filters])

  const hasActiveFilters = Boolean(filters.classOffering || filters.teacher || filters.time)

  const book = async (sessionId) => {
    setError('')
    setBookingSuccess(null)
    setBooking(true)
    const session = sessions.find((row) => row.id === sessionId)
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
    setFilters({ classOffering: '', teacher: '', time: '' })
  }

  return (
    <div className="page-calendar">
      <h1>Book a lesson</h1>
      <p className="page-intro">
        Browse upcoming lessons on the calendar. Filter by class, time, or teacher, then click a session to book.
        Or <Link to="/sessions/request">request a custom time</Link> inside a teacher&apos;s availability.
        {ticketsRemaining != null && (
          <> You have <strong>{ticketsRemaining}</strong> booking ticket{ticketsRemaining === 1 ? '' : 's'} across your memberships.</>
        )}
      </p>
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
      {!error && sessions.length > 0 && (
        <div className="card session-filters">
          <div className="row">
            <div className="field grow">
              <label htmlFor="filter-class">Class</label>
              <select
                id="filter-class"
                value={filters.classOffering}
                onChange={(e) => setFilter('classOffering', e.target.value)}
              >
                <option value="">All classes</option>
                {classOptions.map((option) => (
                  <option key={option.id} value={option.id}>{option.label}</option>
                ))}
              </select>
            </div>
            <div className="field grow">
              <label htmlFor="filter-time">Time</label>
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
            <div className="field grow">
              <label htmlFor="filter-teacher">Teacher</label>
              <select
                id="filter-teacher"
                value={filters.teacher}
                onChange={(e) => setFilter('teacher', e.target.value)}
              >
                <option value="">All teachers</option>
                {teacherOptions.map((option) => (
                  <option key={option.id} value={option.id}>{option.label}</option>
                ))}
              </select>
            </div>
            {hasActiveFilters && (
              <button type="button" className="secondary" onClick={clearFilters}>
                Clear filters
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
