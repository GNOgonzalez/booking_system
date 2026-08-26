import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch } from '../api.js'

const PROVIDER_LABELS = {
  mock: 'Mock checkout',
  stripe: 'Stripe',
  staff: 'Recorded by staff',
}

function money(cents) {
  return `$${((cents || 0) / 100).toFixed(2)}`
}

export default function StaffPaymentsPage() {
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    apiFetch('/api/staff/payments/')
      .then(setStatus)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  const copyWebhook = async () => {
    try {
      await navigator.clipboard.writeText(status.stripe.webhook_url)
      setCopied(true)
    } catch {
      setError('Could not copy — select the URL and copy manually.')
    }
  }

  if (loading) return <p className="page-intro">Loading payment settings…</p>
  if (!status) return <div className="error">{error || 'Not available.'}</div>

  const stripe = status.stripe

  return (
    <div>
      <p className="card-meta"><Link to="/staff">← Staff dashboard</Link></p>
      <h1>Payments</h1>
      <p className="page-intro">
        How money is being taken right now. Keys live in environment variables, so this page is
        read-only — it never shows a secret key.
      </p>
      {error && <div className="error">{error}</div>}

      <div className="card">
        <div className="card-row">
          <div>
            <div className="card-title">
              {status.is_live ? 'Live — Stripe' : 'Mock checkout'}
              <span className={`badge ${status.is_live ? 'badge--success' : 'badge--muted'}`}>
                {status.mode}
              </span>
            </div>
            <div className="card-meta">
              {status.is_live
                ? 'Purchases go through Stripe Checkout and charge real cards.'
                : 'Purchases complete instantly without charging anything.'}
            </div>
          </div>
        </div>
        {!status.is_live && !status.mock_payments_allowed && (
          <p className="card-meta">
            <strong>Purchases are blocked.</strong> Stripe is not configured and mock payments are
            off. Set <code>STRIPE_SECRET_KEY</code>, or <code>ALLOW_MOCK_PAYMENTS=true</code> for
            testing.
          </p>
        )}
      </div>

      <div className="card">
        <div className="card-title">Stripe connection</div>
        <ul className="staff-alerts-list">
          <li className="staff-alert-item">
            <div className="staff-alert-item-main">
              <span className="staff-alert-title">Secret key</span>
              <span className={`badge ${stripe.secret_key_configured ? 'badge--success' : 'badge--muted'}`}>
                {stripe.secret_key_configured ? stripe.secret_key_hint : 'not set'}
              </span>
            </div>
            <div className="card-meta"><code>STRIPE_SECRET_KEY</code></div>
          </li>
          <li className="staff-alert-item">
            <div className="staff-alert-item-main">
              <span className="staff-alert-title">Publishable key</span>
              <span className={`badge ${stripe.publishable_key ? 'badge--success' : 'badge--muted'}`}>
                {stripe.publishable_key || 'not set'}
              </span>
            </div>
            <div className="card-meta"><code>STRIPE_PUBLISHABLE_KEY</code></div>
          </li>
          <li className="staff-alert-item">
            <div className="staff-alert-item-main">
              <span className="staff-alert-title">Webhook signing secret</span>
              <span className={`badge ${stripe.webhook_secret_configured ? 'badge--success' : 'badge--muted'}`}>
                {stripe.webhook_secret_configured ? 'configured' : 'not set'}
              </span>
            </div>
            <div className="card-meta"><code>STRIPE_WEBHOOK_SECRET</code></div>
          </li>
        </ul>
        <div className="field">
          <label>Webhook URL to paste into Stripe</label>
          <input value={stripe.webhook_url} readOnly onFocus={(e) => e.target.select()} />
        </div>
        <button type="button" className="secondary" onClick={copyWebhook}>
          {copied ? 'Copied' : 'Copy webhook URL'}
        </button>
      </div>

      <div className="card">
        <div className="card-title">Completed payments by source</div>
        {!status.completed_by_provider.length && (
          <p className="card-meta">No completed payments yet.</p>
        )}
        {status.completed_by_provider.map((row) => (
          <div key={row.provider} className="card-row">
            <div className="card-meta">{PROVIDER_LABELS[row.provider] || row.provider}</div>
            <div className="card-meta">
              {row.count} payment(s) · {money(row.amount_cents)}
            </div>
          </div>
        ))}
        <p className="card-meta">
          {status.pending_count} pending · {status.failed_count} failed ·{' '}
          <Link to="/staff/reports">See reports</Link>
        </p>
      </div>

      <div className="card">
        <div className="card-title">Changing keys</div>
        <p className="card-meta">
          Set these in your host&apos;s environment (Render → Environment) and redeploy. Keys are
          deliberately not editable here so they are never stored in the database.
        </p>
        <ul className="staff-alerts-list">
          {status.env_keys.map((key) => (
            <li key={key} className="staff-alert-item">
              <code>{key}</code>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
