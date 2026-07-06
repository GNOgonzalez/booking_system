import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch } from '../api.js'
import { useGlossary } from '../hooks/useGlossary.jsx'

export default function StaffStudentsPage() {
  const { label, labels } = useGlossary()
  const [students, setStudents] = useState([])
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [editingId, setEditingId] = useState(null)
  const [editName, setEditName] = useState('')

  const load = () => {
    apiFetch('/api/staff/students/')
      .then(setStudents)
      .catch((err) => setError(err.message))
  }

  useEffect(load, [])

  const toggleActive = async (student) => {
    setError('')
    setMessage('')
    try {
      await apiFetch(`/api/staff/students/${student.id}/`, {
        method: 'PATCH',
        body: JSON.stringify({ is_active: !student.is_active }),
      })
      setMessage(`${student.username} marked ${student.is_active ? 'inactive' : 'active'}.`)
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  const saveName = async (e, studentId) => {
    e.preventDefault()
    setError('')
    setMessage('')
    try {
      await apiFetch(`/api/staff/students/${studentId}/`, {
        method: 'PATCH',
        body: JSON.stringify({ display_name: editName }),
      })
      setEditingId(null)
      setMessage('Display name saved.')
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div>
      <p className="card-meta"><Link to="/staff">← Staff dashboard</Link></p>
      <h1>{labels('student')}</h1>
      <p className="page-intro">
        Activate or deactivate {label('student').toLowerCase()} accounts. Inactive {labels('student').toLowerCase()} cannot log in or book {labels('session').toLowerCase()}.
      </p>
      {message && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}

      {students.map((student) => (
        <div key={student.id} className={`card${student.is_active ? '' : ' card--inactive'}`}>
          <div className="card-row">
            <div>
              <div className="card-title">
                {student.label}
                {!student.is_active && <span className="badge badge--muted">Inactive</span>}
              </div>
              <div className="card-meta">@{student.username}</div>
            </div>
            <div className="row-actions">
              <button
                type="button"
                className={student.is_active ? 'danger' : 'secondary'}
                onClick={() => toggleActive(student)}
              >
                {student.is_active ? 'Deactivate' : 'Activate'}
              </button>
            </div>
          </div>
          {editingId === student.id ? (
            <form onSubmit={(e) => saveName(e, student.id)} style={{ marginTop: '0.75rem' }}>
              <div className="field">
                <label>Display name</label>
                <input value={editName} onChange={(e) => setEditName(e.target.value)} />
              </div>
              <div className="row-actions">
                <button type="submit">Save name</button>
                <button type="button" className="secondary" onClick={() => setEditingId(null)}>Cancel</button>
              </div>
            </form>
          ) : (
            <button
              type="button"
              className="ghost"
              style={{ marginTop: '0.5rem' }}
              onClick={() => {
                setEditingId(student.id)
                setEditName(student.display_name || '')
              }}
            >
              Edit display name
            </button>
          )}
        </div>
      ))}
      {!students.length && !error && <p className="card-meta">No students found.</p>}
    </div>
  )
}
