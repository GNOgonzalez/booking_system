import { NavLink, Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { clearTokens, getMe, getTokens, login } from './api.js'
import LoginPage from './pages/LoginPage.jsx'
import ProfilePage from './pages/ProfilePage.jsx'
import StudentSessionsPage from './pages/StudentSessionsPage.jsx'
import StudentBookingsPage from './pages/StudentBookingsPage.jsx'
import StudentProgressPage from './pages/StudentProgressPage.jsx'
import MembershipPage from './pages/MembershipPage.jsx'
import TeacherSessionsPage from './pages/TeacherSessionsPage.jsx'
import TeacherCreateSessionPage from './pages/TeacherCreateSessionPage.jsx'
import TeacherAvailabilityPage from './pages/TeacherAvailabilityPage.jsx'
import TeacherClassTypesPage from './pages/TeacherClassTypesPage.jsx'
import TeacherProgressPage from './pages/TeacherProgressPage.jsx'
import InboxPage from './pages/InboxPage.jsx'
import CurriculumPage from './pages/CurriculumPage.jsx'

function Sidebar({ me, onLogout }) {
  const roles = me?.roles || []
  const isStudent = roles.includes('student')
  const isTeacher = roles.includes('teacher')
  const displayName = me?.display_name || me?.username || 'Account'

  return (
    <aside className="sidebar">
      <div className="brand">Booking Studio</div>

      <NavLink to="/" end className="nav-link">Home</NavLink>

      {isStudent && (
        <>
          <div className="nav-section">Student</div>
          <NavLink to="/sessions" className="nav-link">Open sessions</NavLink>
          <NavLink to="/bookings" className="nav-link">My bookings</NavLink>
          <NavLink to="/membership" className="nav-link">Membership</NavLink>
          <NavLink to="/progress" className="nav-link">My progress</NavLink>
        </>
      )}

      {isTeacher && (
        <>
          <div className="nav-section">Teacher</div>
          <NavLink to="/teacher/sessions" className="nav-link">My sessions</NavLink>
          <NavLink to="/teacher/sessions/new" className="nav-link">New session</NavLink>
          <NavLink to="/teacher/availability" className="nav-link">Availability</NavLink>
          <NavLink to="/teacher/class-types" className="nav-link">Class types</NavLink>
          <NavLink to="/teacher/progress" className="nav-link">Student reports</NavLink>
        </>
      )}

      <div className="nav-section">Account</div>
      <NavLink to="/inbox" className="nav-link">Inbox</NavLink>
      <NavLink to="/curriculum" className="nav-link">Curriculum</NavLink>
      <NavLink to="/profile" className="nav-link">Profile & settings</NavLink>

      <div className="sidebar-footer">
        <div className="sidebar-user">
          {displayName}
          {roles.length > 0 && <> · <span className="badge">{roles[0]}</span></>}
        </div>
        <button type="button" className="ghost" onClick={onLogout}>Log out</button>
      </div>
    </aside>
  )
}

function HomePage({ me }) {
  const roles = me?.roles || []
  return (
    <div>
      <h1>Welcome{me?.display_name ? `, ${me.display_name}` : ''}</h1>
      <p className="page-intro">
        {roles.includes('teacher')
          ? 'Manage your sessions, availability, and student progress.'
          : 'Browse open sessions, manage bookings, and track your progress.'}
      </p>
      <div className="card">
        <div className="card-title">Getting started</div>
        <p className="card-meta">Use the menu on the left to navigate. Your role determines what you can do.</p>
      </div>
    </div>
  )
}

function AppRoutes() {
  const navigate = useNavigate()
  const [authed, setAuthed] = useState(Boolean(getTokens().access))
  const [me, setMe] = useState(null)

  const loadMe = () => {
    if (getTokens().access) {
      getMe().then(setMe).catch(() => setMe(null))
    }
  }

  useEffect(() => {
    loadMe()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authed])

  const handleLogin = async (username, password) => {
    await login(username, password)
    setAuthed(true)
    navigate('/')
  }

  const handleLogout = () => {
    clearTokens()
    setMe(null)
    setAuthed(false)
    navigate('/login')
  }

  if (!authed) {
    return (
      <Routes>
        <Route path="/login" element={<LoginPage onLogin={handleLogin} />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    )
  }

  return (
    <div className="app-shell">
      <Sidebar me={me} onLogout={handleLogout} />
      <main className="main">
        <Routes>
          <Route path="/" element={<HomePage me={me} />} />
          <Route path="/sessions" element={<StudentSessionsPage />} />
          <Route path="/bookings" element={<StudentBookingsPage />} />
          <Route path="/membership" element={<MembershipPage />} />
          <Route path="/progress" element={<StudentProgressPage />} />
          <Route path="/teacher/sessions" element={<TeacherSessionsPage />} />
          <Route path="/teacher/sessions/new" element={<TeacherCreateSessionPage />} />
          <Route path="/teacher/availability" element={<TeacherAvailabilityPage />} />
          <Route path="/teacher/class-types" element={<TeacherClassTypesPage />} />
          <Route path="/teacher/progress" element={<TeacherProgressPage />} />
          <Route path="/inbox" element={<InboxPage />} />
          <Route path="/curriculum" element={<CurriculumPage />} />
          <Route path="/profile" element={<ProfilePage onSaved={loadMe} />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  )
}

export default function App() {
  return <AppRoutes />
}
