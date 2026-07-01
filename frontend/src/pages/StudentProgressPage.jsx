import { useEffect, useState } from 'react'
import { apiFetch } from '../api.js'

export default function StudentProgressPage() {
  const [reports, setReports] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    apiFetch('/api/progress/')
      .then(setReports)
      .catch((err) => setError(err.message))
  }, [])

  return (
    <div>
      <h1>My progress</h1>
      {error && <p className="error">{error}</p>}
      {reports.map((report) => (
        <div key={report.id} className="card">
          <strong>{report.rating}/5</strong>
          {report.skill_name ? ` — ${report.skill_name}` : ''}
          <p>by {report.teacher_name}</p>
          {report.note && <p>{report.note}</p>}
        </div>
      ))}
      {!reports.length && !error && <p>No progress reports yet.</p>}
    </div>
  )
}
