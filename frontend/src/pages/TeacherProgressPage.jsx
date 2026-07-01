import { useEffect, useState } from 'react'
import { apiFetch } from '../api.js'

export default function TeacherProgressPage() {
  const [reports, setReports] = useState([])
  const [studentId, setStudentId] = useState('')
  const [rating, setRating] = useState(3)
  const [note, setNote] = useState('')
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const load = () => {
    apiFetch('/api/progress/teacher/')
      .then(setReports)
      .catch((err) => setError(err.message))
  }

  useEffect(load, [])

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setMessage('')
    try {
      await apiFetch('/api/progress/teacher/', {
        method: 'POST',
        body: JSON.stringify({ student: Number(studentId), rating: Number(rating), note }),
      })
      setMessage('Report saved.')
      setNote('')
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div>
      <h1>Student progress</h1>
      {message && <p className="success">{message}</p>}
      {error && <p className="error">{error}</p>}

      <form onSubmit={submit} className="card">
        <p>
          <label>
            Student ID
            <input value={studentId} onChange={(e) => setStudentId(e.target.value)} />
          </label>
        </p>
        <p>
          <label>
            Rating
            <select value={rating} onChange={(e) => setRating(e.target.value)}>
              {[1, 2, 3, 4, 5].map((n) => (
                <option key={n} value={n}>{n}</option>
              ))}
            </select>
          </label>
        </p>
        <p>
          <label>
            Note
            <input value={note} onChange={(e) => setNote(e.target.value)} />
          </label>
        </p>
        <button type="submit">Save report</button>
      </form>

      {reports.map((report) => (
        <div key={report.id} className="card">
          <strong>{report.student_name}</strong> — {report.rating}/5
          {report.note && <p>{report.note}</p>}
        </div>
      ))}
    </div>
  )
}
