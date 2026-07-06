import { useEffect, useMemo, useState } from 'react'
import { apiFetch } from '../api.js'
import StudentHistoryPanel from '../components/StudentHistoryPanel.jsx'
import { useScoreDimensions, scoreValue, emptyScores, scoreOptions, defaultScore } from '../hooks/useScoreDimensions.js'
import { useTeacherScope } from '../hooks/useTeacherScope.js'
import { useTeacherPermissions } from '../hooks/useTeacherPermissions.js'

export default function TeacherProgressPage() {
  const { isStaff, paths } = useTeacherScope()
  const { can } = useTeacherPermissions()
  const [feedback, setFeedback] = useState([])
  const [students, setStudents] = useState([])
  const [sessions, setSessions] = useState([])
  const [form, setForm] = useState({ student: '', session: '', scores: {}, class_notes: '' })
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [editingId, setEditingId] = useState(null)
  const [editForm, setEditForm] = useState(null)
  const canEdit = isStaff || can('write_reports')
  const [aiAvailable, setAiAvailable] = useState(false)
  const [aiLoading, setAiLoading] = useState(false)

  const selectedSession = useMemo(
    () => sessions.find((s) => String(s.id) === form.session),
    [sessions, form.session],
  )
  const formSubject = selectedSession?.class_subject || ''
  const dimensions = useScoreDimensions(formSubject)

  const load = () => {
    Promise.all([
      apiFetch(paths.feedback),
      apiFetch(paths.students),
      apiFetch(paths.sessions),
    ])
      .then(([feedbackData, studentData, sessionData]) => {
        setFeedback(feedbackData)
        setStudents(studentData)
        setSessions(sessionData)
      })
      .catch((err) => setError(err.message))
  }

  useEffect(load, [paths.feedback, paths.students, paths.sessions])

  useEffect(() => {
    apiFetch('/api/teacher/ai/status/')
      .then((data) => setAiAvailable(Boolean(data.available)))
      .catch(() => setAiAvailable(false))
  }, [])

  useEffect(() => {
    setForm((f) => ({ ...f, scores: emptyScores(dimensions) }))
  }, [formSubject, dimensions.length])

  const onField = (key) => (e) => setForm({ ...form, [key]: e.target.value })
  const onScore = (key) => (e) => setForm({
    ...form,
    scores: { ...form.scores, [key]: Number(e.target.value) },
  })

  const sessionLabel = (session) => {
    const when = session.start_time
      ? new Date(session.start_time).toLocaleString(undefined, {
          month: 'short',
          day: 'numeric',
          hour: 'numeric',
          minute: '2-digit',
        })
      : ''
    return when ? `${session.title} — ${when}` : session.title
  }

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setMessage('')
    if (!form.student) {
      setError('Please choose a student.')
      return
    }
    try {
      const payload = {
        student: Number(form.student),
        class_notes: form.class_notes,
        scores: form.scores,
      }
      if (form.session) payload.session = Number(form.session)
      await apiFetch(paths.feedback, {
        method: 'POST',
        body: JSON.stringify(payload),
      })
      setMessage('Feedback saved.')
      setForm({ ...form, class_notes: '' })
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  const startEdit = (item) => {
    setEditingId(item.id)
    setEditForm({
      scores: { ...(item.scores || {}) },
      class_notes: item.class_notes || '',
      subject: item.session_subject || '',
    })
  }

  const saveEdit = async (e) => {
    e.preventDefault()
    setError('')
    setMessage('')
    try {
      await apiFetch(paths.feedbackDetail(editingId), {
        method: 'PATCH',
        body: JSON.stringify({
          class_notes: editForm.class_notes,
          scores: editForm.scores,
        }),
      })
      setEditingId(null)
      setMessage('Feedback updated.')
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  const removeFeedback = async (id) => {
    if (!window.confirm('Delete this feedback report?')) return
    setError('')
    try {
      await apiFetch(paths.feedbackDetail(id), { method: 'DELETE' })
      setMessage('Feedback deleted.')
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  const suggestNotes = async () => {
    if (!form.student) {
      setError('Choose a student first.')
      return
    }
    setAiLoading(true)
    setError('')
    try {
      const metricLabels = Object.fromEntries(dimensions.map((d) => [d.key, d.label]))
      const result = await apiFetch('/api/teacher/ai/suggest-feedback/', {
        method: 'POST',
        body: JSON.stringify({
          student: Number(form.student),
          session: form.session ? Number(form.session) : undefined,
          scores: form.scores,
          metric_labels: metricLabels,
        }),
      })
      setForm({ ...form, class_notes: result.suggestion })
      setMessage('AI draft added — review and edit before saving.')
    } catch (err) {
      setError(err.message)
    } finally {
      setAiLoading(false)
    }
  }

  return (
    <div>
      {!isStaff && <h1>Student progress</h1>}
      <p className="page-intro">Rate each skill after a session; students see the trends.</p>
      {message && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}

      {canEdit ? (
      <form onSubmit={submit} className="card">
        <h2>New session feedback</h2>
        {formSubject && <p className="card-meta">Metrics for {formSubject}</p>}
        <div className="row">
          <div className="field grow">
            <label>Student</label>
            <select value={form.student} onChange={onField('student')} required>
              <option value="">Choose a student…</option>
              {students.map((student) => (
                <option key={student.id} value={student.id}>
                  {student.label}
                </option>
              ))}
            </select>
          </div>
          <div className="field grow">
            <label>Session (optional)</label>
            <select value={form.session} onChange={onField('session')}>
              <option value="">No session linked</option>
              {sessions.map((session) => (
                <option key={session.id} value={session.id}>
                  {sessionLabel(session)}
                </option>
              ))}
            </select>
          </div>
        </div>
        {dimensions.length > 0 ? (
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
          <p className="card-meta">Pick a session or ask staff to configure metrics for this subject.</p>
        )}
        <div className="field">
          <label>Class notes</label>
          <textarea value={form.class_notes} onChange={onField('class_notes')} rows={3} />
          {aiAvailable && (
            <div className="form-actions" style={{ marginTop: '0.5rem' }}>
              <button
                type="button"
                className="secondary"
                onClick={suggestNotes}
                disabled={aiLoading || !form.student}
              >
                {aiLoading ? 'Drafting…' : 'Suggest notes with AI'}
              </button>
            </div>
          )}
        </div>
        <div className="form-actions">
          <button type="submit" disabled={!dimensions.length}>Save feedback</button>
        </div>
      </form>
      ) : (
        <div className="card card-meta">You do not have permission to write reports. Contact staff.</div>
      )}

      <StudentHistoryPanel />

      {feedback.map((f) => (
        <FeedbackCard
          key={f.id}
          item={f}
          editing={editingId === f.id}
          editForm={editForm}
          canEdit={canEdit}
          onStartEdit={() => startEdit(f)}
          onCancelEdit={() => setEditingId(null)}
          onSaveEdit={saveEdit}
          onDelete={() => removeFeedback(f.id)}
          onEditScore={(key, value) => setEditForm({
            ...editForm,
            scores: { ...editForm.scores, [key]: Number(value) },
          })}
          onEditNotes={(value) => setEditForm({ ...editForm, class_notes: value })}
        />
      ))}
      {!feedback.length && !error && <div className="empty">No feedback recorded yet.</div>}
    </div>
  )
}

function FeedbackCard({
  item,
  editing,
  editForm,
  canEdit,
  onStartEdit,
  onCancelEdit,
  onSaveEdit,
  onDelete,
  onEditScore,
  onEditNotes,
}) {
  const editSubject = editForm?.subject || ''
  const itemSubject = item.session_subject || ''
  const editDimensions = useScoreDimensions(editSubject)
  const displayDimensions = useScoreDimensions(itemSubject)

  if (editing && editForm) {
    return (
      <div className="card">
        <form onSubmit={onSaveEdit}>
          <div className="card-title">{item.student_name}</div>
          <div className="row">
            {editDimensions.map((dim) => (
              <div key={dim.key} className="field grow">
                <label>{dim.label}</label>
                <select
                  value={editForm.scores[dim.key] ?? dim.min_score ?? 0}
                  onChange={(e) => onEditScore(dim.key, e.target.value)}
                >
                  {scoreOptions(dim).map((n) => (
                    <option key={n} value={n}>{n}</option>
                  ))}
                </select>
              </div>
            ))}
          </div>
          <div className="field">
            <label>Class notes</label>
            <textarea
              value={editForm.class_notes}
              onChange={(e) => onEditNotes(e.target.value)}
              rows={3}
            />
          </div>
          <div className="row-actions">
            <button type="submit">Save</button>
            <button type="button" className="secondary" onClick={onCancelEdit}>Cancel</button>
          </div>
        </form>
      </div>
    )
  }

  return (
    <div className="card">
      <div className="card-row">
        <div>
          <div className="card-title">{item.student_name}</div>
          <div className="card-meta">
            {item.session_title || 'No session'}
            {item.session_start_time ? ` · ${new Date(item.session_start_time).toLocaleDateString()}` : ''}
            {item.session_subject ? ` · ${item.session_subject}` : ''}
          </div>
        </div>
        <div className="card-meta">
          {displayDimensions.map((d) => `${d.label[0]}${scoreValue(item, d)}`).join(' · ')}
        </div>
      </div>
      {item.class_notes && <div className="card-meta" style={{ marginTop: '0.4rem' }}>{item.class_notes}</div>}
      {canEdit && (
        <div className="row-actions" style={{ marginTop: '0.75rem' }}>
          <button type="button" className="secondary" onClick={onStartEdit}>Edit</button>
          <button type="button" className="danger" onClick={onDelete}>Delete</button>
        </div>
      )}
    </div>
  )
}
