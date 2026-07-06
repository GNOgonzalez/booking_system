import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { apiFetch } from '../api.js'
import { useGlossary } from '../hooks/useGlossary.jsx'

function activeMemberships(data) {
  if (!data?.active) return []
  return data.memberships?.length ? data.memberships : [data]
}

function formatTimeLeft(validUntil) {
  if (!validUntil) return 'No end date'
  const end = new Date(`${validUntil}T23:59:59`)
  const now = new Date()
  const days = Math.ceil((end.getTime() - now.getTime()) / (1000 * 60 * 60 * 24))
  if (days < 0) return 'Expired'
  if (days === 0) return 'Expires today'
  if (days === 1) return '1 day left'
  return `${days} days left`
}

function ticketPackMatchesMembership(ticketPlan, membership) {
  const plan = membership.plan
  if (!plan || plan.plan_type === 'ticket_pack') return false
  if (ticketPlan.includes_all_classes || plan.includes_all_classes) return true
  if (ticketPlan.subject && plan.subject) return ticketPlan.subject === plan.subject
  const membershipClassIds = new Set((plan.allowed_classes || []).map((c) => c.id))
  return (ticketPlan.allowed_classes || []).some((c) => membershipClassIds.has(c.id))
}

const CHECKOUT_POLL_INTERVAL_MS = 2000
const CHECKOUT_POLL_ATTEMPTS = 8

function sleep(ms) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms)
  })
}

