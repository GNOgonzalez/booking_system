import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch } from '../api.js'
import { useGlossary } from '../hooks/useGlossary.jsx'

const EMPTY_FORM = {
  id: null,
  name: '',
  description: '',
  plan_type: 'subscription',
  price_dollars: '',
  billing_period_days: '30',
  ticket_allowance: '10',
  is_active: true,
  allowed_class_ids: [],
}

function dollarsToCents(value) {
  const amount = Number.parseFloat(value)
  if (Number.isNaN(amount) || amount < 0) return null
  return Math.round(amount * 100)
}

export default function StaffMembershipPlansPage() {
  const { labels, label } = useGlossary()
  const [plans, setPlans] = useState([])
  const [classes, setClasses] = useState([])
  const [form, setForm] = useState(EMPTY_FORM)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [saving, setSaving] = useState(false)

  const load = () => {
    Promise.all([
      apiFetch('/api/staff/membership-plans/'),
      apiFetch('/api/staff/class-offerings/'),
    ])
      .then(([planRows, classRows]) => {
        setPlans(planRows)
        setClasses(classRows)
      })
      .catch((err) => setError(err.message))
  }

  useEffect(load, [])

  const editing = form.id != null

  const selectedClassSet = useMemo(
    () => new Set(form.allowed_class_ids.map(String)),
    [form.allowed_class_ids],
  )

  const resetForm = () => setForm(EMPTY_FORM)

  const editPlan = (plan) => {
    setForm({
      id: plan.id,
      name: plan.name,
      description: plan.description || '',
      plan_type: plan.plan_type || 'subscription',
      price_dollars: (plan.price_cents / 100).toFixed(2),
      billing_period_days: String(plan.billing_period_days),
      ticket_allowance: String(plan.ticket_allowance),
      is_active: plan.is_active,
      allowed_class_ids: plan.allowed_classes.map((item) => item.id),
    })
    setError('')
    setMessage('')
  }

  const toggleClass = (classId) => {
    setForm((current) => {
      const ids = new Set(current.allowed_class_ids.map(String))
      const key = String(classId)
      if (ids.has(key)) ids.delete(key)
      else ids.add(key)
      return { ...current, allowed_class_ids: [...ids].map(Number) }
    })
  }

  const save = async (e) => {
    e.preventDefault()
    const priceCents = dollarsToCents(form.price_dollars)
    if (priceCents == null) {
      setError('Enter a valid price.')
      return
    }
    setSaving(true)
    setError('')
    setMessage('')
    const payload = {
      name: form.name.trim(),
      description: form.description.trim(),
      plan_type: form.plan_type,
      price_cents: priceCents,
      billing_period_days: Number(form.billing_period_days),
      ticket_allowance: Number(form.ticket_allowance),
      is_active: form.is_active,
      allowed_class_ids: form.allowed_class_ids,
    }
    try {
      if (editing) {
        await apiFetch(`/api/staff/membership-plans/${form.id}/`, {
          method: 'PATCH',
          body: JSON.stringify(payload),
        })
        setMessage('Membership plan updated.')
      } else {
        await apiFetch('/api/staff/membership-plans/', {
          method: 'POST',
          body: JSON.stringify(payload),
        })
        setMessage('Membership plan created.')
      }
      resetForm()
      load()
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  const removePlan = async (plan) => {
    if (!window.confirm(`Delete "${plan.name}"?`)) return
    setError('')
    setMessage('')
    try {
      await apiFetch(`/api/staff/membership-plans/${plan.id}/`, { method: 'DELETE' })
      setMessage('Membership plan deleted.')
      if (form.id === plan.id) resetForm()
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div>
      <h1>Membership plans</h1>
      <p className="page-intro">
        Create subscriptions and one-off ticket packs. Ticket packs top up an existing subject membership.
      </p>
      <p className="card-meta"><Link to="/staff">← Back to staff dashboard</Link></p>
      {message && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}

      <form onSubmit={save} className="card">
        <h2>{editing ? 'Edit plan' : 'New plan'}</h2>
        <div className="field">
          <label>Name</label>
          <input
            value={form.name}
            onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
            required
          />
        </div>
        <div className="field">
          <label>Description</label>
          <textarea
            rows={2}
            value={form.description}
            onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
          />
        </div>
        <div className="field">
          <label>Plan type</label>
          <select
            value={form.plan_type}
            onChange={(e) => setForm((f) => ({
              ...f,
              plan_type: e.target.value,
              billing_period_days: e.target.value === 'ticket_pack' ? '0' : (f.billing_period_days === '0' ? '30' : f.billing_period_days),
              ticket_allowance: e.target.value === 'ticket_pack' && f.ticket_allowance === '10' ? '1' : f.ticket_allowance,
            }))}
          >
            <option value="subscription">Subscription (recurring)</option>
            <option value="ticket_pack">Ticket pack (single purchase)</option>
          </select>
        </div>
        <div className="row">
          <div className="field grow">
            <label>Price (USD)</label>
            <input
              type="number"
              min="0"
              step="0.01"
              value={form.price_dollars}
              onChange={(e) => setForm((f) => ({ ...f, price_dollars: e.target.value }))}
              required
            />
          </div>
          <div className="field grow">
            <label>{form.plan_type === 'ticket_pack' ? 'Billing period (days, use 0)' : 'Billing period (days)'}</label>
            <input
              type="number"
              min="0"
              value={form.billing_period_days}
              onChange={(e) => setForm((f) => ({ ...f, billing_period_days: e.target.value }))}
              required
            />
          </div>
          <div className="field grow">
            <label>{form.plan_type === 'ticket_pack' ? 'Tickets in pack' : 'Tickets per period'}</label>
            <input
              type="number"
              min="0"
              value={form.ticket_allowance}
              onChange={(e) => setForm((f) => ({ ...f, ticket_allowance: e.target.value }))}
              required
            />
          </div>
        </div>
        <div className="field">
          <label>
            <input
              type="checkbox"
              checked={form.is_active}
              onChange={(e) => setForm((f) => ({ ...f, is_active: e.target.checked }))}
            />
            {' '}Active (available for purchase)
          </label>
        </div>
        <div className="field">
          <label>Included {labels('class').toLowerCase()}</label>
          {!classes.length ? (
            <p className="card-meta">No active {labels('class').toLowerCase()} in the catalog yet.</p>
          ) : (
            <div className="membership-class-grid">
              {classes.map((item) => (
                <label key={item.id} className="membership-class-option">
                  <input
                    type="checkbox"
                    checked={selectedClassSet.has(String(item.id))}
                    onChange={() => toggleClass(item.id)}
                  />
                  <span>{item.label}</span>
                </label>
              ))}
            </div>
          )}
          <p className="card-meta">No selection = all {labels('class').toLowerCase()} included.</p>
        </div>
        <div className="form-actions">
          <button type="submit" disabled={saving}>
            {saving ? 'Saving…' : editing ? 'Save changes' : 'Create plan'}
          </button>
          {editing && (
            <button type="button" className="secondary" onClick={resetForm}>Cancel edit</button>
          )}
        </div>
      </form>

      <h2 style={{ marginTop: '1.5rem' }}>Existing plans</h2>
      {plans.map((plan) => (
        <div key={plan.id} className={`card${plan.is_active ? '' : ' card--inactive'}`}>
          <div className="card-row">
            <div>
              <div className="card-title">
                {plan.name}
                {plan.plan_type === 'ticket_pack' ? (
                  <span className="badge">Ticket pack</span>
                ) : (
                  <span className="badge badge--muted">Subscription</span>
                )}
                {!plan.is_active && <span className="badge badge--muted">Inactive</span>}
              </div>
              <div className="card-meta">
                {plan.price_display}
                {plan.plan_type === 'ticket_pack'
                  ? ` · ${plan.ticket_allowance} ticket${plan.ticket_allowance === 1 ? '' : 's'}`
                  : ` · ${plan.billing_period_days} days · ${plan.ticket_allowance} ticket${plan.ticket_allowance === 1 ? '' : 's'}`}
                {' · '}
                {plan.includes_all_classes
                  ? `All ${labels('class').toLowerCase()}`
                  : `${plan.allowed_classes.length} ${labels('class').toLowerCase()}`}
              </div>
              {plan.description && <p className="card-meta">{plan.description}</p>}
            </div>
            <div className="row-actions">
              <button type="button" className="secondary" onClick={() => editPlan(plan)}>Edit</button>
              <button type="button" className="danger" onClick={() => removePlan(plan)}>Delete</button>
            </div>
          </div>
          {!plan.includes_all_classes && plan.allowed_classes.length > 0 && (
            <ul className="membership-class-list">
              {plan.allowed_classes.map((item) => (
                <li key={item.id}>{item.label}</li>
              ))}
            </ul>
          )}
        </div>
      ))}
      {!plans.length && !error && (
        <p className="card-meta">No membership plans yet. Create one above.</p>
      )}
    </div>
  )
}
