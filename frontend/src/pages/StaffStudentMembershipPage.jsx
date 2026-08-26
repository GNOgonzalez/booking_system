import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { apiFetch } from '../api.js'
import { useGlossary } from '../hooks/useGlossary.jsx'
import { formatDateTime } from '../utils/datetime.js'

const PROVIDER_LABELS = {
  mock: 'Mock',
  stripe: 'Stripe',
  staff: 'Recorded by staff',
}

function money(cents) {
  return `$${((cents || 0) / 100).toFixed(2)}`
}

function formatDate(value) {
  if (!value) return 'No expiry'
  return new Date(`${value}T00:00:00`).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

export default function StaffStudentMembershipPage() {
  const { studentId } = useParams()
  const { label, labels } = useGlossary()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const [grant, setGrant] = useState({ plan_id: '', months: '1', amount_dollars: '0', note: '' })
  const [ticketForm, setTicketForm] = useState({})
  const [note, setNote] = useState('')
  const [password, setPassword] = useState('')

  const basePath = `/api/staff/students/${studentId}/membership/`

  const load = () => {
    setLoading(true)
    apiFetch(basePath)
      .then(setData)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }

  useEffect(load, [studentId])

  /** Every write reloads the panel so payments and the audit trail stay in step. */
  const run = async (path, options, successMessage) => {
    setError('')
    setMessage('')
    setBusy(true)
    try {
      await apiFetch(path, options)
      load()
      setMessage(successMessage)
      return true
    } catch (err) {
      setError(err.message)
      return false
    } finally {
      setBusy(false)
    }
  }

  const submitGrant = async (e) => {
    e.preventDefault()
    const dollars = Number(grant.amount_dollars || 0)
    if (Number.isNaN(dollars) || dollars < 0) {
      setError('Amount collected must be zero or more.')
      return
    }
    const ok = await run(
      basePath,
      {
        method: 'POST',
        body: JSON.stringify({
          plan_id: Number(grant.plan_id),
          months: Number(grant.months) || 1,
          amount_cents: Math.round(dollars * 100),
          note: grant.note,
        }),
      },
      dollars > 0 ? 'Membership added and payment recorded.' : 'Membership comped.',
    )
    if (ok) setGrant({ plan_id: '', months: '1', amount_dollars: '0', note: '' })
  }

  const patchMembership = (membershipId, body, successMessage) => run(
    `${basePath}${membershipId}/`,
    { method: 'PATCH', body: JSON.stringify({ ...body, note }) },
    successMessage,
  )

  const adjustTickets = async (membershipId, sign) => {
    const raw = ticketForm[membershipId]
    const amount = Number(raw)
    if (!raw || Number.isNaN(amount) || amount < 1) {
      setError('Enter how many tickets to add or remove.')
      return
    }
    const ok = await patchMembership(
      membershipId,
      { tickets_delta: sign * Math.round(amount) },
      sign > 0 ? `Added ${amount} ticket(s).` : `Removed ${amount} ticket(s).`,
    )
    if (ok) setTicketForm((current) => ({ ...current, [membershipId]: '' }))
  }

  const cancelBooking = async (booking, refund) => {
    const question = refund
      ? `Cancel "${booking.session_title}" and refund ${booking.tickets_spent} ticket(s)?`
      : `Cancel "${booking.session_title}" without refunding?`
    if (!window.confirm(question)) return
    await run(
      `/api/staff/bookings/${booking.id}/cancel/`,
      { method: 'POST', body: JSON.stringify({ refund, note }) },
      refund ? 'Booking cancelled and ticket refunded.' : 'Booking cancelled, no refund.',
    )
  }

  const resetPassword = async (e) => {
    e.preventDefault()
    const ok = await run(
      `/api/staff/students/${studentId}/password/`,
      { method: 'POST', body: JSON.stringify({ password, note }) },
      'Password updated. Share it and ask them to change it.',
    )
    if (ok) setPassword('')
  }

  if (loading) return <p className="page-intro">Loading {label('student').toLowerCase()}…</p>
  if (!data) return <div className="error">{error || 'Not found.'}</div>

  const student = data.student

  return (
    <div>
      <p className="card-meta">
        <Link to="/staff/students">← {labels('student')}</Link>
      </p>
      <h1>{student.username}</h1>
      <p className="page-intro">
        {student.email || 'No email on file'} · {data.tickets_remaining} ticket(s) available
        {!data.has_active_membership && ' · no active membership'}
      </p>
      {message && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}

      <div className="card">
        <div className="field">
          <label>Reason (attached to every change below)</label>
          <input
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="e.g. make-up for cancelled lesson"
          />
        </div>
      </div>

      <h2>Memberships</h2>
      {!data.memberships.length && (
        <p className="card-meta">No memberships yet. Add one below.</p>
      )}
      {data.memberships.map((membership) => (
        <div
          key={membership.id}
          className={`card${membership.is_active ? '' : ' card--inactive'}`}
        >
          <div className="card-row">
            <div>
              <div className="card-title">
                {membership.plan_name}
                {!membership.is_active && <span className="badge badge--muted">Cancelled</span>}
                {membership.is_expired && <span className="badge badge--muted">Expired</span>}
              </div>
              <div className="card-meta">
                {membership.tickets_remaining} ticket(s) · {formatDate(membership.valid_until)}
              </div>
            </div>
            <div className="row-actions">
              <button
                type="button"
                className="secondary"
                disabled={busy}
                onClick={() => patchMembership(membership.id, { extend_days: 30 }, 'Extended 30 days.')}
              >
                +30 days
              </button>
              <button
                type="button"
                className={membership.is_active ? 'danger' : 'secondary'}
                disabled={busy}
                onClick={() => patchMembership(
                  membership.id,
                  { is_active: !membership.is_active },
                  membership.is_active ? 'Membership cancelled.' : 'Membership reactivated.',
                )}
              >
                {membership.is_active ? 'Cancel membership' : 'Reactivate'}
              </button>
            </div>
          </div>
          <div className="row">
            <div className="field grow">
              <label>Tickets</label>
              <input
                type="number"
                min="1"
                value={ticketForm[membership.id] || ''}
                onChange={(e) => setTicketForm({ ...ticketForm, [membership.id]: e.target.value })}
                placeholder="e.g. 2"
              />
            </div>
            <div className="field" style={{ alignSelf: 'end' }}>
              <button type="button" disabled={busy} onClick={() => adjustTickets(membership.id, 1)}>
                Add
              </button>
            </div>
            <div className="field" style={{ alignSelf: 'end' }}>
              <button
                type="button"
                className="secondary"
                disabled={busy}
                onClick={() => adjustTickets(membership.id, -1)}
              >
                Remove
              </button>
            </div>
          </div>
        </div>
      ))}

      <form onSubmit={submitGrant} className="card">
        <div className="card-title">Add a membership</div>
        <p className="card-meta">
          Leave the amount at 0 to comp it. Enter what you collected to record a cash or
          bank-transfer sale — it shows up in reports as “recorded by staff”.
        </p>
        <div className="row">
          <div className="field grow">
            <label>Plan</label>
            <select
              value={grant.plan_id}
              onChange={(e) => setGrant({ ...grant, plan_id: e.target.value })}
              required
            >
              <option value="">Choose plan…</option>
              {(data.plans || []).map((plan) => (
                <option key={plan.id} value={plan.id}>
                  {plan.name} — {money(plan.price_cents)} / {plan.ticket_allowance} tickets
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Periods</label>
            <input
              type="number"
              min="1"
              max="24"
              value={grant.months}
              onChange={(e) => setGrant({ ...grant, months: e.target.value })}
            />
          </div>
          <div className="field">
            <label>Amount collected ($)</label>
            <input
              type="number"
              min="0"
              step="0.01"
              value={grant.amount_dollars}
              onChange={(e) => setGrant({ ...grant, amount_dollars: e.target.value })}
            />
          </div>
        </div>
        <div className="field">
          <label>Note (optional)</label>
          <input
            value={grant.note}
            onChange={(e) => setGrant({ ...grant, note: e.target.value })}
            placeholder="e.g. paid cash at the front desk"
          />
        </div>
        <button type="submit" disabled={busy || !grant.plan_id}>Add membership</button>
      </form>

      <h2>Upcoming {labels('session').toLowerCase()}</h2>
      {!data.upcoming_bookings.length && (
        <p className="card-meta">No upcoming bookings.</p>
      )}
      {data.upcoming_bookings.map((booking) => (
        <div key={booking.id} className="card">
          <div className="card-row">
            <div>
              <div className="card-title">{booking.session_title}</div>
              <div className="card-meta">
                {formatDateTime(booking.start_time)} · {booking.teacher} ·{' '}
                {booking.tickets_spent} ticket(s)
              </div>
            </div>
            <div className="row-actions">
              <button
                type="button"
                className="secondary"
                disabled={busy}
                onClick={() => cancelBooking(booking, true)}
              >
                Cancel + refund
              </button>
              <button
                type="button"
                className="danger"
                disabled={busy}
                onClick={() => cancelBooking(booking, false)}
              >
                Cancel, no refund
              </button>
            </div>
          </div>
        </div>
      ))}

      <h2>Payments</h2>
      {!data.payments.length && <p className="card-meta">No payments recorded.</p>}
      {data.payments.map((payment) => (
        <div key={payment.id} className="card">
          <div className="card-row">
            <div>
              <div className="card-title">
                {money(payment.amount_cents)} · {payment.plan_name}
              </div>
              <div className="card-meta">
                {PROVIDER_LABELS[payment.provider] || payment.provider} · {payment.status} ·{' '}
                {formatDateTime(payment.created_at)}
              </div>
            </div>
          </div>
        </div>
      ))}

      <h2>Account</h2>
      <form onSubmit={resetPassword} className="card">
        <div className="card-title">Set a temporary password</div>
        <p className="card-meta">
          Use this when they are locked out. Share it in person and ask them to change it under
          Account.
        </p>
        <div className="row">
          <div className="field grow">
            <label>New password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="new-password"
              required
            />
          </div>
          <div className="field" style={{ alignSelf: 'end' }}>
            <button type="submit" disabled={busy}>Set password</button>
          </div>
        </div>
      </form>

      {(data.recent_actions || []).length > 0 && (
        <>
          <h2>Recent staff changes</h2>
          <ul className="staff-alerts-list">
            {data.recent_actions.map((entry) => (
              <li key={entry.id} className="staff-alert-item">
                <div className="staff-alert-item-main">
                  <span className="staff-alert-title">{entry.summary}</span>
                </div>
                <div className="card-meta">
                  {entry.actor} · {formatDateTime(entry.created_at)}
                  {entry.note && ` · ${entry.note}`}
                </div>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  )
}
