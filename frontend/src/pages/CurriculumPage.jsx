import { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { apiFetch, getMe } from '../api.js'

function statusLabel(status) {
  if (status === 'completed') return 'Done'
  if (status === 'skipped') return 'Skipped'
  return 'Upcoming'
}

export default function CurriculumPage() {
  const [me, setMe] = useState(null)
  const [enrollment, setEnrollment] = useState(undefined)
  const [templates, setTemplates] = useState([])
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
        ]).then(([mine, templateRows]) => {
          setEnrollment(mine.enrollment)
          setTemplates(templateRows)
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
      setMessage('You are on this curriculum.')
    } catch (err) {
      setError(err.message)
    }
  }

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

  const modules = enrollment?.track?.modules || []

  return (
    <div>
      <h1>Curriculum</h1>
      <p className="page-intro">
        Follow a studio path in order. Your teacher can skip a module or assign a custom plan.
      </p>
      {message && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}

      {enrollment && (
        <div className="card">
          <div className="card-title">{enrollment.track.title}</div>
          {enrollment.track.description && <p className="card-meta">{enrollment.track.description}</p>}
          {modules.map((module) => (
            <div
              key={module.id}
              className={`card${module.is_current ? ' curriculum-module--current' : ''}`}
            >
              <div className="card-title">{module.title}</div>
              <div className="card-meta">
                {statusLabel(module.status)}
                {module.is_current ? ' · Current' : ''}
              </div>
              {module.content && <p>{module.content}</p>}
            </div>
          ))}
        </div>
      )}

      {enrollment === null && (
        <>
          <h2>Choose a path</h2>
          {!templates.length && (
            <p className="empty">
              No premade curricula yet. Ask staff to publish one, or wait for your teacher to assign a custom plan.
            </p>
          )}
          {templates.map((track) => (
            <div key={track.id} className="card">
              <div className="card-title">{track.title}</div>
              {track.description && <p className="card-meta">{track.description}</p>}
              <div className="card-meta">{track.module_count} modules</div>
              <button type="button" onClick={() => pickTemplate(track.id)}>Start this curriculum</button>
            </div>
          ))}
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
