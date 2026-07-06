import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch } from '../api.js'

export default function StaffGlossaryPage() {
  const [terms, setTerms] = useState([])
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [saving, setSaving] = useState(false)

  const load = () => {
    apiFetch('/api/staff/glossary/')
      .then(setTerms)
      .catch((err) => setError(err.message))
  }

  useEffect(load, [])

  const update = (key, field, value) => {
    setTerms((rows) => rows.map((r) => (r.key === key ? { ...r, [field]: value } : r)))
  }

  const resetTerm = (key) => {
    setTerms((rows) => rows.map((r) => (
      r.key === key
        ? { ...r, singular: r.default_singular, plural: r.default_plural }
        : r
    )))
  }

  const save = async (e) => {
    e.preventDefault()
    setSaving(true)
    setError('')
    setMessage('')
    try {
      const payload = Object.fromEntries(
        terms.map((t) => [t.key, { singular: t.singular, plural: t.plural }]),
      )
      const updated = await apiFetch('/api/staff/glossary/', {
        method: 'PATCH',
        body: JSON.stringify({ terms: payload }),
      })
      setTerms(updated)
      setMessage('Glossary saved.')
      window.dispatchEvent(new Event('glossary-updated'))
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <h1>Studio glossary</h1>
      <p className="page-intro">
        Rename terms across the app. For example, call students &quot;clients&quot; or catalog
        entries &quot;programs&quot; while keeping calendar items as &quot;sessions.&quot;
      </p>
      <p className="card-meta"><Link to="/staff">← Back to staff dashboard</Link></p>
      {message && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}

      <form onSubmit={save} className="card">
        <p className="card-meta" style={{ marginBottom: '1rem' }}>
          <strong>Class</strong> = teachable catalog template · <strong>Session</strong> = scheduled slot on the calendar.
        </p>

        {terms.map((term) => (
          <div key={term.key} className="glossary-row card" style={{ marginBottom: '0.75rem' }}>
            <div className="card-meta">{term.description}</div>
            <div className="card-title" style={{ fontSize: '0.95rem' }}>Key: {term.key}</div>
            <div className="row">
              <div className="field grow">
                <label>Singular</label>
                <input
                  value={term.singular}
                  onChange={(e) => update(term.key, 'singular', e.target.value)}
                  required
                />
              </div>
              <div className="field grow">
                <label>Plural</label>
                <input
                  value={term.plural}
                  onChange={(e) => update(term.key, 'plural', e.target.value)}
                  required
                />
              </div>
            </div>
            <button type="button" className="ghost" onClick={() => resetTerm(term.key)}>
              Reset to default ({term.default_singular} / {term.default_plural})
            </button>
          </div>
        ))}

        <div className="form-actions">
          <button type="submit" disabled={saving || !terms.length}>
            {saving ? 'Saving…' : 'Save glossary'}
          </button>
        </div>
      </form>
    </div>
  )
}
