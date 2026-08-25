import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch } from '../api.js'
import { useGlossary } from '../hooks/useGlossary.jsx'

function formatRelativeTime(iso) {
  if (!iso) return ''
  const then = new Date(iso).getTime()
  const diffMs = Date.now() - then
  const minutes = Math.round(diffMs / 60000)
  if (minutes < 1) return 'just now'
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.round(hours / 24)
  if (days < 14) return `${days}d ago`
  return new Date(iso).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
  })
}

function AlertSection({ title, emptyLabel, items, seeAllTo }) {
  return (
    <div className="card staff-alerts-panel">
      <div className="card-row">
        <div className="card-title">{title}</div>
        {seeAllTo && (
          <Link to={seeAllTo} className="card-meta">
            View all
          </Link>
        )}
      </div>
      {items.length === 0 ? (
        <p className="card-meta">{emptyLabel}</p>
      ) : (
        <ul className="staff-alerts-list">
          {items.map((alert) => (
            <li
              key={alert.id}
              className={`staff-alert-item${alert.is_unread ? ' staff-alert-item--unread' : ''}`}
            >
              <div className="staff-alert-item-main">
                <span className="staff-alert-title">{alert.title}</span>
                {alert.is_unread && <span className="badge badge--success">New</span>}
              </div>
              {alert.body && <div className="card-meta">{alert.body}</div>}
              <div className="card-meta">{formatRelativeTime(alert.created_at)}</div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export default function StaffDashboardPage() {
  const { label, labels } = useGlossary()
  const [teachers, setTeachers] = useState([])
  const [alerts, setAlerts] = useState(null)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [markingRead, setMarkingRead] = useState(false)

  const load = () => {
    Promise.all([
      apiFetch('/api/staff/teachers/'),
      apiFetch('/api/staff/alerts/?limit=10'),
    ])
      .then(([teacherList, alertData]) => {
        setTeachers(teacherList)
        setAlerts(alertData)
      })
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

  const markAllRead = async () => {
    setError('')
    setMessage('')
    setMarkingRead(true)
    try {
      const data = await apiFetch('/api/staff/alerts/mark-read/', {
        method: 'POST',
        body: JSON.stringify({ all: true }),
      })
      setAlerts(data)
      setMessage('All alerts marked as read.')
    } catch (err) {
      setError(err.message)
    } finally {
      setMarkingRead(false)
    }
  }

  const unreadTotal = alerts?.unread?.total || 0

  return (
    <div>
      <h1>Staff dashboard</h1>
      <p className="page-intro">
        Manage {labels('teacher').toLowerCase()}, schedules, {labels('class').toLowerCase()}, and {label('studio').toLowerCase()}-wide settings.
      </p>
      {message && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}

      <section className="staff-alerts">
        <div className="card-row staff-alerts-header">
          <h2>
            Alerts
            {unreadTotal > 0 && (
              <span className="badge badge--success staff-alerts-count">{unreadTotal}</span>
            )}
          </h2>
          <button
            type="button"
            className="secondary"
            disabled={markingRead || unreadTotal === 0}
            onClick={markAllRead}
          >
            {markingRead ? 'Marking…' : 'Mark all read'}
          </button>
        </div>
        <div className="staff-alerts-grid">
          <AlertSection
            title="New students"
            emptyLabel="No recent signups."
            items={alerts?.users || []}
            seeAllTo="/staff/students"
          />
          <AlertSection
            title="Membership"
            emptyLabel="No recent membership changes."
            items={alerts?.membership || []}
            seeAllTo="/staff/memberships"
          />
          <AlertSection
            title="Payments"
            emptyLabel="No recent payments."
            items={alerts?.financial || []}
            seeAllTo="/staff/reports"
          />
        </div>
      </section>

      <div className="card">
        <div className="card-title">{label('studio')} schedule</div>
        <p className="card-meta">See every {label('teacher').toLowerCase()}&apos;s {labels('session').toLowerCase()} on one calendar.</p>
        <Link to="/staff/schedule" className="btn">View overall schedule</Link>
      </div>

      <div className="card">
        <div className="card-title">Class roadmap</div>
        <p className="card-meta">Subjects, levels, focuses, and topics teachers pick when creating {labels('class').toLowerCase()}.</p>
        <Link to="/staff/class-catalog" className="btn secondary">Manage roadmap</Link>
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
