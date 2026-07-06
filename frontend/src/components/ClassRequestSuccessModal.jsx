import { useEffect } from 'react'
import { formatDateTime } from '../utils/datetime.js'

export default function ClassRequestSuccessModal({ request, result, onClose }) {
  useEffect(() => {
    const onKey = (event) => {
      if (event.key === 'Escape') onClose?.()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const label = request?.class_offering_label
    || request?.class_profile_label
    || request?.classLabel
    || result?.class_offering_label
    || result?.class_profile_label
  const teacherName = request?.teacher_name || request?.teacherLabel || result?.teacher_name
  const startTime = request?.start_time || result?.start_time
  const endTime = request?.end_time || result?.end_time
  const tickets = request?.tickets_requested ?? result?.tickets_requested
  const email = result?.notification_email
  const teacherEmailSent = result?.teacher_email_sent
  const openRequest = result?.open_to_any_teacher

  let approvalNote = email
    ? `Your request is pending. When a teacher approves it, a confirmation email will be sent to ${email}.`
    : 'Your request is pending. Add your email in Profile so we can notify you when a teacher approves it.'

  let teacherNote = openRequest
    ? 'Eligible teachers were notified by email and can accept your request in the app.'
    : 'Your teacher was notified by email and will review the request in the app.'
  if (!teacherEmailSent) {
    teacherNote = openRequest
      ? 'Eligible teachers can accept your request in the app (email notification could not be sent).'
      : 'Your teacher can review the request in the app (email notification could not be sent).'
  }

  return (
    <>
      <button type="button" className="modal-backdrop" aria-label="Close" onClick={onClose} />
      <div className="modal-dialog" role="dialog" aria-modal="true" aria-labelledby="class-request-success-title">
        <h2 id="class-request-success-title">Request sent!</h2>
        <p>
          <strong>{label}</strong>
          {teacherName && <> · {teacherName}</>}
        </p>
        {startTime && (
          <p>
            {formatDateTime(startTime)}
            {endTime && <> – {formatDateTime(endTime)}</>}
          </p>
        )}
        {tickets != null && (
          <p>{tickets} ticket{tickets === 1 ? '' : 's'} held until your teacher responds.</p>
        )}
        <p>{approvalNote}</p>
        <p>{teacherNote}</p>
        <div className="form-actions">
          <button type="button" onClick={onClose}>
            Done
          </button>
        </div>
      </div>
    </>
  )
}
