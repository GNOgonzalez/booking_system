import { useEffect, useState } from 'react'
import { apiFetch } from '../api.js'

export default function CurriculumPage() {
  const [items, setItems] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    apiFetch('/api/curriculum/')
      .then(setItems)
      .catch((err) => setError(err.message))
  }, [])

  return (
    <div>
      <h1>Curriculum</h1>
      {error && <p className="error">{error}</p>}
      {items.map((item) => (
        <div key={item.id} className="card">
          <h2>{item.title}</h2>
          <p>{item.content}</p>
        </div>
      ))}
      {!items.length && !error && <p>No curriculum items.</p>}
    </div>
  )
}
