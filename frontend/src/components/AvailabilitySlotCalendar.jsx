import { useEffect, useMemo, useState } from 'react'
import { formatSlotRange, timezoneLabel } from '../utils/datetime.js'

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

export default function AvailabilitySlotCalendar({
  slots = [],
  selectedStart = '',
  onSelectSlot,
  loading = false,
}) {
  const today = useMemo(() => new Date(), [])
  const [month, setMonth] = useState(() => startOfMonth(today))
  const [selectedDay, setSelectedDay] = useState(today)

  const slotsByDay = useMemo(() => {
    const map = {}
    for (const slot of slots) {
      const key = dateKey(new Date(slot.start))
      if (!map[key]) map[key] = []
      map[key].push(slot)
    }
    for (const key of Object.keys(map)) {
      map[key].sort((a, b) => new Date(a.start) - new Date(b.start))
    }
    return map
  }, [slots])

  const firstSlotDay = useMemo(() => {
    if (!slots.length) return null
    return new Date(slots[0].start)
  }, [slots])

  useEffect(() => {
    if (!firstSlotDay) return
    setMonth(startOfMonth(firstSlotDay))
    setSelectedDay(firstSlotDay)
  }, [firstSlotDay])

  const cells = useMemo(() => buildMonthCells(month), [month])
  const selectedKey = dateKey(selectedDay)
  const daySlots = slotsByDay[selectedKey] || []

  const shiftMonth = (delta) => {
    setMonth((current) => new Date(current.getFullYear(), current.getMonth() + delta, 1))
  }

  const selectDay = (day) => {
    setSelectedDay(day)
  }

  const pickSlot = (slot) => {
    onSelectSlot?.(slot)
    setSelectedDay(new Date(slot.start))
  }

  if (loading) {
    return <p className="card-meta">Loading available times…</p>
  }

  if (!slots.length) {
    return (
      <p className="card-meta">
        No open slots in the next 4 weeks — enter a custom time below.
      </p>
    )
  }

  return (
    <div className="availability-calendar">
      <div className="calendar-wrap">
        <div className="calendar-toolbar">
          <div className="calendar-nav">
            <button type="button" className="secondary" onClick={() => shiftMonth(-1)} aria-label="Previous month">
              ‹
            </button>
            <h3 className="calendar-month">{formatMonthYear(month)}</h3>
            <button type="button" className="secondary" onClick={() => shiftMonth(1)} aria-label="Next month">
              ›
            </button>
          </div>
          <button
            type="button"
            className="secondary"
            onClick={() => {
              setMonth(startOfMonth(today))
              setSelectedDay(today)
            }}
          >
            Today
          </button>
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
            const count = (slotsByDay[key] || []).length
            const isToday = sameDay(day, today)
            const isSelected = sameDay(day, selectedDay)
            const inMonth = day.getMonth() === month.getMonth()
            const isPast = day < new Date(today.getFullYear(), today.getMonth(), today.getDate())

            return (
              <div
                key={key}
                className={[
                  'calendar-day',
                  isToday ? 'calendar-day--today' : '',
                  isSelected ? 'calendar-day--selected' : '',
                  !inMonth ? 'calendar-day--muted' : '',
                  count ? 'calendar-day--has-slots' : '',
                ].filter(Boolean).join(' ')}
              >
                <button
                  type="button"
                  className="calendar-day-hit"
                  onClick={() => selectDay(day)}
                  disabled={!count}
                  aria-label={count ? `${day.getDate()} — ${count} available time${count === 1 ? '' : 's'}` : `${day.getDate()} — no times`}
                >
                  <span className="calendar-day-num">{day.getDate()}</span>
                  {count > 0 && (
                    <span className="calendar-day-slot-count" aria-hidden="true">
                      {count > 3 ? '•••' : '•'.repeat(Math.min(count, 3))}
                    </span>
                  )}
                </button>
                {count > 0 && inMonth && !isPast && (
                  <div className="calendar-day-events">
                    {(slotsByDay[key] || []).slice(0, 2).map((slot) => (
                      <button
                        key={slot.start}
                        type="button"
                        className={[
                          'calendar-event',
                          selectedStart === slot.start ? 'calendar-event--active' : '',
                        ].filter(Boolean).join(' ')}
                        onClick={() => pickSlot(slot)}
                      >
                        {formatTime(slot.start)}
                      </button>
                    ))}
                    {count > 2 && (
                      <span className="calendar-more">+{count - 2} more</span>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>

        <div className="card calendar-day-list">
          <h3>
            {selectedDay.toLocaleDateString(undefined, {
              weekday: 'long',
              month: 'long',
              day: 'numeric',
            })}
          </h3>
          {daySlots.length ? (
            daySlots.map((slot) => (
              <button
                key={slot.start}
                type="button"
                className={[
                  'calendar-day-list-item',
                  selectedStart === slot.start ? 'calendar-day-list-item--active' : '',
                ].filter(Boolean).join(' ')}
                onClick={() => pickSlot(slot)}
              >
                <span className="calendar-day-list-time">{formatTime(slot.start)}</span>
                <span className="calendar-day-list-title">
                  until {formatTime(slot.end)}
                  {slot.note ? ` · ${slot.note}` : ''}
                </span>
              </button>
            ))
          ) : (
            <p className="card-meta">No available times on this day.</p>
          )}
        </div>
      </div>
      <p className="card-meta">
        Times shown in {timezoneLabel()}. Pick a day, then choose a slot.
      </p>
    </div>
  )
}
