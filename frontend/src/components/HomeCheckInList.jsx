import CheckInButton from './CheckInButton.jsx'

function formatLessonTime(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString(undefined, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

export default function HomeCheckInList({ items, onCheckedIn }) {
  if (!items?.length) return null

  return (
    <div className="card">
      <div className="card-title">Check in</div>
      <p className="card-meta">
        Confirm you are coming. Check-in opens before the lesson and stays open until it ends.
      </p>
      <ul className="teacher-queue-list">
        {items.map((item) => (
          <li key={item.session_id} className="card-row">
            <div>
              <strong>{item.title}</strong>
              <div className="card-meta">
                {formatLessonTime(item.start_time)}
                {item.teacher_name ? ` · with ${item.teacher_name}` : ''}
                {item.students?.length ? ` · ${item.students.join(', ')}` : ''}
              </div>
              <CheckInButton
                sessionId={item.session_id}
                checkIn={item.check_in}
                onCheckedIn={(updated) => onCheckedIn?.(item.session_id, updated.check_in)}
              />
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}
