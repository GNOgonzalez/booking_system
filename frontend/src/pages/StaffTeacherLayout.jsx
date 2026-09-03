import { Link, NavLink, Outlet, useParams } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { apiFetch } from '../api.js'

import { useGlossary } from '../hooks/useGlossary.jsx'

export default function StaffTeacherLayout() {
  const { label, labels } = useGlossary()
  const { teacherId } = useParams()
  const [teacher, setTeacher] = useState(null)

  useEffect(() => {
    apiFetch('/api/staff/teachers/')
      .then((rows) => setTeacher(rows.find((t) => String(t.id) === teacherId) || null))
      .catch(() => setTeacher(null))
  }, [teacherId])

  const base = `/staff/teachers/${teacherId}`
  const nav = [
    ['students', labels('student')],
    ['sessions', labels('session')],
    ['requests', 'Class requests'],
    ['classes', labels('class')],
    ['availability', label('availability')],
    ['progress', labels('report')],
    ['homework', 'Homework'],
    ['curriculum', 'Curriculum'],
    ['permissions', 'Permissions'],
  ]

  return (
    <div>
      <p className="card-meta"><Link to="/staff">← All teachers</Link></p>
      <h1>{teacher ? teacher.label : label('teacher')}</h1>
      <p className="page-intro">Staff view — manage this {label('teacher').toLowerCase()}&apos;s schedule and catalog.</p>
      <nav className="staff-teacher-nav">
        {nav.map(([segment, label]) => (
          <NavLink
            key={segment}
            to={`${base}/${segment}`}
            className={({ isActive }) => `staff-teacher-nav-link${isActive ? ' active' : ''}`}
          >
            {label}
          </NavLink>
        ))}
      </nav>
      <Outlet />
    </div>
  )
}
