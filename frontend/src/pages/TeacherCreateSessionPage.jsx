import { useEffect, useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { apiFetch } from '../api.js'
import { useTeacherScope } from '../hooks/useTeacherScope.js'
import { useTeacherPermissions } from '../hooks/useTeacherPermissions.js'

function formatTopics(item) {
  const titles = (item.topics || []).map((topic) => topic.title).filter(Boolean)
  if (!titles.length) return '—'
  const suffix = item.topics_ordered ? ' (in order)' : ''
  return `${titles.join(' · ')}${suffix}`
}

export default function TeacherCreateSessionPage() {
  const navigate = useNavigate()
  const { isStaff, paths } = useTeacherScope()
  const { can } = useTeacherPermissions()
  const [classes, setClasses] = useState([])
  const [classOffering, setClassOffering] = useState('')
  const [classTopicId, setClassTopicId] = useState('')
  const [start, setStart] = useState('')
  const [end, setEnd] = useState('')
  const [capacity, setCapacity] = useState('')
  const [meetingProvider, setMeetingProvider] = useState('google_meet')
  const [error, setError] = useState('')
  const [loadingClasses, setLoadingClasses] = useState(true)

  useEffect(() => {
    apiFetch(paths.classes)
      .then((rows) => {
        const active = rows.filter((c) => c.is_active)
        setClasses(active)
        if (active.length === 1) {
          setClassOffering(String(active[0].id))
          setCapacity(String(active[0].default_capacity))
          const firstTopic = active[0].topics?.[0]
          setClassTopicId(firstTopic ? String(firstTopic.id) : '')
        }
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoadingClasses(false))
  }, [paths.classes])

  const onClassChange = (e) => {
    const id = e.target.value
    setClassOffering(id)
    const picked = classes.find((c) => String(c.id) === id)
    if (picked) {
      setCapacity(String(picked.default_capacity))
      const firstTopic = picked.topics?.[0]
      setClassTopicId(firstTopic ? String(firstTopic.id) : '')
    } else {
      setClassTopicId('')
    }
  }

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    if (!classOffering) {
      setError('Choose a class from the catalog.')
      return
    }
    try {
      await apiFetch(paths.sessions, {
        method: 'POST',
        body: JSON.stringify({
          class_offering: Number(classOffering),
          class_topic_id: classTopicId ? Number(classTopicId) : null,
          start_time: start,
          end_time: end,
          capacity: capacity ? Number(capacity) : undefined,
          meeting_provider: meetingProvider,
        }),
      })
      navigate(paths.staffTeacherSessions)
    } catch (err) {
      setError(err.message)
    }
  }

  const selected = classes.find((c) => String(c.id) === classOffering)
  const classesLink = isStaff ? `${paths.staffTeacherSessions.replace('/sessions', '/classes')}` : '/teacher/classes'

  if (!isStaff && !can('manage_schedule')) {
    return <Navigate to={paths.staffTeacherSessions || '/teacher/sessions'} replace />
  }

  return (
    <div>
      <h1>Create session</h1>
      <p className="page-intro">
        Pick a class from the catalog. Optionally choose which topic this session covers.
      </p>
      {error && <div className="error">{error}</div>}
      <form onSubmit={submit} className="card">
        <div className="field">
          <label>Class</label>
          <select
            value={classOffering}
            onChange={onClassChange}
            required
            disabled={loadingClasses}
          >
            <option value="">
              {loadingClasses ? 'Loading classes…' : 'Choose a class…'}
            </option>
            {classes.map((item) => (
              <option key={item.id} value={item.id}>{item.label}</option>
            ))}
          </select>
          {!loadingClasses && classes.length === 0 && (
            <p className="card-meta">
              No classes in catalog yet. <Link to={classesLink}>Add classes first</Link>.
            </p>
          )}
        </div>

        {selected && (
          <>
            <dl className="class-catalog-meta class-catalog-meta--compact">
              <div><dt>Subject</dt><dd>{selected.subject}</dd></div>
              <div><dt>Level</dt><dd>{selected.level}</dd></div>
              <div><dt>Focus</dt><dd>{selected.focus}</dd></div>
              <div><dt>Topics</dt><dd>{formatTopics(selected)}</dd></div>
            </dl>
            {selected.topics?.length > 0 && (
              <div className="field">
                <label>Topic for this session</label>
                <select value={classTopicId} onChange={(e) => setClassTopicId(e.target.value)}>
                  <option value="">General / no specific topic</option>
                  {selected.topics.map((topic) => (
                    <option key={topic.id} value={topic.id}>{topic.title}</option>
                  ))}
                </select>
              </div>
            )}
          </>
        )}

        <div className="field">
          <label>Start</label>
          <input type="datetime-local" value={start} onChange={(e) => setStart(e.target.value)} required />
        </div>
        <div className="field">
          <label>End</label>
          <input type="datetime-local" value={end} onChange={(e) => setEnd(e.target.value)} required />
        </div>
        <div className="field" style={{ maxWidth: '8rem' }}>
          <label>Capacity</label>
          <input type="number" min="1" value={capacity} onChange={(e) => setCapacity(e.target.value)} />
        </div>
        <div className="field">
          <label>Video link</label>
          <select value={meetingProvider} onChange={(e) => setMeetingProvider(e.target.value)}>
            <option value="none">No video link</option>
            <option value="google_meet">Google Meet</option>
            <option value="zoom">Zoom</option>
          </select>
          <p className="card-meta">
            A join link is generated automatically. Real Google or Zoom APIs activate when credentials are set in <code>.env</code>.
          </p>
        </div>
        <button type="submit" disabled={!classes.length}>Create session</button>
      </form>
    </div>
  )
}
