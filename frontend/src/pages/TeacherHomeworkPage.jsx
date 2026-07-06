import { useEffect, useState } from 'react'
import { apiFetch, apiUpload } from '../api.js'
import HomeworkThread from '../components/HomeworkThread.jsx'
import { useTeacherScope } from '../hooks/useTeacherScope.js'
import { useTeacherPermissions } from '../hooks/useTeacherPermissions.js'
import { homeworkFileHint, useUploadLimits } from '../hooks/useUploadLimits.js'

function sessionLabel(session) {
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

export default function TeacherHomeworkPage() {
  const { isStaff, paths } = useTeacherScope()
  const { can } = useTeacherPermissions()
  const canAssign = isStaff || can('assign_homework')
  const limits = useUploadLimits()
  const fileHint = homeworkFileHint(limits)

  const [assignments, setAssignments] = useState([])
  const [students, setStudents] = useState([])
  const [sessions, setSessions] = useState([])
  const [selected, setSelected] = useState(null)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState({
    student: '',
    session: '',
    kind: 'file',
    title: '',
    prompt: '',
    file: null,
  })

  const loadList = () => {
    Promise.all([
      apiFetch(paths.homework),
      apiFetch(paths.students),
    ])
      .then(([rows, studentRows]) => {
        setAssignments(rows)
        setStudents(studentRows)
      })
      .catch((err) => setError(err.message))
  }

  useEffect(loadList, [paths.homework, paths.students])

  useEffect(() => {
    if (!form.student) {
      setSessions([])
      setForm((f) => ({ ...f, session: '' }))
      return undefined
    }
    const qs = `?student=${encodeURIComponent(form.student)}`
    apiFetch(`${paths.sessions}${qs}`)
      .then(setSessions)
      .catch(() => setSessions([]))
  }, [form.student, paths.sessions])

  const open = async (id) => {
    setError('')
    try {
      const detail = await apiFetch(paths.homeworkDetail(id))
      setSelected(detail)
    } catch (err) {
      setError(err.message)
    }
  }

  const onUpdated = (updated) => {
    setSelected(updated)
    loadList()
  }

  const create = async (e) => {
    e.preventDefault()
    if (!canAssign) return
    setSaving(true)
    setError('')
    setMessage('')
    try {
      const data = new FormData()
      data.append('student', form.student)
      data.append('session', form.session)
      data.append('kind', form.kind)
      if (form.title.trim()) data.append('title', form.title.trim())
      if (form.prompt.trim()) data.append('prompt', form.prompt.trim())
      if (form.file && form.kind === 'file') data.append('attachment', form.file)
      const created = await apiUpload(paths.homework, data)
      setMessage('Homework sent.')
      setForm({ student: '', session: '', kind: 'file', title: '', prompt: '', file: null })
      loadList()
      setSelected(created)
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <h1>Homework</h1>
      <p className="page-intro">
        Assign homework tied to a session the student attended. Files expire after 7 days;
        journal prompts stay open for ongoing reflection.
      </p>
      {message && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}

      {canAssign && (
        <form onSubmit={create} className="card" style={{ marginBottom: '1rem' }}>
          <h2>New homework</h2>
          <div className="field">
            <label>Student</label>
            <select
              value={form.student}
              onChange={(e) => setForm({ ...form, student: e.target.value, session: '' })}
              required
            >
              <option value="">Choose a student…</option>
              {students.map((s) => (
                <option key={s.id} value={s.id}>{s.label || s.username}</option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Session</label>
            <select
              value={form.session}
              onChange={(e) => setForm({ ...form, session: e.target.value })}
              required
              disabled={!form.student}
            >
              <option value="">Choose a booked session…</option>
              {sessions.map((s) => (
                <option key={s.id} value={s.id}>{sessionLabel(s)}</option>
              ))}
            </select>
            {form.student && !sessions.length && (
              <p className="card-meta">No booked sessions for this student.</p>
            )}
          </div>
          <div className="field">
            <label>Type</label>
            <select
              value={form.kind}
              onChange={(e) => setForm({ ...form, kind: e.target.value, file: null })}
            >
              <option value="file">File exchange (7-day files)</option>
              <option value="journal">Journal prompt (text only)</option>
            </select>
          </div>
          <div className="field">
            <label>Title (optional)</label>
            <input
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
              placeholder="e.g. Week 3 practice"
            />
          </div>
          <div className="field">
            <label>{form.kind === 'journal' ? 'Journal prompt' : 'Message'}</label>
            <textarea
              value={form.prompt}
              onChange={(e) => setForm({ ...form, prompt: e.target.value })}
              rows={4}
              placeholder={
                form.kind === 'journal'
                  ? 'What should the student reflect on after this session?'
                  : 'Instructions for the student…'
              }
              required={form.kind === 'journal'}
            />
          </div>
          {form.kind === 'file' && (
            <div className="field">
              <label>Attach file (optional)</label>
              <input
                type="file"
                onChange={(e) => setForm({ ...form, file: e.target.files?.[0] || null })}
              />
              {fileHint && <p className="card-meta">{fileHint}</p>}
            </div>
          )}
          <button type="submit" disabled={saving || !form.session}>
            {saving ? 'Sending…' : 'Send homework'}
          </button>
        </form>
      )}

      <div className="homework-layout">
        <div>
          <h2>Sent homework</h2>
          {assignments.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`card homework-list-card${selected?.id === item.id ? ' homework-list-card--active' : ''}`}
              onClick={() => open(item.id)}
            >
              <div className="card-title">
                {item.title || (item.kind === 'journal' ? 'Journal prompt' : 'File exchange')}
              </div>
              <div className="card-meta">
                {item.student_name}
                {item.session_title && <> · {item.session_title}</>}
                {' · '}
                {item.kind === 'journal' ? 'Journal' : 'Files'}
                {' · '}
                {item.entry_count} message{item.entry_count === 1 ? '' : 's'}
              </div>
            </button>
          ))}
          {!assignments.length && <p className="card-meta">No homework sent yet.</p>}
        </div>

        <HomeworkThread
          assignment={selected}
          onUpdated={onUpdated}
          postPath={selected ? paths.homeworkEntry(selected.id) : ''}
          canReply={canAssign}
          replyLabel="Reply"
        />
      </div>
    </div>
  )
}
