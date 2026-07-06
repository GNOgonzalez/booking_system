import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch } from '../api.js'

function findSubject(subjects, name) {
  return subjects.find((item) => item.name === name)
}

function findLevel(subject, name) {
  return subject?.levels?.find((item) => item.name === name)
}

function findFocus(level, name) {
  return level?.focuses?.find((item) => item.name === name)
}

function topicTitlesFromFocus(focus) {
  return (focus?.topics || []).map((topic) => topic.title)
}

export default function ClassCatalogPicker({
  value,
  onChange,
  disabled = false,
  showStaffCatalogLink = false,
}) {
  const [catalog, setCatalog] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    apiFetch('/api/class-catalog/')
      .then((data) => setCatalog(data.subjects || []))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  const subjectOptions = useMemo(() => {
    const names = catalog.map((item) => item.name)
    if (value.subject && !names.includes(value.subject)) {
      return [value.subject, ...names]
    }
    return names
  }, [catalog, value.subject])

  const selectedSubject = findSubject(catalog, value.subject)
  const levelOptions = useMemo(() => {
    const names = (selectedSubject?.levels || []).map((item) => item.name)
    if (value.level && !names.includes(value.level)) {
      return [value.level, ...names]
    }
    return names
  }, [selectedSubject, value.level])

  const selectedLevel = findLevel(selectedSubject, value.level)
  const focusOptions = useMemo(() => {
    const names = (selectedLevel?.focuses || []).map((item) => item.name)
    if (value.focus && !names.includes(value.focus)) {
      return [value.focus, ...names]
    }
    return names
  }, [selectedLevel, value.focus])

  const selectedFocus = findFocus(selectedLevel, value.focus)
  const availableTopics = topicTitlesFromFocus(selectedFocus)
  const selectedTopics = value.topicTitles || []

  const setPartial = (patch) => onChange({ ...value, ...patch })

  const onSubjectChange = (name) => {
    setPartial({
      subject: name,
      level: '',
      focus: '',
      topicTitles: [],
    })
  }

  const onLevelChange = (name) => {
    setPartial({
      level: name,
      focus: '',
      topicTitles: [],
    })
  }

  const onFocusChange = (name) => {
    const level = findLevel(selectedSubject, value.level)
    const focus = findFocus(level, name)
    setPartial({
      focus: name,
      topicTitles: topicTitlesFromFocus(focus),
    })
  }

  const toggleTopic = (title) => {
    const next = selectedTopics.includes(title)
      ? selectedTopics.filter((item) => item !== title)
      : [...selectedTopics, title]
    setPartial({ topicTitles: next })
  }

  if (loading) {
    return <p className="card-meta">Loading class roadmap…</p>
  }

  if (error) {
    return <div className="error">{error}</div>
  }

  if (!catalog.length) {
    return (
      <div className="card-meta">
        No class roadmap defined yet.
        {showStaffCatalogLink && (
          <> <Link to="/staff/class-catalog">Set up subjects, levels, and topics</Link>.</>
        )}
      </div>
    )
  }

  return (
    <>
      <div className="row">
        <div className="field grow">
          <label>Subject</label>
          <select
            value={value.subject}
            onChange={(e) => onSubjectChange(e.target.value)}
            required
            disabled={disabled}
          >
            <option value="">Choose subject…</option>
            {subjectOptions.map((name) => (
              <option key={name} value={name}>{name}</option>
            ))}
          </select>
        </div>
        <div className="field grow">
          <label>Level</label>
          <select
            value={value.level}
            onChange={(e) => onLevelChange(e.target.value)}
            required
            disabled={disabled || !value.subject}
          >
            <option value="">{value.subject ? 'Choose level…' : 'Pick subject first'}</option>
            {levelOptions.map((name) => (
              <option key={name} value={name}>{name}</option>
            ))}
          </select>
        </div>
      </div>
      <div className="field">
        <label>Focus</label>
        <select
          value={value.focus}
          onChange={(e) => onFocusChange(e.target.value)}
          required
          disabled={disabled || !value.level}
        >
          <option value="">{value.level ? 'Choose focus…' : 'Pick level first'}</option>
          {focusOptions.map((name) => (
            <option key={name} value={name}>{name}</option>
          ))}
        </select>
      </div>
      {value.focus && (
        <div className="field">
          <label>Topics</label>
          {availableTopics.length ? (
            <>
              <div className="topic-checklist-actions">
                <button
                  type="button"
                  className="ghost"
                  disabled={disabled}
                  onClick={() => setPartial({ topicTitles: [...availableTopics] })}
                >
                  Select all
                </button>
                <button
                  type="button"
                  className="ghost"
                  disabled={disabled}
                  onClick={() => setPartial({ topicTitles: [] })}
                >
                  Clear
                </button>
              </div>
              <div className="topic-checklist">
                {availableTopics.map((title) => (
                  <label key={title} className="topic-checklist-item">
                    <input
                      type="checkbox"
                      checked={selectedTopics.includes(title)}
                      onChange={() => toggleTopic(title)}
                      disabled={disabled}
                    />
                    <span>{title}</span>
                  </label>
                ))}
              </div>
            </>
          ) : (
            <p className="card-meta">
              No topics under this focus yet.
              {showStaffCatalogLink && (
                <> <Link to="/staff/class-catalog">Bulk-add topics in the roadmap</Link>.</>
              )}
            </p>
          )}
        </div>
      )}
      <label className="checkbox-row">
        <input
          type="checkbox"
          checked={Boolean(value.topics_ordered)}
          onChange={(e) => setPartial({ topics_ordered: e.target.checked })}
          disabled={disabled}
        />
        Teach topics in order (roadmap)
      </label>
    </>
  )
}

export function catalogSelectionToTopics(topicTitles) {
  return topicTitles.map((title, index) => ({ title, sort_order: index }))
}

export const EMPTY_CATALOG_SELECTION = {
  subject: '',
  level: '',
  focus: '',
  topicTitles: [],
  topics_ordered: false,
}
