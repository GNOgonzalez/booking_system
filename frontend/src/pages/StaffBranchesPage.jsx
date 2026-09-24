import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch } from '../api.js'
import BranchClassForm from '../components/BranchClassForm.jsx'

const WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

/** Mon–Sat 12:00–20:00 — the owner's default; one click fills it in. */
const DEFAULT_HOURS = [0, 1, 2, 3, 4, 5].map((weekday) => ({ weekday, start_time: '12:00', end_time: '20:00' }))

function emptyRows() {
  return WEEKDAYS.map((_, weekday) => ({ weekday, open: false, start_time: '12:00', end_time: '20:00' }))
}

function rowsFromHours(hours) {
  const rows = emptyRows()
  for (const h of hours || []) {
    rows[h.weekday] = { weekday: h.weekday, open: true, start_time: h.start_time, end_time: h.end_time }
  }
  return rows
}

function hoursFromRows(rows) {
  return rows.filter((r) => r.open).map(({ weekday, start_time, end_time }) => ({ weekday, start_time, end_time }))
}

function HoursEditor({ branch, onSaved, onCancel }) {
  const [name, setName] = useState(branch?.name || '')
  const [isActive, setIsActive] = useState(branch ? branch.is_active : true)
  const [rows, setRows] = useState(branch ? rowsFromHours(branch.hours) : rowsFromHours(DEFAULT_HOURS))
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  const setRow = (weekday, patch) => {
    setRows((current) => current.map((r) => (r.weekday === weekday ? { ...r, ...patch } : r)))
  }

  const submit = async (event) => {
    event.preventDefault()
    setError('')
    if (!name.trim()) return setError('Give the branch a name.')
    setSaving(true)
    try {
      const body = { name: name.trim(), is_active: isActive, hours: hoursFromRows(rows) }
      const saved = branch
        ? await apiFetch(`/api/staff/branches/${branch.id}/`, { method: 'PATCH', body: JSON.stringify(body) })
        : await apiFetch('/api/staff/branches/', { method: 'POST', body: JSON.stringify(body) })
      onSaved(saved)
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={submit} className="card">
      <h3 className="card-title">{branch ? `Edit ${branch.name}` : 'New branch'}</h3>
      <div className="row">
        <div className="field grow">
          <label htmlFor="branch-name">Branch name</label>
          <input id="branch-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Main branch" />
        </div>
        <label className="checkbox-row" style={{ alignSelf: 'end' }}>
          <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
          <span>Open for scheduling</span>
        </label>
      </div>
      <div className="row" style={{ justifyContent: 'space-between', alignItems: 'center' }}>
        <strong>Opening hours</strong>
        <button type="button" className="secondary small" onClick={() => setRows(rowsFromHours(DEFAULT_HOURS))}>
          Use Mon–Sat 12:00–20:00
        </button>
      </div>
      <table className="branch-hours-table">
        <tbody>
          {rows.map((row) => (
            <tr key={row.weekday} className={row.open ? '' : 'branch-hours-closed'}>
              <td>
                <label className="checkbox-row">
                  <input
                    type="checkbox"
                    checked={row.open}
                    onChange={(e) => setRow(row.weekday, { open: e.target.checked })}
                  />
                  <span>{WEEKDAYS[row.weekday]}</span>
                </label>
              </td>
              <td>
                <input
                  type="time"
                  value={row.start_time}
                  disabled={!row.open}
                  onChange={(e) => setRow(row.weekday, { start_time: e.target.value })}
                  aria-label={`${WEEKDAYS[row.weekday]} opens`}
                />
              </td>
              <td>to</td>
              <td>
                <input
                  type="time"
                  value={row.end_time}
                  disabled={!row.open}
                  onChange={(e) => setRow(row.weekday, { end_time: e.target.value })}
                  aria-label={`${WEEKDAYS[row.weekday]} closes`}
                />
              </td>
              <td className="card-meta">{row.open ? '' : 'Closed'}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="card-meta">
        Hours are in the studio&apos;s timezone. Classes must start and finish inside these hours.
      </p>
      {error && <div className="error">{error}</div>}
      <div className="form-actions">
        <button type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save branch'}</button>
        {onCancel && <button type="button" className="secondary" onClick={onCancel}>Cancel</button>}
      </div>
    </form>
  )
}

function hoursSummary(hours) {
  if (!hours?.length) return 'No opening hours set'
  return hours.map((h) => `${h.weekday_label.slice(0, 3)} ${h.start_time}–${h.end_time}`).join(' · ')
}

export default function StaffBranchesPage() {
  const [branches, setBranches] = useState([])
  const [teacherOptions, setTeacherOptions] = useState([])
  const [editing, setEditing] = useState(null) // null | 'new' | branch
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [placed, setPlaced] = useState([])

  const load = useCallback(() => {
    setLoading(true)
    Promise.all([
      apiFetch('/api/staff/branches/'),
      apiFetch('/api/staff/branches/teacher-options/'),
    ])
      .then(([rows, teachers]) => {
        setBranches(rows)
        setTeacherOptions(teachers)
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(load, [load])

  const onSaved = (saved) => {
    setBranches((rows) => {
      const exists = rows.some((b) => b.id === saved.id)
      return exists ? rows.map((b) => (b.id === saved.id ? saved : b)) : [...rows, saved]
    })
    setEditing(null)
  }

  const postPath = useCallback((branchId) => `/api/staff/branches/${branchId}/classes/`, [])
  const dayPath = useCallback((branchId) => `/api/staff/branches/${branchId}/day/`, [])

  return (
    <div>
      <p className="card-meta"><Link to="/staff">← Staff dashboard</Link></p>
      <h1>Branches &amp; open hours</h1>
      <p className="page-intro">
        Publish when each branch is open, then place teachers&apos; classes inside those hours.
        Students only see classes that have a teacher and a topic — empty hours are never shown to them.
        Tick <strong>walk-ins</strong> on a class and students can still grab a seat after it starts.
      </p>
      {error && <div className="error">{error}</div>}
      {loading && <div className="empty">Loading branches…</div>}

      {!loading && (
        <>
          <section className="card">
            <div className="row" style={{ justifyContent: 'space-between', alignItems: 'center' }}>
              <h2 className="card-title" style={{ margin: 0 }}>Branches</h2>
              {editing !== 'new' && (
                <button type="button" onClick={() => setEditing('new')}>Add branch</button>
              )}
            </div>
            {!branches.length && editing !== 'new' && (
              <p className="card-meta">No branches yet. Add your first one and set its opening hours.</p>
            )}
            <ul className="teacher-queue-list">
              {branches.map((branch) => (
                <li key={branch.id}>
                  <div className="row" style={{ justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <strong>{branch.name}</strong>{' '}
                      {!branch.is_active && <span className="badge badge--muted">Inactive</span>}
                      <div className="card-meta">{hoursSummary(branch.hours)}</div>
                    </div>
                    <div className="row-actions">
                      <button type="button" className="secondary small" onClick={() => setEditing(branch)}>
                        Edit hours
                      </button>
                    </div>
                  </div>
                  {editing && editing !== 'new' && editing.id === branch.id && (
                    <div style={{ marginTop: '0.75rem' }}>
                      <HoursEditor branch={branch} onSaved={onSaved} onCancel={() => setEditing(null)} />
                    </div>
                  )}
                </li>
              ))}
            </ul>
            {editing === 'new' && (
              <div style={{ marginTop: '0.75rem' }}>
                <HoursEditor onSaved={onSaved} onCancel={() => setEditing(null)} />
              </div>
            )}
          </section>

          <section className="card">
            <h2 className="card-title">Place a class</h2>
            <p className="card-meta">
              Pick the teacher, their class and topic, and a time inside the branch&apos;s hours.
              The open stretches for that day appear once you choose a start time.
              Placed classes also show on the <Link to="/staff/schedule">studio schedule</Link>.
            </p>
            <BranchClassForm
              branches={branches}
              teacherOptions={teacherOptions}
              postPath={postPath}
              dayPath={dayPath}
              onPlaced={(session) => setPlaced((rows) => [session, ...rows])}
            />
            {placed.length > 0 && (
              <ul className="teacher-queue-list">
                {placed.map((s) => (
                  <li key={s.id}>
                    <strong>{s.title}</strong> · {s.teacher_name} · {s.branch_name}{' '}
                    {s.accepts_walk_ins && <span className="badge badge--success">Walk-ins</span>}
                    <div className="card-meta">{new Date(s.start_time).toLocaleString()} – {new Date(s.end_time).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}</div>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      )}
    </div>
  )
}
