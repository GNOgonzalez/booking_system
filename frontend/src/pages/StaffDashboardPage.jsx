import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch } from '../api.js'
import { useGlossary } from '../hooks/useGlossary.jsx'

export default function StaffDashboardPage() {
  const { label, labels } = useGlossary()
  const [teachers, setTeachers] = useState([])
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const load = () => {
    apiFetch('/api/staff/teachers/')
      .then(setTeachers)
      .catch((err) => setError(err.message))
  }

  useEffect(load, [])

  const toggleActive = async (teacher) => {
    setError('')
    setMessage('')
    try {
      await apiFetch(`/api/staff/teachers/${teacher.id}/`, {
        method: 'PATCH',
        body: JSON.stringify({ is_active: !teacher.is_active }),
      })
      setMessage(`${teacher.username} marked ${teacher.is_active ? 'inactive' : 'active'}.`)
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div>
      <h1>Staff dashboard</h1>
      <p className="page-intro">
        Manage {labels('teacher').toLowerCase()}, schedules, {labels('class').toLowerCase()}, and {label('studio').toLowerCase()}-wide settings.
      </p>
      {message && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}

      <div className="card">
        <div className="card-title">{label('studio')} schedule</div>
        <p className="card-meta">See every {label('teacher').toLowerCase()}&apos;s {labels('session').toLowerCase()} on one calendar.</p>
        <Link to="/staff/schedule" className="btn">View overall schedule</Link>
      </div>

      <div className="card">
        <div className="card-title">Create {label('class').toLowerCase()}</div>
        <p className="card-meta">Add a teachable {label('class').toLowerCase()} to any {label('teacher').toLowerCase()}&apos;s catalog.</p>
        <Link to="/staff/classes/new" className="btn">Create {label('class').toLowerCase()}</Link>
      </div>

      <div className="card">
        <div className="card-title">{labels('student')}</div>
        <p className="card-meta">Activate or deactivate {label('student').toLowerCase()} accounts.</p>
        <Link to="/staff/students" className="btn secondary">Manage {labels('student').toLowerCase()}</Link>
      </div>

      <div className="card">
        <div className="card-title">Blog posts</div>
        <p className="card-meta">Publish announcements and photos on the home page for everyone to see.</p>
        <Link to="/blog/manage" className="btn secondary">Manage blog</Link>
      </div>

      <div className="card">
        <div className="card-title">Reports</div>
        <p className="card-meta">Financials, bookings, teacher activity, and student stats.</p>
        <Link to="/staff/reports" className="btn">View reports</Link>
      </div>

      <div className="card">
        <div className="card-title">Memberships</div>
        <p className="card-meta">Create plans, set prices, and choose which {labels('class').toLowerCase()} each tier includes.</p>
        <Link to="/staff/memberships" className="btn secondary">Manage memberships</Link>
      </div>

      <div className="card">
        <div className="card-title">Sign-in branding</div>
        <p className="card-meta">Customize the app name and logo on the sign-in screen and sidebar.</p>
        <Link to="/staff/branding" className="btn secondary">Edit branding</Link>
      </div>

      <div className="card">
        <div className="card-title">Glossary</div>
        <p className="card-meta">Rename {labels('student').toLowerCase()}, {labels('class').toLowerCase()}, {labels('session').toLowerCase()}, and other terms.</p>
        <Link to="/staff/glossary" className="btn secondary">Edit glossary</Link>
      </div>

      <div className="card">
        <div className="card-title">{label('studio')} settings</div>
        <p className="card-meta">Rename progress {labels('metric').toLowerCase()} and other labels used across the app.</p>
        <Link to="/staff/metrics" className="btn secondary">Edit metric names</Link>
      </div>

      <div className="card">
        <div className="card-title">AI assistant</div>
        <p className="card-meta">
          Connect OpenAI, Anthropic, Ollama, or a compatible API. Grant <strong>Use AI</strong> per teacher under Permissions.
        </p>
        <Link to="/staff/ai" className="btn secondary">Configure AI</Link>
      </div>

      <h2 style={{ marginTop: '1.5rem' }}>{labels('teacher')}</h2>
      {teachers.map((teacher) => (
        <div key={teacher.id} className={`card staff-teacher-card${teacher.is_active ? '' : ' card--inactive'}`}>
          <div className="card-row">
            <div>
              <div className="card-title">
                {teacher.label}
                {!teacher.is_active && <span className="badge badge--muted">Inactive</span>}
              </div>
              <div className="card-meta">{teacher.email || teacher.username}</div>
            </div>
            <div className="staff-teacher-actions">
              <Link to={`/staff/teachers/${teacher.id}/sessions`} className="btn">
                Manage schedule
              </Link>
              <Link to={`/staff/teachers/${teacher.id}/permissions`} className="btn secondary">
                Permissions
              </Link>
              <button
                type="button"
                className={teacher.is_active ? 'danger' : 'secondary'}
                onClick={() => toggleActive(teacher)}
              >
                {teacher.is_active ? 'Deactivate' : 'Activate'}
              </button>
            </div>
          </div>
        </div>
      ))}
      {!teachers.length && !error && (
        <p className="card-meta">No teachers found. Create a user in the teacher group via Django admin.</p>
      )}
    </div>
  )
}
