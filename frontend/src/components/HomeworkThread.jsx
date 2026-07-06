import { useState } from 'react'
import { apiDownload, apiUpload } from '../api.js'
import MarkdownPreview, { MarkdownBody } from './MarkdownPreview.jsx'
import { homeworkFileHint, useUploadLimits } from '../hooks/useUploadLimits.js'

function formatWhen(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

export default function HomeworkThread({
  assignment,
  onUpdated,
  postPath,
  canReply = true,
  replyLabel = 'Send',
}) {
  const [body, setBody] = useState('')
  const [file, setFile] = useState(null)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const limits = useUploadLimits()
  const fileHint = homeworkFileHint(limits)

  if (!assignment) {
    return (
      <aside className="card homework-panel homework-panel--empty">
        <p className="card-meta">Select homework to view the thread.</p>
      </aside>
    )
  }

  const isJournal = assignment.kind === 'journal'
  const closed = assignment.is_expired && !isJournal

  const submit = async (e) => {
    e.preventDefault()
    if (!canReply || closed) return
    setSaving(true)
    setError('')
    try {
      const form = new FormData()
      if (body.trim()) form.append('body', body.trim())
      if (file && !isJournal) form.append('attachment', file)
      const updated = await apiUpload(postPath, form)
      setBody('')
      setFile(null)
      onUpdated?.(updated)
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  const download = async (entry) => {
    if (!entry.download_url) return
    try {
      const path = entry.download_url.replace(/^https?:\/\/[^/]+/, '')
      await apiDownload(path, entry.attachment_name || 'homework-file')
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <aside className="card homework-panel">
      <div className="homework-panel-header">
        <div>
          <h2>{assignment.title || (isJournal ? 'Journal prompt' : 'File exchange')}</h2>
          <div className="card-meta">
            {isJournal ? 'Journal' : 'File exchange'}
            {' · '}
            {assignment.teacher_name} → {assignment.student_name}
          </div>
          {assignment.session_title && (
            <div className="card-meta">
              Session: {assignment.session_title}
              {assignment.session_start_time && (
                <> · {formatWhen(assignment.session_start_time)}</>
              )}
              {assignment.session_subject && <> · {assignment.session_subject}</>}
            </div>
          )}
        </div>
        {!isJournal && assignment.days_remaining != null && !assignment.is_expired && (
          <div
            className={`homework-expiry-chip${assignment.days_remaining <= 2 ? ' homework-expiry-chip--warning' : ''}`}
            role="status"
          >
            <div className="homework-expiry-chip-count" aria-hidden="true">
              {assignment.days_remaining}
            </div>
            <div className="homework-expiry-chip-copy">
              <span className="homework-expiry-chip-title">Files available</span>
              <span className="homework-expiry-chip-meta">
                {assignment.days_remaining === 1 ? '1 day left' : `${assignment.days_remaining} days left`}
              </span>
            </div>
          </div>
        )}
        {closed && (
          <div className="homework-expiry-chip homework-expiry-chip--expired" role="status">
            <div className="homework-expiry-chip-copy">
              <span className="homework-expiry-chip-title">Files expired</span>
              <span className="homework-expiry-chip-meta">Upload window closed</span>
            </div>
          </div>
        )}
      </div>

      {assignment.prompt && (
        <div className="homework-prompt">
          <div className="card-meta">Instructions</div>
          <p>{assignment.prompt}</p>
        </div>
      )}

      {!isJournal && (
        <p className="card-meta" style={{ marginBottom: '0.75rem' }}>
          Uploaded files are kept for 7 days, then removed automatically.
        </p>
      )}

      {error && <div className="error">{error}</div>}

      <div className="homework-thread">
        {(assignment.entries || []).map((entry) => (
          <div
            key={entry.id}
            className={`homework-entry homework-entry--${entry.author_role}`}
          >
            <div className="homework-entry-meta">
              <strong>{entry.author_name}</strong>
              <span className="card-meta">{formatWhen(entry.created_at)}</span>
            </div>
            {entry.body_html ? (
              <MarkdownBody html={entry.body_html} />
            ) : (
              entry.body && <p>{entry.body}</p>
            )}
            {entry.has_attachment && (
              <button type="button" className="secondary" onClick={() => download(entry)}>
                Download {entry.attachment_name}
              </button>
            )}
            {!entry.has_attachment && entry.attachment_name && (
              <span className="card-meta">File expired</span>
            )}
          </div>
        ))}
        {!assignment.entries?.length && (
          <p className="card-meta">No replies yet.</p>
        )}
      </div>

      {canReply && !closed && (
        <form onSubmit={submit} className="homework-reply-form">
          <div className="field">
            <label>{isJournal ? 'Journal entry' : 'Message'}</label>
            <textarea
              value={body}
              onChange={(e) => setBody(e.target.value)}
              rows={isJournal ? 5 : 3}
              placeholder={isJournal ? 'Write your reflection…' : 'Optional message…'}
            />
            <MarkdownPreview source={body} />
          </div>
          {!isJournal && (
            <div className="field">
              <label>Attach file (optional)</label>
              <input
                type="file"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
              />
              {fileHint && <p className="card-meta">{fileHint}</p>}
            </div>
          )}
          <button type="submit" disabled={saving || (!body.trim() && !file)}>
            {saving ? 'Sending…' : replyLabel}
          </button>
        </form>
      )}
    </aside>
  )
}
