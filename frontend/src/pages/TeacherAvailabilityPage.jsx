import { useEffect, useState } from 'react'
import { apiFetch } from '../api.js'
import { useTeacherScope } from '../hooks/useTeacherScope.js'
import { useTeacherPermissions } from '../hooks/useTeacherPermissions.js'

const WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

export default function TeacherAvailabilityPage() {
  const { isStaff, paths } = useTeacherScope()
  const { can } = useTeacherPermissions()
  const canEdit = isStaff || can('manage_availability')
  const [blocks, setBlocks] = useState([])
  const [specialBlocks, setSpecialBlocks] = useState([])
  const [weekday, setWeekday] = useState(0)
  const [start, setStart] = useState('09:00')
  const [end, setEnd] = useState('10:00')
  const [specialDate, setSpecialDate] = useState('')
  const [specialStart, setSpecialStart] = useState('09:00')
  const [specialEnd, setSpecialEnd] = useState('10:00')
  const [specialNote, setSpecialNote] = useState('')
  const [editingWeeklyId, setEditingWeeklyId] = useState(null)
  const [editingSpecialId, setEditingSpecialId] = useState(null)
  const [editWeekly, setEditWeekly] = useState(null)
  const [editSpecial, setEditSpecial] = useState(null)
  const [error, setError] = useState('')

  const load = () => {
    Promise.all([
      apiFetch(paths.availability),
      apiFetch(paths.specialAvailability),
    ])
      .then(([weekly, special]) => {
        setBlocks(weekly)
        setSpecialBlocks(special)
      })
      .catch((err) => setError(err.message))
  }

  useEffect(load, [paths.availability, paths.specialAvailability])

  const addWeekly = async (e) => {
    e.preventDefault()
    setError('')
    try {
      await apiFetch(paths.availability, {
        method: 'POST',
        body: JSON.stringify({ weekday: Number(weekday), start_time: start, end_time: end }),
      })
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  const addSpecial = async (e) => {
    e.preventDefault()
    setError('')
    try {
      await apiFetch(paths.specialAvailability, {
        method: 'POST',
        body: JSON.stringify({
          date: specialDate,
          start_time: specialStart,
          end_time: specialEnd,
          note: specialNote,
        }),
      })
      setSpecialNote('')
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  const removeWeekly = async (id) => {
    setError('')
    try {
      await apiFetch(paths.availabilityDetail(id), { method: 'DELETE' })
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  const saveWeeklyEdit = async (e) => {
    e.preventDefault()
    setError('')
    try {
      await apiFetch(paths.availabilityDetail(editingWeeklyId), {
        method: 'PATCH',
        body: JSON.stringify({
          weekday: Number(editWeekly.weekday),
          start_time: editWeekly.start_time,
          end_time: editWeekly.end_time,
        }),
      })
      setEditingWeeklyId(null)
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  const removeSpecial = async (id) => {
    setError('')
    try {
      await apiFetch(paths.specialAvailabilityDetail(id), { method: 'DELETE' })
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  const saveSpecialEdit = async (e) => {
    e.preventDefault()
    setError('')
    try {
      await apiFetch(paths.specialAvailabilityDetail(editingSpecialId), {
        method: 'PATCH',
        body: JSON.stringify(editSpecial),
      })
      setEditingSpecialId(null)
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  const formatDate = (value) => {
    if (!value) return ''
    return new Date(`${value}T12:00:00`).toLocaleDateString(undefined, {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    })
  }

  return (
    <div>
      {!isStaff && <h1>Availability</h1>}
      <p className="page-intro">
        Set weekly windows and one-off special days. Sessions must fit a block when any are defined.
      </p>
      {error && <div className="error">{error}</div>}

      {canEdit ? (
      <form onSubmit={addWeekly} className="card">
        <h2>Weekly blocks</h2>
        <div className="row">
          <div className="field grow">
            <label>Weekday</label>
            <select value={weekday} onChange={(e) => setWeekday(e.target.value)}>
              {WEEKDAYS.map((day, i) => (
                <option key={i} value={i}>{day}</option>
              ))}
            </select>
          </div>
          <div className="field grow">
            <label>Start</label>
            <input type="time" value={start} onChange={(e) => setStart(e.target.value)} />
          </div>
          <div className="field grow">
            <label>End</label>
            <input type="time" value={end} onChange={(e) => setEnd(e.target.value)} />
          </div>
        </div>
        <div className="form-actions">
          <button type="submit">Add weekly block</button>
        </div>
      </form>
      ) : (
        <div className="card card-meta">You do not have permission to edit availability. Contact staff.</div>
      )}

      {blocks.map((block) => (
        <div key={block.id} className="card">
          {editingWeeklyId === block.id ? (
            <form onSubmit={saveWeeklyEdit}>
              <div className="row">
                <div className="field grow">
                  <label>Weekday</label>
                  <select
                    value={editWeekly.weekday}
                    onChange={(e) => setEditWeekly({ ...editWeekly, weekday: e.target.value })}
                  >
                    {WEEKDAYS.map((day, i) => (
                      <option key={i} value={i}>{day}</option>
                    ))}
                  </select>
                </div>
                <div className="field grow">
                  <label>Start</label>
                  <input
                    type="time"
                    value={editWeekly.start_time}
                    onChange={(e) => setEditWeekly({ ...editWeekly, start_time: e.target.value })}
                  />
                </div>
                <div className="field grow">
                  <label>End</label>
                  <input
                    type="time"
                    value={editWeekly.end_time}
                    onChange={(e) => setEditWeekly({ ...editWeekly, end_time: e.target.value })}
                  />
                </div>
              </div>
              <div className="row-actions">
                <button type="submit">Save</button>
                <button type="button" className="secondary" onClick={() => setEditingWeeklyId(null)}>Cancel</button>
              </div>
            </form>
          ) : (
            <div className="card-row">
              <div className="card-title">
                {block.weekday_display} · {block.start_time} – {block.end_time}
              </div>
              {canEdit && (
                <div className="row-actions">
                  <button
                    type="button"
                    className="secondary"
                    onClick={() => {
                      setEditingWeeklyId(block.id)
                      setEditWeekly({
                        weekday: block.weekday,
                        start_time: block.start_time,
                        end_time: block.end_time,
                      })
                    }}
                  >
                    Edit
                  </button>
                  <button type="button" className="danger" onClick={() => removeWeekly(block.id)}>Delete</button>
                </div>
              )}
            </div>
          )}
        </div>
      ))}
      {!blocks.length && !specialBlocks.length && !error && (
        <div className="empty">No availability yet — any session time is allowed.</div>
      )}

      {canEdit ? (
      <form onSubmit={addSpecial} className="card">
        <h2>Special days</h2>
        <p className="card-meta">One-off availability for a specific date (e.g. holiday makeup).</p>
        <div className="row">
          <div className="field grow">
            <label>Date</label>
            <input type="date" value={specialDate} onChange={(e) => setSpecialDate(e.target.value)} required />
          </div>
          <div className="field grow">
            <label>Start</label>
            <input type="time" value={specialStart} onChange={(e) => setSpecialStart(e.target.value)} />
          </div>
          <div className="field grow">
            <label>End</label>
            <input type="time" value={specialEnd} onChange={(e) => setSpecialEnd(e.target.value)} />
          </div>
        </div>
        <div className="field">
          <label>Note (optional)</label>
          <input
            value={specialNote}
            onChange={(e) => setSpecialNote(e.target.value)}
            placeholder="e.g. Holiday makeup"
          />
        </div>
        <div className="form-actions">
          <button type="submit">Add special day</button>
        </div>
      </form>
      ) : null}

      {specialBlocks.map((block) => (
        <div key={block.id} className="card">
          {editingSpecialId === block.id ? (
            <form onSubmit={saveSpecialEdit}>
              <div className="row">
                <div className="field grow">
                  <label>Date</label>
                  <input
                    type="date"
                    value={editSpecial.date}
                    onChange={(e) => setEditSpecial({ ...editSpecial, date: e.target.value })}
                    required
                  />
                </div>
                <div className="field grow">
                  <label>Start</label>
                  <input
                    type="time"
                    value={editSpecial.start_time}
                    onChange={(e) => setEditSpecial({ ...editSpecial, start_time: e.target.value })}
                  />
                </div>
                <div className="field grow">
                  <label>End</label>
                  <input
                    type="time"
                    value={editSpecial.end_time}
                    onChange={(e) => setEditSpecial({ ...editSpecial, end_time: e.target.value })}
                  />
                </div>
              </div>
              <div className="field">
                <label>Note</label>
                <input
                  value={editSpecial.note}
                  onChange={(e) => setEditSpecial({ ...editSpecial, note: e.target.value })}
                />
              </div>
              <div className="row-actions">
                <button type="submit">Save</button>
                <button type="button" className="secondary" onClick={() => setEditingSpecialId(null)}>Cancel</button>
              </div>
            </form>
          ) : (
            <div className="card-row">
              <div>
                <div className="card-title">
                  {formatDate(block.date)} · {block.start_time} – {block.end_time}
                </div>
                {block.note && <div className="card-meta">{block.note}</div>}
              </div>
              {canEdit && (
                <div className="row-actions">
                  <button
                    type="button"
                    className="secondary"
                    onClick={() => {
                      setEditingSpecialId(block.id)
                      setEditSpecial({
                        date: block.date,
                        start_time: block.start_time,
                        end_time: block.end_time,
                        note: block.note || '',
                      })
                    }}
                  >
                    Edit
                  </button>
                  <button type="button" className="danger" onClick={() => removeSpecial(block.id)}>Delete</button>
                </div>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
