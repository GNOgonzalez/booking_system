import { useEffect, useState } from 'react'
import { NavLink } from 'react-router-dom'
import { apiFetch } from '../api.js'
import { useGlossary } from '../hooks/useGlossary.jsx'

function formatTimeLeft(validUntil) {
  if (!validUntil) return { label: 'No end date', detail: null }
  const end = new Date(`${validUntil}T23:59:59`)
  const now = new Date()
  const ms = end.getTime() - now.getTime()
  const days = Math.ceil(ms / (1000 * 60 * 60 * 24))
  if (days < 0) return { label: 'Expired', detail: `Ended ${validUntil}` }
  if (days === 0) return { label: 'Expires today', detail: validUntil }
  if (days === 1) return { label: '1 day left', detail: `Until ${validUntil}` }
  return { label: `${days} days left`, detail: `Until ${validUntil}` }
}

function formatLessonTime(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString(undefined, {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

function activeMemberships(data) {
  if (!data?.active) return []
  return data.memberships?.length ? data.memberships : [data]
}

export default function StudentHomeDashboard() {
  const { labels } = useGlossary()
  const [homeData, setHomeData] = useState(null)
  const [membershipData, setMembershipData] = useState(null)
  const [enrollment, setEnrollment] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      apiFetch('/api/student/home/'),
      apiFetch('/api/membership/'),
      apiFetch('/api/curriculum/me/').catch(() => null),
    ])
      .then(([home, membership, curriculum]) => {
        setHomeData(home)
        setMembershipData(membership)
        setEnrollment(curriculum?.enrollment || null)
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  const memberships = activeMemberships(membershipData)
  const totalTickets = membershipData?.tickets_remaining ?? homeData?.tickets_remaining ?? 0
  const nextLesson = homeData?.next_lesson
  const modules = enrollment?.track?.modules || []
  const doneCount = modules.filter((module) => module.status === 'completed').length
  const percent = modules.length ? Math.round((doneCount / modules.length) * 100) : 0
  const currentModule = modules.find((module) => module.is_current)

  if (error) return <div className="error">{error}</div>
  if (loading) return <div className="card card-meta">Loading your dashboard…</div>

  return (
    <>
      {homeData?.low_ticket_warning && (
        <div className="card student-dashboard-alert">
          <div className="card-title">Running low on tickets</div>
          <p className="card-meta">
            You have {homeData.tickets_remaining} booking
            {homeData.tickets_remaining === 1 ? ' ticket' : ' tickets'} left. Top up before your next lesson.
          </p>
          <NavLink to="/membership" className="btn">Get more tickets</NavLink>
        </div>
      )}

      {nextLesson ? (
        <div className="hero-card">
          <div className="hero-body">
            <div className="hero-eyebrow">Your next lesson</div>
            <div className="hero-title">{nextLesson.session_title}</div>
            <div className="card-meta">
              {formatLessonTime(nextLesson.session_start_time)}
              {nextLesson.teacher_name ? ` · with ${nextLesson.teacher_name}` : ''}
            </div>
          </div>
          <div className="row-actions">
            {nextLesson.meeting_url && (
              <a href={nextLesson.meeting_url} target="_blank" rel="noreferrer" className="btn">
                Join meeting
              </a>
            )}
            <NavLink to="/bookings" className="btn secondary">View bookings</NavLink>
          </div>
        </div>
      ) : (
        <div className="hero-card">
          <div className="hero-body">
            <div className="hero-eyebrow">Nothing booked yet</div>
            <div className="hero-title">Book your next {labels('session').toLowerCase().replace(/s$/, '')}</div>
            <div className="card-meta">
              {homeData?.has_membership
                ? 'Pick an open class, or turn up to a walk-in class at the branch.'
                : 'Get a membership first, then book a lesson.'}
            </div>
          </div>
          <NavLink to={homeData?.has_membership ? '/sessions' : '/membership'} className="btn">
            {homeData?.has_membership ? 'Browse lessons' : 'Get a membership'}
          </NavLink>
        </div>
      )}

      <div className="stat-grid">
        <div className="stat">
          <div className="stat-label">Tickets</div>
          <div className="stat-value">{totalTickets}</div>
          <div className="card-meta">across all plans</div>
        </div>
        <div className="stat">
          <div className="stat-label">Active plans</div>
          <div className="stat-value">{memberships.length}</div>
          <div className="card-meta">{memberships.length === 1 ? '1 plan' : `${memberships.length} plans`}</div>
        </div>
        {homeData?.open_homework_count > 0 && (
          <div className="stat">
            <div className="stat-label">Open homework</div>
            <div className="stat-value">{homeData.open_homework_count}</div>
            <div className="card-meta"><NavLink to="/homework">View assignments</NavLink></div>
          </div>
        )}
        {homeData?.pending_class_requests > 0 && (
          <div className="stat">
            <div className="stat-label">Pending requests</div>
            <div className="stat-value">{homeData.pending_class_requests}</div>
            <div className="card-meta"><NavLink to="/sessions/request">View requests</NavLink></div>
          </div>
        )}
      </div>

      {enrollment && modules.length > 0 && (
        <div className="card">
          <div className="section-head">
            <h2>{enrollment.track.title}</h2>
            <NavLink to="/curriculum" className="btn secondary small">Open curriculum</NavLink>
          </div>
          <div className="progress-row">
            <span className="progress">
              <span
                className={`progress-fill${percent === 100 ? ' progress-fill--done' : ''}`}
                style={{ width: `${percent}%` }}
              />
            </span>
            <span className="progress-value">{doneCount} of {modules.length} done</span>
          </div>
          {currentModule && (
            <p className="card-meta" style={{ marginTop: '0.6rem' }}>
              Up next: <strong>{currentModule.title}</strong>
              {currentModule.cefr_level ? ` · ${currentModule.cefr_level}` : ''}
            </p>
          )}
        </div>
      )}

      {memberships.length > 0 ? (
        <div className="card">
          <div className="section-head">
            <h2>Your memberships</h2>
            <NavLink to="/membership" className="btn secondary small">Manage</NavLink>
          </div>
          <ul className="list-rows">
            {memberships.map((membership) => {
              const timeLeft = formatTimeLeft(membership.valid_until)
              return (
                <li key={membership.id}>
                  <div>
                    <div className="card-title">{membership.plan_name || membership.plan?.name}</div>
                    <div className="card-meta">
                      {membership.tickets_remaining} ticket
                      {membership.tickets_remaining === 1 ? '' : 's'}
                      {timeLeft.detail ? ` · ${timeLeft.detail}` : ''}
                    </div>
                  </div>
                  <span className={`badge${timeLeft.label === 'Expired' ? ' badge--danger' : ' badge--muted'}`}>
                    {timeLeft.label}
                  </span>
                </li>
              )
            })}
          </ul>
        </div>
      ) : (
        <div className="card">
          <div className="card-title">No active membership</div>
          <p className="card-meta">
            You need a membership and booking tickets before you can reserve {labels('session').toLowerCase()}.
          </p>
          <NavLink to="/membership" className="btn">Get a membership</NavLink>
        </div>
      )}

      <div className="card">
        <div className="card-title">Quick links</div>
        <div className="row" style={{ marginTop: '0.6rem' }}>
          <NavLink to="/progress" className="btn secondary">My progress</NavLink>
          <NavLink to="/homework" className="btn secondary">Homework</NavLink>
          <NavLink to="/inbox" className="btn secondary">Inbox</NavLink>
        </div>
      </div>
    </>
  )
}
