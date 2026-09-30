import { useEffect, useMemo, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { apiFetch, getMe } from '../api.js'

function statusLabel(status) {
  if (status === 'completed') return 'Done'
  if (status === 'skipped') return 'Skipped'
  return 'Upcoming'
}

function statusClass(module) {
  if (module.status === 'completed') return 'done'
  if (module.is_current) return 'current'
  return 'upcoming'
}

export default function CurriculumPage() {
  const [me, setMe] = useState(null)
  const [enrollment, setEnrollment] = useState(undefined)
  const [templates, setTemplates] = useState([])
  const [supplementary, setSupplementary] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const load = () => {
    getMe()
      .then((profile) => {
        setMe(profile)
        const roles = profile.roles || []
        if (!roles.includes('student')) return
        return Promise.all([
          apiFetch('/api/curriculum/me/'),
          apiFetch('/api/curriculum/templates/'),
          apiFetch('/api/curriculum/me/supplementary/'),
        ]).then(([mine, templateRows, extraRows]) => {
          setEnrollment(mine.enrollment)
          setTemplates(templateRows)
          setSupplementary(extraRows)
        })
      })
      .catch((err) => setError(err.message))
  }

  useEffect(load, [])

  const pickTemplate = async (trackId) => {
    setError('')
    setMessage('')
    try {
      const result = await apiFetch('/api/curriculum/me/', {
        method: 'POST',
        body: JSON.stringify({ track_id: trackId }),
      })
      setEnrollment(result.enrollment)
      setSelectedId(null)
      setMessage('You are on this curriculum.')
    } catch (err) {
      setError(err.message)
    }
  }

  const modules = useMemo(() => enrollment?.track?.modules || [], [enrollment])
  const current = modules.find((module) => module.is_current) || modules[0] || null
  const selected = modules.find((module) => module.id === selectedId) || current
  const doneCount = modules.filter((module) => module.status === 'completed').length
  const percent = modules.length ? Math.round((doneCount / modules.length) * 100) : 0

  const roles = me?.roles || []
  const isStudent = roles.includes('student')
  const isTeacher = roles.includes('teacher')
  const isStaff = roles.includes('staff')

  if (me && !isStudent && isTeacher) {
    return <Navigate to="/teacher/curriculum" replace />
  }
  if (me && !isStudent && isStaff) {
    return <Navigate to="/staff/curriculum" replace />
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>My curriculum</h1>
          <p className="page-intro">
            Work through your path in order. Your teacher can skip a module or add extra practice.
          </p>
        </div>
      </div>

      {message && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}

      {enrollment && current && (
        <div className="hero-card">
          <div className="hero-body">
            <div className="hero-eyebrow">
              {doneCount ? 'Continue where you left off' : 'Start here'}
            </div>
            <div className="hero-title">
              {current.cefr_level && <><span className="badge">{current.cefr_level}</span>{' '}</>}
              {current.title}
            </div>
            <div className="card-meta">{enrollment.track.title}</div>
            <div className="progress-row" style={{ marginTop: '0.75rem' }}>
              <span className="progress">
                <span
                  className={`progress-fill${percent === 100 ? ' progress-fill--done' : ''}`}
                  style={{ width: `${percent}%` }}
                />
              </span>
              <span className="progress-value">{doneCount} of {modules.length} done</span>
            </div>
          </div>
          {selected?.id !== current.id && (
            <button type="button" onClick={() => setSelectedId(current.id)}>Open this module</button>
          )}
        </div>
      )}

      {enrollment && (
        <div className="course-layout">
          <aside className="card course-outline">
            <div className="section-head">
              <h3>{enrollment.track.title}</h3>
            </div>
            {enrollment.track.description && (
              <p className="card-meta">{enrollment.track.description}</p>
            )}
            <ol className="module-list">
              {modules.map((module, index) => (
                <li key={module.id}>
                  <button
                    type="button"
                    className={`module-item module-item--${statusClass(module)}${
                      selected?.id === module.id ? ' module-item--selected' : ''
                    }`}
                    onClick={() => setSelectedId(module.id)}
                  >
                    <span className={`status-dot status-dot--${statusClass(module)}`} aria-hidden="true" />
                    <span className="module-item-text">
                      <span className="module-title">{index + 1}. {module.title}</span>
                      <span className="card-meta">
                        {module.cefr_level ? `${module.cefr_level} · ` : ''}
                        {statusLabel(module.status)}
                        {module.is_current ? ' · Current' : ''}
                      </span>
                    </span>
                  </button>
                </li>
              ))}
            </ol>
            {!modules.length && <p className="empty">This path has no modules yet.</p>}
          </aside>

          <section className="card course-lesson">
            {selected ? (
              <>
                <div className="section-head">
                  <h2>{selected.title}</h2>
                  <span className={`badge${selected.status === 'completed' ? ' badge--success' : ''}`}>
                    {statusLabel(selected.status)}
                  </span>
                </div>
                {selected.cefr_level && (
                  <p className="card-meta">CEFR level {selected.cefr_level}</p>
                )}
                {selected.content
                  ? <p className="lesson-body">{selected.content}</p>
                  : <p className="card-meta">Your teacher will cover this in your next lesson.</p>}
              </>
            ) : (
              <p className="empty">Pick a module to see what it covers.</p>
            )}
          </section>
        </div>
      )}

      {supplementary.length > 0 && (
        <div className="card">
          <div className="section-head">
            <h2>Extra practice from your teacher</h2>
          </div>
          <p className="card-meta">Added alongside your main path to strengthen specific skills.</p>
          <ul className="module-list" style={{ marginTop: '0.75rem' }}>
            {supplementary.map((item) => (
              <li key={item.id} className="module-item">
                <span className="status-dot" aria-hidden="true" />
                <span className="module-item-text">
                  <span className="module-title">
                    {item.module?.cefr_level && <><span className="badge">{item.module.cefr_level}</span>{' '}</>}
                    {item.title}
                  </span>
                  {item.content && <span className="card-meta">{item.content}</span>}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {enrollment === null && (
        <>
          <div className="section-head">
            <h2>Choose a path</h2>
          </div>
          {!templates.length ? (
            <p className="empty">
              No premade curricula yet. Ask staff to publish one, or wait for your teacher to assign a custom plan.
            </p>
          ) : (
            <div className="course-grid">
              {templates.map((track) => (
                <div key={track.id} className="course-card">
                  <div className="course-card-title">{track.title}</div>
                  {track.description && <p className="card-meta">{track.description}</p>}
                  <div className="card-meta">{track.module_count} modules</div>
                  <div className="course-card-foot">
                    <button type="button" onClick={() => pickTemplate(track.id)}>Start this curriculum</button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {isStudent && enrollment && templates.length > 0 && (
        <p className="card-meta">
          Want a different path?{' '}
          <button
            type="button"
            className="ghost"
            onClick={() => {
              const track = templates.find((row) => row.id !== enrollment.track.id) || templates[0]
              if (track) pickTemplate(track.id)
            }}
          >
            Switch curriculum
          </button>
          {' '}or ask your teacher.
        </p>
      )}

      {!isStudent && !me && !error && <p className="page-intro">Loading…</p>}
    </div>
  )
}
