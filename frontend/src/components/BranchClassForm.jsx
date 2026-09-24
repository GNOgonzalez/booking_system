import { useEffect, useMemo, useState } from 'react'
import { apiFetch } from '../api.js'
import { datetimeLocalToIso, endFromStartDuration, formatTime, toDatetimeLocal } from '../utils/datetime.js'

/**
 * Place one class inside a branch's open hours.
 *
 * Staff pass `teacherOptions` (teachers with their offerings) and pick a teacher;
 * teachers pass their own `offerings`. Either way `postPath(branchId)` is where the
 * class is created and `dayPath(branchId)` shows what is already placed that day.
 */
export default function BranchClassForm({
  branches,
  offerings,
  teacherOptions,
  postPath,
  dayPath,
  onPlaced,
}) {
  const [branchId, setBranchId] = useState('')
  const [teacherId, setTeacherId] = useState('')
  const [offeringId, setOfferingId] = useState('')
  const [topicId, setTopicId] = useState('')
  const [start, setStart] = useState('')
  const [end, setEnd] = useState('')
  const [capacity, setCapacity] = useState('')
  const [walkIns, setWalkIns] = useState(false)
  const [day, setDay] = useState(null)
  const [dayError, setDayError] = useState('')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(null)

  const activeBranches = useMemo(() => (branches || []).filter((b) => b.is_active), [branches])
  useEffect(() => {
    if (!branchId && activeBranches.length) setBranchId(String(activeBranches[0].id))
  }, [activeBranches, branchId])

  const teacherRows = teacherOptions || []
  const currentOfferings = useMemo(() => {
    if (teacherOptions) {
      return teacherRows.find((t) => String(t.id) === teacherId)?.offerings || []
    }
    return offerings || []
  }, [teacherOptions, teacherRows, teacherId, offerings])
  const offering = currentOfferings.find((o) => String(o.id) === offeringId)

  useEffect(() => {
    if (teacherOptions && !teacherId && teacherRows.length) setTeacherId(String(teacherRows[0].id))
  }, [teacherOptions, teacherRows, teacherId])

  useEffect(() => {
    setOfferingId(currentOfferings.length === 1 ? String(currentOfferings[0].id) : '')
    setTopicId('')
  }, [currentOfferings])

  const dateOnly = start ? start.slice(0, 10) : ''
  useEffect(() => {
    if (!branchId || !dateOnly || !dayPath) {
      setDay(null)
      return
    }
    let cancelled = false
    setDayError('')
    apiFetch(`${dayPath(branchId)}?date=${dateOnly}`)
      .then((data) => { if (!cancelled) setDay(data) })
      .catch((err) => { if (!cancelled) setDayError(err.message) })
    return () => { cancelled = true }
  }, [branchId, dateOnly, dayPath, saved])

  const onStartChange = (value) => {
    setStart(value)
    if (value) setEnd(endFromStartDuration(value, 60))
  }

  const useWindow = (window) => {
    setStart(toDatetimeLocal(window.start))
    setEnd(endFromStartDuration(toDatetimeLocal(window.start), 60))
  }

  const submit = async (event) => {
    event.preventDefault()
    setError('')
    setSaved(null)
    if (!branchId) return setError('Pick a branch.')
    if (teacherOptions && !teacherId) return setError('Pick a teacher.')
    if (!offeringId) return setError('Pick a class.')
    if (!start || !end) return setError('Pick a start and end time.')
    setSaving(true)
    try {
      const body = {
        class_offering: Number(offeringId),
        start_time: datetimeLocalToIso(start),
        end_time: datetimeLocalToIso(end),
        accepts_walk_ins: walkIns,
      }
      if (teacherOptions) body.teacher = Number(teacherId)
      if (topicId) body.class_topic_id = Number(topicId)
      if (capacity) body.capacity = Number(capacity)
      const session = await apiFetch(postPath(branchId), { method: 'POST', body: JSON.stringify(body) })
      setSaved(session)
      onPlaced?.(session)
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  if (!activeBranches.length) {
    return <p className="card-meta">No branches with open hours yet.</p>
  }

  return (
    <form onSubmit={submit} className="branch-class-form">
      <div className="row">
        <div className="field grow">
          <label htmlFor="bcf-branch">Branch</label>
          <select id="bcf-branch" value={branchId} onChange={(e) => setBranchId(e.target.value)}>
            {activeBranches.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
          </select>
        </div>
        {teacherOptions && (
          <div className="field grow">
            <label htmlFor="bcf-teacher">Teacher</label>
            <select id="bcf-teacher" value={teacherId} onChange={(e) => setTeacherId(e.target.value)}>
              {teacherRows.map((t) => <option key={t.id} value={t.id}>{t.username}</option>)}
            </select>
          </div>
        )}
      </div>
      <div className="row">
        <div className="field grow">
          <label htmlFor="bcf-offering">Class</label>
          <select id="bcf-offering" value={offeringId} onChange={(e) => { setOfferingId(e.target.value); setTopicId('') }}>
            <option value="">Choose a class…</option>
            {currentOfferings.map((o) => <option key={o.id} value={o.id}>{o.label}</option>)}
          </select>
          {!currentOfferings.length && (
            <p className="card-meta">This teacher has no active classes to schedule.</p>
          )}
        </div>
        {offering?.topics?.length > 0 && (
          <div className="field grow">
            <label htmlFor="bcf-topic">Topic</label>
            <select id="bcf-topic" value={topicId} onChange={(e) => setTopicId(e.target.value)}>
              <option value="">General</option>
              {offering.topics.map((t) => <option key={t.id} value={t.id}>{t.title}</option>)}
            </select>
          </div>
        )}
      </div>
      <div className="row">
        <div className="field grow">
          <label htmlFor="bcf-start">Starts</label>
          <input id="bcf-start" type="datetime-local" value={start} onChange={(e) => onStartChange(e.target.value)} />
        </div>
        <div className="field grow">
          <label htmlFor="bcf-end">Ends</label>
          <input id="bcf-end" type="datetime-local" value={end} onChange={(e) => setEnd(e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="bcf-capacity">Seats</label>
          <input
            id="bcf-capacity"
            type="number"
            min="1"
            placeholder={offering ? String(offering.default_capacity) : ''}
            value={capacity}
            onChange={(e) => setCapacity(e.target.value)}
            style={{ width: '5rem' }}
          />
        </div>
      </div>
      <label className="checkbox-row">
        <input type="checkbox" checked={walkIns} onChange={(e) => setWalkIns(e.target.checked)} />
        <span>Walk-ins welcome — students can still take a seat after it starts, until it ends.</span>
      </label>

      {dateOnly && (
        <div className="branch-day-preview">
          {dayError && <p className="card-meta">{dayError}</p>}
          {day && (
            <>
              <p className="card-meta">
                <strong>{day.name}</strong> on {dateOnly}:{' '}
                {day.classes.length
                  ? `${day.classes.length} class${day.classes.length === 1 ? '' : 'es'} placed.`
                  : 'nothing placed yet.'}
              </p>
              {day.open_windows.length ? (
                <div className="branch-windows">
                  {day.open_windows.map((w) => (
                    <button
                      key={w.start}
                      type="button"
                      className="secondary small"
                      onClick={() => useWindow(w)}
                      title="Start a class at the beginning of this open stretch"
                    >
                      Open {formatTime(w.start)} – {formatTime(w.end)}
                    </button>
                  ))}
                </div>
              ) : (
                <p className="card-meta">The branch is closed that day, or every open stretch already has a class.</p>
              )}
            </>
          )}
        </div>
      )}

      {error && <div className="error">{error}</div>}
      {saved && (
        <div className="success">
          Placed <strong>{saved.title}</strong> at {saved.branch_name}, {formatTime(saved.start_time)} – {formatTime(saved.end_time)}.
        </div>
      )}
      <div className="form-actions">
        <button type="submit" disabled={saving}>{saving ? 'Placing…' : 'Place class'}</button>
      </div>
    </form>
  )
}
