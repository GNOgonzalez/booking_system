import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { apiFetch } from '../api.js'
import { useGlossary } from '../hooks/useGlossary.jsx'

export default function StaffTeacherStudentsPage() {
  const { teacherId } = useParams()
  const { label, labels } = useGlossary()
  const [allStudents, setAllStudents] = useState([])
  const [assignedIds, setAssignedIds] = useState([])
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [saving, setSaving] = useState(false)

  const load = () => {
    Promise.all([
      apiFetch(`/api/staff/teachers/${teacherId}/students/?all=1`),
      apiFetch(`/api/staff/teachers/${teacherId}/students/`),
    ])
      .then(([everyone, assigned]) => {
        setAllStudents(everyone)
        setAssignedIds(assigned.map((row) => row.id))
      })
      .catch((err) => setError(err.message))
  }

  useEffect(load, [teacherId])

  const toggle = (id) => {
    setAssignedIds((current) => (
      current.includes(id) ? current.filter((item) => item !== id) : [...current, id]
    ))
  }

  const save = async (e) => {
    e.preventDefault()
    setSaving(true)
    setError('')
    setMessage('')
    try {
      const saved = await apiFetch(`/api/staff/teachers/${teacherId}/students/`, {
        method: 'PUT',
        body: JSON.stringify({ student_ids: assignedIds }),
      })
      setAssignedIds(saved.map((row) => row.id))
      setMessage('Assigned students saved.')
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <h2>Assigned {labels('student').toLowerCase()}</h2>
      <p className="page-intro">
        Choose which {labels('student').toLowerCase()} this {label('teacher').toLowerCase()} handles.
        They can also manage anyone they have already taught.
      </p>
      {message && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}
      <form onSubmit={save} className="card">
        {!allStudents.length && (
          <p className="card-meta">No {labels('student').toLowerCase()} in the studio yet.</p>
        )}
        {allStudents.map((student) => (
          <label key={student.id} className="checkbox-row">
            <input
              type="checkbox"
              checked={assignedIds.includes(student.id)}
              onChange={() => toggle(student.id)}
            />
            {student.label}
          </label>
        ))}
        <div className="form-actions">
          <button type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save assignments'}</button>
        </div>
      </form>
    </div>
  )
}
