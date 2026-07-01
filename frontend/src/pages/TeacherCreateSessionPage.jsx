import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiFetch } from '../api.js'

export default function TeacherCreateSessionPage() {
  const navigate = useNavigate()
  const [title, setTitle] = useState('')
  const [start, setStart] = useState('')
  const [end, setEnd] = useState('')
  const [capacity, setCapacity] = useState(1)
  const [error, setError] = useState('')

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    try {
      await apiFetch('/api/teacher/sessions/', {
        method: 'POST',
        body: JSON.stringify({
          title,
          start_time: start,
          end_time: end,
          capacity: Number(capacity),
        }),
      })
      navigate('/teacher/sessions')
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div>
      <h1>Create session</h1>
      {error && <p className="error">{error}</p>}
      <form onSubmit={submit} className="card">
        <p><input placeholder="Title" value={title} onChange={(e) => setTitle(e.target.value)} /></p>
        <p>Start <input type="datetime-local" value={start} onChange={(e) => setStart(e.target.value)} /></p>
        <p>End <input type="datetime-local" value={end} onChange={(e) => setEnd(e.target.value)} /></p>
        <p>Capacity <input type="number" min="1" value={capacity} onChange={(e) => setCapacity(e.target.value)} /></p>
        <button type="submit">Create</button>
      </form>
    </div>
  )
}
