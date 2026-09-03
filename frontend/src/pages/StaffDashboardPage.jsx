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
  const [showAddTeacher, setShowAddTeacher] = useState(false)
  const [newTeacher, setNewTeacher] = useState({
    username: '',
    email: '',
    display_name: '',
    password: '',
  })
  const [creating, setCreating] = useState(false)
  const [resettingId, setResettingId] = useState(null)
  const [newPassword, setNewPassword] = useState('')

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

  const createTeacher = async (e) => {
    e.preventDefault()
    setError('')
    setMessage('')
    setCreating(true)
    try {
      const created = await apiFetch('/api/staff/teachers/', {
        method: 'POST',
        body: JSON.stringify(newTeacher),
      })
      setNewTeacher({ username: '', email: '', display_name: '', password: '' })
      setShowAddTeacher(false)
      setMessage(`${created.username} added. All ${label('teacher').toLowerCase()} permissions are enabled — adjust them under Permissions.`)
      load()
    } catch (err) {
      setError(err.message)
    } finally {
      setCreating(false)
    }
  }

  const resetPassword = async (e, teacher) => {
    e.preventDefault()
    setError('')
    setMessage('')
    try {
      const data = await apiFetch(`/api/staff/teachers/${teacher.id}/password/`, {
        method: 'POST',
        body: JSON.stringify({ password: newPassword }),
      })
      setResettingId(null)
      setNewPassword('')
      setMessage(data.detail)
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
        <div className="card-title">Curriculum templates</div>
        <p className="card-meta">
          Premade learning paths students can pick. Assign teachers to students so they can skip modules or build a custom path.
        </p>
        <Link to="/staff/curriculum" className="btn secondary">Manage curriculum</Link>
      </div>

      <div className="card">
        <div className="card-title">Create {label('class').toLowerCase()}</div>
        <p className="card-meta">Add a teachable {label('class').toLowerCase()} to any {label('teacher').toLowerCase()}&apos;s catalog.</p>
        <Link to="/staff/classes/new" className="btn">Create {label('class').toLowerCase()}</Link>
      </div>

      <div className="card">
        <div className="card-title">{labels('student')}</div>
        <p className="card-meta">
          Add accounts, grant memberships and tickets, cancel bookings, and reset passwords.
        </p>
        <Link to="/staff/students" className="btn secondary">Manage {labels('student').toLowerCase()}</Link>
      </div>

      <div className="card">
        <div className="card-title">Payments</div>
        <p className="card-meta">Whether Stripe is live or checkout is mocked, and the webhook URL to paste into Stripe.</p>
        <Link to="/staff/payments" className="btn secondary">View payment settings</Link>
      </div>

      <div className="card">
        <div className="card-title">Integrations</div>
        <p className="card-meta">
          Whether emails are really being delivered and which teachers have connected Google.
        </p>
        <Link to="/staff/integrations" className="btn secondary">View integrations</Link>
      </div>

      <div className="card">
        <div className="card-title">Pending class requests</div>
        <p className="card-meta">
          Every request across the {label('studio').toLowerCase()} waiting on approval.
        </p>
        <Link to="/staff/requests" className="btn secondary">Review requests</Link>
      </div>

      <div className="card">
        <div className="card-title">Staff activity</div>
        <p className="card-meta">Audit trail of every staff override — memberships, tickets, bookings, passwords.</p>
        <Link to="/staff/activity" className="btn secondary">View activity log</Link>
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

      <div className="card-row" style={{ marginTop: '1.5rem' }}>
        <h2>{labels('teacher')}</h2>
        <button
          type="button"
          className={showAddTeacher ? 'secondary' : ''}
          onClick={() => setShowAddTeacher((open) => !open)}
        >
          {showAddTeacher ? 'Cancel' : `Add ${label('teacher').toLowerCase()}`}
        </button>
      </div>

      {showAddTeacher && (
        <form onSubmit={createTeacher} className="card">
          <div className="card-title">New {label('teacher').toLowerCase()}</div>
          <p className="card-meta">
            Share these credentials with them; they can change the password under Account.
          </p>
          <div className="row">
            <div className="field grow">
              <label>Username</label>
              <input
                value={newTeacher.username}
                onChange={(e) => setNewTeacher({ ...newTeacher, username: e.target.value })}
                autoComplete="off"
                required
              />
            </div>
            <div className="field grow">
              <label>Email (optional)</label>
              <input
                type="email"
                value={newTeacher.email}
                onChange={(e) => setNewTeacher({ ...newTeacher, email: e.target.value })}
                autoComplete="off"
              />
            </div>
          </div>
          <div className="row">
            <div className="field grow">
              <label>Display name (optional)</label>
              <input
                value={newTeacher.display_name}
                onChange={(e) => setNewTeacher({ ...newTeacher, display_name: e.target.value })}
              />
            </div>
            <div className="field grow">
              <label>Temporary password</label>
              <input
                type="password"
                value={newTeacher.password}
                onChange={(e) => setNewTeacher({ ...newTeacher, password: e.target.value })}
                autoComplete="new-password"
                required
              />
            </div>
          </div>
          <button type="submit" disabled={creating}>
            {creating ? 'Creating…' : `Create ${label('teacher').toLowerCase()}`}
          </button>
        </form>
      )}

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
                className="ghost"
                onClick={() => {
                  setResettingId(resettingId === teacher.id ? null : teacher.id)
                  setNewPassword('')
                }}
              >
                Reset password
              </button>
              <button
                type="button"
                className={teacher.is_active ? 'danger' : 'secondary'}
                onClick={() => toggleActive(teacher)}
              >
                {teacher.is_active ? 'Deactivate' : 'Activate'}
              </button>
            </div>
          </div>
          {resettingId === teacher.id && (
            <form onSubmit={(e) => resetPassword(e, teacher)} className="row">
              <div className="field grow">
                <label>Temporary password for {teacher.username}</label>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  autoComplete="new-password"
                  required
                />
              </div>
              <div className="field" style={{ alignSelf: 'end' }}>
                <button type="submit">Set password</button>
              </div>
              <div className="field" style={{ alignSelf: 'end' }}>
                <button type="button" className="secondary" onClick={() => setResettingId(null)}>
                  Cancel
                </button>
              </div>
            </form>
          )}
        </div>
      ))}
      {!teachers.length && !error && (
        <p className="card-meta">
          No {labels('teacher').toLowerCase()} yet. Use <strong>Add {label('teacher').toLowerCase()}</strong> above to create one.
        </p>
      )}
    </div>
  )
}
