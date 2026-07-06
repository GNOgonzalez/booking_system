import { useParams } from 'react-router-dom'

/** API paths when staff manages a specific teacher. */
export function staffPathsForTeacher(teacherId) {
  const base = `/api/staff/teachers/${teacherId}`
  return {
    sessions: `${base}/sessions/`,
    sessionDetail: (sessionId) => `${base}/sessions/${sessionId}/`,
    sessionStudents: (sessionId) => `${base}/sessions/${sessionId}/students/`,
    classes: `${base}/classes/`,
    classDetail: (classId) => `${base}/classes/${classId}/`,
    availability: `${base}/availability/`,
    availabilityDetail: (blockId) => `${base}/availability/${blockId}/`,
    specialAvailability: `${base}/special-availability/`,
    specialAvailabilityDetail: (blockId) => `${base}/special-availability/${blockId}/`,
    students: `${base}/students/`,
    feedback: `/api/progress/staff/teachers/${teacherId}/feedback/`,
    feedbackDetail: (feedbackId) => `/api/progress/staff/teachers/${teacherId}/feedback/${feedbackId}/`,
    homework: `/api/progress/staff/teachers/${teacherId}/homework/`,
    homeworkDetail: (homeworkId) => `/api/progress/staff/teachers/${teacherId}/homework/${homeworkId}/`,
    homeworkEntry: (homeworkId) => `/api/progress/staff/teachers/${teacherId}/homework/${homeworkId}/entries/`,
    classRequests: `${base}/class-requests/`,
    classRequestDetail: (requestId) => `${base}/class-requests/${requestId}/`,
    classRequestApprove: (requestId) => `${base}/class-requests/${requestId}/approve/`,
    classRequestDeny: (requestId) => `${base}/class-requests/${requestId}/deny/`,
    classRequestDelete: (requestId) => `${base}/class-requests/${requestId}/delete/`,
    studentHistory: (studentId) => `/api/progress/staff/teachers/${teacherId}/students/${studentId}/history/`,
    sessionHistoryPrivacy: null,
    newSession: `/staff/teachers/${teacherId}/sessions/new`,
    staffHome: '/staff',
    staffTeacherSessions: `/staff/teachers/${teacherId}/sessions`,
  }
}

/** API paths for teacher self-service or staff acting on a teacher's behalf. */
export function useTeacherScope() {
  const { teacherId } = useParams()
  const isStaff = Boolean(teacherId)
  const id = teacherId ? Number(teacherId) : null

  const paths = isStaff
    ? staffPathsForTeacher(teacherId)
    : {
        sessions: '/api/teacher/sessions/',
        sessionDetail: (sessionId) => `/api/teacher/sessions/${sessionId}/`,
        sessionStudents: (sessionId) => `/api/teacher/sessions/${sessionId}/students/`,
        classes: '/api/teacher/classes/',
        classDetail: (classId) => `/api/teacher/classes/${classId}/`,
        availability: '/api/teacher/availability/',
        availabilityDetail: (blockId) => `/api/teacher/availability/${blockId}/`,
        specialAvailability: '/api/teacher/special-availability/',
        specialAvailabilityDetail: (blockId) => `/api/teacher/special-availability/${blockId}/`,
        students: '/api/teacher/students/',
        feedback: '/api/progress/feedback/teacher/',
        feedbackDetail: (feedbackId) => `/api/progress/feedback/teacher/${feedbackId}/`,
        homework: '/api/progress/homework/teacher/',
        homeworkDetail: (homeworkId) => `/api/progress/homework/teacher/${homeworkId}/`,
        homeworkEntry: (homeworkId) => `/api/progress/homework/teacher/${homeworkId}/entries/`,
        classRequests: '/api/teacher/class-requests/',
        classRequestDetail: (requestId) => `/api/teacher/class-requests/${requestId}/`,
        classRequestApprove: (requestId) => `/api/teacher/class-requests/${requestId}/approve/`,
        classRequestDeny: (requestId) => `/api/teacher/class-requests/${requestId}/deny/`,
        classRequestDelete: (requestId) => `/api/teacher/class-requests/${requestId}/delete/`,
        studentHistory: (studentId) => `/api/teacher/students/${studentId}/history/`,
        sessionHistoryPrivacy: (sessionId) => `/api/teacher/sessions/${sessionId}/history-privacy/`,
        newSession: '/teacher/sessions/new',
        staffHome: '/staff',
        staffTeacherSessions: '/teacher/sessions',
      }

  return { isStaff, teacherId: id, paths }
}
