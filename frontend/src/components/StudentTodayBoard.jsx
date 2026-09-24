import { useEffect, useState } from 'react'
import { apiFetch } from '../api.js'
import { formatTime } from '../utils/datetime.js'

function todayIso() {
  const d = new Date()
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

/**
 * "Today at the branch": classes a student can still join, grouped by branch.
 * Walk-in classes stay bookable after they begin (until they end).
 */
export default function StudentTodayBoard({ onBook, booking, refreshKey }) {
  const [date, setDate] = useState(todayIso())
  const [payload, setPayload] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    apiFetch(`/api/sessions/today/?date=${date}`)
      .then((data) => { if (!cancelled) setPayload(data) })
      .catch((err) => { if (!cancelled) setError(err.message) })
    return () => { cancelled = true }
  }, [date, refreshKey])

  const branches = (payload?.branches || []).filter((b) => b.classes.length > 0)
  const anyBranches = (payload?.branches || []).length > 0
  if (!anyBranches && !error) return null

  const now = Date.now()

  return (
    <section className="card student-today-board">
      <div className="row" style={{ justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 className="card-title" style={{ margin: 0 }}>At the branch</h2>
          <p className="card-meta" style={{ margin: 0 }}>
            In-person classes you can join. <span className="badge badge--success">Walk-ins</span> classes take
            students even after they begin — just turn up.
          </p>
        </div>
        <div className="field" style={{ margin: 0 }}>
          <label htmlFor="today-date" className="sr-only">Day</label>
          <input id="today-date" type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        </div>
      </div>
      {error && <div className="error">{error}</div>}
      {payload && !branches.length && (
        <p className="empty" style={{ marginTop: '0.75rem' }}>No branch classes left to join on this day.</p>
      )}
      {branches.map((branch) => (
        <div key={branch.id} className="student-today-branch">
          <h3 className="card-title">{branch.name}</h3>
          <ul className="teacher-queue-list">
            {branch.classes.map((c) => {
              const started = new Date(c.start_time).getTime() <= now
              const full = c.confirmed_count >= c.capacity
              const seatsLeft = Math.max(c.capacity - c.confirmed_count, 0)
              return (
                <li key={c.id}>
                  <div className="row" style={{ justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <strong>{formatTime(c.start_time)} – {formatTime(c.end_time)}</strong> · {c.title}
                      <div className="card-meta">
                        {c.teacher_name}
                        {c.class_topic ? ` · ${c.class_topic}` : ''}
                        {' · '}{seatsLeft} seat{seatsLeft === 1 ? '' : 's'} left
                        {c.ticket_cost != null && ` · ${c.ticket_cost} ticket${c.ticket_cost === 1 ? '' : 's'}`}
                      </div>
                      <div className="row-actions" style={{ marginTop: '0.25rem' }}>
                        {c.accepts_walk_ins && <span className="badge badge--success">Walk-ins</span>}
                        {started && c.accepts_walk_ins && <span className="badge badge--muted">In progress</span>}
                        {c.student_booked && <span className="badge badge--muted">You&apos;re in</span>}
                      </div>
                    </div>
                    <div>
                      {c.student_booked ? null : full ? (
                        <span className="badge badge--muted">Full</span>
                      ) : (
                        <button type="button" disabled={booking} onClick={() => onBook(c.id, c)}>
                          {started ? 'Take a seat' : 'Book'}
                        </button>
                      )}
                    </div>
                  </div>
                </li>
              )
            })}
          </ul>
        </div>
      ))}
    </section>
  )
}
