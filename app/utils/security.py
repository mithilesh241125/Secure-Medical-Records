import hashlib
import hmac
import os
import bcrypt
from functools import wraps
from flask import abort, session, request
from datetime import datetime, timedelta
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, DateField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional, Regexp

# Form validation classes
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6, max=128)])

class UserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Length(max=120)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6, max=128)])
    role = SelectField('Role', validators=[DataRequired()], 
                       choices=[('board_member', 'Board Member'), ('admin', 'Admin'), ('doctor', 'Doctor'), ('nurse', 'Nurse')])

class PatientForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(max=100)])
    medical_record_number = StringField('MRN', validators=[DataRequired(), Length(max=50)])
    dob = DateField('Date of Birth', validators=[DataRequired()])
    gender = SelectField('Gender', validators=[DataRequired()], 
                         choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')])
    # Adding more useful fields for patient management
    phone = StringField('Phone Number', validators=[Length(max=20)])
    email = StringField('Email', validators=[Length(max=120)])
    address = TextAreaField('Address', validators=[Length(max=200)])
    emergency_contact_name = StringField('Emergency Contact Name', validators=[Length(max=100)])
    emergency_contact_phone = StringField('Emergency Contact Phone', validators=[Length(max=20)])
    blood_type = SelectField('Blood Type', choices=[
        ('', 'Select Blood Type'),
        ('A+', 'A+'), ('A-', 'A-'), 
        ('B+', 'B+'), ('B-', 'B-'), 
        ('AB+', 'AB+'), ('AB-', 'AB-'), 
        ('O+', 'O+'), ('O-', 'O-'),
        ('Unknown', 'Unknown')
    ])
    allergies = TextAreaField('Allergies', validators=[Length(max=500)])

class MedicalRecordForm(FlaskForm):
    diagnosis = TextAreaField('Diagnosis', validators=[DataRequired()])
    treatment = TextAreaField('Treatment', validators=[DataRequired()])
    prescription = TextAreaField('Prescription', validators=[Optional()])

# Adding a new form for data export
class ExportForm(FlaskForm):
    format = SelectField('Format', choices=[
        ('pdf', 'PDF Document'),
        ('csv', 'CSV File'),
        ('json', 'JSON Data')
    ], validators=[DataRequired()])
    includeAudit = SelectField('Include Audit Trail', choices=[
        ('yes', 'Yes'),
        ('no', 'No')
    ], default='yes')

def hash_password(password):
    """Hash a password using bcrypt"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt)

def verify_password(password, hashed):
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed)

def generate_token(user_id, secret_key):
    """Generate a simple token for session management"""
    data = f"{user_id}:{datetime.utcnow().timestamp()}".encode()
    return hmac.new(secret_key.encode(), data, hashlib.sha256).hexdigest()

def verify_token(token, user_id, secret_key):
    """Verify a token"""
    expected = generate_token(user_id, secret_key)
    return hmac.compare_digest(token, expected)

def require_role(required_role):
    """Decorator to require a specific role for accessing a route"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check if user is logged in
            if 'user_role' not in session:
                abort(401)
            
            # Check for session timeout (30 minutes)
            if 'last_activity' in session:
                last_activity = datetime.fromisoformat(session['last_activity'])
                if datetime.utcnow() - last_activity > timedelta(minutes=30):
                    session.clear()
                    abort(401)
            
            # Update last activity
            session['last_activity'] = datetime.utcnow().isoformat()
            
            # Check for IP binding (basic security measure)
            if 'ip_address' in session and session['ip_address'] != request.remote_addr:
                session.clear()
                abort(401)
            
            # Set IP address in session if not already set
            if 'ip_address' not in session:
                session['ip_address'] = request.remote_addr
            
            user_role = session['user_role']
            role_hierarchy = {
                'board_member': 4,  # Highest level
                'admin': 3,
                'doctor': 2,
                'nurse': 1
            }
            
            if role_hierarchy.get(user_role, 0) < role_hierarchy.get(required_role, 0):
                abort(403)
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def log_audit_action(user_id, action, table_name, record_id, db_session):
    """Log an audit action to the database with enhanced details"""
    from app.models.models import AuditLog, User
    
    # Get user for additional context
    user = User.query.get(user_id)
    username = user.username if user else "Unknown"
    
    audit_log = AuditLog(
        user_id=user_id,
        action=action,
        table_name=table_name,
        record_id=record_id,
        ip_address=request.remote_addr
    )
    
    db_session.add(audit_log)
    db_session.commit()
    
    # Also log to application logger for additional traceability
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"AUDIT: User {username}({user_id}) performed '{action}' on {table_name}:{record_id} from IP {request.remote_addr}")
    
    # Add to blockchain for immutable audit trail
    try:
        from app.blockchain.blockchain import add_audit_record
        add_audit_record(action, user_id, table_name, record_id, f"User: {username}")
    except Exception as e:
        logger.error(f"Failed to add audit record to blockchain: {e}")

