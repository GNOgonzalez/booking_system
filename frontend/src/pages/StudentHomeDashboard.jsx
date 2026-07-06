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

function activeMemberships(data) {
  if (!data?.active) return []
  return data.memberships?.length ? data.memberships : [data]
}

export default function StudentHomeDashboard() {
  const { labels } = useGlossary()
  const [membershipData, setMembershipData] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    apiFetch('/api/membership/')
      .then(setMembershipData)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  const memberships = activeMemberships(membershipData)
  const totalTickets = membershipData?.tickets_remaining ?? 0

  return (
    <>
      {error && <div className="error">{error}</div>}

      {loading ? (
        <div className="card card-meta">Loading membership…</div>
      ) : memberships.length > 0 ? (
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
  )
}