export default function MembershipPage() {
  const { labels } = useGlossary()
  const [searchParams, setSearchParams] = useSearchParams()
  const [membershipData, setMembershipData] = useState(null)
  const [plans, setPlans] = useState([])
  const [paymentConfig, setPaymentConfig] = useState({ mode: 'mock', checkout_available: false })
  const [planId, setPlanId] = useState('')
  const [ticketPackId, setTicketPackId] = useState('')
  const [ticketMembershipId, setTicketMembershipId] = useState('')
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [activating, setActivating] = useState(false)
  const [busy, setBusy] = useState(false)

  const stripeMode = paymentConfig.mode === 'stripe' && paymentConfig.checkout_available

  const load = () => Promise.all([
    apiFetch('/api/membership/'),
    apiFetch('/api/membership/plans/'),
    apiFetch('/api/membership/payment-config/'),
  ])
    .then(([membershipResponse, planRows, config]) => {
      setMembershipData(membershipResponse)
      setPlans(planRows)
      setPaymentConfig(config)
      const subscriptions = planRows.filter((p) => p.plan_type !== 'ticket_pack')
      const packs = planRows.filter((p) => p.plan_type === 'ticket_pack')
      setPlanId((current) => current || (subscriptions[0] ? String(subscriptions[0].id) : ''))
      setTicketPackId((current) => current || (packs[0] ? String(packs[0].id) : ''))
      return membershipResponse
    })
    .catch((err) => {
      setError(err.message)
      return null
    })

  useEffect(() => {
    load()
  }, [])

  useEffect(() => {
    const checkout = searchParams.get('checkout')
    const paymentId = searchParams.get('payment_id')
    if (checkout !== 'success' && checkout !== 'cancelled') return undefined

    setSearchParams({}, { replace: true })

    if (checkout === 'cancelled') {
      setMessage('')
      setError('Checkout cancelled. No charge was made.')
      return undefined
    }

    let cancelled = false

    const pollAfterCheckout = async () => {
      setActivating(true)
      setError('')
      setMessage('Activating your membership…')

      for (let attempt = 0; attempt < CHECKOUT_POLL_ATTEMPTS; attempt += 1) {
        if (cancelled) return

        try {
          if (paymentId) {
            const status = await apiFetch(`/api/membership/payments/${paymentId}/`)
            if (status.status === 'completed') {
              setActivating(false)
              setMessage('Membership active! Your tickets are ready to use.')
              await load()
              return
            }
            if (status.status === 'failed') {
              setActivating(false)
              setMessage('')
              setError('Payment could not be completed. Please try again or contact support.')
              await load()
              return
            }
          } else {
            const membershipResponse = await apiFetch('/api/membership/')
            if (membershipResponse?.active) {
              setActivating(false)
              setMessage('Membership active! Your tickets are ready to use.')
              await load()
              return
            }
          }
        } catch (err) {
          if (attempt === CHECKOUT_POLL_ATTEMPTS - 1) {
            setActivating(false)
            setMessage('')
            setError(err.message)
            return
          }
        }

        if (attempt < CHECKOUT_POLL_ATTEMPTS - 1) {
          await sleep(CHECKOUT_POLL_INTERVAL_MS)
        }
      }

      if (cancelled) return
      setActivating(false)
      setMessage('')
      setError(
        'Payment received, but activation is taking longer than usual. '
        + 'Try refreshing in a moment or contact support if it does not appear.',
      )
      await load()
    }

    pollAfterCheckout()

    return () => {
      cancelled = true
    }
  }, [searchParams, setSearchParams])

  const memberships = activeMemberships(membershipData)
  const subscriptionPlans = useMemo(
    () => plans.filter((p) => p.plan_type !== 'ticket_pack'),
    [plans],
  )
  const ticketPacks = useMemo(
    () => plans.filter((p) => p.plan_type === 'ticket_pack'),
    [plans],
  )
  const selectedPlan = subscriptionPlans.find((plan) => String(plan.id) === planId)
  const selectedTicketPack = ticketPacks.find((plan) => String(plan.id) === ticketPackId)
  const ownedPlanIds = new Set(memberships.map((m) => m.plan?.id))

  const compatibleMemberships = useMemo(() => {
    if (!selectedTicketPack) return []
    return memberships.filter((m) => ticketPackMatchesMembership(selectedTicketPack, m))
  }, [memberships, selectedTicketPack])

  useEffect(() => {
    if (!compatibleMemberships.length) {
      setTicketMembershipId('')
      return
    }
    if (!compatibleMemberships.some((m) => String(m.id) === ticketMembershipId)) {
      setTicketMembershipId(String(compatibleMemberships[0].id))
    }
  }, [compatibleMemberships, ticketMembershipId])

  const startCheckout = async ({ plan_id, months = 1, membership_id = null }) => {
    setBusy(true)
    setError('')
    setMessage('')
    try {
      const body = { plan_id, months }
      if (membership_id != null) body.membership_id = membership_id
      const origin = window.location.origin
      const result = await apiFetch('/api/membership/checkout/', {
        method: 'POST',
        body: JSON.stringify({
          ...body,
          success_url: `${origin}/membership?checkout=success`,
          cancel_url: `${origin}/membership?checkout=cancelled`,
        }),
      })
      window.location.href = result.checkout_url
    } catch (err) {
      setError(err.message)
      setBusy(false)
    }
  }

  const purchaseMock = async (body) => {
    setBusy(true)
    setError('')
    setMessage('')
    try {
      await apiFetch('/api/membership/', {
        method: 'POST',
        body: JSON.stringify(body),
      })
      setMessage('Purchase complete!')
      load()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const purchaseSubscription = async (e) => {
    e.preventDefault()

    const selected = subscriptionPlans.find((plan) => String(plan.id) === planId)
    if (!selected) return

    const alreadyOnPlan = memberships.some((m) => m.plan?.id === selected.id)
    const hasOtherPlans = memberships.some((m) => m.plan?.id !== selected.id)

    if (memberships.length > 0 && hasOtherPlans && !alreadyOnPlan) {
      const names = memberships.map((m) => m.plan_name || m.plan?.name).join(', ')
      const ok = window.confirm(
        `You already have active membership(s): ${names}.\n\n`
        + `Purchasing "${selected.name}" adds a separate membership so you can study multiple subjects. `
        + 'Each plan has its own tickets and expiry.\n\nContinue?',
      )
      if (!ok) return
    } else if (alreadyOnPlan) {
      const ok = window.confirm(
        `Extend your "${selected.name}" membership? `
        + `You will receive ${selected.ticket_allowance} more ticket${selected.ticket_allowance === 1 ? '' : 's'}.`,
      )
      if (!ok) return
    }

    if (stripeMode) {
      await startCheckout({ plan_id: Number(planId), months: 1 })
      return
    }
    await purchaseMock({ plan_id: Number(planId), months: 1 })
  }

  const purchaseTickets = async (e) => {
    e.preventDefault()

    if (!selectedTicketPack) return
    if (!ticketMembershipId) {
      setError('Choose which membership should receive these tickets.')
      return
    }

    const target = memberships.find((m) => String(m.id) === ticketMembershipId)
    const ok = window.confirm(
      `Buy ${selectedTicketPack.ticket_allowance} ticket${selectedTicketPack.ticket_allowance === 1 ? '' : 's'} `
      + `(${selectedTicketPack.price_display}) for your `
      + `"${target?.plan_name || target?.plan?.name}" membership?`,
    )
    if (!ok) return

    const body = {
      plan_id: Number(ticketPackId),
      months: 1,
      membership_id: Number(ticketMembershipId),
    }
    if (stripeMode) {
      await startCheckout(body)
      return
    }
    await purchaseMock(body)
  }

  const subscriptionButtonLabel = stripeMode
    ? (ownedPlanIds.has(Number(planId)) ? 'Pay to extend (Stripe)' : 'Pay with Stripe')
    : (ownedPlanIds.has(Number(planId)) ? 'Extend subscription (mock)' : 'Purchase subscription (mock)')

  const ticketButtonLabel = stripeMode ? 'Pay with Stripe' : 'Buy tickets (mock)'

  return (
    <div>
      <h1>Membership</h1>
      <p className="page-intro">
        Subscribe by subject, or buy individual tickets to top up an existing membership.
      </p>
      {activating && <div className="success">Activating your membership…</div>}
      {message && !activating && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}

      {stripeMode && (
        <div className="card card-meta">
          Payments run through Stripe Checkout.
          {!paymentConfig.webhook_configured && (
            <> Webhook secret not set — use the Stripe CLI to forward events while testing locally.</>
          )}
        </div>
      )}

      {memberships.length > 0 ? (
        <>
          <h2>Active memberships</h2>
          {memberships.map((item) => (
            <div key={item.id} className="card">
              <div className="card-title">{item.plan_name || item.plan?.name}</div>
              {item.valid_until && (
                <p className="card-meta">{formatTimeLeft(item.valid_until)} · until {item.valid_until}</p>
              )}
              <p className="card-meta">
                {item.tickets_remaining} booking ticket{item.tickets_remaining === 1 ? '' : 's'} remaining
              </p>
              {item.plan?.includes_all_classes ? (
                <p className="card-meta">Includes all {labels('class').toLowerCase()}.</p>
              ) : item.plan?.subject ? (
                <p className="card-meta">Includes all {item.plan.subject} {labels('class').toLowerCase()}.</p>
              ) : item.plan?.allowed_classes?.length ? (
                <ul className="membership-class-list">
                  {item.plan.allowed_classes.map((cls) => (
                    <li key={cls.id}>{cls.label}</li>
                  ))}
                </ul>
              ) : null}
            </div>
          ))}
        </>
      ) : (
        <p>No active membership. Booking requires a subject subscription.</p>
      )}

      {subscriptionPlans.length > 0 && (
        <form onSubmit={purchaseSubscription} className="card">
          <h2>{ownedPlanIds.has(Number(planId)) ? 'Extend a subscription' : 'Purchase a subscription'}</h2>
          <div className="field">
            <label>Plan</label>
            <select value={planId} onChange={(e) => setPlanId(e.target.value)} required>
              {subscriptionPlans.map((plan) => (
                <option key={plan.id} value={plan.id}>
                  {plan.name}
                  {ownedPlanIds.has(plan.id) ? ' (owned)' : ''}
                  {' — '}
                  {plan.price_display} / {plan.billing_period_days} days ({plan.ticket_allowance} tickets)
                </option>
              ))}
            </select>
          </div>
          {selectedPlan && (
            <>
              {selectedPlan.description && <p className="card-meta">{selectedPlan.description}</p>}
              <p className="card-meta">
                Grants {selectedPlan.ticket_allowance} ticket{selectedPlan.ticket_allowance === 1 ? '' : 's'} per billing period.
              </p>
            </>
          )}
          <button type="submit" disabled={busy}>{subscriptionButtonLabel}</button>
        </form>
      )}

      {ticketPacks.length > 0 && (
        <form onSubmit={purchaseTickets} className="card">
          <h2>Buy individual tickets</h2>
          <p className="card-meta">
            Top up an active subject membership without extending its expiry date.
          </p>
          <div className="field">
            <label>Ticket pack</label>
            <select value={ticketPackId} onChange={(e) => setTicketPackId(e.target.value)} required>
              {ticketPacks.map((plan) => (
                <option key={plan.id} value={plan.id}>
                  {plan.name} — {plan.price_display} ({plan.ticket_allowance} ticket{plan.ticket_allowance === 1 ? '' : 's'})
                </option>
              ))}
            </select>
          </div>
          {memberships.length > 0 ? (
            <div className="field">
              <label>Add tickets to</label>
              <select
                value={ticketMembershipId}
                onChange={(e) => setTicketMembershipId(e.target.value)}
                required
              >
                {compatibleMemberships.length ? (
                  compatibleMemberships.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.plan_name || m.plan?.name} ({m.tickets_remaining} tickets now)
                    </option>
                  ))
                ) : (
                  <option value="">No matching membership for this pack</option>
                )}
              </select>
            </div>
          ) : (
            <p className="card-meta">Purchase a subject subscription first.</p>
          )}
          {selectedTicketPack?.description && (
            <p className="card-meta">{selectedTicketPack.description}</p>
          )}
          <button type="submit" disabled={!compatibleMemberships.length || busy}>
            {ticketButtonLabel}
          </button>
        </form>
      )}

      {!subscriptionPlans.length && !ticketPacks.length && !error && (
        <p className="card-meta">No membership plans are available right now.</p>
      )}
      {!stripeMode && (
        <p className="card-meta">Payments are mocked until Stripe credentials are configured in <code>.env</code>.</p>
      )}
    </div>
  )
}
