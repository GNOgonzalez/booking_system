import { useEffect, useState } from 'react'
import { apiFetch } from '../api.js'

const PERIODS = [7, 30, 90]

function SignalsPanel({ signals }) {
  if (!signals) return null
  if (!signals.report_count) {
    return <p className="card-meta">No session reports in the last {signals.days} days yet.</p>
  }
  return (
    <div>
      <div className="card-meta">
        From {signals.report_count} report(s) in the last {signals.days} days
      </div>
      <ul className="adaptive-signal-list">
        {signals.dimensions.map((dim) => (
          <li key={dim.key}>
            <span>{dim.label}</span>
            <span className="adaptive-bar" aria-hidden="true">
              <span
                className={`adaptive-bar__fill${dim.is_weak ? ' adaptive-bar__fill--weak' : ''}`}
                style={{ width: `${Math.round(Math.min(dim.ratio, 1) * 100)}%` }}
              />
            </span>
            <span className="card-meta">
              {dim.average}/{dim.max}{dim.is_weak ? ' · needs work' : ''}
            </span>
          </li>
        ))}
      </ul>
      {signals.recent_notes[0] && (
        <p className="card-meta">
          Last note ({signals.recent_notes[0].date}): {signals.recent_notes[0].excerpt}
        </p>
      )}
    </div>
  )
}

function SuggestionCard({ suggestion, canEdit, busy, onAccept, onDismiss }) {
  return (
    <div className="card">
      <div className="card-row">
        <div>
          <div className="card-title">{suggestion.title}</div>
          <div className="card-meta">
            {suggestion.kind_label}
            {suggestion.target_module?.cefr_level ? ` · ${suggestion.target_module.cefr_level}` : ''}
            {' · '}
            {suggestion.source === 'llm' ? 'AI' : 'Rules'}
          </div>
          {suggestion.rationale && <p>{suggestion.rationale}</p>}
          {suggestion.content && <p className="card-meta">{suggestion.content}</p>}
        </div>
        {canEdit && (
          <div className="row-actions">
            <button type="button" disabled={busy} onClick={() => onAccept(suggestion.id)}>
              Accept
            </button>
            <button type="button" className="ghost" disabled={busy} onClick={() => onDismiss(suggestion.id)}>
              Dismiss
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

function SummaryPanel({ summary, days, onDaysChange }) {
  return (
    <div>
      <div className="subject-tabs">
        {PERIODS.map((value) => (
          <button
            key={value}
            type="button"
            className={value === days ? '' : 'secondary'}
            onClick={() => onDaysChange(value)}
          >
            {value} days
          </button>
        ))}
      </div>
      {summary && (
        <ul className="teacher-queue-list">
          <li>
            Modules finished this period: <strong>{summary.modules_completed.length}</strong>
            {' '}({summary.modules_finished_total}/{summary.modules_total} overall)
          </li>
          <li>Reports this period: <strong>{summary.report_count}</strong></li>
          <li>
            Suggestions: {summary.open_suggestions} open · {summary.accepted_in_period} accepted
            {' '}· {summary.dismissed_in_period} dismissed
          </li>
          {summary.estimated_cefr_band && (
            <li>Working at: <span className="badge">{summary.estimated_cefr_band}</span></li>
          )}
          {summary.weak_keys.length > 0 && (
            <li>Focus areas: {summary.dimensions.filter((d) => d.is_weak).map((d) => d.label).join(', ')}</li>
          )}
        </ul>
      )}
    </div>
  )
}

/** Signals, pending suggestions, and period summary for one student. */
export default function CurriculumAdaptivePanel({ studentId, paths, canEdit, onEnrollmentChange }) {
  const [data, setData] = useState(null)
  const [summary, setSummary] = useState(null)
  const [days, setDays] = useState(30)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  useEffect(() => {
    setData(null)
    setError('')
    setNotice('')
    apiFetch(paths.curriculumSuggestions(studentId))
      .then(setData)
      .catch((err) => setError(err.message))
  }, [studentId, paths])

  useEffect(() => {
    apiFetch(`${paths.curriculumSummary(studentId)}?days=${days}`)
      .then(setSummary)
      .catch(() => setSummary(null))
  }, [studentId, paths, days, data])

  const suggest = async () => {
    setBusy(true)
    setError('')
    setNotice('')
    try {
      const result = await apiFetch(paths.curriculumSuggest(studentId), { method: 'POST', body: '{}' })
      setData(result)
      if (!result.created.length) setNotice('No new suggestions — everything relevant is already pending.')
      else if (result.used_llm) setNotice(`Added ${result.created.length} suggestion(s) with AI help.`)
      else setNotice(`Added ${result.created.length} suggestion(s).`)
      if (result.llm_error) setNotice((text) => `${text} AI was unavailable, so rules were used: ${result.llm_error}`)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const resolve = async (url) => {
    setBusy(true)
    setError('')
    setNotice('')
    try {
      const result = await apiFetch(url, { method: 'POST', body: '{}' })
      setData((current) => ({ ...current, pending: result.pending, recent: result.recent }))
      onEnrollmentChange?.(result.enrollment)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="card">
      <div className="card-row">
        <h3>Adaptive suggestions</h3>
        {canEdit && (
          <button type="button" disabled={busy} onClick={suggest}>
            {busy ? 'Working…' : 'Suggest next step'}
          </button>
        )}
      </div>
      <p className="card-meta">
        Based on recent session reports. Nothing changes on the student&apos;s path until you accept.
      </p>
      {error && <div className="error">{error}</div>}
      {notice && <div className="success">{notice}</div>}

      {data && <SignalsPanel signals={data.signals} />}

      {data?.pending?.length > 0 && (
        <>
          <h4>Pending</h4>
          {data.pending.map((row) => (
            <SuggestionCard
              key={row.id}
              suggestion={row}
              canEdit={canEdit}
              busy={busy}
              onAccept={(id) => resolve(paths.curriculumSuggestionAccept(id))}
              onDismiss={(id) => resolve(paths.curriculumSuggestionDismiss(id))}
            />
          ))}
        </>
      )}
      {data && !data.pending?.length && (
        <p className="card-meta">No pending suggestions.</p>
      )}

      {data?.recent?.length > 0 && (
        <details>
          <summary>Recently handled ({data.recent.length})</summary>
          <ul className="teacher-queue-list">
            {data.recent.map((row) => (
              <li key={row.id}>
                <span className={`badge ${row.status === 'accepted' ? 'badge--success' : 'badge--muted'}`}>
                  {row.status}
                </span>{' '}
                {row.title}
                {row.resolved_by ? <span className="card-meta"> · {row.resolved_by}</span> : null}
              </li>
            ))}
          </ul>
        </details>
      )}

      <h4>Progress summary</h4>
      <SummaryPanel summary={summary} days={days} onDaysChange={setDays} />
    </div>
  )
}
