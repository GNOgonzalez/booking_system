import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch } from '../api.js'

export default function OnboardingChecklist() {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  const load = () => {
    apiFetch('/api/me/onboarding/')
      .then(setData)
      .catch((err) => setError(err.message))
  }

  useEffect(load, [])

  const dismiss = async () => {
    try {
      const next = await apiFetch('/api/me/onboarding/', {
        method: 'PATCH',
        body: JSON.stringify({ dismissed: true }),
      })
      setData(next)
    } catch (err) {
      setError(err.message)
    }
  }

  if (error) return null
  if (!data || data.dismissed || data.complete || !data.steps?.length) return null

  const done = data.steps.filter((s) => s.completed).length

  return (
    <div className="card onboarding-card">
      <div className="card-title">Getting started</div>
      <p className="card-meta">
        {done} of {data.steps.length} complete — finish these steps to get the most from the app.
      </p>
      <ol className="onboarding-list">
        {data.steps.map((step) => (
          <li key={step.key} className={step.completed ? 'onboarding-step onboarding-step--done' : 'onboarding-step'}>
            {step.completed ? (
              <span className="onboarding-check" aria-hidden="true">✓</span>
            ) : (
              <span className="onboarding-check onboarding-check--open" aria-hidden="true">○</span>
            )}
            {step.completed ? (
              <span>{step.label}</span>
            ) : (
              <Link to={step.path}>{step.label}</Link>
            )}
          </li>
        ))}
      </ol>
      <div className="form-actions">
        <button type="button" className="ghost" onClick={dismiss}>Dismiss checklist</button>
      </div>
    </div>
  )
}
