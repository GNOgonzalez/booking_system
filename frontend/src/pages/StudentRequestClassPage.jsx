import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch } from '../api.js'
import AvailabilitySlotCalendar from '../components/AvailabilitySlotCalendar.jsx'
import ClassRequestSuccessModal from '../components/ClassRequestSuccessModal.jsx'
import {
  datetimeLocalToIso,
  formatDateTime,
  formatSlotRange,
  toDatetimeLocal,
} from '../utils/datetime.js'

const ANY_TEACHER = 'any'

function formatWhen(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

function profileKey(profile) {
  return `${profile.subject}::${profile.level}::${profile.focus}`
}

export default function StudentRequestClassPage() {
  const [teachers, setTeachers] = useState([])
  const [openClasses, setOpenClasses] = useState([])
  const [classes, setClasses] = useState([])
  const [availability, setAvailability] = useState({ windows: [], busy: [], slots: [] })
  const [requests, setRequests] = useState([])
  const [ticketsRemaining, setTicketsRemaining] = useState(null)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [saving, setSaving] = useState(false)
  const [loadingSlots, setLoadingSlots] = useState(false)
  const [selectedSlotData, setSelectedSlotData] = useState(null)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [confirmPreview, setConfirmPreview] = useState(null)
  const [requestSuccess, setRequestSuccess] = useState(null)
  const [form, setForm] = useState({
    teacher: '',
    classOffering: '',
    classTopic: '',
    start: '',
    end: '',
    tickets: '1',
  })

  const isAnyTeacher = form.teacher === ANY_TEACHER

  const loadRequests = () => {
    apiFetch('/api/class-requests/')
      .then(setRequests)
      .catch(() => {})
  }

  useEffect(() => {
    Promise.all([
      apiFetch('/api/class-requests/teachers/'),
      apiFetch('/api/class-requests/open-classes/'),
      apiFetch('/api/membership/'),
    ])
      .then(([teacherRows, openClassRows, membership]) => {
        setTeachers(teacherRows)
        setOpenClasses(openClassRows)
        setTicketsRemaining(membership?.active ? membership.tickets_remaining : 0)
      })
      .catch((err) => setError(err.message))
    loadRequests()
  }, [])

  useEffect(() => {
    if (!form.teacher || isAnyTeacher) {
      if (!isAnyTeacher) {
        setClasses([])
        setAvailability({ windows: [], busy: [], slots: [] })
      }
      return undefined
    }

    let cancelled = false
    setLoadingSlots(true)
    setClasses([])
    setSelectedSlotData(null)
    const qs = `?teacher=${encodeURIComponent(form.teacher)}&include_slots=true`
    Promise.all([
      apiFetch(`/api/class-requests/classes/${qs}`),
      apiFetch(`/api/class-requests/availability/${qs}`),
    ])
      .then(([classRows, snapshot]) => {
        if (cancelled) return
        setClasses(classRows)
        setAvailability(snapshot)
        setSelectedSlotData(null)
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
  }, [form.teacher, isAnyTeacher])

  useEffect(() => {
    if (!isAnyTeacher || !form.classOffering) {
      if (isAnyTeacher) {
        setAvailability({ windows: [], busy: [], slots: [] })
      }
      return undefined
    }

    const profile = openClasses.find((item) => profileKey(item) === form.classOffering)
    if (!profile) return undefined

    let cancelled = false
    setLoadingSlots(true)
    setSelectedSlotData(null)
    const qs = new URLSearchParams({
      subject: profile.subject,
      level: profile.level,
      focus: profile.focus,
    })
    apiFetch(`/api/class-requests/open-availability/?${qs}`)
      .then((snapshot) => {
        if (cancelled) return
        setAvailability(snapshot)
        setSelectedSlotData(null)
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
  }, [isAnyTeacher, form.classOffering, openClasses])

  useEffect(() => {
    if (!selectedSlotData) return
    setForm((current) => ({
      ...current,
      start: toDatetimeLocal(selectedSlotData.start),
      end: toDatetimeLocal(selectedSlotData.end),
    }))
  }, [selectedSlotData])

  const handleSlotSelect = (slot) => {
    setSelectedSlotData(slot)
  }

  const selectedClass = useMemo(() => {
    if (isAnyTeacher) {
      return openClasses.find((item) => profileKey(item) === form.classOffering)
    }
    return classes.find((item) => String(item.id) === form.classOffering)
  }, [classes, openClasses, form.classOffering, isAnyTeacher])

  const topicOptions = isAnyTeacher ? [] : (selectedClass?.topics || [])
  const minTickets = isAnyTeacher
    ? (selectedClass?.min_ticket_cost || 1)
    : (selectedClass?.ticket_cost || 1)

  const onTeacherChange = (teacher) => {
    setClasses([])
    setAvailability({ windows: [], busy: [], slots: [] })
    setSelectedSlotData(null)
    setForm({
      teacher,
      classOffering: '',
      classTopic: '',
      start: '',
      end: '',
      tickets: '1',
    })
  }

  const onClassChange = (classOffering) => {
    if (isAnyTeacher) {
      const picked = openClasses.find((item) => profileKey(item) === classOffering)
      setSelectedSlotData(null)
      setForm((current) => ({
        ...current,
        classOffering,
        classTopic: '',
        start: '',
        end: '',
        tickets: String(Math.max(picked?.min_ticket_cost || 1, Number(current.tickets) || 1)),
      }))
      return
    }

    const picked = classes.find((item) => String(item.id) === classOffering)
    const firstTopic = picked?.topics?.[0]
    setSelectedSlotData(null)
    setForm((current) => ({
      ...current,
      classOffering,
      classTopic: firstTopic ? String(firstTopic.id) : '',
      start: '',
      end: '',
      tickets: String(Math.max(picked?.ticket_cost || 1, Number(current.tickets) || 1)),
    }))
  }

  const resolveRequestTimes = () => {
    if (selectedSlotData?.start && selectedSlotData?.end) {
      return {
        start_time: selectedSlotData.start,
        end_time: selectedSlotData.end,
      }
    }
    const start_time = datetimeLocalToIso(form.start)
    const end_time = datetimeLocalToIso(form.end)
    if (!start_time || !end_time) {
      throw new Error('Pick a time from the calendar or enter custom start and end.')
    }
    return { start_time, end_time }
  }

  const buildRequestBody = () => {
    const body = {
      ...resolveRequestTimes(),
      tickets_requested: Number(form.tickets),
    }

    if (isAnyTeacher) {
      const profile = openClasses.find((item) => profileKey(item) === form.classOffering)
      if (!profile) throw new Error('Choose a class.')
      Object.assign(body, {
        open_to_any_teacher: true,
        subject: profile.subject,
        level: profile.level,
        focus: profile.focus,
      })
      return {
        body,
        preview: {
          classLabel: profile.label,
          teacherLabel: 'Any available teacher',
          openToAnyTeacher: true,
        },
      }
    }

    const offeringId = Number(form.classOffering)
    if (!Number.isFinite(offeringId) || offeringId <= 0) {
      throw new Error('Choose a class for this teacher.')
    }
    const pickedClass = classes.find((item) => item.id === offeringId)
    if (!pickedClass) {
      throw new Error('That class is not offered by this teacher. Choose the class again.')
    }
    const pickedTeacher = teachers.find((item) => String(item.id) === form.teacher)
    const pickedTopic = pickedClass.topics?.find((topic) => String(topic.id) === form.classTopic)
    Object.assign(body, {
      teacher: Number(form.teacher),
      class_offering: offeringId,
      class_topic: form.classTopic ? Number(form.classTopic) : null,
    })
    return {
      body,
      preview: {
        classLabel: pickedClass.label || `${pickedClass.subject} · ${pickedClass.level} · ${pickedClass.focus}`,
        teacherLabel: pickedTeacher?.label || 'Teacher',
        topicLabel: pickedTopic?.title || '',
        openToAnyTeacher: false,
      },
    }
  }

  const sendRequest = async (body, preview) => {
    setSaving(true)
    setError('')
    setMessage('')
    try {
      const result = await apiFetch('/api/class-requests/', {
        method: 'POST',
        body: JSON.stringify(body),
      })
      setConfirmOpen(false)
      setConfirmPreview(null)
      setRequestSuccess({
        preview: {
          ...preview,
          start_time: body.start_time,
          end_time: body.end_time,
          tickets_requested: body.tickets_requested,
        },
        result,
      })
      setForm((current) => ({
        ...current,
        start: '',
        end: '',
      }))
      setSelectedSlotData(null)
      loadRequests()
      apiFetch('/api/membership/').then((membership) => {
        setTicketsRemaining(membership?.active ? membership.tickets_remaining : 0)
      })
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  const submit = (e) => {
    e.preventDefault()
    setError('')
    try {
      const { body, preview } = buildRequestBody()
      setConfirmPreview({ body, preview })
      setConfirmOpen(true)
    } catch (err) {
      setError(err.message)
    }
  }

  const handleConfirmRequest = () => {
    if (!confirmPreview?.body) return
    sendRequest(confirmPreview.body, confirmPreview.preview)
  }

  useEffect(() => {
    if (!confirmOpen) return undefined
    const onKey = (event) => {
      if (event.key === 'Escape' && !saving) {
        setConfirmOpen(false)
        setConfirmPreview(null)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [confirmOpen, saving])

  const cancelRequest = async (id) => {
    if (!window.confirm('Cancel this pending request? Your tickets will be returned.')) return
    setError('')
    try {
      await apiFetch(`/api/class-requests/${id}/`, { method: 'DELETE' })
      setMessage('Request cancelled.')
      loadRequests()
      apiFetch('/api/membership/').then((membership) => {
        setTicketsRemaining(membership?.active ? membership.tickets_remaining : 0)
      })
    } catch (err) {
      setError(err.message)
    }
  }

  const pending = requests.filter((item) => item.status === 'pending')
  const slots = availability.slots || []

  return (
    <div>
      <h1>Request a class</h1>
      <p className="page-intro">
        Pick a time inside a teacher&apos;s availability, or open your request to any teacher who teaches your class.
        Tickets are held until a teacher approves or denies the request.
        {ticketsRemaining != null && (
          <> You have <strong>{ticketsRemaining}</strong> ticket{ticketsRemaining === 1 ? '' : 's'} available.</>
        )}
      </p>
      <p className="card-meta">
        <Link to="/sessions">← Browse scheduled sessions</Link>
      </p>

      {message && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}
      {requestSuccess && (
        <ClassRequestSuccessModal
          request={requestSuccess.preview}
          result={requestSuccess.result}
          onClose={() => setRequestSuccess(null)}
        />
      )}

      {confirmOpen && confirmPreview && (
        <>
          <button
            type="button"
            className="modal-backdrop"
            aria-label="Cancel request"
            onClick={() => {
              if (saving) return
              setConfirmOpen(false)
              setConfirmPreview(null)
            }}
            disabled={saving}
          />
          <div
            className="modal-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="class-request-confirm-title"
          >
            <h2 id="class-request-confirm-title">Confirm class request</h2>
            <p>
              Request <strong>{confirmPreview.preview.classLabel}</strong>
              {' '}with {confirmPreview.preview.teacherLabel}?
            </p>
            {confirmPreview.preview.topicLabel && (
              <p>Topic: {confirmPreview.preview.topicLabel}</p>
            )}
            <p>
              {formatDateTime(confirmPreview.body.start_time)}
              {' – '}
              {formatDateTime(confirmPreview.body.end_time)}
            </p>
            <p>
              This will hold {confirmPreview.body.tickets_requested} ticket
              {confirmPreview.body.tickets_requested === 1 ? '' : 's'} until a teacher responds.
            </p>
            <div className="form-actions">
              <button type="button" onClick={handleConfirmRequest} disabled={saving}>
                {saving ? 'Sending…' : 'Send request'}
              </button>
              <button
                type="button"
                className="secondary"
                onClick={() => {
                  setConfirmOpen(false)
                  setConfirmPreview(null)
                }}
                disabled={saving}
              >
                Cancel
              </button>
            </div>
          </div>
        </>
      )}

      <form onSubmit={submit} className="card" style={{ marginBottom: '1.5rem' }}>
        <h2>New request</h2>
        <div className="field">
          <label>Teacher</label>
          <select
            value={form.teacher}
            onChange={(e) => onTeacherChange(e.target.value)}
            required
          >
            <option value="">Choose a teacher…</option>
            {openClasses.length > 0 && (
              <option value={ANY_TEACHER}>Any available teacher</option>
            )}
            {teachers.map((teacher) => (
              <option key={teacher.id} value={teacher.id}>{teacher.label}</option>
            ))}
          </select>
          {!teachers.length && !openClasses.length && (
            <p className="card-meta">No teachers with availability are bookable on your plan.</p>
          )}
        </div>

        {form.teacher && (
          <>
            <div className="field">
              <label>Class</label>
              <select
                value={form.classOffering}
                onChange={(e) => onClassChange(e.target.value)}
                required
              >
                <option value="">Choose a class…</option>
                {isAnyTeacher
                  ? openClasses.map((item) => (
                    <option key={profileKey(item)} value={profileKey(item)}>
                      {item.label} ({item.min_ticket_cost} ticket{item.min_ticket_cost === 1 ? '' : 's'} · {item.teacher_count} teacher{item.teacher_count === 1 ? '' : 's'})
                    </option>
                  ))
                  : classes.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.label || `${item.subject} · ${item.level} · ${item.focus}`} ({item.ticket_cost} ticket{item.ticket_cost === 1 ? '' : 's'})
                    </option>
                  ))}
              </select>
            </div>

            {!isAnyTeacher && topicOptions.length > 0 && (
              <div className="field">
                <label>Topic</label>
                <select
                  value={form.classTopic}
                  onChange={(e) => setForm({ ...form, classTopic: e.target.value })}
                >
                  <option value="">No specific topic</option>
                  {topicOptions.map((topic) => (
                    <option key={topic.id} value={topic.id}>{topic.title}</option>
                  ))}
                </select>
              </div>
            )}

            <div className="field">
              <label>Tickets to offer</label>
              <input
                type="number"
                min={minTickets}
                max={ticketsRemaining ?? minTickets}
                value={form.tickets}
                onChange={(e) => setForm({ ...form, tickets: e.target.value })}
                required
              />
              <p className="card-meta">Minimum for this class: {minTickets}. Held until approved or denied.</p>
            </div>

            {form.classOffering && (
              <>
                <div className="field">
                  <label>Available times</label>
                  <AvailabilitySlotCalendar
                    slots={slots}
                    selectedStart={selectedSlotData?.start || ''}
                    onSelectSlot={handleSlotSelect}
                    loading={loadingSlots}
                  />
                </div>

                {selectedSlotData && (
                  <p className="card-meta">
                    Selected: {formatSlotRange(selectedSlotData.start, selectedSlotData.end)}
                    {' '}
                    <button
                      type="button"
                      className="ghost"
                      onClick={() => {
                        setSelectedSlotData(null)
                        setForm((current) => ({ ...current, start: '', end: '' }))
                      }}
                    >
                      Clear
                    </button>
                  </p>
                )}

                <details className="card-meta">
                  <summary>Custom time</summary>
                  <div className="row" style={{ marginTop: '0.75rem' }}>
                    <div className="field grow">
                      <label>Start</label>
                      <input
                        type="datetime-local"
                        value={form.start}
                        onChange={(e) => {
                          setSelectedSlotData(null)
                          setForm({ ...form, start: e.target.value })
                        }}
                        required={!selectedSlotData}
                      />
                    </div>
                    <div className="field grow">
                      <label>End</label>
                      <input
                        type="datetime-local"
                        value={form.end}
                        onChange={(e) => {
                          setSelectedSlotData(null)
                          setForm({ ...form, end: e.target.value })
                        }}
                        required={!selectedSlotData}
                      />
                    </div>
                  </div>
                </details>
              </>
            )}
          </>
        )}

        <button type="submit" disabled={saving || !form.teacher || !form.classOffering}>
          {saving ? 'Sending…' : 'Review request'}
        </button>
      </form>

      <h2>Your requests</h2>
      {pending.map((item) => (
        <div key={item.id} className="card class-request-item">
          <div className="card-title">{item.class_offering_label || item.class_profile_label}</div>
          <div className="card-meta">
            {item.teacher_name} · {formatWhen(item.start_time)} – {formatWhen(item.end_time)}
            {item.class_topic_title && <> · {item.class_topic_title}</>}
          </div>
          <div className="card-meta">
            {item.tickets_requested} ticket{item.tickets_requested === 1 ? '' : 's'} held · Pending approval
          </div>
          <button type="button" className="secondary" onClick={() => cancelRequest(item.id)}>
            Cancel request
          </button>
        </div>
      ))}
      {!pending.length && <p className="card-meta">No pending requests.</p>}
    </div>
  )
}
