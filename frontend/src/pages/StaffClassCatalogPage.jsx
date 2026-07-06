import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch } from '../api.js'

function parseTopicLines(text) {
  return text
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
}

export default function StaffClassCatalogPage() {
  const [subjects, setSubjects] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [newSubject, setNewSubject] = useState('')
  const [newLevel, setNewLevel] = useState({ subjectId: '', name: '' })
  const [newFocus, setNewFocus] = useState({ levelId: '', name: '' })
  const [bulkTopics, setBulkTopics] = useState({})

  const load = () => {
    setLoading(true)
    apiFetch('/api/staff/class-catalog/')
      .then((data) => setSubjects(data.subjects || []))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }

  useEffect(load, [])

  const addSubject = async (e) => {
    e.preventDefault()
    setError('')
    setMessage('')
    try {
      await apiFetch('/api/staff/class-catalog/', {
        method: 'POST',
        body: JSON.stringify({ kind: 'subject', name: newSubject.trim() }),
      })
      setNewSubject('')
      setMessage('Subject added.')
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  const addLevel = async (e) => {
    e.preventDefault()
    setError('')
    setMessage('')
    try {
      await apiFetch('/api/staff/class-catalog/', {
        method: 'POST',
        body: JSON.stringify({
          kind: 'level',
          subject_id: Number(newLevel.subjectId),
          name: newLevel.name.trim(),
        }),
      })
      setNewLevel({ subjectId: newLevel.subjectId, name: '' })
      setMessage('Level added.')
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  const addFocus = async (e) => {
    e.preventDefault()
    setError('')
    setMessage('')
    try {
      await apiFetch('/api/staff/class-catalog/', {
        method: 'POST',
        body: JSON.stringify({
          kind: 'focus',
          level_id: Number(newFocus.levelId),
          name: newFocus.name.trim(),
        }),
      })
      setNewFocus({ levelId: newFocus.levelId, name: '' })
      setMessage('Focus added.')
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  const bulkAddTopics = async (focusId) => {
    const text = bulkTopics[focusId] || ''
    const lines = parseTopicLines(text)
    if (!lines.length) {
      setError('Enter at least one topic (one per line).')
      return
    }
    setError('')
    setMessage('')
    try {
      await apiFetch(`/api/staff/class-catalog/focuses/${focusId}/topics/bulk/`, {
        method: 'POST',
        body: JSON.stringify({ topics: text }),
      })
      setBulkTopics((current) => ({ ...current, [focusId]: '' }))
      setMessage(`Added ${lines.length} topic${lines.length === 1 ? '' : 's'}.`)
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  const allLevels = subjects.flatMap((subject) => (
    (subject.levels || []).map((level) => ({ ...level, subjectName: subject.name }))
  ))

  return (
    <div>
      <p className="card-meta"><Link to="/staff">← Staff dashboard</Link></p>
      <h1>Class roadmap</h1>
      <p className="page-intro">
        Define subjects, levels, focuses, and topics once. Teachers pick from these dropdowns when
        creating classes. Bulk-add topics under a focus to build a learning roadmap.
      </p>
      {message && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}

      <form onSubmit={addSubject} className="card">
        <div className="card-title">Add subject</div>
        <div className="row">
          <div className="field grow">
            <label>Name</label>
            <input
              value={newSubject}
              onChange={(e) => setNewSubject(e.target.value)}
              placeholder="Japanese"
              required
            />
          </div>
          <div className="field" style={{ alignSelf: 'end' }}>
            <button type="submit">Add subject</button>
          </div>
        </div>
      </form>

      <form onSubmit={addLevel} className="card">
        <div className="card-title">Add level</div>
        <div className="row">
          <div className="field grow">
            <label>Subject</label>
            <select
              value={newLevel.subjectId}
              onChange={(e) => setNewLevel({ ...newLevel, subjectId: e.target.value })}
              required
            >
              <option value="">Choose subject…</option>
              {subjects.map((subject) => (
                <option key={subject.id} value={subject.id}>{subject.name}</option>
              ))}
            </select>
          </div>
          <div className="field grow">
            <label>Level name</label>
            <input
              value={newLevel.name}
              onChange={(e) => setNewLevel({ ...newLevel, name: e.target.value })}
              placeholder="Beginner"
              required
            />
          </div>
          <div className="field" style={{ alignSelf: 'end' }}>
            <button type="submit" disabled={!subjects.length}>Add level</button>
          </div>
        </div>
      </form>

      <form onSubmit={addFocus} className="card">
        <div className="card-title">Add focus</div>
        <div className="row">
          <div className="field grow">
            <label>Subject · level</label>
            <select
              value={newFocus.levelId}
              onChange={(e) => setNewFocus({ ...newFocus, levelId: e.target.value })}
              required
            >
              <option value="">Choose level…</option>
              {allLevels.map((level) => (
                <option key={level.id} value={level.id}>
                  {level.subjectName} · {level.name}
                </option>
              ))}
            </select>
          </div>
          <div className="field grow">
            <label>Focus name</label>
            <input
              value={newFocus.name}
              onChange={(e) => setNewFocus({ ...newFocus, name: e.target.value })}
              placeholder="Grammar and Vocabulary"
              required
            />
          </div>
          <div className="field" style={{ alignSelf: 'end' }}>
            <button type="submit" disabled={!allLevels.length}>Add focus</button>
          </div>
        </div>
      </form>

      {loading && <p className="page-intro">Loading roadmap…</p>}

      {!loading && subjects.map((subject) => (
        <div key={subject.id} className="card">
          <div className="card-title">{subject.name}</div>
          {(subject.levels || []).map((level) => (
            <div key={level.id} className="roadmap-level">
              <h3>{level.name}</h3>
              {(level.focuses || []).map((focus) => (
                <div key={focus.id} className="roadmap-focus">
                  <div className="card-meta"><strong>{focus.name}</strong></div>
                  {(focus.topics || []).length > 0 && (
                    <ol className="roadmap-topic-list">
                      {focus.topics.map((topic) => (
                        <li key={topic.id}>{topic.title}</li>
                      ))}
                    </ol>
                  )}
                  <div className="field">
                    <label>Bulk-add topics (one per line)</label>
                    <textarea
                      rows={4}
                      value={bulkTopics[focus.id] || ''}
                      onChange={(e) => setBulkTopics({ ...bulkTopics, [focus.id]: e.target.value })}
                      placeholder={'Present Tense Verbs\nHiragana Review\nParticles は and が'}
                    />
                  </div>
                  <button type="button" onClick={() => bulkAddTopics(focus.id)}>
                    Add topics to {focus.name}
                  </button>
                </div>
              ))}
              {!level.focuses?.length && (
                <p className="card-meta">No focuses yet — add one above.</p>
              )}
            </div>
          ))}
          {!subject.levels?.length && (
            <p className="card-meta">No levels yet — add one above.</p>
          )}
        </div>
      ))}
    </div>
  )
}
