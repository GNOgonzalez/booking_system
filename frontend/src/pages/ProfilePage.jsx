import { useEffect, useState } from 'react'
import { changePassword, getMe, updateMe } from '../api.js'

export default function ProfilePage({ onSaved }) {
  const [form, setForm] = useState({
    display_name: '',
    first_name: '',
    last_name: '',
    email: '',
    timezone: 'UTC',
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
          timezone: me.timezone || 'UTC',
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
            <input value={form.timezone} onChange={onField('timezone')} placeholder="e.g. UTC, America/New_York" />
          </div>
          <div className="form-actions">
            <button type="submit">Save changes</button>
          </div>
        </form>
      </div>

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
