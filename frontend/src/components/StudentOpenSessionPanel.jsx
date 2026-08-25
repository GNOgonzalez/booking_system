import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

function formatDateTime(iso) {
  return new Date(iso).toLocaleString(undefined, {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

function formatDuration(startIso, endIso) {
  const mins = Math.round((new Date(endIso) - new Date(startIso)) / 60000)
  if (mins < 60) return `${mins} minutes`
  const h = Math.floor(mins / 60)
  const m = mins % 60
  return m ? `${h} hr ${m} min` : `${h} hour${h > 1 ? 's' : ''}`
}

function ticketsForSession(session, memberships) {
  if (!session?.class_offering || !memberships?.length) return null
  for (const membership of memberships) {
    const plan = membership.plan
    if (!plan) continue
    const allowed = plan.allowed_classes || []
    if (!allowed.length || allowed.some((cls) => cls.id === session.class_offering)) {
      return membership.tickets_remaining
    }
  }
  return null
}

export default function StudentOpenSessionPanel({
  session,
  onClose,
  onBook,
  booking = false,
  ticketsRemaining = null,
  memberships = [],
}) {
  if (!session) {
    return (
      <aside className="session-panel session-panel--empty card">
        <h2>Session details</h2>
        <p className="card-meta">Click a session on the calendar to see details and book.</p>
      </aside>
    )
  }

  const spotsLeft = Math.max(session.capacity - session.confirmed_count, 0)
  const full = spotsLeft <= 0
  const alreadyBooked = Boolean(session.student_booked)
  const ticketCost = session.ticket_cost ?? 1
  const subjectTickets = ticketsForSession(session, memberships)
  const applicableTickets = subjectTickets ?? ticketsRemaining
  const insufficientTickets = applicableTickets != null && applicableTickets < ticketCost
  const [confirmOpen, setConfirmOpen] = useState(false)

  useEffect(() => {
    setConfirmOpen(false)
  }, [session?.id])

  useEffect(() => {
    if (!confirmOpen) return undefined
    const onKey = (event) => {
      if (event.key === 'Escape') setConfirmOpen(false)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [confirmOpen])

  const handleConfirm = () => {
    setConfirmOpen(false)
    onBook?.(session.id)
  }

  return (
    <aside className="session-panel card">
      <div className="session-panel-header">
        <div>
          <h2>{session.title}</h2>
          <div className="session-panel-badges">
            {session.teacher_name && <span className="badge">{session.teacher_name}</span>}
            {full ? (
              <span className="badge badge--muted">Full</span>
            ) : alreadyBooked ? (
              <span className="badge">Booked</span>
            ) : (
              <span className="badge">{spotsLeft} spot{spotsLeft === 1 ? '' : 's'} left</span>
            )}
            <span className="badge">{ticketCost} ticket{ticketCost === 1 ? '' : 's'}</span>
          </div>
        </div>
        <button type="button" className="ghost session-panel-close" onClick={onClose} aria-label="Close">
          ✕
        </button>
      </div>

      <dl className="session-detail-list">
        <div className="session-detail-item">
          <dt>Starts</dt>
          <dd>{formatDateTime(session.start_time)}</dd>
        </div>
        <div className="session-detail-item">
          <dt>Ends</dt>
          <dd>{formatDateTime(session.end_time)}</dd>
        </div>
        <div className="session-detail-item">
          <dt>Duration</dt>
          <dd>{formatDuration(session.start_time, session.end_time)}</dd>
        </div>
        {session.class_subject && (
          <>
            <div className="session-detail-item">
              <dt>Subject</dt>
              <dd>{session.class_subject}</dd>
            </div>
            <div className="session-detail-item">
              <dt>Level</dt>
              <dd>{session.class_level}</dd>
            </div>
            <div className="session-detail-item">
              <dt>Focus</dt>
              <dd>{session.class_focus}</dd>
            </div>
            <div className="session-detail-item">
              <dt>Topic</dt>
              <dd>{session.class_topic}</dd>
            </div>
          </>
        )}
        <div className="session-detail-item">
          <dt>Ticket cost</dt>
          <dd>
            {ticketCost} ticket{ticketCost === 1 ? '' : 's'}
            {applicableTickets != null && (
              <> · you have {applicableTickets} for this subject</>
            )}
          </dd>
        </div>
        <div className="session-detail-item">
          <dt>Capacity</dt>
          <dd>
            {session.confirmed_count} of {session.capacity} booked
          </dd>
        </div>
        {session.meeting_url && (
          <div className="session-detail-item">
            <dt>{session.meeting_provider_display || 'Meeting'}</dt>
            <dd>
              <a href={session.meeting_url} target="_blank" rel="noreferrer" className="btn secondary">
                Open {session.meeting_provider === 'zoom' ? 'Zoom' : session.meeting_provider === 'google_meet' ? 'Meet' : 'meeting'} link
              </a>
            </dd>
          </div>
        )}
      </dl>

      <div className="form-actions">
        {insufficientTickets ? (
          <>
            <p className="card-meta">Not enough tickets for this session.</p>
            <Link to="/membership" className="btn">Get more tickets</Link>
          </>
        ) : (
        <button
          type="button"
          onClick={() => setConfirmOpen(true)}
          disabled={booking || full || alreadyBooked}
        >
          {booking
            ? 'Booking…'
            : alreadyBooked
              ? 'Already booked'
              : full
                ? 'Session full'
                : `Book (${ticketCost} ticket${ticketCost === 1 ? '' : 's'})`}
        </button>
        )}
      </div>

      {confirmOpen && (
        <>
          <button
            type="button"
            className="modal-backdrop"
            aria-label="Cancel booking"
            onClick={() => setConfirmOpen(false)}
            disabled={booking}
          />
          <div
            className="modal-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="booking-confirm-title"
          >
            <h2 id="booking-confirm-title">Confirm booking</h2>
            <p>
              Book <strong>{session.title}</strong>
              {session.teacher_name && <> with {session.teacher_name}</>}?
            </p>
            <p>
              Starts {formatDateTime(session.start_time)}.
              {' '}This will use {ticketCost} ticket{ticketCost === 1 ? '' : 's'}.
            </p>
            <div className="form-actions">
              <button type="button" onClick={handleConfirm} disabled={booking}>
                {booking ? 'Booking…' : 'Confirm booking'}
              </button>
              <button
                type="button"
                className="secondary"
                onClick={() => setConfirmOpen(false)}
                disabled={booking}
              >
                Cancel
              </button>
            </div>
          </div>
        </>
      )}
    </aside>
  )
}
