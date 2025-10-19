from flask import Blueprint, request, session, redirect, url_for, render_template, flash
from app.models.models import User
from app import db
from app.utils.security import hash_password, verify_password, require_role, LoginForm, UserForm
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)

def create_or_update_user(user, form, is_new=True):
    """Helper function to create or update a user"""
    try:
        # For new users, check if username or email already exists
        if is_new:
            if User.query.filter_by(username=form.username.data).first():
                flash('Username already exists')
                return False
            
            if User.query.filter_by(email=form.email.data).first():
                flash('Email already registered')
                return False
        
        # Update user fields
        user.username = form.username.data
        user.email = form.email.data
        user.role = form.role.data
        
        # Only update password if provided (for existing users) or always for new users
        if form.password.data or is_new:
            user.password_hash = hash_password(form.password.data)
        
        return True
    except Exception as e:
        logger.error(f"Error in create_or_update_user: {str(e)}")
        flash('An error occurred while processing user data', 'error')
        return False

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    try:
        if form.validate_on_submit():
            username = form.username.data
            password = form.password.data
            
            user = User.query.filter_by(username=username).first()
            
            if user and verify_password(password, user.password_hash):
                session['user_id'] = user.id
                session['username'] = user.username
                session['user_role'] = user.role
                return redirect(url_for('main.dashboard'))
            else:
                flash('Invalid username or password')
        elif request.method == 'POST':
            flash('Please correct the errors in the form')
    except Exception as e:
        logger.error(f"Error during login: {str(e)}")
        flash('An error occurred during login', 'error')
    
    return render_template('login.html', form=form)

@auth_bp.route('/logout', methods=['GET', 'POST'])
def logout():
    if request.method == 'POST':
        try:
            session.clear()
            flash('You have been successfully logged out.', 'success')
        except Exception as e:
            logger.error(f"Error during logout: {str(e)}")
            flash('An error occurred during logout', 'error')
        return redirect(url_for('auth.login'))
    else:
        # For GET requests, redirect to login (or show confirmation)
        try:
            session.clear()
            flash('You have been successfully logged out.', 'success')
        except Exception as e:
            logger.error(f"Error during logout: {str(e)}")
            flash('An error occurred during logout', 'error')
        return redirect(url_for('auth.login'))

# Admin routes for user management
@auth_bp.route('/users')
@require_role('admin')
def list_users():
    try:
        users = User.query.all()
        return render_template('users.html', users=users)
    except Exception as e:
        logger.error(f"Error loading users: {str(e)}")
        flash('An error occurred while loading users', 'error')
        return render_template('users.html', users=[])

@auth_bp.route('/users/add', methods=['GET', 'POST'])
@require_role('admin')
def add_user():
    form = UserForm()
    try:
        if form.validate_on_submit():
            user = User()  # Create a new user instance
            if create_or_update_user(user, form, is_new=True):
                db.session.add(user)
                db.session.commit()
                flash('User added successfully')
                return redirect(url_for('auth.list_users'))
        elif request.method == 'POST':
            flash('Please correct the errors in the form')
    except Exception as e:
        logger.error(f"Error adding user: {str(e)}")
        db.session.rollback()
        flash('An error occurred while adding the user', 'error')
    
    return render_template('add_user.html', form=form)

@auth_bp.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@require_role('admin')
def edit_user(user_id):
    user = None
    form = None
    try:
        user = User.query.get_or_404(user_id)
        form = UserForm(obj=user)
        
        if form.validate_on_submit():
            if create_or_update_user(user, form, is_new=False):
                db.session.commit()
                flash('User updated successfully')
                return redirect(url_for('auth.list_users'))
        elif request.method == 'POST':
            flash('Please correct the errors in the form')
    except Exception as e:
        logger.error(f"Error updating user: {str(e)}")
        db.session.rollback()
        flash('An error occurred while updating the user', 'error')
    
    return render_template('edit_user.html', form=form, user=user)

@auth_bp.route('/users/delete/<int:user_id>')
@require_role('admin')
def delete_user(user_id):
    try:
        user = User.query.get_or_404(user_id)
        db.session.delete(user)
        db.session.commit()
        flash('User deleted successfully')
    except Exception as e:
        logger.error(f"Error deleting user: {str(e)}")
        db.session.rollback()
        flash('An error occurred while deleting the user', 'error')
    
    return redirect(url_for('auth.list_users'))