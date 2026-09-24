import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch } from '../api.js'

const PERIODS = [
  { days: 7, label: '7 days' },
  { days: 30, label: '30 days' },
  { days: 90, label: '90 days' },
]

function formatWhen(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

function StatCard({ label, value, meta }) {
  return (
    <div className="card reports-stat-card">
      <div className="card-meta">{label}</div>
      <div className="reports-stat-value">{value}</div>
      {meta && <div className="card-meta">{meta}</div>}
    </div>
  )
}

export default function StaffReportsPage() {
  const [days, setDays] = useState(30)
  const [report, setReport] = useState(null)
  const [feedback, setFeedback] = useState(null)
  const [teacherFilter, setTeacherFilter] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    setError('')
    apiFetch(`/api/staff/reports/?days=${days}`)
      .then(setReport)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [days])

  useEffect(() => {
    const teacherQuery = teacherFilter ? `&teacher_id=${teacherFilter}` : ''
    apiFetch(`/api/progress/staff/feedback/?days=${days}${teacherQuery}`)
      .then(setFeedback)
      .catch((err) => setError(err.message))
  }, [days, teacherFilter])

  const financials = report?.financials
  const bookings = report?.bookings
  const teachers = report?.teachers
  const students = report?.students

  return (
    <div>
      <p className="card-meta"><Link to="/staff">← Staff dashboard</Link></p>
      <h1>Reports</h1>
      <p className="page-intro">
        Studio overview — revenue, bookings, teacher activity, and student engagement.
      </p>

      <div className="reports-period-tabs">
        {PERIODS.map((period) => (
          <button
            key={period.days}
            type="button"
            className={days === period.days ? 'subject-tab active' : 'subject-tab'}
            onClick={() => setDays(period.days)}
          >
            {period.label}
          </button>
        ))}
      </div>

      {error && <div className="error">{error}</div>}
      {loading && <p className="card-meta">Loading reports…</p>}

      {report && !loading && (
        <>
          <section className="reports-section">
            <h2>Financials</h2>
            <div className="card-meta reports-mode">
              Payment mode: <strong>{financials.mode}</strong>
              {financials.mode === 'mock' && ' — purchases recorded locally until Stripe is wired'}
            </div>
            <div className="row">
              <StatCard
                label="Revenue"
                value={financials.total_revenue.display}
                meta={`${financials.payment_count} payment${financials.payment_count === 1 ? '' : 's'}`}
              />
              <StatCard
                label="Tickets used"
                value={bookings.tickets_spent}
                meta="From confirmed bookings"
              />
              <StatCard
                label="Session reports"
                value={report.progress.feedback_in_period}
                meta="Teacher feedback submitted"
              />
            </div>

            {financials.by_plan.length > 0 && (
              <div className="card">
                <h3>Revenue by plan</h3>
                <table className="reports-table">
                  <thead>
                    <tr>
                      <th>Plan</th>
                      <th>Payments</th>
                      <th>Revenue</th>
                    </tr>
                  </thead>
                  <tbody>
                    {financials.by_plan.map((row) => (
                      <tr key={row.plan_name}>
                        <td>{row.plan_name}</td>
                        <td>{row.count}</td>
                        <td>{row.revenue.display}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {financials.recent_payments.length > 0 && (
              <div className="card">
                <h3>Recent payments</h3>
                <table className="reports-table">
                  <thead>
                    <tr>
                      <th>Student</th>
                      <th>Plan</th>
                      <th>Amount</th>
                      <th>Provider</th>
                      <th>When</th>
                    </tr>
                  </thead>
                  <tbody>
                    {financials.recent_payments.map((row) => (
                      <tr key={row.id}>
                        <td>{row.user}</td>
                        <td>{row.plan_name}</td>
                        <td>{row.amount.display}</td>
                        <td><span className="badge">{row.provider}</span></td>
                        <td>{formatWhen(row.created_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {!financials.payment_count && (
              <p className="card-meta">No completed payments in this period.</p>
            )}
          </section>

          <section className="reports-section">
            <h2>Bookings</h2>
            <div className="row">
              <StatCard label="Confirmed" value={bookings.confirmed} />
              <StatCard label="Cancelled" value={bookings.cancelled} />
              <StatCard label="Sessions held" value={report.sessions.in_period} />
              <StatCard label="Open upcoming" value={report.sessions.open_upcoming} />
            </div>

            {bookings.by_subject.length > 0 && (
              <div className="card">
                <h3>By subject</h3>
                <table className="reports-table">
                  <thead>
                    <tr>
                      <th>Subject</th>
                      <th>Bookings</th>
                      <th>Tickets</th>
                    </tr>
                  </thead>
                  <tbody>
                    {bookings.by_subject.map((row) => (
                      <tr key={row.subject}>
                        <td>{row.subject}</td>
                        <td>{row.bookings}</td>
                        <td>{row.tickets}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {bookings.recent.length > 0 && (
              <div className="card">
                <h3>Recent bookings</h3>
                <table className="reports-table">
                  <thead>
                    <tr>
                      <th>Student</th>
                      <th>Session</th>
                      <th>Teacher</th>
                      <th>Status</th>
                      <th>When</th>
                    </tr>
                  </thead>
                  <tbody>
                    {bookings.recent.map((row) => (
                      <tr key={row.id}>
                        <td>{row.student}</td>
                        <td>{row.session_title}</td>
                        <td>{row.teacher}</td>
                        <td>
                          <span className={`badge${row.status === 'cancelled' ? ' badge--muted' : ''}`}>
                            {row.status}
                          </span>
                        </td>
                        <td>{formatWhen(row.created_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <section className="reports-section">
            <h2>Teachers</h2>
            <div className="row">
              <StatCard label="Teachers" value={teachers.count} />
            </div>
            {teachers.rows.length > 0 ? (
              <div className="card">
                <table className="reports-table">
                  <thead>
                    <tr>
                      <th>Teacher</th>
                      <th>Sessions</th>
                      <th>Upcoming</th>
                      <th>Bookings</th>
                      <th>Reports</th>
                    </tr>
                  </thead>
                  <tbody>
                    {teachers.rows.map((row) => (
                      <tr key={row.id}>
                        <td>
                          {row.username}
                          {!row.is_active && <span className="badge badge--muted">Inactive</span>}
                        </td>
                        <td>{row.sessions_in_period}</td>
                        <td>{row.upcoming_sessions}</td>
                        <td>{row.bookings_in_period}</td>
                        <td>{row.feedback_in_period}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="card-meta">No teachers in this period.</p>
            )}
          </section>

          <section className="reports-section">
            <h2>Completed session reports</h2>
            <div className="card">
              <div className="card-row">
                <p className="card-meta">
                  {feedback
                    ? `${feedback.total} report${feedback.total === 1 ? '' : 's'} written in this period.`
                    : 'Loading reports…'}
                </p>
                <div className="field">
                  <label htmlFor="report-teacher-filter">Teacher</label>
                  <select
                    id="report-teacher-filter"
                    value={teacherFilter}
                    onChange={(e) => setTeacherFilter(e.target.value)}
                  >
                    <option value="">All teachers</option>
                    {teachers.rows.map((row) => (
                      <option key={row.id} value={row.id}>{row.username}</option>
                    ))}
                  </select>
                </div>
              </div>

              {feedback?.reports?.length ? (
                <>
                  <table className="reports-table">
                    <thead>
                      <tr>
                        <th>Written</th>
                        <th>Teacher</th>
                        <th>Student</th>
                        <th>Session</th>
                        <th>Notes</th>
                        <th />
                      </tr>
                    </thead>
                    <tbody>
                      {feedback.reports.map((row) => (
                        <tr key={row.id}>
                          <td>{formatWhen(row.created_at)}</td>
                          <td>{row.teacher_name}</td>
                          <td>{row.student_name}</td>
                          <td>
                            {row.session_title || 'No session linked'}
                            {row.subject && <div className="card-meta">{row.subject}</div>}
                          </td>
                          <td>
                            {row.notes_excerpt || <span className="card-meta">No notes</span>}
                            {row.notes_truncated && '…'}
                          </td>
                          <td>
                            <Link to={`/staff/teachers/${row.teacher_id}/progress`}>Open</Link>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {feedback.total > feedback.returned && (
                    <p className="card-meta">
                      Showing the {feedback.returned} most recent. Open a teacher to see all of theirs.
                    </p>
                  )}
                </>
              ) : (
                feedback && <p className="card-meta">No reports written in this period.</p>
              )}
            </div>
          </section>

          <section className="reports-section">
            <h2>Students</h2>
            <div className="row">
              <StatCard label="Active" value={students.active} />
              <StatCard label="Inactive" value={students.inactive} />
              <StatCard
                label="With membership"
                value={students.with_active_membership}
                meta={`${students.tickets_remaining} tickets remaining studio-wide`}
              />
            </div>

            {students.top_by_bookings.length > 0 && (
              <div className="card">
                <h3>Most active students</h3>
                <table className="reports-table">
                  <thead>
                    <tr>
                      <th>Student</th>
                      <th>Bookings</th>
                      <th>Tickets spent</th>
                    </tr>
                  </thead>
                  <tbody>
                    {students.top_by_bookings.map((row) => (
                      <tr key={row.id}>
                        <td>{row.username}</td>
                        <td>{row.bookings}</td>
                        <td>{row.tickets_spent}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}
    </div>
  )
}
