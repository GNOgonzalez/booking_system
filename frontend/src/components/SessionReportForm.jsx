import { useEffect, useState } from 'react'
import { apiFetch } from '../api.js'
import { useScoreDimensions, emptyScores, scoreOptions, defaultScore } from '../hooks/useScoreDimensions.js'
import { useTeacherScope } from '../hooks/useTeacherScope.js'

export default function SessionReportForm({ session, apiPaths: apiPathsProp, onSaved, onCancel }) {
  const scope = useTeacherScope()
  const apiPaths = apiPathsProp || scope.paths
  const subject = session?.class_subject || ''
  const dimensions = useScoreDimensions(subject)
  const [students, setStudents] = useState([])
  const [form, setForm] = useState({ student: '', scores: {}, class_notes: '' })
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [loadingStudents, setLoadingStudents] = useState(true)

  useEffect(() => {
    setLoadingStudents(true)
    setForm({ student: '', scores: emptyScores(dimensions), class_notes: '' })
    setError('')
    setMessage('')

    apiFetch(apiPaths.sessionStudents(session.id))
      .then(async (booked) => {
        if (booked.length) {
          setStudents(booked)
          return
        }
        const all = await apiFetch(apiPaths.students)
        setStudents(all)
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoadingStudents(false))
  }, [session.id, apiPaths, dimensions])

  const onField = (key) => (e) => setForm({ ...form, [key]: e.target.value })
  const onScore = (key) => (e) => setForm({
    ...form,
    scores: { ...form.scores, [key]: Number(e.target.value) },
  })

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setMessage('')
    if (!form.student) {
      setError('Please choose a student.')
      return
    }
    try {
      await apiFetch(apiPaths.feedback, {
        method: 'POST',
        body: JSON.stringify({
          student: Number(form.student),
          session: session.id,
          class_notes: form.class_notes,
          scores: form.scores,
        }),
      })
      setMessage('Report saved.')
      setForm({ ...form, class_notes: '' })
      if (onSaved) onSaved()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <form onSubmit={submit} className="calendar-report">
      <h3>Write report</h3>
      {subject && <p className="card-meta">Metrics for {subject}</p>}
      {message && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}

      <div className="field">
        <label>Student</label>
        <select
          value={form.student}
          onChange={onField('student')}
          required
          disabled={loadingStudents}
        >
          <option value="">
            {loadingStudents ? 'Loading students…' : 'Choose a student…'}
          </option>
          {students.map((student) => (
            <option key={student.id} value={student.id}>
              {student.label}
            </option>
          ))}
        </select>
        {!loadingStudents && students.length === 0 && (
          <p className="card-meta">No students available for this session.</p>
        )}
      </div>

      {dimensions.length ? (
        <div className="row">
          {dimensions.map((dim) => (
            <div key={dim.key} className="field grow">
              <label>{dim.label}</label>
              <select
                value={form.scores[dim.key] ?? defaultScore(dim)}
                onChange={onScore(dim.key)}
              >
                {scoreOptions(dim).map((n) => (
                  <option key={n} value={n}>{n}</option>
                ))}
              </select>
            </div>
          ))}
        </div>
      ) : (
        <p className="card-meta">No metrics configured for this subject. Ask staff to add them.</p>
      )}

      <div className="field">
        <label>Class notes</label>
        <textarea value={form.class_notes} onChange={onField('class_notes')} rows={3} />
      </div>

      <div className="form-actions">
        <button type="submit" disabled={!dimensions.length}>Save report</button>
        {onCancel && (
          <button type="button" className="secondary" onClick={onCancel}>Cancel</button>
        )}
      </div>
    </form>
  )
}
