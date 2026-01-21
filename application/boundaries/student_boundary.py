from flask import Blueprint, render_template, session, redirect, url_for, flash, current_app, request
from application.controls.auth_control import AuthControl, requires_roles
from application.controls.attendance_control import AttendanceControl
from application.entities2 import ClassModel, SemesterModel, UserModel
from pprint import pprint
from datetime import date

from database.base import get_session

student_bp = Blueprint('student', __name__)

@student_bp.route('/')
@requires_roles('student')
def dashboard():
    """Main dashboard route"""
    return render_template('institution/student/student_dashboard.html')

@student_bp.route('/profile')
@requires_roles('student')
def profile():
    """User profile route"""
    return render_template('institution/student/student_profile_management.html')

@student_bp.route('/attendance')
@requires_roles('student')
def attendance():
    """Student attendance overview"""
    good_attendance_cutoff = 0.9
    uid = session.get('user_id')
    with get_session() as db_session:
        class_model = ClassModel(db_session)
        sem_model = SemesterModel(db_session)
        term_info = sem_model.get_current_semester_info()
        term_info["student_id"] = uid
        term_info["cutoff"] = good_attendance_cutoff * 100
        
        def analyse_report(report):
            y, m = report["year"], report["month"]
            p, a, l, e = report["p"], report["a"], report["l"], report["e"]
            total = report["total_classes"]
            present_percent = p + a + l / total * 100
            return {
                "month": date(y, m, 1).strftime("%B %Y"),
                "present": p,
                "absent": a,
                "late": l,
                "excused": e,
                "present_percent": present_percent,
                "absent_percent": a / total * 100,
                "total_classes": total,
                "is_good": present_percent >= good_attendance_cutoff
            }
        monthly_report = [analyse_report(report) for report in class_model.student_attendance_monthly(uid, 4)]
        
        term_stats = sem_model.student_dashboard_term_attendance(uid)
        p, a, l, e = term_stats.get("present", 0), term_stats.get("absent", 0), term_stats.get("late", 0), term_stats.get("excused", 0)
        marked = p + a + l + e

        context = {
            "term_info": term_info,
            "monthly_report": monthly_report,
            "overview": {
                "present_percent": (p + l + e) / marked * 100 if marked > 0 else 100.0,
                "absent_percent": a / marked * 100 if marked > 0 else 100.0,
                "present": p + l + e,
                "absent": a,
                "total": sum(term_stats.values()),
            },
            "classes": class_model.student_attendance_absent_late(uid),
        }
    return render_template('institution/student/student_attendance_management.html', **context)


@student_bp.route('/attendance/history')
@requires_roles('student')
def attendance_history():
    """Attendance history route"""
    return render_template('institution/student/student_attendance_management_history.html',
                           user=session.get('user'))


@student_bp.route('/attendance/checkin')
@requires_roles('student')
def class_checkin():
    """Student class check-in view"""
    return render_template('institution/student/student_class_checkin.html',
                           user=session.get('user'))


@student_bp.route('/attendance/checkin/face')
@requires_roles('student')
def class_checkin_face():
    """Student class check-in (face capture)"""
    # Allow frontend to pass a session_id via query string for context (e.g. ?session_id=123)
    session_id = request.args.get('session_id')
    user_id = session.get('user_id')

    return render_template('institution/student/student_class_checkin_face.html',
                           user=session.get('user'),
                           session_id=session_id,
                           user_id=user_id)


@student_bp.route('/appeal')
@requires_roles('student')
def appeal_management():
    """Student appeal management"""
    return render_template('institution/student/student_appeal_management.html', user=session.get('user'))


@student_bp.route('/appeal/form', endpoint='appeal_form')
@requires_roles('student')
def appeal_form():
    """Show appeal form"""
    return render_template('institution/student/student_appeal_management_appeal_form.html', user=session.get('user'))


@student_bp.route('/absent-records', endpoint='absent_records')
@requires_roles('student')
def absent_records():
    """View all absent records (stub)"""
    # For now reuse the attendance history template as a placeholder
    return render_template('institution/student/student_attendance_management_history.html',
                            user=session.get('user'),
                            summary={},
                            records=[])

# TODO: Add more student-specific routes and functionalities as needed