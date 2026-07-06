import { Link } from 'react-router-dom'
import { useEffect } from 'react'

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

export default function BookingSuccessModal({ session, result, onClose }) {
  useEffect(() => {
    const onKey = (event) => {
      if (event.key === 'Escape') onClose?.()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const title = session?.title || result?.session_title || 'Session'
  const startTime = session?.start_time || result?.session_start_time
  const teacherName = session?.teacher_name || result?.teacher_name
  const email = result?.confirmation_email
  const emailSent = result?.confirmation_email_sent

  let emailNote = 'Add your email in Profile to receive confirmation emails.'
  if (email && emailSent) {
    emailNote = `A confirmation email was sent to ${email}.`
  } else if (email) {
    emailNote = 'Your booking is confirmed, but the confirmation email could not be sent right now. The studio may still be setting up email — you can check My bookings for session details.'
  }

  return (
    <>
      <button type="button" className="modal-backdrop" aria-label="Close" onClick={onClose} />
      <div className="modal-dialog" role="dialog" aria-modal="true" aria-labelledby="booking-success-title">
        <h2 id="booking-success-title">You&apos;re booked!</h2>
        <p>
          <strong>{title}</strong>
          {teacherName && <> with {teacherName}</>}
        </p>
        {startTime && <p>{formatDateTime(startTime)}</p>}
        <p>{emailNote}</p>
        {session?.meeting_url && (
          <p>
            <a href={session.meeting_url} target="_blank" rel="noreferrer" className="btn secondary">
              Open meeting link
            </a>
          </p>
        )}
        <div className="form-actions">
          <Link to="/bookings" className="btn" onClick={onClose}>
            View my bookings
          </Link>
          <button type="button" className="secondary" onClick={onClose}>
            Done
          </button>
        </div>
      </div>
    </>
  )
}
