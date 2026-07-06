import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { apiFetch, changePassword, getMe, updateMe } from '../api.js'
import { applyTheme } from '../hooks/useTheme.js'
import { browserTimezone } from '../utils/datetime.js'

function GoogleCalendarCard() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [gStatus, setGStatus] = useState(null)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const load = () => {
    apiFetch('/api/integrations/google/status/')
      .then(setGStatus)
      .catch(() => setGStatus(null))
  }

  useEffect(load, [])

  useEffect(() => {
    const result = searchParams.get('google')
    if (!result) return
    if (result === 'connected') setMessage('Google Calendar connected. New sessions will get real Meet links.')
    else if (result === 'denied') setError('Google connection was cancelled.')
    else setError('Google connection failed. Try again.')
    searchParams.delete('google')
    setSearchParams(searchParams, { replace: true })
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const connect = async () => {
    setBusy(true)
    setError('')
    try {
      const origin = encodeURIComponent(window.location.origin)
      const data = await apiFetch(`/api/integrations/google/connect/?frontend_origin=${origin}`)
      window.location.assign(data.authorization_url)
    } catch (err) {
      setError(err.message)
      setBusy(false)
    }
  }

  const disconnectGoogle = async () => {
    setBusy(true)
    setError('')
    try {
      const next = await apiFetch('/api/integrations/google/disconnect/', { method: 'POST' })
      setGStatus(next)
      setMessage('Google Calendar disconnected.')
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  if (gStatus === null) return null

  return (
    <div className="card">
      <h2>Google Calendar</h2>
      {message && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}
      {!gStatus.configured ? (
        <p className="card-meta">
          Google OAuth is not configured on this server. Sessions use placeholder Meet links.
        </p>
      ) : gStatus.connected ? (
        <>
          <p className="card-meta">
            Connected — sessions you create with Google Meet get real meeting links.
          </p>
          <div className="form-actions">
            <button type="button" className="secondary" onClick={disconnectGoogle} disabled={busy}>
              Disconnect
            </button>
          </div>
        </>
      ) : (
        <>
          <p className="card-meta">
            Connect your Google account so new sessions get real Meet links on your calendar.
          </p>
          <div className="form-actions">
            <button type="button" onClick={connect} disabled={busy}>
              {busy ? 'Redirecting…' : 'Connect Google Calendar'}
            </button>
          </div>
        </>
      )}
    </div>
  )
}

export default function ProfilePage({ onSaved }) {
  const [form, setForm] = useState({
    display_name: '',
    first_name: '',
    last_name: '',
    email: '',
    timezone: 'UTC',
    theme: 'system',
  })
  const [username, setUsername] = useState('')
  const [roles, setRoles] = useState([])
  const [profileMsg, setProfileMsg] = useState('')
  const [profileErr, setProfileErr] = useState('')

  const [pw, setPw] = useState({ current_password: '', new_password: '', confirm: '' })
  const [pwMsg, setPwMsg] = useState('')
  const [pwErr, setPwErr] = useState('')

  useEffect(() => {
    getMe()
      .then((me) => {
        setUsername(me.username)
        setRoles(me.roles || [])
        setForm({
          display_name: me.display_name || '',
          first_name: me.first_name || '',
          last_name: me.last_name || '',
          email: me.email || '',
          timezone: me.timezone || browserTimezone(),
          theme: me.theme || 'system',
        })
      })
      .catch((err) => setProfileErr(err.message))
  }, [])

  const onField = (key) => (e) => setForm({ ...form, [key]: e.target.value })
  const onPwField = (key) => (e) => setPw({ ...pw, [key]: e.target.value })

  const saveProfile = async (e) => {
    e.preventDefault()
    setProfileMsg('')
    setProfileErr('')
    try {
      await updateMe(form)
      applyTheme(form.theme)
      setProfileMsg('Profile saved.')
      if (onSaved) onSaved()
    } catch (err) {
      setProfileErr(err.message)
    }
  }

  const savePassword = async (e) => {
    e.preventDefault()
    setPwMsg('')
    setPwErr('')
    if (pw.new_password !== pw.confirm) {
      setPwErr('New passwords do not match.')
      return
    }
    try {
      await changePassword(pw.current_password, pw.new_password)
      setPwMsg('Password updated.')
      setPw({ current_password: '', new_password: '', confirm: '' })
    } catch (err) {
      setPwErr('Could not update password. Check your current password and try a stronger new one.')
    }
  }

  return (
    <div>
      <h1>Profile &amp; settings</h1>
      <p className="page-intro">
        Signed in as <strong>{username}</strong>
        {roles.length > 0 && <> · <span className="badge">{roles.join(', ')}</span></>}
      </p>

      <div className="card">
        <h2>Your information</h2>
        {profileMsg && <div className="success">{profileMsg}</div>}
        {profileErr && <div className="error">{profileErr}</div>}
        <form onSubmit={saveProfile}>
          <div className="field">
            <label>Display name</label>
            <input value={form.display_name} onChange={onField('display_name')} placeholder="How your name appears" />
          </div>
          <div className="row">
            <div className="field grow">
              <label>First name</label>
              <input value={form.first_name} onChange={onField('first_name')} />
            </div>
            <div className="field grow">
              <label>Last name</label>
              <input value={form.last_name} onChange={onField('last_name')} />
            </div>
          </div>
          <div className="field">
            <label>Email</label>
            <input type="email" value={form.email} onChange={onField('email')} />
          </div>
          <div className="field">
            <label>Timezone</label>
            <input value={form.timezone} onChange={onField('timezone')} placeholder={browserTimezone()} />
            <p className="card-meta">Detected from your browser on login. Used for availability and scheduling.</p>
          </div>
          <div className="field">
            <label>Theme</label>
            <select value={form.theme} onChange={onField('theme')}>
              <option value="system">System default</option>
              <option value="light">Light</option>
              <option value="dark">Dark</option>
            </select>
          </div>
          <div className="form-actions">
            <button type="submit">Save changes</button>
          </div>
        </form>
      </div>

      {(roles.includes('teacher') || roles.includes('staff')) && <GoogleCalendarCard />}

      <div className="card">
        <h2>Change password</h2>
        {pwMsg && <div className="success">{pwMsg}</div>}
        {pwErr && <div className="error">{pwErr}</div>}
        <form onSubmit={savePassword}>
          <div className="field">
            <label>Current password</label>
            <input type="password" value={pw.current_password} onChange={onPwField('current_password')} />
          </div>
          <div className="field">
            <label>New password</label>
            <input type="password" value={pw.new_password} onChange={onPwField('new_password')} />
          </div>
          <div className="field">
            <label>Confirm new password</label>
            <input type="password" value={pw.confirm} onChange={onPwField('confirm')} />
          </div>
          <div className="form-actions">
            <button type="submit">Update password</button>
          </div>
        </form>
      </div>
    </div>
  )
}
