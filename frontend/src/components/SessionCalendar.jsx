import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import SessionDetailPanel from './SessionDetailPanel.jsx'
import StudentOpenSessionPanel from './StudentOpenSessionPanel.jsx'
import StudentBookingPanel from './StudentBookingPanel.jsx'

const WEEKDAY_LABELS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

function startOfMonth(date) {
  return new Date(date.getFullYear(), date.getMonth(), 1)
}

function endOfMonth(date) {
  return new Date(date.getFullYear(), date.getMonth() + 1, 0, 23, 59, 59, 999)
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

function formatDayHeading(date) {
  return date.toLocaleDateString(undefined, {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
  })
}

function sessionStudents(session) {
  return Array.isArray(session.students) ? session.students : []
}

function uniqueTeacherOptions(sessions, extra) {
  const map = new Map()
  for (const session of sessions) {
    const id = session.teacher
    if (id == null) continue
    map.set(String(id), session.teacher_name || `Teacher ${id}`)
  }
  for (const option of extra || []) {
    if (option?.id == null) continue
    const id = String(option.id)
    map.set(id, option.label || option.username || map.get(id) || `Teacher ${id}`)
  }
  return [...map.entries()]
    .map(([id, label]) => ({ id, label }))
    .sort((a, b) => a.label.localeCompare(b.label))
}

function uniqueClassOptions(sessions) {
  const map = new Map()
  for (const session of sessions) {
    const id = session.class_offering
    const label = session.class_offering_label || session.title
    if (id != null && label) map.set(String(id), label)
  }
  return [...map.entries()]
    .map(([id, label]) => ({ id, label }))
    .sort((a, b) => a.label.localeCompare(b.label))
}

function uniqueStudentOptions(sessions) {
  const map = new Map()
  for (const session of sessions) {
    for (const student of sessionStudents(session)) {
      if (student?.id != null && student.username) {
        map.set(String(student.id), student.username)
      }
    }
  }
  return [...map.entries()]
    .map(([id, label]) => ({ id, label }))
    .sort((a, b) => a.label.localeCompare(b.label))
}

function matchesFilters(session, filters) {
  if (filters.teacher && String(session.teacher) !== filters.teacher) return false
  if (filters.classOffering && String(session.class_offering) !== filters.classOffering) return false
  if (filters.student) {
    const booked = sessionStudents(session).some((student) => String(student.id) === filters.student)
    if (!booked) return false
  }
  return true
}

function studentNames(session) {
  return sessionStudents(session).map((student) => student.username).join(', ')
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
  teacherFilterOptions,
  alwaysShowTeacherFilter = false,
}) {
  const today = useMemo(() => new Date(), [])
  const [month, setMonth] = useState(() => startOfMonth(today))
  const [selected, setSelected] = useState(today)
  const [activeSession, setActiveSession] = useState(null)
  const [view, setView] = useState('month')
  const [filters, setFilters] = useState({ teacher: '', student: '', classOffering: '' })

  const teacherOptions = useMemo(
    () => uniqueTeacherOptions(sessions, teacherFilterOptions),
    [sessions, teacherFilterOptions],
  )
  const classOptions = useMemo(() => uniqueClassOptions(sessions), [sessions])
  const studentOptions = useMemo(() => uniqueStudentOptions(sessions), [sessions])
  const showTeacherFilter = teacherOptions.length > 0 && (
    alwaysShowTeacherFilter || teacherOptions.length > 1
  )
  const showClassFilter = classOptions.length > 1
  const showStudentFilter = studentOptions.length > 0
  const hasFilterControls = showTeacherFilter || showClassFilter || showStudentFilter
  const hasActiveFilters = Boolean(filters.teacher || filters.student || filters.classOffering)

  const visibleSessions = useMemo(
    () => sessions.filter((session) => matchesFilters(session, filters)),
    [sessions, filters],
  )

  const monthSessions = useMemo(() => {
    const start = startOfMonth(month)
    const end = endOfMonth(month)
    return visibleSessions
      .filter((session) => {
        const at = new Date(session.start_time)
        return at >= start && at <= end
      })
      .sort((a, b) => new Date(a.start_time) - new Date(b.start_time))
  }, [visibleSessions, month])

  const sessionsByDay = useMemo(() => {
    const map = {}
    for (const session of visibleSessions) {
      const key = dateKey(new Date(session.start_time))
      if (!map[key]) map[key] = []
      map[key].push(session)
    }
    for (const key of Object.keys(map)) {
      map[key].sort((a, b) => new Date(a.start_time) - new Date(b.start_time))
    }
    return map
  }, [visibleSessions])

  const listGroups = useMemo(() => {
    const groups = []
    let currentKey = ''
    for (const session of monthSessions) {
      const key = dateKey(new Date(session.start_time))
      if (key !== currentKey) {
        groups.push({ key, date: new Date(session.start_time), sessions: [] })
        currentKey = key
      }
      groups[groups.length - 1].sessions.push(session)
    }
    return groups
  }, [monthSessions])

  const cells = useMemo(() => buildMonthCells(month), [month])
  const selectedKey = dateKey(selected)
  const selectedSessions = sessionsByDay[selectedKey] || []

  const setFilter = (key, value) => {
    setFilters((current) => ({ ...current, [key]: value }))
    setActiveSession(null)
  }

  const shiftMonth = (delta) => {
    setMonth((current) => new Date(current.getFullYear(), current.getMonth() + delta, 1))
    setActiveSession(null)
  }

  const selectDay = (day) => {
    setSelected(day)
    setActiveSession(null)
  }

  const selectSession = (session, day) => {
    if (day) setSelected(day)
    setActiveSession(session)
  }

  const panelPaths = useMemo(() => {
    if (activeSession && resolveApiPaths) return resolveApiPaths(activeSession)
    return apiPaths
  }, [activeSession, resolveApiPaths, apiPaths])

  const renderSessionRow = (session) => {
    const names = studentNames(session)
    return (
      <button
        key={session.id}
        type="button"
        className={[
          'calendar-day-list-item',
          activeSession?.id === session.id ? 'calendar-day-list-item--active' : '',
          session.student_booked ? 'calendar-day-list-item--booked' : '',
        ].filter(Boolean).join(' ')}
        onClick={() => selectSession(session, new Date(session.start_time))}
      >
        <span className="calendar-day-list-time">{formatTime(session.start_time)}</span>
        <span className="calendar-day-list-title">
          {showTeacher && session.teacher_name && (
            <span className="calendar-day-list-teacher">{session.teacher_name} · </span>
          )}
          {session.title}
          {session.student_booked && (
            <span className="calendar-day-list-booked"> · Booked</span>
          )}
          {names && (
            <span className="calendar-day-list-students"> · {names}</span>
          )}
        </span>
      </button>
    )
  }

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
              <div className="calendar-view-toggle" role="group" aria-label="Calendar view">
                <button
                  type="button"
                  className={view === 'month' ? 'calendar-view-toggle-btn is-active' : 'calendar-view-toggle-btn'}
                  onClick={() => setView('month')}
                >
                  Month
                </button>
                <button
                  type="button"
                  className={view === 'list' ? 'calendar-view-toggle-btn is-active' : 'calendar-view-toggle-btn'}
                  onClick={() => setView('list')}
                >
                  List
                </button>
              </div>
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

          {hasFilterControls && (
            <div className="session-filters calendar-filters">
              <div className="row">
                {showTeacherFilter && (
                  <div className="field grow">
                    <label htmlFor="calendar-filter-teacher">Teacher</label>
                    <select
                      id="calendar-filter-teacher"
                      value={filters.teacher}
                      onChange={(e) => setFilter('teacher', e.target.value)}
                    >
                      <option value="">All teachers</option>
                      {teacherOptions.map((option) => (
                        <option key={option.id} value={option.id}>{option.label}</option>
                      ))}
                    </select>
                  </div>
                )}
                {showStudentFilter && (
                  <div className="field grow">
                    <label htmlFor="calendar-filter-student">Student</label>
                    <select
                      id="calendar-filter-student"
                      value={filters.student}
                      onChange={(e) => setFilter('student', e.target.value)}
                    >
                      <option value="">All students</option>
                      {studentOptions.map((option) => (
                        <option key={option.id} value={option.id}>{option.label}</option>
                      ))}
                    </select>
                  </div>
                )}
                {showClassFilter && (
                  <div className="field grow">
                    <label htmlFor="calendar-filter-class">Class</label>
                    <select
                      id="calendar-filter-class"
                      value={filters.classOffering}
                      onChange={(e) => setFilter('classOffering', e.target.value)}
                    >
                      <option value="">All classes</option>
                      {classOptions.map((option) => (
                        <option key={option.id} value={option.id}>{option.label}</option>
                      ))}
                    </select>
                  </div>
                )}
                {hasActiveFilters && (
                  <button
                    type="button"
                    className="secondary"
                    onClick={() => setFilters({ teacher: '', student: '', classOffering: '' })}
                  >
                    Clear filters
                  </button>
                )}
              </div>
            </div>
          )}

          {view === 'month' && (
            <>
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
                <h2>{formatDayHeading(selected)}</h2>
                {selectedSessions.length ? (
                  selectedSessions.map(renderSessionRow)
                ) : (
                  <div className="empty">
                    {hasActiveFilters ? 'No matching sessions on this day.' : 'No sessions on this day.'}
                  </div>
                )}
              </div>
            </>
          )}

          {view === 'list' && (
            <div className="card calendar-month-list">
              {listGroups.length ? (
                listGroups.map((group) => (
                  <section key={group.key} className="calendar-month-list-group">
                    <h2>{formatDayHeading(group.date)}</h2>
                    {group.sessions.map(renderSessionRow)}
                  </section>
                ))
              ) : (
                <div className="empty">
                  {hasActiveFilters
                    ? 'No matching sessions this month.'
                    : 'No sessions this month.'}
                </div>
              )}
            </div>
          )}
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
