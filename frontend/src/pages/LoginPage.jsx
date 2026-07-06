import { useState } from 'react'
import { useBranding } from '../hooks/useBranding.jsx'

export default function LoginPage({ onLogin }) {
  const { branding } = useBranding()
  const [username, setUsername] = useState('demo_student')
  const [password, setPassword] = useState('demo1234')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await onLogin(username, password)
    } catch {
      setError('Login failed. Check your credentials.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-wrap">
      <div className="auth-card">
        <div className="auth-brand">
          {branding.logo_url && (
            <img src={branding.logo_url} alt="" className="branding-logo branding-logo--auth" />
          )}
          <h1>{branding.display_name}</h1>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="field">
            <label>Username</label>
            <input value={username} onChange={(e) => setUsername(e.target.value)} autoFocus />
          </div>
          <div className="field">
            <label>Password</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          </div>
          {error && <div className="error">{error}</div>}
          <button type="submit" className="btn-block" disabled={loading}>
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
        <p className="auth-hint">Demo: demo_student / demo_teacher · demo1234</p>
      </div>
    </div>
  )
}
