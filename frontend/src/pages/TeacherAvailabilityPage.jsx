import { useEffect, useState } from 'react'
import { apiFetch } from '../api.js'

const WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

export default function TeacherAvailabilityPage() {
  const [blocks, setBlocks] = useState([])
  const [weekday, setWeekday] = useState(0)
  const [start, setStart] = useState('09:00')
  const [end, setEnd] = useState('10:00')
  const [error, setError] = useState('')

  const load = () => {
    apiFetch('/api/teacher/availability/')
      .then(setBlocks)
      .catch((err) => setError(err.message))
  }

  useEffect(load, [])

  const add = async (e) => {
    e.preventDefault()
    setError('')
    try {
      await apiFetch('/api/teacher/availability/', {
        method: 'POST',
        body: JSON.stringify({ weekday: Number(weekday), start_time: start, end_time: end }),
      })
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  const remove = async (id) => {
    setError('')
    try {
      await apiFetch(`/api/teacher/availability/${id}/`, { method: 'DELETE' })
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div>
      <h1>Availability</h1>
      <p className="page-intro">Set the weekly windows when you can teach.</p>
      {error && <div className="error">{error}</div>}
      <form onSubmit={add} className="card">
        <h2>Add a block</h2>
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
          <button type="submit">Add block</button>
        </div>
      </form>
      {blocks.map((block) => (
        <div key={block.id} className="card">
          <div className="card-row">
            <div className="card-title">
              {block.weekday_display} · {block.start_time} – {block.end_time}
            </div>
            <button type="button" className="danger" onClick={() => remove(block.id)}>Delete</button>
          </div>
        </div>
      ))}
      {!blocks.length && !error && <div className="empty">No availability blocks yet.</div>}
    </div>
  )
}
