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
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      apiFetch('/api/student/home/'),
      apiFetch('/api/membership/'),
    ])
      .then(([home, membership]) => {
        setHomeData(home)
        setMembershipData(membership)
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  const memberships = activeMemberships(membershipData)
  const totalTickets = membershipData?.tickets_remaining ?? homeData?.tickets_remaining ?? 0
  const nextLesson = homeData?.next_lesson

  return (
    <>
      {error && <div className="error">{error}</div>}

      {loading ? (
        <div className="card card-meta">Loading your dashboard…</div>
      ) : (
        <>
          {homeData?.low_ticket_warning && (
            <div className="card student-dashboard-alert">
              <div className="card-title">Running low on tickets</div>
              <p className="card-meta">
                You have {homeData.tickets_remaining} booking ticket
                {homeData.tickets_remaining === 1 ? '' : 's'} left. Top up before your next lesson.
              </p>
              <NavLink to="/membership" className="btn">Get more tickets</NavLink>
            </div>
          )}

          {nextLesson ? (
            <div className="card student-dashboard-next-lesson">
              <div className="card-title">Next lesson</div>
              <p className="card-meta">{formatLessonTime(nextLesson.session_start_time)}</p>
              <p><strong>{nextLesson.session_title}</strong></p>
              {nextLesson.teacher_name && (
                <p className="card-meta">With {nextLesson.teacher_name}</p>
              )}
              <div className="row" style={{ marginTop: '1rem' }}>
                <NavLink to="/bookings" className="btn secondary">View bookings</NavLink>
                {nextLesson.meeting_url && (
                  <a href={nextLesson.meeting_url} target="_blank" rel="noreferrer" className="btn">
                    Join meeting
                  </a>
                )}
              </div>
            </div>
          ) : homeData?.has_membership ? (
            <div className="card">
              <div className="card-title">No upcoming lessons</div>
              <p className="card-meta">Browse open sessions and book your next {labels('session').toLowerCase()}.</p>
              <NavLink to="/sessions" className="btn">Book a lesson</NavLink>
            </div>
          ) : null}

          {homeData?.pending_class_requests > 0 && (
            <div className="card">
              <div className="card-title">Pending class requests</div>
              <p className="card-meta">
                {homeData.pending_class_requests} request
                {homeData.pending_class_requests === 1 ? '' : 's'} waiting for teacher approval.
              </p>
              <NavLink to="/sessions/request" className="btn secondary">View requests</NavLink>
            </div>
          )}

          {memberships.length > 0 ? (
            <>
              <div className="card student-dashboard-membership">
                <div className="card-title">Your memberships</div>
                <div className="dashboard-stats">
                  <div className="dashboard-stat">
                    <div className="dashboard-stat-label">Total tickets</div>
                    <div className="dashboard-stat-value">{totalTickets}</div>
                    <div className="dashboard-stat-meta">across all plans</div>
                  </div>
                  <div className="dashboard-stat">
                    <div className="dashboard-stat-label">Active plans</div>
                    <div className="dashboard-stat-value">{memberships.length}</div>
                    <div className="dashboard-stat-meta">
                      {memberships.length === 1 ? '1 subject' : `${memberships.length} subjects`}
                    </div>
                  </div>
                  {homeData?.open_homework_count > 0 && (
                    <div className="dashboard-stat">
                      <div className="dashboard-stat-label">Open homework</div>
                      <div className="dashboard-stat-value">{homeData.open_homework_count}</div>
                      <div className="dashboard-stat-meta">
                        <NavLink to="/homework">View assignments</NavLink>
                      </div>
                    </div>
                  )}
                </div>
                <div className="row" style={{ marginTop: '1rem' }}>
                  <NavLink to="/sessions" className="btn">Book a lesson</NavLink>
                  <NavLink to="/membership" className="btn secondary">Membership</NavLink>
                  <NavLink to="/bookings" className="btn secondary">My {labels('booking').toLowerCase()}</NavLink>
                </div>
              </div>

              {memberships.map((membership) => {
                const timeLeft = formatTimeLeft(membership.valid_until)
                return (
                  <div key={membership.id} className="card">
                    <div className="card-title">{membership.plan_name || membership.plan?.name}</div>
                    <div className="dashboard-stats">
                      <div className="dashboard-stat">
                        <div className="dashboard-stat-label">Tickets</div>
                        <div className="dashboard-stat-value">{membership.tickets_remaining}</div>
                        <div className="dashboard-stat-meta">for this subject</div>
                      </div>
                      <div className="dashboard-stat">
                        <div className="dashboard-stat-label">Time left</div>
                        <div className="dashboard-stat-value">{timeLeft.label}</div>
                        {timeLeft.detail && <div className="dashboard-stat-meta">{timeLeft.detail}</div>}
                      </div>
                    </div>
                  </div>
                )
              })}
            </>
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
            <div className="row">
              <NavLink to="/progress" className="btn secondary">My progress</NavLink>
              <NavLink to="/homework" className="btn secondary">Homework</NavLink>
              <NavLink to="/inbox" className="btn secondary">Inbox</NavLink>
            </div>
          </div>
        </>
      )}
    </>
  )
}
