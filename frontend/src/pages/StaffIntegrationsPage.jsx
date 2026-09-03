import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch } from '../api.js'

function StatusBadge({ ok, okLabel, offLabel }) {
  return (
    <span className={`badge ${ok ? 'badge--success' : 'badge--muted'}`}>
      {ok ? okLabel : offLabel}
    </span>
  )
}

function EnvKeys({ keys }) {
  return (
    <ul className="staff-alerts-list">
      {keys.map((key) => (
        <li key={key} className="staff-alert-item">
          <code>{key}</code>
        </li>
      ))}
    </ul>
  )
}

export default function StaffIntegrationsPage() {
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    apiFetch('/api/staff/integrations/')
      .then(setStatus)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <p className="page-intro">Loading integrations…</p>
  if (!status) return <div className="error">{error || 'Not available.'}</div>

  const { email, google } = status

  return (
    <div>
      <p className="card-meta"><Link to="/staff">← Staff dashboard</Link></p>
      <h1>Integrations</h1>
      <p className="page-intro">
        Whether email and Google are actually working. Credentials live in environment variables, so
        this page is read-only and never shows a secret.
      </p>
      {error && <div className="error">{error}</div>}

      <div className="card">
        <div className="card-row">
          <div>
            <div className="card-title">
              Email
              <StatusBadge ok={email.is_live} okLabel="sending" offLabel="console only" />
            </div>
            <div className="card-meta">
              {email.is_live
                ? `Delivered over SMTP via ${email.host}.`
                : 'Emails are printed to the server log — students and teachers receive nothing.'}
            </div>
          </div>
        </div>
        {!email.is_live && (
          <p className="card-meta">
            <strong>Nobody is being notified.</strong> Booking confirmations, cancellations, and
            receipts all go to the log until <code>EMAIL_HOST</code> is set.
          </p>
        )}
        <ul className="staff-alerts-list">
          <li className="staff-alert-item">
            <div className="staff-alert-item-main">
              <span className="staff-alert-title">From address</span>
              <span className="badge">{email.from_address}</span>
            </div>
            <div className="card-meta"><code>DEFAULT_FROM_EMAIL</code></div>
          </li>
          {email.is_live && (
            <>
              <li className="staff-alert-item">
                <div className="staff-alert-item-main">
                  <span className="staff-alert-title">SMTP host</span>
                  <span className="badge badge--success">
                    {email.host}:{email.port}
                  </span>
                </div>
                <div className="card-meta">TLS {email.use_tls ? 'on' : 'off'}</div>
              </li>
              <li className="staff-alert-item">
                <div className="staff-alert-item-main">
                  <span className="staff-alert-title">SMTP password</span>
                  <StatusBadge
                    ok={email.password_configured}
                    okLabel="configured"
                    offLabel="not set"
                  />
                </div>
                <div className="card-meta"><code>EMAIL_HOST_PASSWORD</code></div>
              </li>
            </>
          )}
        </ul>
        <EnvKeys keys={email.env_keys} />
      </div>

      <div className="card">
        <div className="card-row">
          <div>
            <div className="card-title">
              Google Calendar &amp; Meet
              <StatusBadge ok={google.configured} okLabel="configured" offLabel="not configured" />
            </div>
            <div className="card-meta">
              {google.configured
                ? `${google.connected_count} of ${google.teacher_count} teacher(s) connected.`
                : 'Sessions use placeholder meeting links until OAuth credentials are set.'}
            </div>
          </div>
        </div>

        <ul className="staff-alerts-list">
          <li className="staff-alert-item">
            <div className="staff-alert-item-main">
              <span className="staff-alert-title">Client ID</span>
              <StatusBadge
                ok={google.client_id_configured}
                okLabel="configured"
                offLabel="not set"
              />
            </div>
            <div className="card-meta"><code>GOOGLE_CLIENT_ID</code></div>
          </li>
          <li className="staff-alert-item">
            <div className="staff-alert-item-main">
              <span className="staff-alert-title">Client secret</span>
              <StatusBadge
                ok={google.client_secret_configured}
                okLabel="configured"
                offLabel="not set"
              />
            </div>
            <div className="card-meta"><code>GOOGLE_CLIENT_SECRET</code></div>
          </li>
        </ul>

        <div className="field">
          <label>Redirect URI to register with Google</label>
          <input value={google.redirect_uri} readOnly onFocus={(e) => e.target.select()} />
        </div>

        {google.configured && (
          <>
            <div className="card-title">Teacher connections</div>
            <ul className="staff-alerts-list">
              {google.teachers.map((teacher) => (
                <li key={teacher.id} className="staff-alert-item">
                  <div className="staff-alert-item-main">
                    <span className="staff-alert-title">{teacher.username}</span>
                    <StatusBadge
                      ok={teacher.connected}
                      okLabel="connected"
                      offLabel="not connected"
                    />
                  </div>
                </li>
              ))}
            </ul>
            <p className="card-meta">
              Each teacher connects their own calendar from Profile &amp; settings — staff cannot do
              it on their behalf.
            </p>
          </>
        )}
        <EnvKeys keys={google.env_keys} />
      </div>

      <div className="card">
        <div className="card-title">Changing these</div>
        <p className="card-meta">
          Set the variables in your host&apos;s environment (Render → Environment) and redeploy.
          They are deliberately not editable here so credentials are never stored in the database.
          Payment keys live on the <Link to="/staff/payments">Payments</Link> page.
        </p>
      </div>
    </div>
  )
}