def detect_anomaly(user_id, action, details, db_session):
    """Detect and log potential anomalies"""
    from app.models.models import AnomalyDetection
    
    # Simple anomaly detection rules
    # In a real system, this would be more sophisticated
    anomaly = AnomalyDetection(
        user_id=user_id,
        action=action,
        details=details,
        ip_address=request.remote_addr
    )
    
    db_session.add(anomaly)
    db_session.commit()
    
    return anomaly

def detect_suspicious_activity(user_id, action, details, db_session):
    """
    Enhanced anomaly detection with more sophisticated rules
    """
    from app.models.models import AnomalyDetection, AuditLog, User
    from sqlalchemy import func
    
    # Get current timestamp
    now = datetime.utcnow()
    
    # Get user for additional context
    user = User.query.get(user_id)
    username = user.username if user else "Unknown"
    
    # Rule 1: Too many actions in a short time (possible brute force)
    one_minute_ago = now - timedelta(minutes=1)
    recent_actions = AuditLog.query.filter(
        AuditLog.user_id == user_id,
        AuditLog.timestamp >= one_minute_ago
    ).count()
    
    if recent_actions > 10:  # More than 10 actions per minute
        anomaly = AnomalyDetection(
            user_id=user_id,
            action='suspicious_activity_rate',
            details=f'User {username} performed {recent_actions} actions in the last minute. {details}',
            ip_address=request.remote_addr
        )
        db_session.add(anomaly)
        db_session.commit()
        return anomaly
    
    # Rule 2: Unusual access patterns (accessing records outside normal hours)
    current_hour = now.hour
    if current_hour < 6 or current_hour > 22:  # Outside 6 AM - 10 PM
        anomaly = AnomalyDetection(
            user_id=user_id,
            action='unusual_access_time',
            details=f'User {username} accessed system at unusual time ({current_hour}:00). {details}',
            ip_address=request.remote_addr
        )
        db_session.add(anomaly)
        db_session.commit()
        return anomaly
    
    # Rule 3: Multiple failed integrity checks
    if action == 'record_integrity_violation':
        # Check if this user has had multiple integrity violations recently
        one_hour_ago = now - timedelta(hours=1)
        recent_integrity_violations = AnomalyDetection.query.filter(
            AnomalyDetection.user_id == user_id,
            AnomalyDetection.action == 'record_integrity_violation',
            AnomalyDetection.timestamp >= one_hour_ago
        ).count()
        
        if recent_integrity_violations > 2:  # More than 2 integrity violations per hour
            anomaly = AnomalyDetection(
                user_id=user_id,
                action='multiple_integrity_violations',
                details=f'User {username} has {recent_integrity_violations} integrity violations in the last hour. {details}',
                ip_address=request.remote_addr
            )
            db_session.add(anomaly)
            db_session.commit()
            return anomaly
    
    # Rule 4: Repeated failed login attempts
    if action == 'failed_login':
        # Check recent failed login attempts
        five_minutes_ago = now - timedelta(minutes=5)
        recent_failed_logins = AnomalyDetection.query.filter(
            AnomalyDetection.user_id == user_id,
            AnomalyDetection.action == 'failed_login',
            AnomalyDetection.timestamp >= five_minutes_ago
        ).count()
        
        if recent_failed_logins > 3:  # More than 3 failed logins in 5 minutes
            anomaly = AnomalyDetection(
                user_id=user_id,
                action='brute_force_attempt',
                details=f'User {username} has {recent_failed_logins} failed login attempts in the last 5 minutes. {details}',
                ip_address=request.remote_addr
            )
            db_session.add(anomaly)
            db_session.commit()
            return anomaly
    
    # Rule 5: Access from multiple IPs in short time (potential account compromise)
    one_hour_ago = now - timedelta(hours=1)
    recent_ips = db_session.query(AuditLog.ip_address).filter(
        AuditLog.user_id == user_id,
        AuditLog.timestamp >= one_hour_ago
    ).distinct().count()
    
    if recent_ips > 3:  # More than 3 different IPs in one hour
        anomaly = AnomalyDetection(
            user_id=user_id,
            action='multiple_ip_access',
            details=f'User {username} accessed system from {recent_ips} different IPs in the last hour. {details}',
            ip_address=request.remote_addr
        )
        db_session.add(anomaly)
        db_session.commit()
        return anomaly
    
    # If no specific rules triggered, create a general anomaly
    anomaly = AnomalyDetection(
        user_id=user_id,
        action=action,
        details=f'User {username}: {details}',
        ip_address=request.remote_addr
    )
    
    db_session.add(anomaly)
    db_session.commit()
    
    return anomaly