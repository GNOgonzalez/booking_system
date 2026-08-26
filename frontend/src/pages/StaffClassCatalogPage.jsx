import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch } from '../api.js'

const KIND_LABELS = {
  subject: 'subject',
  level: 'level',
  focus: 'focus',
  topic: 'topic',
}

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
  const [editing, setEditing] = useState(null)
  const [editName, setEditName] = useState('')

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

  const nodePath = (kind, node) => `/api/staff/class-catalog/${kind}/${node.id}/`

  const startRename = (kind, node) => {
    setEditing({ kind, id: node.id })
    setEditName(kind === 'topic' ? node.title : node.name)
  }

  const saveRename = async (e, kind, node) => {
    e.preventDefault()
    setError('')
    setMessage('')
    try {
      await apiFetch(nodePath(kind, node), {
        method: 'PATCH',
        body: JSON.stringify({ name: editName.trim() }),
      })
      setEditing(null)
      setMessage(`${KIND_LABELS[kind]} renamed. Existing classes were updated to match.`)
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  const toggleActive = async (kind, node) => {
    setError('')
    setMessage('')
    try {
      await apiFetch(nodePath(kind, node), {
        method: 'PATCH',
        body: JSON.stringify({ is_active: !node.is_active }),
      })
      setMessage(`${KIND_LABELS[kind]} ${node.is_active ? 'hidden from pickers' : 'restored'}.`)
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  const removeNode = async (kind, node, childCount) => {
    const name = kind === 'topic' ? node.title : node.name
    const extra = childCount
      ? ` This also removes ${childCount} entr${childCount === 1 ? 'y' : 'ies'} beneath it.`
      : ''
    if (!window.confirm(`Delete ${KIND_LABELS[kind]} "${name}"?${extra}`)) return
    setError('')
    setMessage('')
    try {
      await apiFetch(nodePath(kind, node), { method: 'DELETE' })
      setMessage(`${KIND_LABELS[kind]} "${name}" deleted.`)
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  const nodeActions = (kind, node, childCount = 0) => (
    <div className="row-actions">
      <button type="button" className="ghost" onClick={() => startRename(kind, node)}>Rename</button>
      <button type="button" className="ghost" onClick={() => toggleActive(kind, node)}>
        {node.is_active ? 'Hide' : 'Restore'}
      </button>
      <button type="button" className="danger" onClick={() => removeNode(kind, node, childCount)}>
        Delete
      </button>
    </div>
  )

  const renameForm = (kind, node) => (
    <form onSubmit={(e) => saveRename(e, kind, node)} className="row">
      <div className="field grow">
        <label>New {KIND_LABELS[kind]} name</label>
        <input value={editName} onChange={(e) => setEditName(e.target.value)} required />
      </div>
      <div className="field" style={{ alignSelf: 'end' }}>
        <button type="submit">Save</button>
      </div>
      <div className="field" style={{ alignSelf: 'end' }}>
        <button type="button" className="secondary" onClick={() => setEditing(null)}>Cancel</button>
      </div>
    </form>
  )

  const isEditing = (kind, node) => editing?.kind === kind && editing?.id === node.id

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
      <p className="card-meta">
        <strong>Hide</strong> keeps history intact and removes an entry from teacher dropdowns.
        <strong> Delete</strong> is blocked while any class still uses the entry.
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
        <div key={subject.id} className={`card${subject.is_active ? '' : ' card--inactive'}`}>
          <div className="card-row">
            <div className="card-title">
              {subject.name}
              {!subject.is_active && <span className="badge badge--muted">Hidden</span>}
            </div>
            {nodeActions('subject', subject, (subject.levels || []).length)}
          </div>
          {isEditing('subject', subject) && renameForm('subject', subject)}

          {(subject.levels || []).map((level) => (
            <div key={level.id} className="roadmap-level">
              <div className="card-row">
                <h3>
                  {level.name}
                  {!level.is_active && <span className="badge badge--muted">Hidden</span>}
                </h3>
                {nodeActions('level', level, (level.focuses || []).length)}
              </div>
              {isEditing('level', level) && renameForm('level', level)}

              {(level.focuses || []).map((focus) => (
                <div key={focus.id} className="roadmap-focus">
                  <div className="card-row">
                    <div className="card-meta">
                      <strong>{focus.name}</strong>
                      {!focus.is_active && <span className="badge badge--muted">Hidden</span>}
                    </div>
                    {nodeActions('focus', focus, (focus.topics || []).length)}
                  </div>
                  {isEditing('focus', focus) && renameForm('focus', focus)}

                  {(focus.topics || []).length > 0 && (
                    <ol className="roadmap-topic-list">
                      {focus.topics.map((topic) => (
                        <li key={topic.id}>
                          <div className="card-row">
                            <span>
                              {topic.title}
                              {!topic.is_active && <span className="badge badge--muted">Hidden</span>}
                            </span>
                            {nodeActions('topic', topic)}
                          </div>
                          {isEditing('topic', topic) && renameForm('topic', topic)}
                        </li>
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
