import { useEffect, useState } from 'react'
import { apiUpload } from '../api.js'
import { clearBrandingCache, useBranding } from '../hooks/useBranding.jsx'
import { useUploadLimits } from '../hooks/useUploadLimits.js'

function logoHint(limits) {
  if (!limits) return null
  const exts = (limits.logo_extensions || []).join(', ')
  return `Max ${limits.logo_max_mb} MB${exts ? ` · ${exts}` : ''}`
}

export default function StaffBrandingPage() {
  const { branding, reload } = useBranding()
  const limits = useUploadLimits()
  const hint = logoHint(limits)

  const [displayName, setDisplayName] = useState('')
  const [logoFile, setLogoFile] = useState(null)
  const [clearLogo, setClearLogo] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    setDisplayName(branding.display_name || '')
    setClearLogo(false)
    setLogoFile(null)
  }, [branding])

  const submit = async (e) => {
    e.preventDefault()
    setSaving(true)
    setError('')
    setMessage('')
    try {
      const data = new FormData()
      data.append('display_name', displayName.trim())
      if (logoFile) data.append('logo', logoFile)
      if (clearLogo) data.append('clear_logo', 'true')
      await apiUpload('/api/staff/branding/', data, { method: 'PATCH' })
      clearBrandingCache()
      reload()
      setLogoFile(null)
      setClearLogo(false)
      setMessage('Branding saved.')
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  const showLogo = !clearLogo && (logoFile ? URL.createObjectURL(logoFile) : branding.logo_url)

  return (
    <div>
      <h1>Sign-in branding</h1>
      <p className="page-intro">
        Customize the app name and logo shown on the sign-in screen and in the sidebar header.
      </p>
      {message && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}

      <form onSubmit={submit} className="card">
        <div className="field">
          <label>Display name</label>
          <input
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            required
            maxLength={120}
            placeholder="Booking Studio"
          />
        </div>

        <div className="field">
          <label>Logo (optional)</label>
          <input
            type="file"
            accept="image/*"
            onChange={(e) => {
              setLogoFile(e.target.files?.[0] || null)
              setClearLogo(false)
            }}
          />
          {hint && <p className="card-meta">{hint}</p>}
        </div>

        {showLogo && (
          <div className="branding-preview">
            <img src={showLogo} alt="" className="branding-logo" />
            <button
              type="button"
              className="ghost"
              onClick={() => {
                setLogoFile(null)
                setClearLogo(true)
              }}
            >
              Remove logo
            </button>
          </div>
        )}

        <button type="submit" disabled={saving}>
          {saving ? 'Saving…' : 'Save branding'}
        </button>
      </form>

      <div className="card auth-card branding-preview-card">
        <p className="card-meta">Sign-in preview</p>
        <div className="auth-brand">
          {showLogo && <img src={showLogo} alt="" className="branding-logo branding-logo--auth" />}
          <h2>{displayName.trim() || 'Booking Studio'}</h2>
        </div>
      </div>
    </div>
  )
}
