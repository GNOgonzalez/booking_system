import { useCallback, useEffect, useMemo, useState } from 'react'
import { apiFetch } from '../api.js'
import { formatTime } from '../utils/datetime.js'
import BranchClassForm from './BranchClassForm.jsx'

function todayIso() {
  const d = new Date()
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

/**
 * Teacher view of a branch day: hours, classes already placed, remaining open stretches,
 * plus an add-class form. Also lets the teacher flip walk-ins on their own classes.
 */
export default function TeacherBranchPanel({ canManage, onSessionPlaced, onSessionChanged }) {
  const [data, setData] = useState({ branches: [], offerings: [] })
  const [branchId, setBranchId] = useState('')
  const [date, setDate] = useState(todayIso())
  const [day, setDay] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [reloadKey, setReloadKey] = useState(0)
  const [me, setMe] = useState(null)

  useEffect(() => {
    Promise.all([apiFetch('/api/teacher/branches/'), apiFetch('/api/me/')])
      .then(([payload, meRow]) => {
        setData(payload)
        setMe(meRow)
        if (payload.branches.length) setBranchId(String(payload.branches[0].id))
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (!branchId || !date) return
    let cancelled = false
    apiFetch(`/api/teacher/branches/${branchId}/day/?date=${date}`)
      .then((row) => { if (!cancelled) setDay(row) })
      .catch((err) => { if (!cancelled) setError(err.message) })
    return () => { cancelled = true }
  }, [branchId, date, reloadKey])

  const postPath = useCallback((id) => `/api/teacher/branches/${id}/classes/`, [])
  const dayPath = useCallback((id) => `/api/teacher/branches/${id}/day/`, [])

  const toggleWalkIns = async (session) => {
    setError('')
    try {
      const updated = await apiFetch(`/api/teacher/sessions/${session.id}/walk-ins/`, {
        method: 'POST',
        body: JSON.stringify({ accepts_walk_ins: !session.accepts_walk_ins }),
      })
      setDay((current) => current && ({
        ...current,
        classes: current.classes.map((c) => (c.id === updated.id ? updated : c)),
      }))
      onSessionChanged?.(updated)
    } catch (err) {
      setError(err.message)
    }
  }

  const hoursToday = useMemo(() => {
    if (!day) return null
    const weekday = (new Date(`${date}T12:00:00`).getDay() + 6) % 7 // JS Sunday=0 → Monday=0
    return day.hours.filter((h) => h.weekday === weekday)
  }, [day, date])

  if (loading) return null
  if (!data.branches.length) return null

  return (
    <section className="card teacher-branch-panel">
      <h2 className="card-title">Branch classes</h2>
      <p className="card-meta">
        In-person classes inside a branch&apos;s open hours. Students pick from this day&apos;s list;
        tick walk-ins and they can still join after the class begins.
      </p>
      {error && <div className="error">{error}</div>}

      <div className="row">
        <div className="field">
          <label htmlFor="tbp-branch">Branch</label>
          <select id="tbp-branch" value={branchId} onChange={(e) => setBranchId(e.target.value)}>
            {data.branches.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
          </select>
        </div>
        <div className="field">
          <label htmlFor="tbp-date">Day</label>
          <input id="tbp-date" type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        </div>
      </div>

      {day && (
        <div className="branch-day">
          <p className="card-meta">
            {hoursToday?.length
              ? `Open ${hoursToday.map((h) => `${h.start_time}–${h.end_time}`).join(', ')} (studio time).`
              : 'Closed this day.'}
          </p>
          {day.classes.length > 0 && (
            <ul className="teacher-queue-list">
              {day.classes.map((c) => {
                const mine = me && c.teacher === me.id
                return (
                  <li key={c.id}>
                    <div className="row" style={{ justifyContent: 'space-between', alignItems: 'center' }}>
                      <div>
                        <strong>{formatTime(c.start_time)} – {formatTime(c.end_time)}</strong> · {c.title}
                        {!mine && <span className="card-meta"> · {c.teacher_name}</span>}
                        {c.accepts_walk_ins && <> <span className="badge badge--success">Walk-ins</span></>}
                        <div className="card-meta">{c.confirmed_count}/{c.capacity} seats taken</div>
                      </div>
                      {mine && canManage && (
                        <button type="button" className="secondary small" onClick={() => toggleWalkIns(c)}>
                          {c.accepts_walk_ins ? 'Stop walk-ins' : 'Allow walk-ins'}
                        </button>
                      )}
                    </div>
                  </li>
                )
              })}
            </ul>
          )}
          {hoursToday?.length > 0 && (
            <p className="card-meta">
              {day.open_windows.length
                ? <>Still open: {day.open_windows.map((w) => `${formatTime(w.start)}–${formatTime(w.end)}`).join(', ')}</>
                : 'Every open stretch has a class.'}
            </p>
          )}
        </div>
      )}

      {canManage && data.offerings.length > 0 && (
        <details className="branch-add-class" open={!day?.classes?.length}>
          <summary>Add a class here</summary>
          <BranchClassForm
            branches={data.branches}
            offerings={data.offerings}
            postPath={postPath}
            dayPath={dayPath}
            onPlaced={(session) => {
              setReloadKey((k) => k + 1)
              onSessionPlaced?.(session)
            }}
          />
        </details>
      )}
      {canManage && !data.offerings.length && (
        <p className="card-meta">Create a class first, then you can place it in a branch.</p>
      )}
    </section>
  )
}
