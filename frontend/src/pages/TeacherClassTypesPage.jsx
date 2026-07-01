import { useEffect, useState } from 'react'
import { apiFetch } from '../api.js'

export default function TeacherClassTypesPage() {
  const [classTypes, setClassTypes] = useState([])
  const [name, setName] = useState('')
  const [capacity, setCapacity] = useState(1)
  const [error, setError] = useState('')

  const load = () => {
    apiFetch('/api/teacher/class-types/')
      .then(setClassTypes)
      .catch((err) => setError(err.message))
  }

  useEffect(load, [])

  const add = async (e) => {
    e.preventDefault()
    setError('')
    try {
      await apiFetch('/api/teacher/class-types/', {
        method: 'POST',
        body: JSON.stringify({ name, default_capacity: Number(capacity), is_active: true, description: '' }),
      })
      setName('')
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div>
      <h1>Class types</h1>
      {error && <p className="error">{error}</p>}
      <form onSubmit={add} className="card">
        <input placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} />
        <input type="number" min="1" value={capacity} onChange={(e) => setCapacity(e.target.value)} />
        <button type="submit">Add</button>
      </form>
      {classTypes.map((ct) => (
        <div key={ct.id} className="card">
          <strong>{ct.name}</strong> — capacity {ct.default_capacity} {ct.is_active ? '(active)' : '(inactive)'}
        </div>
      ))}
      {!classTypes.length && !error && <p>No class types yet.</p>}
    </div>
  )
}
