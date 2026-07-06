import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch } from '../api.js'

const PROVIDER_HINTS = {
  openai: { base: 'Leave blank for OpenAI default.', model: 'e.g. gpt-4o-mini' },
  anthropic: { base: 'Leave blank for Anthropic default.', model: 'e.g. claude-sonnet-4-20250514' },
  ollama: { base: 'e.g. http://127.0.0.1:11434', model: 'e.g. llama3.2' },
  openai_compatible: { base: 'Your host base URL (…/v1)', model: 'Model id your host expects' },
}

export default function StaffLLMSettingsPage() {
  const [config, setConfig] = useState(null)
  const [form, setForm] = useState({
    provider: 'openai',
    base_url: '',
    model_name: '',
    is_enabled: false,
    max_tokens: 500,
    api_key: '',
  })
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)

  const load = () => {
    apiFetch('/api/staff/llm/')
      .then((data) => {
        setConfig(data)
        setForm({
          provider: data.provider,
          base_url: data.base_url || '',
          model_name: data.model_name || '',
          is_enabled: data.is_enabled,
          max_tokens: data.max_tokens,
          api_key: '',
        })
      })
      .catch((err) => setError(err.message))
  }

  useEffect(load, [])

  const hint = PROVIDER_HINTS[form.provider] || PROVIDER_HINTS.openai

  const save = async (e) => {
    e.preventDefault()
    setSaving(true)
    setError('')
    setMessage('')
    try {
      const payload = {
        provider: form.provider,
        base_url: form.base_url,
        model_name: form.model_name,
        is_enabled: form.is_enabled,
        max_tokens: Number(form.max_tokens),
      }
      if (form.api_key.trim()) {
        payload.api_key = form.api_key.trim()
      }
      const updated = await apiFetch('/api/staff/llm/', {
        method: 'PATCH',
        body: JSON.stringify(payload),
      })
      setConfig(updated)
      setForm((f) => ({ ...f, api_key: '' }))
      setMessage('AI settings saved.')
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  const test = async () => {
    setTesting(true)
    setError('')
    setMessage('')
    try {
      const result = await apiFetch('/api/staff/llm/test/', { method: 'POST', body: '{}' })
      setMessage(`Connection OK. Model replied: “${result.sample}”`)
    } catch (err) {
      setError(err.message)
    } finally {
      setTesting(false)
    }
  }

  if (!config) {
    return <div>{error ? <div className="error">{error}</div> : <p className="card-meta">Loading…</p>}</div>
  }

  return (
    <div>
      <h1>AI settings</h1>
      <p className="page-intro">
        Connect your studio&apos;s LLM. Teachers need the <strong>Use AI</strong> permission
        (set per teacher under Permissions) before they can draft session notes.
      </p>
      <p className="card-meta"><Link to="/staff">← Back to staff dashboard</Link></p>
      {message && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}

      <form onSubmit={save} className="card">
        <label className="permission-row card" style={{ marginBottom: '1rem' }}>
          <input
            type="checkbox"
            checked={form.is_enabled}
            onChange={(e) => setForm({ ...form, is_enabled: e.target.checked })}
          />
          <div>
            <div className="card-title">Enable studio AI</div>
            <div className="card-meta">When off, no teacher can use AI features regardless of permission.</div>
          </div>
        </label>

        <div className="field">
          <label>Provider</label>
          <select
            value={form.provider}
            onChange={(e) => setForm({ ...form, provider: e.target.value })}
          >
            {(config.providers || []).map((p) => (
              <option key={p.value} value={p.value}>{p.label}</option>
            ))}
          </select>
        </div>

        <div className="field">
          <label>API key</label>
          <input
            type="password"
            value={form.api_key}
            onChange={(e) => setForm({ ...form, api_key: e.target.value })}
            placeholder={config.has_api_key ? `Saved (${config.api_key_masked}) — leave blank to keep` : 'Paste API key'}
            autoComplete="off"
          />
          {form.provider === 'ollama' && (
            <p className="card-meta">Ollama on localhost usually needs no key.</p>
          )}
        </div>

        <div className="field">
          <label>Base URL</label>
          <input
            value={form.base_url}
            onChange={(e) => setForm({ ...form, base_url: e.target.value })}
            placeholder={hint.base}
          />
        </div>

        <div className="field">
          <label>Model</label>
          <input
            value={form.model_name}
            onChange={(e) => setForm({ ...form, model_name: e.target.value })}
            placeholder={hint.model}
            required
          />
        </div>

        <div className="field">
          <label>Max tokens per request</label>
          <input
            type="number"
            min={50}
            max={4000}
            value={form.max_tokens}
            onChange={(e) => setForm({ ...form, max_tokens: e.target.value })}
          />
        </div>

        <div className="form-actions row-actions">
          <button type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save settings'}</button>
          <button type="button" className="secondary" onClick={test} disabled={testing}>
            {testing ? 'Testing…' : 'Test connection'}
          </button>
        </div>
      </form>
    </div>
  )
}
