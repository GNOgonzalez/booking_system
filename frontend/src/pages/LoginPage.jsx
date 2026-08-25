import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useBranding } from '../hooks/useBranding.jsx'

export default function LoginPage({ onLogin }) {
  const { branding } = useBranding()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
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
        <p className="auth-footer">
          New here? <Link to="/register">Create a student account</Link>
        </p>
        <p className="auth-hint">
          Demo: <code>demo_student</code> / <code>demo_teacher</code> / <code>demo_staff</code> · password{' '}
          <code>demo1234</code>
        </p>
      </div>
    </div>
  )
}
