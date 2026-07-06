import { useEffect, useState } from 'react'
import { apiFetch } from '../api.js'
import HomeworkThread from '../components/HomeworkThread.jsx'

export default function StudentHomeworkPage() {
  const [assignments, setAssignments] = useState([])
  const [selected, setSelected] = useState(null)
  const [error, setError] = useState('')

  const loadList = () => {
    apiFetch('/api/progress/homework/')
      .then(setAssignments)
      .catch((err) => setError(err.message))
  }

  const loadDetail = (id) => {
    apiFetch(`/api/progress/homework/${id}/`)
      .then(setSelected)
      .catch((err) => setError(err.message))
  }

  useEffect(loadList, [])

  const open = (id) => {
    setError('')
    loadDetail(id)
  }

  const onUpdated = (updated) => {
    setSelected(updated)
    loadList()
  }

  return (
    <div className="homework-layout">
      <div>
        <h1>Homework</h1>
        <p className="page-intro">
          Files from your teacher (kept 7 days) and journal prompts you can write in anytime.
        </p>
        {error && <div className="error">{error}</div>}

        {assignments.map((item) => (
          <button
            key={item.id}
            type="button"
            className={`card homework-list-card${selected?.id === item.id ? ' homework-list-card--active' : ''}`}
            onClick={() => open(item.id)}
          >
            <div className="card-title">
              {item.title || (item.kind === 'journal' ? 'Journal prompt' : 'File exchange')}
            </div>
            <div className="card-meta">
              {item.kind === 'journal' ? 'Journal' : 'Files'}
              {item.session_title && <> · {item.session_title}</>}
              {' · '}
              {item.teacher_name}
              {' · '}
              {item.entry_count} message{item.entry_count === 1 ? '' : 's'}
              {!item.is_expired && item.kind === 'file' && item.days_remaining != null && (
                <> · {item.days_remaining}d left</>
              )}
            </div>
          </button>
        ))}
        {!assignments.length && !error && (
          <p className="card-meta">No homework yet. Your teacher can send files or journal prompts here.</p>
        )}
      </div>

      <HomeworkThread
        assignment={selected}
        onUpdated={onUpdated}
        postPath={selected ? `/api/progress/homework/${selected.id}/entries/` : ''}
        replyLabel={selected?.kind === 'journal' ? 'Add journal entry' : 'Send reply'}
      />
    </div>
  )
}
