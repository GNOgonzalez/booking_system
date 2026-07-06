import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { apiFetch } from '../api.js'
import { scoreValue, scoreChartBounds } from '../hooks/useScoreDimensions.js'

const COLORS = ['#2d5296', '#4a82d4', '#9cc2ee', '#1f8a5b', '#c45c26', '#6b4fa0', '#c4302b', '#2a9d8f', '#e9c46a', '#264653']

function shortDate(value) {
  if (!value) return ''
  return new Date(value).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

function formatDateTime(value) {
  if (!value) return ''
  return new Date(value).toLocaleString(undefined, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

function withColors(metrics) {
  return metrics.map((dim, i) => ({
    ...dim,
    min_score: dim.min_score ?? 0,
    max_score: dim.max_score ?? 5,
    color: COLORS[i % COLORS.length],
  }))
}

function TopicProgressTrack({ progress }) {
  if (!progress) return null

  return (
    <div className="topic-progress">
      <div className="topic-progress-summary">
        {progress.all_complete ? (
          <span>All {progress.total} topics completed</span>
        ) : (
          <span>
            Topic {progress.position} of {progress.total}
            {progress.next_topic ? ` — ${progress.next_topic.title}` : ''}
          </span>
        )}
      </div>
      <ol className="topic-progress-steps">
        {progress.steps.map((step) => (
          <li key={step.id} className={`topic-step topic-step--${step.status}`}>
            <span className="topic-step-marker" aria-hidden="true" />
            <span className="topic-step-title">{step.title}</span>
            {step.status === 'completed' && <span className="badge badge--success">Done</span>}
            {step.status === 'current' && <span className="badge">Up next</span>}
          </li>
        ))}
      </ol>
      {progress.next_class && (
        <div className="topic-next-class">
          <div className="topic-next-class-label">
            {progress.next_class.is_booked ? 'Your next class' : 'Next class to book'}
          </div>
          <strong>{progress.next_class.title}</strong>
          <div className="card-meta">{formatDateTime(progress.next_class.start_time)}</div>
          <div className="card-meta">{progress.next_class.teacher_name}</div>
          {!progress.next_class.is_booked && (
            <Link to="/sessions" className="topic-next-class-link">Book this session →</Link>
          )}
        </div>
      )}
      {progress.next_topic && !progress.next_class && !progress.all_complete && (
        <p className="card-meta topic-next-class-missing">
          No open sessions for <strong>{progress.next_topic.title}</strong> yet — check back soon.
        </p>
      )}
    </div>
  )
}

function SubjectProgressPanel({ section, onPrivacyChange }) {
  const dimensions = useMemo(() => withColors(section.metrics || []), [section.metrics])
  const feedback = section.feedback || []
  const { min: chartMin, max: chartMax } = scoreChartBounds(dimensions)

  const lineData = useMemo(
    () =>
      feedback.map((f, i) => {
        const row = { label: shortDate(f.session_start_time || f.created_at) || `#${i + 1}` }
        for (const dim of dimensions) {
          row[dim.label] = scoreValue(f, dim)
        }
        return row
      }),
    [feedback, dimensions],
  )

  const latest = feedback.length ? feedback[feedback.length - 1] : null

  const radarData = useMemo(
    () =>
      dimensions.map((dim) => ({
        skill: dim.label,
        value: latest ? scoreValue(latest, dim) : 0,
      })),
    [latest, dimensions],
  )

  return (
    <div className="subject-panel">
      <div className="row" style={{ marginBottom: '1rem' }}>
        <div className="card grow" style={{ marginBottom: 0 }}>
          <div className="card-meta">Classes taken</div>
          <div style={{ fontSize: '1.4rem', fontWeight: 650 }}>{section.class_count}</div>
        </div>
        <div className="card grow" style={{ marginBottom: 0 }}>
          <div className="card-meta">Sessions attended</div>
          <div style={{ fontSize: '1.4rem', fontWeight: 650 }}>{section.session_count}</div>
        </div>
        <div className="card grow" style={{ marginBottom: 0 }}>
          <div className="card-meta">Reports received</div>
          <div style={{ fontSize: '1.4rem', fontWeight: 650 }}>{section.feedback_count}</div>
        </div>
      </div>

      {latest && dimensions.length > 0 && (
        <div className="row" style={{ marginBottom: '1rem' }}>
          {dimensions.map((dim) => (
            <div key={dim.key} className="card grow" style={{ marginBottom: 0 }}>
              <div className="card-meta">{dim.label}</div>
              <div style={{ fontSize: '1.6rem', fontWeight: 650, color: dim.color }}>
                {scoreValue(latest, dim)}
                <span style={{ color: 'var(--muted)', fontSize: '1rem' }}>/{dim.max_score}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {feedback.length > 0 && dimensions.length > 0 ? (
        <>
          <div className="card">
            <h2>Skills over time</h2>
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={lineData} margin={{ top: 8, right: 16, bottom: 8, left: -16 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f2" />
                <XAxis dataKey="label" tick={{ fontSize: 12 }} />
                <YAxis domain={[chartMin, chartMax]} tick={{ fontSize: 12 }} />
                <Tooltip />
                <Legend />
                {dimensions.map((dim) => (
                  <Line
                    key={dim.key}
                    type="monotone"
                    dataKey={dim.label}
                    stroke={dim.color}
                    strokeWidth={2}
                    dot={{ r: 3 }}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="card">
            <h2>Latest snapshot</h2>
            <ResponsiveContainer width="100%" height={280}>
              <RadarChart data={radarData} outerRadius="70%">
                <PolarGrid stroke="#e2e8f2" />
                <PolarAngleAxis dataKey="skill" tick={{ fontSize: 12 }} />
                <PolarRadiusAxis domain={[chartMin, chartMax]} tick={{ fontSize: 11 }} />
                <Radar
                  name="Score"
                  dataKey="value"
                  stroke="#3767b8"
                  fill="#4a82d4"
                  fillOpacity={0.5}
                />
                <Tooltip />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </>
      ) : (
        <div className="card">
          <p className="card-meta">
            No session reports yet for {section.subject}. Charts appear once your teacher rates a session.
          </p>
        </div>
      )}

      <h2 style={{ marginTop: '1.5rem' }}>Classes in {section.subject}</h2>
      {(section.classes || []).map((klass) => (
        <div key={klass.class_offering_id} className="card class-history-card">
          <div className="card-title">{klass.label}</div>
          <div className="card-meta">
            {klass.level} · {klass.focus}
            {klass.topics?.length && !klass.topic_progress ? (
              <> · {klass.topics.map((topic) => topic.title).join(' · ')}</>
            ) : null}
            {' · '}{klass.session_count} session{klass.session_count === 1 ? '' : 's'}
          </div>
          <TopicProgressTrack progress={klass.topic_progress} />
          <ul className="session-history-list">
            {klass.sessions.map((session) => {
              const isPast = session.end_time && new Date(session.end_time) <= new Date()
              return (
              <li key={session.id} className="session-history-item">
                <div>
                  <strong>{session.title}</strong>
                  <div className="card-meta">{formatDateTime(session.start_time)}</div>
                  {isPast && onPrivacyChange && (
                    <label className="card-meta" style={{ display: 'block', marginTop: '0.35rem' }}>
                      <input
                        type="checkbox"
                        checked={Boolean(session.privacy?.hidden_by_student)}
                        onChange={(e) => onPrivacyChange(session.id, e.target.checked)}
                      />
                      {' '}Hide from other teachers
                      <span
                        className="badge badge--muted"
                        style={{ marginLeft: '0.4rem' }}
                        title="Other teachers won't see this lesson. Studio staff may still access records for safety and policy reasons."
                      >
                        ?
                      </span>
                    </label>
                  )}
                </div>
                <div className="session-history-badges">
                  {session.class_topic && <span className="badge">{session.class_topic}</span>}
                  <span className="badge">{session.teacher_name}</span>
                  {session.has_feedback ? (
                    <span className="badge badge--success">Reported</span>
                  ) : (
                    <span className="badge badge--muted">No report yet</span>
                  )}
                </div>
              </li>
              )
            })}
          </ul>
        </div>
      ))}
      {!section.classes?.length && (
        <p className="card-meta">No classes booked in {section.subject} yet.</p>
      )}
    </div>
  )
}

export default function StudentProgressPage() {
  const [sections, setSections] = useState([])
  const [reports, setReports] = useState([])
  const [error, setError] = useState('')
  const [activeSubject, setActiveSubject] = useState('')

  useEffect(() => {
    apiFetch('/api/progress/dashboard/')
      .then((rows) => {
        setSections(rows)
        if (rows.length) setActiveSubject(rows[0].subject)
      })
      .catch((err) => setError(err.message))
    apiFetch('/api/progress/')
      .then(setReports)
      .catch(() => {})
  }, [])

  const activeSection = sections.find((s) => s.subject === activeSubject) || null

  const updateSessionPrivacy = async (sessionId, hidden) => {
    try {
      await apiFetch(`/api/progress/sessions/${sessionId}/history-privacy/`, {
        method: 'PATCH',
        body: JSON.stringify({ hidden_by_student: hidden }),
      })
      const rows = await apiFetch('/api/progress/dashboard/')
      setSections(rows)
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div>
      <h1>My progress</h1>
      <p className="page-intro">
        Track your skill ratings and see every class you have taken, organized by subject.
      </p>
      {error && <div className="error">{error}</div>}

      {sections.length > 1 && (
        <div className="subject-tabs" role="tablist" aria-label="Subjects">
          {sections.map((section) => (
            <button
              key={section.subject}
              type="button"
              role="tab"
              aria-selected={section.subject === activeSubject}
              className={section.subject === activeSubject ? 'subject-tab active' : 'subject-tab'}
              onClick={() => setActiveSubject(section.subject)}
            >
              {section.subject}
              <span className="subject-tab-count">{section.session_count}</span>
            </button>
          ))}
        </div>
      )}

      {activeSection ? (
        <SubjectProgressPanel section={activeSection} onPrivacyChange={updateSessionPrivacy} />
      ) : (
        !error && (
          <div className="empty">
            No progress yet. Book a session to start tracking your classes and metrics.
          </div>
        )
      )}

      {reports.length > 0 && (
        <div className="card">
          <h2>Notes from your teacher</h2>
          {reports.map((report) => (
            <div
              key={report.id}
              style={{ borderTop: '1px solid var(--line)', paddingTop: '0.6rem', marginTop: '0.6rem' }}
            >
              <span className="badge">{report.rating}/5</span>
              {report.skill_name ? ` ${report.skill_name}` : ''} · by {report.teacher_name}
              {report.note && <div className="card-meta">{report.note}</div>}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
