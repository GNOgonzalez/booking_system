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

export default function StudentBookingPanel({
  session,
  onClose,
  onCancel,
  cancelling = false,
}) {
  if (!session) {
    return (
      <aside className="session-panel session-panel--empty card">
        <h2>Booking details</h2>
        <p className="card-meta">Click a booked session on the calendar to see details.</p>
      </aside>
    )
  }

  const canCancel = session.status !== 'cancelled'

  return (
    <aside className="session-panel card">
      <div className="session-panel-header">
        <div>
          <h2>{session.title}</h2>
          <div className="session-panel-badges">
            {session.teacher_name && <span className="badge">{session.teacher_name}</span>}
            <span className="badge badge--muted">Booked</span>
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
        {session.end_time && (
          <>
            <div className="session-detail-item">
              <dt>Ends</dt>
              <dd>{formatDateTime(session.end_time)}</dd>
            </div>
            <div className="session-detail-item">
              <dt>Duration</dt>
              <dd>{formatDuration(session.start_time, session.end_time)}</dd>
            </div>
          </>
        )}
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
        {session.tickets_spent > 0 && (
          <div className="session-detail-item">
            <dt>Tickets used</dt>
            <dd>{session.tickets_spent}</dd>
          </div>
        )}
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

      {canCancel && (
        <div className="form-actions">
          {session.no_ticket_refund && (
            <p className="card-meta">Tickets are not refunded when cancelling a request-approved lesson.</p>
          )}
          <button
            type="button"
            className="danger"
            onClick={() => onCancel?.(session.bookingId)}
            disabled={cancelling}
          >
            {cancelling ? 'Cancelling…' : 'Cancel booking'}
          </button>
        </div>
      )}
    </aside>
  )
}
