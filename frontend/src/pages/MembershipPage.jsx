import { useEffect, useState } from 'react'
import { apiFetch } from '../api.js'

export default function MembershipPage() {
  const [membership, setMembership] = useState(null)
  const [plan, setPlan] = useState('basic')
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const load = () => {
    apiFetch('/api/membership/')
      .then(setMembership)
      .catch((err) => setError(err.message))
  }

  useEffect(load, [])

  const purchase = async (e) => {
    e.preventDefault()
    setError('')
    setMessage('')
    try {
      await apiFetch('/api/membership/', {
        method: 'POST',
        body: JSON.stringify({ plan_type: plan, months: 1 }),
      })
      setMessage('Membership active!')
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div>
      <h1>Membership</h1>
      {message && <p className="success">{message}</p>}
      {error && <p className="error">{error}</p>}
      {membership && membership.active ? (
        <p className="success">
          Active: {membership.plan_type}
          {membership.valid_until ? ` until ${membership.valid_until}` : ''}
        </p>
      ) : (
        <p>No active membership. Booking requires one.</p>
      )}
      <form onSubmit={purchase}>
        <select value={plan} onChange={(e) => setPlan(e.target.value)}>
          <option value="basic">Basic</option>
          <option value="premium">Premium</option>
        </select>
        <button type="submit">Purchase (mock)</button>
      </form>
    </div>
  )
}
