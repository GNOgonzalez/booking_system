import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { apiFetch } from '../api.js'
import CurriculumAdaptivePanel from '../components/CurriculumAdaptivePanel.jsx'
import { useTeacherPermissions } from '../hooks/useTeacherPermissions.js'
import { useTeacherScope } from '../hooks/useTeacherScope.js'

const EMPTY_MODULE = { title: '', content: '' }

function statusLabel(status) {
  if (status === 'completed') return 'Done'
  if (status === 'skipped') return 'Skipped'
  return 'Upcoming'
}

export default function TeacherCurriculumPage() {
  const { isStaff, paths } = useTeacherScope()
  const { can } = useTeacherPermissions()
  const canEdit = isStaff || can('manage_curriculum')
  const [searchParams] = useSearchParams()
  const requestedStudentId = Number(searchParams.get('student')) || null
  const [students, setStudents] = useState([])
  const [templates, setTemplates] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [showCustom, setShowCustom] = useState(false)
  const [custom, setCustom] = useState({
    title: '',
    description: '',
    modules: [{ ...EMPTY_MODULE }],
    studentIds: [],
  })
  const [saving, setSaving] = useState(false)

  const load = () => {
    Promise.all([
      apiFetch(paths.curriculumStudents),
      apiFetch('/api/curriculum/templates/'),
    ])
      .then(([studentRows, templateRows]) => {
        setStudents(studentRows)
        setTemplates(templateRows)
        setSelectedId((current) => {
          if (current && studentRows.some((row) => row.id === current)) return current
          if (requestedStudentId && studentRows.some((row) => row.id === requestedStudentId)) {
            return requestedStudentId
          }
          return studentRows[0]?.id || null
        })
      })
      .catch((err) => setError(err.message))
  }

  useEffect(load, [paths.curriculumStudents])

  const selected = students.find((row) => row.id === selectedId) || null
  const enrollment = selected?.enrollment

  const replaceEnrollment = (studentId, nextEnrollment) => {
    setStudents((rows) => rows.map((row) => (
      row.id === studentId ? { ...row, enrollment: nextEnrollment } : row
    )))
  }

  const setProgress = async (moduleId, status) => {
    if (!selected) return
    setError('')
    setMessage('')
    try {
      const result = await apiFetch(paths.curriculumModuleProgress(moduleId), {
        method: 'POST',
        body: JSON.stringify({ student_id: selected.id, status }),
      })
      setStudents((rows) => rows.map((row) => (
        row.id === selected.id ? { ...row, enrollment: result.enrollment } : row
      )))
    } catch (err) {
      setError(err.message)
    }
  }

  const enrollOnTemplate = async (trackId) => {
    if (!selected) return
    setError('')
    setMessage('')
    try {
      const result = await apiFetch(paths.curriculumEnroll(selected.id), {
        method: 'POST',
        body: JSON.stringify({ track_id: trackId }),
      })
      setStudents((rows) => rows.map((row) => (
        row.id === selected.id ? { ...row, enrollment: result.enrollment } : row
      )))
      setMessage('Curriculum assigned.')
    } catch (err) {
      setError(err.message)
    }
  }

  const saveCustom = async (e) => {
    e.preventDefault()
    setSaving(true)
    setError('')
    setMessage('')
    try {
      await apiFetch(paths.curriculumTracks, {
        method: 'POST',
        body: JSON.stringify({
          title: custom.title,
          description: custom.description,
          student_ids: custom.studentIds,
          modules: custom.modules
            .filter((row) => row.title.trim())
            .map((row, index) => ({
              title: row.title.trim(),
              content: row.content,
              sort_order: index,
            })),
        }),
      })
      setMessage('Custom curriculum created.')
      setShowCustom(false)
      setCustom({ title: '', description: '', modules: [{ ...EMPTY_MODULE }], studentIds: [] })
      load()
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <div className="page-header">
        <div>
          {!isStaff && <h1>Student curriculum</h1>}
          <p className="page-intro">
            Assigned students and anyone you have already taught. Skip a module, or build a personalized
            curriculum — only those students will see open sessions on that path.
          </p>
        </div>
        {canEdit && (
          <div className="page-header-actions">
            <button
              type="button"
              className={showCustom ? 'secondary' : ''}
              onClick={() => setShowCustom((open) => !open)}
            >
              {showCustom ? 'Close custom curriculum' : 'New custom curriculum'}
            </button>
          </div>
        )}
      </div>
      {message && <div className="success">{message}</div>}
      {error && <div className="error">{error}</div>}

      {showCustom && canEdit && (
        <form onSubmit={saveCustom} className="card">
          <h2>Custom curriculum</h2>
          <div className="field">
            <label>Title</label>
            <input
              value={custom.title}
              onChange={(e) => setCustom({ ...custom, title: e.target.value })}
              required
            />
          </div>
          <div className="field">
            <label>Description</label>
            <textarea
              rows={2}
              value={custom.description}
              onChange={(e) => setCustom({ ...custom, description: e.target.value })}
            />
          </div>
          <div className="field">
            <label>Assign to students</label>
            {students.map((student) => (
              <label key={student.id} className="checkbox-row">
                <input
                  type="checkbox"
                  checked={custom.studentIds.includes(student.id)}
                  onChange={() => setCustom((current) => ({
                    ...current,
                    studentIds: current.studentIds.includes(student.id)
                      ? current.studentIds.filter((id) => id !== student.id)
                      : [...current.studentIds, student.id],
                  }))}
                />
                {student.label}
              </label>
            ))}
            {!students.length && <p className="card-meta">No students on your roster yet.</p>}
          </div>
          {custom.modules.map((module, index) => (
            <div key={index} className="field">
              <label>Module {index + 1}</label>
              <input
                value={module.title}
                onChange={(e) => setCustom((current) => ({
                  ...current,
                  modules: current.modules.map((row, i) => (
                    i === index ? { ...row, title: e.target.value } : row
                  )),
                }))}
                placeholder="Title"
              />
              <textarea
                rows={2}
                value={module.content}
                onChange={(e) => setCustom((current) => ({
                  ...current,
                  modules: current.modules.map((row, i) => (
                    i === index ? { ...row, content: e.target.value } : row
                  )),
                }))}
                placeholder="Notes"
                style={{ marginTop: '0.35rem' }}
              />
            </div>
          ))}
          <div className="form-actions">
            <button
              type="button"
              className="secondary"
              onClick={() => setCustom({ ...custom, modules: [...custom.modules, { ...EMPTY_MODULE }] })}
            >
              Add module
            </button>
            <button type="submit" disabled={saving}>{saving ? 'Saving…' : 'Create and assign'}</button>
          </div>
        </form>
      )}

      {!students.length && !error && (
        <div className="empty">
          No students on your roster yet. Staff can assign students, or they appear here after a confirmed booking.
        </div>
      )}

      {students.length > 0 && (
        <div className="toolbar">
          <div className="field" style={{ margin: 0, minWidth: '16rem' }}>
            <label htmlFor="curriculum-student">Student</label>
            <select
              id="curriculum-student"
              value={selectedId || ''}
              onChange={(e) => setSelectedId(Number(e.target.value))}
            >
              {students.map((student) => (
                <option key={student.id} value={student.id}>
                  {student.label}
                  {student.assigned ? '' : ' (taught)'}
                </option>
              ))}
            </select>
          </div>
        </div>
      )}

      {selected && (
        <div className="card">
          <div className="section-head">
            <h2>{selected.label}</h2>
            {selected.assigned && <span className="badge badge--muted">Staff assigned</span>}
          </div>
          {enrollment ? (
            <>
              <div className="section-head">
                <h3>
                  {enrollment.track.title}
                  {enrollment.track.framework === 'cefr' && <> <span className="badge">CEFR</span></>}
                </h3>
                <span className="progress-value">
                  {enrollment.track.modules.filter((m) => m.status === 'completed').length}
                  {' of '}
                  {enrollment.track.modules.length} done
                </span>
              </div>
              {enrollment.track.description && <p className="card-meta">{enrollment.track.description}</p>}
              <ul className="module-list">
                {enrollment.track.modules.map((module) => {
                  const state = module.status === 'completed'
                    ? 'done'
                    : module.is_current ? 'current' : 'upcoming'
                  return (
                    <li
                      key={module.id}
                      className={`module-item module-item--${state}`}
                    >
                      <span className={`status-dot status-dot--${state}`} aria-hidden="true" />
                      <span className="module-item-text">
                        <span className="module-title">
                          {module.cefr_level && <><span className="badge">{module.cefr_level}</span>{' '}</>}
                          {module.title}
                        </span>
                        <span className="card-meta">
                          {statusLabel(module.status)}
                          {module.is_current ? ' · Current' : ''}
                          {module.skill_keys?.length ? ` · ${module.skill_keys.join(', ')}` : ''}
                        </span>
                        {module.content && <span className="card-meta">{module.content}</span>}
                      </span>
                      {canEdit && (
                        <span className="row-actions module-item-actions">
                          {module.status !== 'skipped' && (
                            <button type="button" onClick={() => setProgress(module.id, 'skipped')}>
                              Skip
                            </button>
                          )}
                          {module.status !== 'completed' && (
                            <button type="button" onClick={() => setProgress(module.id, 'completed')}>
                              Mark done
                            </button>
                          )}
                          {module.status !== 'pending' && (
                            <button type="button" className="ghost" onClick={() => setProgress(module.id, 'pending')}>
                              Reset
                            </button>
                          )}
                        </span>
                      )}
                    </li>
                  )
                })}
              </ul>
            </>
          ) : (
            <p className="card-meta">Not on a curriculum yet.</p>
          )}
          {canEdit && templates.length > 0 && (
            <div className="field" style={{ marginTop: '1rem' }}>
              <label>Assign a premade curriculum</label>
              <select
                defaultValue=""
                onChange={(e) => {
                  if (e.target.value) enrollOnTemplate(Number(e.target.value))
                  e.target.value = ''
                }}
              >
                <option value="">Choose…</option>
                {templates.map((track) => (
                  <option key={track.id} value={track.id}>{track.title}</option>
                ))}
              </select>
            </div>
          )}
        </div>
      )}

      {selected && enrollment && (
        <CurriculumAdaptivePanel
          studentId={selected.id}
          paths={paths}
          canEdit={canEdit}
          onEnrollmentChange={(next) => replaceEnrollment(selected.id, next)}
        />
      )}
    </div>
  )
}
