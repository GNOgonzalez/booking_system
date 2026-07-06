import { useEffect, useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { apiFetch } from '../api.js'
import { useTeacherScope } from '../hooks/useTeacherScope.js'
import { useTeacherPermissions } from '../hooks/useTeacherPermissions.js'
import {
  datetimeLocalToIso,
  endFromStartDuration,
  formatSlotRange,
  timezoneLabel,
  toDatetimeLocal,
} from '../utils/datetime.js'

const AVAILABILITY_ERROR_MARKERS = [
  'Session time is outside your availability.',
  'Session time is outside teacher availability.',
]

const DURATION_OPTIONS = [
  { minutes: 30, label: '30 minutes' },
  { minutes: 60, label: '1 hour' },
  { minutes: 90, label: '1 hour 30 minutes' },
]

function formatTopics(item) {
  const titles = (item.topics || []).map((topic) => topic.title).filter(Boolean)
  if (!titles.length) return '—'
  const suffix = item.topics_ordered ? ' (in order)' : ''
  return `${titles.join(' · ')}${suffix}`
}

function isAvailabilityError(message) {
  return AVAILABILITY_ERROR_MARKERS.some((marker) => message === marker || message.includes(marker))
}

function isOutsideAvailabilityResponse(err) {
  if (err?.code === 'outside_availability') return true
  return isAvailabilityError(err?.message || '')
}

function formatSpecialDay(date, startTime, endTime) {
  if (!date) return ''
  const label = new Date(`${date}T12:00:00`).toLocaleDateString(undefined, {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  })
  return `${label}, ${startTime} – ${endTime}`
}

export default function TeacherCreateSessionPage() {
  const navigate = useNavigate()
  const { isStaff, paths } = useTeacherScope()
  const { can } = useTeacherPermissions()
  const canEditAvailability = isStaff || can('manage_availability')
  const [classes, setClasses] = useState([])
  const [classOffering, setClassOffering] = useState('')
  const [classTopicId, setClassTopicId] = useState('')
  const [start, setStart] = useState('')
  const [end, setEnd] = useState('')
  const [timeMode, setTimeMode] = useState('regular')
  const [durationMinutes, setDurationMinutes] = useState(60)
  const [slots, setSlots] = useState([])
  const [loadingSlots, setLoadingSlots] = useState(false)
  const [selectedSlot, setSelectedSlot] = useState('')
  const [capacity, setCapacity] = useState('')
  const [meetingProvider, setMeetingProvider] = useState('google_meet')
  const [error, setError] = useState('')
  const [loadingClasses, setLoadingClasses] = useState(true)
  const [busy, setBusy] = useState(false)
  const [specialPrompt, setSpecialPrompt] = useState(null)
  const [specialNote, setSpecialNote] = useState('Added when scheduling session')

  useEffect(() => {
    apiFetch(paths.classes)
      .then((rows) => {
        const active = rows.filter((c) => c.is_active)
        setClasses(active)
        if (active.length === 1) {
          setClassOffering(String(active[0].id))
          setCapacity(String(active[0].default_capacity))
          const firstTopic = active[0].topics?.[0]
          setClassTopicId(firstTopic ? String(firstTopic.id) : '')
        }
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoadingClasses(false))
  }, [paths.classes])

  useEffect(() => {
    if (timeMode !== 'regular') return undefined
    let cancelled = false
    setLoadingSlots(true)
    apiFetch(`${paths.schedulingSlots}?duration_minutes=${durationMinutes}`)
      .then((data) => {
        if (cancelled) return
        const rows = data.slots || []
        setSlots(rows)
        setSelectedSlot((current) => (
          rows.some((slot) => slot.start === current) ? current : ''
        ))
      })
      .catch((err) => {
        if (!cancelled) setError(err.message)
      })
      .finally(() => {
        if (!cancelled) setLoadingSlots(false)
      })
    return () => {
      cancelled = true
    }
  }, [paths.schedulingSlots, timeMode, durationMinutes])

  useEffect(() => {
    if (timeMode !== 'regular' || !selectedSlot) return
    const slot = slots.find((item) => item.start === selectedSlot)
    if (!slot) return
    setStart(toDatetimeLocal(slot.start))
    setEnd(toDatetimeLocal(slot.end))
  }, [timeMode, selectedSlot, slots])

  useEffect(() => {
    if (!specialPrompt) return undefined
    const onKey = (event) => {
      if (event.key === 'Escape' && !busy) setSpecialPrompt(null)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [specialPrompt, busy])

  const onClassChange = (e) => {
    const id = e.target.value
    setClassOffering(id)
    const picked = classes.find((c) => String(c.id) === id)
    if (picked) {
      setCapacity(String(picked.default_capacity))
      const firstTopic = picked.topics?.[0]
      setClassTopicId(firstTopic ? String(firstTopic.id) : '')
    } else {
      setClassTopicId('')
    }
  }

  const onDurationChange = (e) => {
    const minutes = Number(e.target.value)
    setDurationMinutes(minutes)
    if (timeMode === 'custom' && start) {
      setEnd(endFromStartDuration(start, minutes))
    }
  }

  const onStartChange = (e) => {
    const value = e.target.value
    setStart(value)
    if (timeMode === 'custom' && value) {
      setEnd(endFromStartDuration(value, durationMinutes))
    }
  }

  const selectedSlotData = slots.find((item) => item.start === selectedSlot)

  const buildSessionBody = () => {
    const startIso = timeMode === 'regular' && selectedSlot
      ? selectedSlot
      : datetimeLocalToIso(start)
    const endIso = timeMode === 'regular' && selectedSlotData
      ? selectedSlotData.end
      : datetimeLocalToIso(end)
    return {
      class_offering: Number(classOffering),
      class_topic_id: classTopicId ? Number(classTopicId) : null,
      start_time: startIso,
      end_time: endIso,
      capacity: capacity ? Number(capacity) : undefined,
      meeting_provider: meetingProvider,
    }
  }

  const createSession = (body) => apiFetch(paths.sessions, {
    method: 'POST',
    body: JSON.stringify(body),
  })

  const checkSessionAvailability = (startTime, endTime) => {
    const params = new URLSearchParams({ start_time: startTime, end_time: endTime })
    return apiFetch(`${paths.sessionAvailabilityCheck}?${params}`)
  }

  const openSpecialPrompt = (sessionBody) => {
    const startLocal = toDatetimeLocal(sessionBody.start_time)
    const [date, startTime] = startLocal.includes('T') ? startLocal.split('T') : ['', '']
    const endTime = toDatetimeLocal(sessionBody.end_time).split('T')[1] || ''
    setSpecialNote('Added when scheduling session')
    setSpecialPrompt({
      sessionBody,
      date,
      startTime,
      endTime,
    })
  }

  const closeSpecialPrompt = () => {
    if (!busy) setSpecialPrompt(null)
  }

  const addSpecialDayAndCreate = async () => {
    if (!specialPrompt) return
    setBusy(true)
    setError('')
    try {
      await createSession({
        ...specialPrompt.sessionBody,
        add_special_availability: true,
        special_availability_note: specialNote.trim(),
      })
      setSpecialPrompt(null)
      navigate(paths.staffTeacherSessions)
    } catch (err) {
      setError(err.message)
      setSpecialPrompt(null)
    } finally {
      setBusy(false)
    }
  }

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    if (!classOffering) {
      setError('Choose a class from the catalog.')
      return
    }
    if (timeMode === 'regular' && !selectedSlot) {
      setError('Choose an available time slot.')
      return
    }
    if (!start || !end) {
      setError('Choose a start and end time.')
      return
    }
    const sessionBody = buildSessionBody()
    setBusy(true)
    try {
      if (timeMode === 'custom') {
        const check = await checkSessionAvailability(sessionBody.start_time, sessionBody.end_time)
        if (!check.available) {
          openSpecialPrompt(sessionBody)
          return
        }
      }
      await createSession(sessionBody)
      navigate(paths.staffTeacherSessions)
    } catch (err) {
      if (isOutsideAvailabilityResponse(err) || isAvailabilityError(err.message)) {
        openSpecialPrompt(sessionBody)
      } else {
        setError(err.message)
      }
    } finally {
      setBusy(false)
    }
  }

  const selected = classes.find((c) => String(c.id) === classOffering)
  const classesLink = isStaff ? `${paths.staffTeacherSessions.replace('/sessions', '/classes')}` : '/teacher/classes'
  const availabilityLink = isStaff
    ? paths.staffTeacherSessions.replace('/sessions', '/availability')
    : '/teacher/availability'

  if (!isStaff && !can('manage_schedule')) {
    return <Navigate to={paths.staffTeacherSessions || '/teacher/sessions'} replace />
  }

  return (
    <div>
      <h1>Create session</h1>
      <p className="page-intro">
        Pick a class from the catalog. Optionally choose which topic this session covers.
      </p>
      {error && <div className="error">{error}</div>}
      <form onSubmit={submit} className="card">
        <div className="field">
          <label>Class</label>
          <select
            value={classOffering}
            onChange={onClassChange}
            required
            disabled={loadingClasses || busy}
          >
            <option value="">
              {loadingClasses ? 'Loading classes…' : 'Choose a class…'}
            </option>
            {classes.map((item) => (
              <option key={item.id} value={item.id}>{item.label}</option>
            ))}
          </select>
          {!loadingClasses && classes.length === 0 && (
            <p className="card-meta">
              No classes in catalog yet. <Link to={classesLink}>Add classes first</Link>.
            </p>
          )}
        </div>

        {selected && (
          <>
            <dl className="class-catalog-meta class-catalog-meta--compact">
              <div><dt>Subject</dt><dd>{selected.subject}</dd></div>
              <div><dt>Level</dt><dd>{selected.level}</dd></div>
              <div><dt>Focus</dt><dd>{selected.focus}</dd></div>
              <div><dt>Topics</dt><dd>{formatTopics(selected)}</dd></div>
            </dl>
            {selected.topics?.length > 0 && (
              <div className="field">
                <label>Topic for this session</label>
                <select value={classTopicId} onChange={(e) => setClassTopicId(e.target.value)} disabled={busy}>
                  <option value="">General / no specific topic</option>
                  {selected.topics.map((topic) => (
                    <option key={topic.id} value={topic.id}>{topic.title}</option>
                  ))}
                </select>
              </div>
            )}
          </>
        )}

        <fieldset className="field time-mode-field">
          <legend>When</legend>
          <div className="time-mode-options">
            <label className="time-mode-option">
              <input
                type="radio"
                name="timeMode"
                value="regular"
                checked={timeMode === 'regular'}
                onChange={() => setTimeMode('regular')}
                disabled={busy}
              />
              Regular times
            </label>
            <label className="time-mode-option">
              <input
                type="radio"
                name="timeMode"
                value="custom"
                checked={timeMode === 'custom'}
                onChange={() => {
                  setTimeMode('custom')
                  setSelectedSlot('')
                }}
                disabled={busy}
              />
              Custom time
            </label>
          </div>
        </fieldset>

        <div className="field" style={{ maxWidth: '14rem' }}>
          <label>Session length</label>
          <select
            value={durationMinutes}
            onChange={onDurationChange}
            disabled={busy}
          >
            {DURATION_OPTIONS.map((option) => (
              <option key={option.minutes} value={option.minutes}>{option.label}</option>
            ))}
          </select>
        </div>

        {timeMode === 'regular' ? (
          <div className="field">
            <label>Available slot</label>
            <select
              value={selectedSlot}
              onChange={(e) => setSelectedSlot(e.target.value)}
              required={timeMode === 'regular'}
              disabled={busy || loadingSlots}
            >
              <option value="">
                {loadingSlots ? 'Loading slots…' : 'Choose a time…'}
              </option>
              {slots.map((slot) => (
                <option key={slot.start} value={slot.start}>
                  {formatSlotRange(slot.start, slot.end)}
                  {slot.note ? ` (${slot.note})` : ''}
                </option>
              ))}
            </select>
            <p className="card-meta">
              Slots come from your weekly and special availability ({timezoneLabel()}).{' '}
              <Link to={availabilityLink}>Edit availability</Link>
            </p>
            {!loadingSlots && slots.length === 0 && (
              <p className="card-meta">
                No open slots in the next 4 weeks — try a different length, add availability, or use custom time.
              </p>
            )}
          </div>
        ) : (
          <>
            <div className="field">
              <label>Start</label>
              <input
                type="datetime-local"
                value={start}
                onChange={onStartChange}
                required
                disabled={busy}
              />
            </div>
            <div className="field">
              <label>End</label>
              <input
                type="datetime-local"
                value={end}
                onChange={(e) => setEnd(e.target.value)}
                required
                disabled={busy}
              />
              <p className="card-meta">Updates automatically from start + session length; you can adjust manually.</p>
              <p className="card-meta">
                Custom times outside your weekly hours will ask you to add a one-off special day before the session is created.
              </p>
            </div>
          </>
        )}

        <div className="field" style={{ maxWidth: '8rem' }}>
          <label>Capacity</label>
          <input type="number" min="1" value={capacity} onChange={(e) => setCapacity(e.target.value)} disabled={busy} />
        </div>
        <div className="field">
          <label>Video link</label>
          <select value={meetingProvider} onChange={(e) => setMeetingProvider(e.target.value)} disabled={busy}>
            <option value="none">No video link</option>
            <option value="google_meet">Google Meet</option>
            <option value="zoom">Zoom</option>
          </select>
          <p className="card-meta">
            A join link is generated automatically. Real Google or Zoom APIs activate when credentials are set in <code>.env</code>.
          </p>
        </div>
        <button type="submit" disabled={!classes.length || busy}>
          {busy && !specialPrompt ? 'Creating…' : 'Create session'}
        </button>
      </form>

      {specialPrompt && (
        <>
          <button
            type="button"
            className="modal-backdrop"
            aria-label="Close dialog"
            onClick={closeSpecialPrompt}
            disabled={busy}
          />
          <div className="modal-dialog" role="dialog" aria-modal="true" aria-labelledby="special-day-title">
            <h2 id="special-day-title">Add a special day?</h2>
            <p>
              This session time is not covered by your weekly or special-day availability yet.
              {canEditAvailability
                ? ' Add a one-off block for this date and time, then create the session in one step?'
                : ' Ask staff to add a special day, or pick a time inside your existing blocks.'}
            </p>
            <p>
              <strong>{formatSpecialDay(specialPrompt.date, specialPrompt.startTime, specialPrompt.endTime)}</strong>
            </p>
            {canEditAvailability ? (
              <>
                <div className="field">
                  <label>Note (optional)</label>
                  <input
                    value={specialNote}
                    onChange={(e) => setSpecialNote(e.target.value)}
                    placeholder="e.g. Holiday makeup"
                    disabled={busy}
                  />
                </div>
                <div className="form-actions">
                  <button type="button" onClick={addSpecialDayAndCreate} disabled={busy}>
                    {busy ? 'Saving…' : 'Add special day & create session'}
                  </button>
                  <button type="button" className="secondary" onClick={closeSpecialPrompt} disabled={busy}>
                    Cancel
                  </button>
                </div>
              </>
            ) : (
              <div className="form-actions">
                <Link to={availabilityLink} className="btn">View availability</Link>
                <button type="button" className="secondary" onClick={closeSpecialPrompt}>
                  Close
                </button>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
