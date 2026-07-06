import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import SessionDetailPanel from './SessionDetailPanel.jsx'
import StudentOpenSessionPanel from './StudentOpenSessionPanel.jsx'
import StudentBookingPanel from './StudentBookingPanel.jsx'

const WEEKDAY_LABELS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

function startOfMonth(date) {
  return new Date(date.getFullYear(), date.getMonth(), 1)
}

function daysInMonth(date) {
  return new Date(date.getFullYear(), date.getMonth() + 1, 0).getDate()
}

function sameDay(a, b) {
  return (
    a.getFullYear() === b.getFullYear()
    && a.getMonth() === b.getMonth()
    && a.getDate() === b.getDate()
  )
}

function dateKey(date) {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

function buildMonthCells(monthDate) {
  const first = startOfMonth(monthDate)
  const leading = first.getDay()
  const totalDays = daysInMonth(monthDate)
  const cells = []

  for (let i = 0; i < leading; i += 1) cells.push(null)
  for (let day = 1; day <= totalDays; day += 1) {
    cells.push(new Date(monthDate.getFullYear(), monthDate.getMonth(), day))
  }
  while (cells.length % 7 !== 0) cells.push(null)
  return cells
}

function formatTime(iso) {
  return new Date(iso).toLocaleTimeString(undefined, {
    hour: 'numeric',
    minute: '2-digit',
  })
}

function formatMonthYear(date) {
  return date.toLocaleDateString(undefined, { month: 'long', year: 'numeric' })
}

export default function SessionCalendar({
  sessions,
  apiPaths,
  resolveApiPaths,
  showTeacher = false,
  showNewSession = true,
  showWriteReport = true,
  showManageSession = false,
  onSessionChanged,
  onBookSession,
  booking = false,
  ticketsRemaining = null,
  memberships = [],
  onCancelBooking,
  cancelling = false,
}) {
  const today = useMemo(() => new Date(), [])
  const [month, setMonth] = useState(() => startOfMonth(today))
  const [selected, setSelected] = useState(today)
  const [activeSession, setActiveSession] = useState(null)

  const sessionsByDay = useMemo(() => {
    const map = {}
    for (const session of sessions) {
      const key = dateKey(new Date(session.start_time))
      if (!map[key]) map[key] = []
      map[key].push(session)
    }
    for (const key of Object.keys(map)) {
      map[key].sort((a, b) => new Date(a.start_time) - new Date(b.start_time))
    }
    return map
  }, [sessions])

  const cells = useMemo(() => buildMonthCells(month), [month])
  const selectedKey = dateKey(selected)
  const selectedSessions = sessionsByDay[selectedKey] || []

  const shiftMonth = (delta) => {
    setMonth((current) => new Date(current.getFullYear(), current.getMonth() + delta, 1))
    setActiveSession(null)
  }

  const selectDay = (day) => {
    setSelected(day)
    setActiveSession(null)
  }

  const selectSession = (session, day) => {
    setSelected(day)
    setActiveSession(session)
  }

  const panelPaths = activeSession && resolveApiPaths
    ? resolveApiPaths(activeSession)
    : apiPaths

  return (
    <div className="calendar-layout">
      <div className="calendar-main">
        <div className="calendar-wrap">
          <div className="calendar-toolbar">
            <div className="calendar-nav">
              <button type="button" className="secondary" onClick={() => shiftMonth(-1)} aria-label="Previous month">
                ‹
              </button>
              <h2 className="calendar-month">{formatMonthYear(month)}</h2>
              <button type="button" className="secondary" onClick={() => shiftMonth(1)} aria-label="Next month">
                ›
              </button>
            </div>
            <div className="row">
              <button
                type="button"
                className="secondary"
                onClick={() => {
                  const now = startOfMonth(today)
                  setMonth(now)
                  setSelected(today)
                  setActiveSession(null)
                }}
              >
                Today
              </button>
              {showNewSession && apiPaths?.newSession && (
                <Link to={apiPaths.newSession} className="btn">New session</Link>
              )}
            </div>
          </div>

          <div className="calendar-grid">
            {WEEKDAY_LABELS.map((label) => (
              <div key={label} className="calendar-weekday">{label}</div>
            ))}
            {cells.map((day, index) => {
              if (!day) {
                return <div key={`empty-${index}`} className="calendar-day calendar-day--empty" />
              }
              const key = dateKey(day)
              const daySessions = sessionsByDay[key] || []
              const isToday = sameDay(day, today)
              const isSelected = sameDay(day, selected)
              const inMonth = day.getMonth() === month.getMonth()

              return (
                <div
                  key={key}
                  className={[
                    'calendar-day',
                    isToday ? 'calendar-day--today' : '',
                    isSelected ? 'calendar-day--selected' : '',
                    !inMonth ? 'calendar-day--muted' : '',
                  ].filter(Boolean).join(' ')}
                >
                  <button type="button" className="calendar-day-hit" onClick={() => selectDay(day)}>
                    <span className="calendar-day-num">{day.getDate()}</span>
                  </button>
                  <div className="calendar-day-events">
                    {daySessions.slice(0, 3).map((session) => (
                      <button
                        key={session.id}
                        type="button"
                        className={[
                          'calendar-event',
                          session.status === 'cancelled' ? 'calendar-event--cancelled' : '',
                          activeSession?.id === session.id ? 'calendar-event--active' : '',
                        ].filter(Boolean).join(' ')}
                        title={`${session.teacher_name ? `${session.teacher_name} · ` : ''}${session.title} · ${formatTime(session.start_time)}`}
                        onClick={() => selectSession(session, day)}
                      >
                        {formatTime(session.start_time)}
                        {showTeacher && session.teacher_name && (
                          <span className="calendar-event-teacher"> {session.teacher_name}</span>
                        )}
                        {' '}{session.title}
                      </button>
                    ))}
                    {daySessions.length > 3 && (
                      <span className="calendar-more">+{daySessions.length - 3} more</span>
                    )}
                  </div>
                </div>
              )
            })}
          </div>

          <div className="card calendar-day-list">
            <h2>
              {selected.toLocaleDateString(undefined, {
                weekday: 'long',
                month: 'long',
                day: 'numeric',
              })}
            </h2>
            {selectedSessions.length ? (
              selectedSessions.map((session) => (
                <button
                  key={session.id}
                  type="button"
                  className={[
                    'calendar-day-list-item',
                    activeSession?.id === session.id ? 'calendar-day-list-item--active' : '',
                  ].filter(Boolean).join(' ')}
                  onClick={() => setActiveSession(session)}
                >
                  <span className="calendar-day-list-time">{formatTime(session.start_time)}</span>
                  <span className="calendar-day-list-title">
                    {showTeacher && session.teacher_name && (
                      <span className="calendar-day-list-teacher">{session.teacher_name} · </span>
                    )}
                    {session.title}
                  </span>
                </button>
              ))
            ) : (
              <div className="empty">No sessions on this day.</div>
            )}
          </div>
        </div>
      </div>

      {onBookSession ? (
        <StudentOpenSessionPanel
          session={activeSession}
          onClose={() => setActiveSession(null)}
          onBook={onBookSession}
          booking={booking}
          ticketsRemaining={ticketsRemaining}
          memberships={memberships}
        />
      ) : onCancelBooking ? (
        <StudentBookingPanel
          session={activeSession}
          onClose={() => setActiveSession(null)}
          onCancel={onCancelBooking}
          cancelling={cancelling}
        />
      ) : (
        <SessionDetailPanel
          session={activeSession}
          onClose={() => setActiveSession(null)}
          apiPaths={panelPaths}
          showTeacherLink={Boolean(resolveApiPaths)}
          showWriteReport={showWriteReport}
          showManageSession={showManageSession}
          onSessionChanged={(updated) => {
            setActiveSession(updated)
            onSessionChanged?.(updated)
          }}
        />
      )}
    </div>
  )
}
