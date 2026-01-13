from flask import Blueprint, render_template, request, jsonify, session, current_app, flash, redirect, url_for
from application.controls.auth_control import AuthControl, requires_roles
from application.controls.attendance_control import AttendanceControl

lecturer_bp = Blueprint('institution_lecturer', __name__)


@lecturer_bp.route('/dashboard')
@requires_roles('lecturer')
def lecturer_dashboard():
    """Lecturer dashboard"""
    return render_template('institution/lecturer/lecturer_dashboard.html')

@lecturer_bp.route('/manage_appeals')
def manage_appeals():
    """Render the lecturer appeal-management page"""
    return render_template('institution/lecturer/lecturer_appeal_management.html')


@lecturer_bp.route('/manage_attendance')
def manage_attendance():
    """Render the lecturer attendance-management page"""
    context = {
        "class": {},
    }
    return render_template('institution/lecturer/lecturer_attendance_management.html', **context)


@lecturer_bp.route('/manage_attendance/statistics')
def attendance_statistics():
    """Render the lecturer attendance statistics page"""
    return render_template('institution/lecturer/lecturer_attendance_management_statistics.html')


@lecturer_bp.route('/manage_classes')
def manage_classes():
    """Render the lecturer class-management page"""
    return render_template('institution/lecturer/lecturer_class_management.html')


@lecturer_bp.route('/timetable')
def timetable():
    """Render the lecturer timetable page"""
    return render_template('institution/lecturer/lecturer_timetable.html')