"""Admin Routes - Private Admin Dashboard.

This module provides admin-only routes for managing teachers.
These routes should be excluded from GitHub tracking.
"""

import os
from flask import (
    Blueprint, render_template, request, redirect, url_for, 
    flash, session
)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from database import get_teachers_container_from_env
from admin.admin_auth import admin_required, verify_admin_credentials, is_admin_authenticated

# Create admin blueprint (templates are in main templates/admin directory)
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login page - accessible only to admins."""
    if is_admin_authenticated():
        return redirect(url_for('admin.admin_dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if verify_admin_credentials(username, password):
            session['admin_authenticated'] = True
            session['admin_username'] = username
            flash('Admin login successful', 'success')
            next_url = request.args.get('next') or url_for('admin.admin_dashboard')
            return redirect(next_url)
        else:
            flash('Invalid admin credentials', 'error')
    
    return render_template('admin/admin_login.html')


@admin_bp.route('/logout')
@admin_required
def admin_logout():
    """Admin logout."""
    session.pop('admin_authenticated', None)
    session.pop('admin_username', None)
    flash('Admin logged out successfully', 'success')
    return redirect(url_for('admin.admin_login'))


# Global app reference for logging
_app = None

def init_admin_routes(app):
    """Initialize admin routes with the Flask app."""
    global _app
    _app = app
    app.register_blueprint(admin_bp)


@admin_bp.route('/dashboard')
@admin_required
def admin_dashboard():
    """Admin dashboard for teacher management."""
    try:
        teachers_container = get_teachers_container_from_env()
        
        # Get all teachers (excluding admin)
        query = "SELECT * FROM c WHERE c.role = 'teacher' ORDER BY c.createdAt DESC"
        teachers = list(teachers_container.query_items(query=query, enable_cross_partition_query=True))
        
        # Get teacher count
        teacher_count = len(teachers)
        
        return render_template('admin/admin_dashboard.html', 
                             teachers=teachers, 
                             teacher_count=teacher_count)
    except Exception as e:
        if _app:
            _app.logger.exception("Admin dashboard error")
        else:
            import logging
            logging.exception("Admin dashboard error")
        flash(f'Error loading dashboard: {e}', 'error')
        return render_template('admin/admin_dashboard.html', teachers=[], teacher_count=0)


@admin_bp.route('/create-teacher', methods=['POST'])
@admin_required
def create_teacher():
    """Create a new teacher account."""
    try:
        teacher_id = request.form.get('teacher_id', '').strip()
        teacher_name = request.form.get('teacher_name', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validation
        if not all([teacher_id, teacher_name, password]):
            flash('All fields are required', 'error')
            return redirect(url_for('admin.admin_dashboard'))
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return redirect(url_for('admin.admin_dashboard'))
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long', 'error')
            return redirect(url_for('admin.admin_dashboard'))
        
        # Check for duplicate teacher ID
        teachers_container = get_teachers_container_from_env()
        
        # Use partition key for efficient lookup
        try:
            existing_teacher = teachers_container.read_item(teacher_id, teacher_id)
            flash(f'Teacher ID "{teacher_id}" already exists', 'error')
            return redirect(url_for('admin.admin_dashboard'))
        except:
            # Teacher ID doesn't exist, proceed with creation
            pass
        
        # Create teacher document
        teacher_doc = {
            "id": teacher_id,
            "name": teacher_name,
            "password": generate_password_hash(password),
            "role": "teacher",
            "createdBy": session.get('admin_username', 'admin'),
            "createdAt": datetime.utcnow().isoformat(),
            "isActive": True
        }
        
        # Save to Cosmos DB
        teachers_container.upsert_item(teacher_doc)
        
        flash(f'Teacher "{teacher_name}" (ID: {teacher_id}) created successfully', 'success')
        return redirect(url_for('admin.admin_dashboard'))
        
    except Exception as e:
        app.logger.exception("Create teacher error")
        flash(f'Error creating teacher: {e}', 'error')
        return redirect(url_for('admin.admin_dashboard'))


@admin_bp.route('/teachers')
@admin_required
def list_teachers():
    """List all teachers (JSON API for AJAX)."""
    try:
        teachers_container = get_teachers_container_from_env()
        query = "SELECT * FROM c WHERE c.role = 'teacher' ORDER BY c.createdAt DESC"
        teachers = list(teachers_container.query_items(query=query, enable_cross_partition_query=True))
        
        # Return JSON for AJAX requests
        return {'teachers': teachers, 'count': len(teachers)}
    except Exception as e:
        app.logger.exception("List teachers error")
        return {'error': str(e)}, 500


@admin_bp.route('/delete-teacher/<teacher_id>', methods=['POST'])
@admin_required
def delete_teacher(teacher_id):
    """Delete a teacher account."""
    try:
        teachers_container = get_teachers_container_from_env()
        
        # Use partition key for efficient deletion
        teachers_container.delete_item(teacher_id, teacher_id)
        
        flash(f'Teacher "{teacher_id}" deleted successfully', 'success')
        return redirect(url_for('admin.admin_dashboard'))
        
    except Exception as e:
        if _app:
            _app.logger.exception("Delete teacher error")
        else:
            import logging
            logging.exception("Delete teacher error")
        flash(f'Error deleting teacher: {e}', 'error')
        return redirect(url_for('admin.admin_dashboard'))
