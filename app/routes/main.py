from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from app.models.models import Patient, MedicalRecord, AuditLog, AnomalyDetection, User
from app import db
from app.utils.security import require_role, log_audit_action, detect_suspicious_activity, PatientForm, MedicalRecordForm, ExportForm
from sqlalchemy import desc, func
from datetime import datetime, timedelta
import logging
import json

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    # If user is logged in, redirect to dashboard, otherwise to login
    if 'user_id' in session:
        return redirect(url_for('main.dashboard'))
    else:
        return redirect(url_for('auth.login'))

@main_bp.route('/dashboard')
@require_role('nurse')  # Minimum role required
def dashboard():
    try:
        # Get recent audit logs for display
        recent_audits = AuditLog.query.order_by(desc(AuditLog.timestamp)).limit(10).all()
        
        # Get unresolved anomalies
        anomalies = AnomalyDetection.query.filter_by(is_resolved=False).order_by(
            desc(AnomalyDetection.timestamp)).limit(5).all()
        
        # Get statistics
        patients_count = Patient.query.count()
        records_count = MedicalRecord.query.count()
        users_count = User.query.count()
        
        # Get additional statistics for the dashboard
        # Anomaly statistics
        total_anomalies = AnomalyDetection.query.count()
        resolved_anomalies = AnomalyDetection.query.filter_by(is_resolved=True).count()
        unresolved_anomalies = total_anomalies - resolved_anomalies
        
        # Audit log statistics
        total_audit_logs = AuditLog.query.count()
        
        # Recent activity counts (last 24 hours)
        twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
        recent_patients = Patient.query.filter(Patient.created_at >= twenty_four_hours_ago).count()
        recent_records = MedicalRecord.query.filter(MedicalRecord.created_at >= twenty_four_hours_ago).count()
        recent_audit_logs = AuditLog.query.filter(AuditLog.timestamp >= twenty_four_hours_ago).count()
        recent_anomalies = AnomalyDetection.query.filter(AnomalyDetection.timestamp >= twenty_four_hours_ago).count()
        
        # User role distribution
        admin_count = User.query.filter_by(role='admin').count()
        doctor_count = User.query.filter_by(role='doctor').count()
        nurse_count = User.query.filter_by(role='nurse').count()
        
        # Anomaly types distribution
        anomaly_types = db.session.query(
            AnomalyDetection.action, 
            func.count(AnomalyDetection.action).label('count')
        ).group_by(AnomalyDetection.action).all()
        
        # Audit log action distribution
        audit_action_types = db.session.query(
            AuditLog.action, 
            func.count(AuditLog.action).label('count')
        ).group_by(AuditLog.action).all()
        
        # Recent anomalies with user details
        recent_anomalies_detailed = db.session.query(
            AnomalyDetection, User
        ).join(User, AnomalyDetection.user_id == User.id).order_by(
            desc(AnomalyDetection.timestamp)
        ).limit(5).all()
        
        # Top active users
        top_users = db.session.query(
            User.username,
            func.count(AuditLog.id).label('activity_count')
        ).join(AuditLog, User.id == AuditLog.user_id).group_by(
            User.id, User.username
        ).order_by(desc('activity_count')).limit(5).all()
        
        # Predictive analytics
        try:
            from app.analytics.predictive_analytics import initialize_analytics, analyze_medical_trends
            
            # Get all medical records for analytics
            all_records = MedicalRecord.query.all()
            
            # Initialize analytics
            analytics_result = initialize_analytics(all_records)
            
            # Analyze trends
            trends = analyze_medical_trends(all_records)
        except Exception as e:
            logger.error(f"Error in predictive analytics: {e}")
            analytics_result = {'trained': False}
            trends = {}
        
        return render_template('dashboard.html', 
                             audits=recent_audits, 
                             anomalies=anomalies,
                             patients_count=patients_count,
                             records_count=records_count,
                             users_count=users_count,
                             total_anomalies=total_anomalies,
                             resolved_anomalies=resolved_anomalies,
                             unresolved_anomalies=unresolved_anomalies,
                             total_audit_logs=total_audit_logs,
                             recent_patients=recent_patients,
                             recent_records=recent_records,
                             recent_audit_logs=recent_audit_logs,
                             recent_anomalies=recent_anomalies,
                             admin_count=admin_count,
                             doctor_count=doctor_count,
                             nurse_count=nurse_count,
                             anomaly_types=anomaly_types,
                             audit_action_types=audit_action_types,
                             recent_anomalies_detailed=recent_anomalies_detailed,
                             top_users=top_users,
                             analytics_result=analytics_result,
                             trends=trends)
    except Exception as e:
        logger.error(f"Error loading dashboard: {str(e)}")
        flash('An error occurred while loading the dashboard', 'error')
        return render_template('dashboard.html', 
                             audits=[], 
                             anomalies=[],
                             patients_count=0,
                             records_count=0,
                             users_count=0,
                             total_anomalies=0,
                             resolved_anomalies=0,
                             unresolved_anomalies=0,
                             total_audit_logs=0,
                             recent_patients=0,
                             recent_records=0,
                             recent_audit_logs=0,
                             recent_anomalies=0,
                             admin_count=0,
                             doctor_count=0,
                             nurse_count=0,
                             anomaly_types=[],
                             audit_action_types=[],
                             recent_anomalies_detailed=[],
                             top_users=[])

# Nurse can only view patients (not add/edit/delete)
@main_bp.route('/patients')
@require_role('nurse')
def patients():
    try:
        page = request.args.get('page', 1, type=int)
        search = request.args.get('search', '', type=str)
        
        # If there's a search query, filter patients
        if search:
            patients_query = Patient.query.filter(
                db.or_(
                    Patient.name.contains(search),
                    Patient.medical_record_number.contains(search),
                    Patient.phone.contains(search)
                )
            ).order_by(Patient.name)
        else:
            patients_query = Patient.query.order_by(Patient.name)
        
        patients = patients_query.paginate(
            page=page, per_page=10, error_out=False)
        
        return render_template('patients.html', patients=patients, search=search)
    except Exception as e:
        logger.error(f"Error loading patients: {str(e)}")
        flash('An error occurred while loading patients', 'error')
        return render_template('patients.html', patients=[], search='')

# Doctor can add patients
@main_bp.route('/patients/add', methods=['GET', 'POST'])
@require_role('doctor')
def add_patient():
    form = PatientForm()
    if form.validate_on_submit():
        try:
            name = form.name.data
            dob = form.dob.data
            gender = form.gender.data
            mrn = form.medical_record_number.data
            
            # Check if patient already exists
            if Patient.query.filter_by(medical_record_number=mrn).first():
                flash('Patient with this MRN already exists')
                return render_template('add_patient.html', form=form)
            
            patient = Patient(
                name=name,
                dob=dob,
                gender=gender,
                medical_record_number=mrn,
                phone=form.phone.data,
                email=form.email.data,
                address=form.address.data,
                emergency_contact_name=form.emergency_contact_name.data,
                emergency_contact_phone=form.emergency_contact_phone.data,
                blood_type=form.blood_type.data,
                allergies=form.allergies.data
            )
            
            db.session.add(patient)
            db.session.commit()
            
            # Log audit action
            log_audit_action(session['user_id'], 'create', 'patient', patient.id, db.session)
            
            flash('Patient added successfully')
            return redirect(url_for('main.patients'))
        except Exception as e:
            logger.error(f"Error adding patient: {str(e)}")
            logger.error(f"Form errors: {form.errors}")
            db.session.rollback()
            flash('An error occurred while adding the patient: ' + str(e), 'error')
    elif request.method == 'POST':
        logger.error(f"Form validation failed: {form.errors}")
        flash('Please correct the errors in the form: ' + str(form.errors), 'error')
    
    return render_template('add_patient.html', form=form)

# Doctor can edit patients
@main_bp.route('/patients/edit/<int:patient_id>', methods=['GET', 'POST'])
@require_role('doctor')
def edit_patient(patient_id):
    try:
        patient = Patient.query.get_or_404(patient_id)
        form = PatientForm(obj=patient)
        
        if form.validate_on_submit():
            try:
                patient.name = form.name.data
                # Handle date conversion properly
                if isinstance(form.dob.data, str):
                    from datetime import datetime
                    patient.dob = datetime.strptime(form.dob.data, '%Y-%m-%d').date()
                else:
                    patient.dob = form.dob.data
                patient.gender = form.gender.data
                patient.medical_record_number = form.medical_record_number.data
                patient.phone = form.phone.data
                patient.email = form.email.data
                patient.address = form.address.data
                patient.emergency_contact_name = form.emergency_contact_name.data
                patient.emergency_contact_phone = form.emergency_contact_phone.data
                patient.blood_type = form.blood_type.data
                patient.allergies = form.allergies.data
                
                # Check if MRN already exists for another patient
                existing_patient = Patient.query.filter_by(medical_record_number=form.medical_record_number.data).first()
                if existing_patient and existing_patient.id != patient.id:
                    flash('Patient with this MRN already exists')
                    return render_template('edit_patient.html', form=form, patient=patient)
                
                db.session.commit()
                
                # Log audit action
                log_audit_action(session['user_id'], 'update', 'patient', patient.id, db.session)
                
                flash('Patient updated successfully')
                return redirect(url_for('main.view_patient', patient_id=patient.id))
            except Exception as e:
                logger.error(f"Error updating patient: {str(e)}")
                logger.error(f"Form errors: {form.errors}")
                db.session.rollback()
                flash('An error occurred while updating the patient: ' + str(e), 'error')
        elif request.method == 'POST':
            logger.error(f"Form validation failed: {form.errors}")
            flash('Please correct the errors in the form: ' + str(form.errors), 'error')
        
        return render_template('edit_patient.html', form=form, patient=patient)
    except Exception as e:
        logger.error(f"Error loading edit patient page: {str(e)}")
        flash('An error occurred while loading the page', 'error')
        return redirect(url_for('main.patients'))

@main_bp.route('/patients/<int:patient_id>')
@require_role('nurse')
def view_patient(patient_id):
    try:
        patient = Patient.query.get_or_404(patient_id)
        # Only show non-sensitive information to nurses
        page = request.args.get('page', 1, type=int)
        records = MedicalRecord.query.filter_by(patient_id=patient_id).order_by(
            desc(MedicalRecord.created_at)).paginate(
            page=page, per_page=5, error_out=False)
        
        # Get patient statistics
        total_records = MedicalRecord.query.filter_by(patient_id=patient_id).count()
        doctors_count = db.session.query(MedicalRecord.doctor_id).filter_by(
            patient_id=patient_id).distinct().count()
        
        # Log audit action
        log_audit_action(session['user_id'], 'view', 'patient', patient_id, db.session)
        
        return render_template('view_patient.html', patient=patient, records=records,
                             total_records=total_records, doctors_count=doctors_count)
    except Exception as e:
        logger.error(f"Error viewing patient: {str(e)}")
        flash('An error occurred while viewing the patient', 'error')
        return redirect(url_for('main.patients'))

# Doctor can add patient records
@main_bp.route('/records/add/<int:patient_id>', methods=['GET', 'POST'])
@require_role('doctor')
def add_record(patient_id):
    try:
        patient = Patient.query.get_or_404(patient_id)
        form = MedicalRecordForm()
        
        if form.validate_on_submit():
            try:
                diagnosis = form.diagnosis.data
                treatment = form.treatment.data
                prescription = form.prescription.data
                
                record = MedicalRecord(
                    patient_id=patient_id,
                    doctor_id=session['user_id'],
                    diagnosis=diagnosis,
                    treatment=treatment,
                    prescription=prescription
                )
                
                # Encrypt sensitive data
                try:
                    from app.encryption.encryption import encrypt_medical_record
                    encrypted_data = encrypt_medical_record(record)
                    record.encrypted_data = json.dumps(encrypted_data)
                    
                    # Clear plaintext data after encryption
                    record.diagnosis = '[ENCRYPTED]'
                    record.treatment = '[ENCRYPTED]'
                    record.prescription = '[ENCRYPTED]' if prescription else None
                except Exception as e:
                    logger.error(f"Error encrypting medical record: {e}")
                
                # Use the new save method that automatically calculates the hash
                record.save(db.session)
                
                # Log audit action
                log_audit_action(session['user_id'], 'create', 'medical_record', record.id, db.session)
                
                flash('Medical record added successfully')
                return redirect(url_for('main.view_patient', patient_id=patient_id))
            except Exception as e:
                logger.error(f"Error adding medical record: {str(e)}")
                db.session.rollback()
                flash('An error occurred while adding the medical record', 'error')
        elif request.method == 'POST':
            flash('Please correct the errors in the form')
        
        return render_template('add_record.html', form=form, patient=patient)
    except Exception as e:
        logger.error(f"Error loading add record page: {str(e)}")
        flash('An error occurred while loading the page', 'error')
        return redirect(url_for('main.patients'))

# Doctor can edit patient records
@main_bp.route('/records/edit/<int:record_id>', methods=['GET', 'POST'])
@require_role('doctor')
def edit_record(record_id):
    try:
        record = MedicalRecord.query.get_or_404(record_id)
        form = MedicalRecordForm(obj=record)
        
        # If this is a GET request, decrypt the data to show in the form
        if request.method == 'GET':
            try:
                # Temporarily decrypt the data for editing
                if record.encrypted_data:
                    from app.encryption.encryption import decrypt_sensitive_data
                    import json
                    encrypted_dict = json.loads(record.encrypted_data)
                    
                    # Decrypt each field if it exists
                    if 'diagnosis' in encrypted_dict and encrypted_dict['diagnosis']:
                        form.diagnosis.data = decrypt_sensitive_data(encrypted_dict['diagnosis'])
                    if 'treatment' in encrypted_dict and encrypted_dict['treatment']:
                        form.treatment.data = decrypt_sensitive_data(encrypted_dict['treatment'])
                    if 'prescription' in encrypted_dict and encrypted_dict['prescription']:
                        form.prescription.data = decrypt_sensitive_data(encrypted_dict['prescription'])
            except Exception as e:
                logger.error(f"Error decrypting medical record for edit: {e}")
        
        if form.validate_on_submit():
            try:
                # Get the plain text values from the form
                diagnosis = form.diagnosis.data
                treatment = form.treatment.data
                prescription = form.prescription.data
                
                # Update the record with plain text (will be encrypted before saving)
                record.diagnosis = diagnosis
                record.treatment = treatment
                record.prescription = prescription
                
                # Encrypt sensitive data
                try:
                    from app.encryption.encryption import encrypt_medical_record
                    encrypted_data = encrypt_medical_record(record)
                    record.encrypted_data = json.dumps(encrypted_data)
                    
                    # Clear plaintext data after encryption
                    record.diagnosis = '[ENCRYPTED]'
                    record.treatment = '[ENCRYPTED]'
                    record.prescription = '[ENCRYPTED]' if prescription else None
                except Exception as e:
                    logger.error(f"Error encrypting medical record: {e}")
                
                # Recalculate hash for integrity
                record.record_hash = record.calculate_hash()
                
                db.session.commit()
                
                # Log audit action
                log_audit_action(session['user_id'], 'update', 'medical_record', record.id, db.session)
                
                flash('Medical record updated successfully')
                return redirect(url_for('main.view_record', record_id=record_id))
            except Exception as e:
                logger.error(f"Error updating medical record: {str(e)}")
                db.session.rollback()
                flash('An error occurred while updating the medical record', 'error')
        elif request.method == 'POST':
            flash('Please correct the errors in the form')
        
        return render_template('edit_record.html', form=form, record=record)
    except Exception as e:
        logger.error(f"Error loading edit record page: {str(e)}")
        flash('An error occurred while loading the page', 'error')
        return redirect(url_for('main.patients'))

@main_bp.route('/records/<int:record_id>')
@require_role('doctor')
def view_record(record_id):
    try:
        record = MedicalRecord.query.get_or_404(record_id)
        
        # Decrypt sensitive data for board members and admins
        decrypted_data = None
        user_role = session.get('user_role')
        if user_role in ['board_member', 'admin']:
            decrypted_data = record.decrypt_sensitive_data(user_role)
        
        # Verify record integrity
        is_valid = record.verify_integrity()
        
        if not is_valid:
            # Log anomaly with enhanced detection
            detect_suspicious_activity(
                session['user_id'], 
                'record_integrity_violation', 
                f'Record {record_id} failed integrity check',
                db.session
            )
            flash('Warning: Record integrity check failed!', 'error')
        
        # Log audit action
        log_audit_action(session['user_id'], 'view', 'medical_record', record_id, db.session)
        
        # Get audit trail for this specific record (only for admins)
        record_audits = []
        if session.get('user_role') == 'admin':
            record_audits = AuditLog.query.filter_by(
                table_name='medical_record',
                record_id=record_id
            ).order_by(desc(AuditLog.timestamp)).all()
        
        return render_template('view_record.html', record=record, is_valid=is_valid, record_audits=record_audits, decrypted_data=decrypted_data)
    except Exception as e:
        logger.error(f"Error viewing medical record: {str(e)}")
        flash('An error occurred while viewing the medical record', 'error')
        return redirect(url_for('main.patients'))

@main_bp.route('/audit')
@require_role('admin')
def audit_logs():
    try:
        page = request.args.get('page', 1, type=int)
        logs = AuditLog.query.order_by(desc(AuditLog.timestamp)).paginate(
            page=page, per_page=20, error_out=False)
        
        # Enhance logs with patient MRN for privacy
        enhanced_logs = []
        for log in logs.items:
            enhanced_log = {
                'log': log,
                'patient_mrn': None
            }
            
            # If this is a patient-related action, get the MRN
            if log.table_name == 'patient' and log.record_id:
                patient = Patient.query.get(log.record_id)
                if patient:
                    enhanced_log['patient_mrn'] = patient.medical_record_number
            
            # If this is a medical record action, get the patient MRN
            elif log.table_name == 'medical_record' and log.record_id:
                medical_record = MedicalRecord.query.get(log.record_id)
                if medical_record and medical_record.patient:
                    enhanced_log['patient_mrn'] = medical_record.patient.medical_record_number
            
            enhanced_logs.append(enhanced_log)
        
        return render_template('audit_logs.html', logs=logs, enhanced_logs=enhanced_logs)
    except Exception as e:
        logger.error(f"Error loading audit logs: {str(e)}")
        flash('An error occurred while loading audit logs', 'error')
        logs = []
        return render_template('audit_logs.html', logs=logs)

@main_bp.route('/access-control')
@require_role('admin')
def access_control():
    return render_template('access_control.html')

@main_bp.route('/notifications')
@require_role('admin')
def notifications():
    try:
        # Get recent anomalies (notifications)
        notifications = AnomalyDetection.query.order_by(desc(AnomalyDetection.timestamp)).limit(50).all()
        
        return render_template('notifications.html', notifications=notifications)
    except Exception as e:
        logger.error(f"Error loading notifications: {str(e)}")
        flash('An error occurred while loading notifications', 'error')
        return render_template('notifications.html', notifications=[])

@main_bp.route('/anomalies/resolve/<int:anomaly_id>')
@require_role('admin')
def resolve_anomaly(anomaly_id):
    try:
        anomaly = AnomalyDetection.query.get_or_404(anomaly_id)
        anomaly.is_resolved = True
        db.session.commit()
        
        flash('Anomaly marked as resolved')
    except Exception as e:
        logger.error(f"Error resolving anomaly: {str(e)}")
        db.session.rollback()
        flash('An error occurred while resolving the anomaly', 'error')
    
    return redirect(url_for('main.notifications'))

@main_bp.route('/anomalies')
@require_role('admin')
def anomalies():
    try:
        page = request.args.get('page', 1, type=int)
        anomalies = AnomalyDetection.query.order_by(desc(AnomalyDetection.timestamp)).paginate(
            page=page, per_page=20, error_out=False)
        
        # Enhance anomalies with patient MRN for privacy
        enhanced_anomalies = []
        for anomaly in anomalies.items:
            enhanced_anomaly = {
                'anomaly': anomaly,
                'patient_mrn': None
            }
            
            # Extract patient MRN from details if available
            if 'Record' in anomaly.details:
                # Try to extract record ID from details like "Record 2 failed integrity check"
                import re
                record_match = re.search(r'Record (\d+)', anomaly.details)
                if record_match:
                    record_id = int(record_match.group(1))
                    medical_record = MedicalRecord.query.get(record_id)
                    if medical_record and medical_record.patient:
                        enhanced_anomaly['patient_mrn'] = medical_record.patient.medical_record_number
            
            enhanced_anomalies.append(enhanced_anomaly)
        
        return render_template('anomalies.html', anomalies=anomalies, enhanced_anomalies=enhanced_anomalies)
    except Exception as e:
        logger.error(f"Error loading anomalies: {str(e)}")
        flash('An error occurred while loading anomalies', 'error')
        anomalies = []
        return render_template('anomalies.html', anomalies=anomalies)

@main_bp.route('/anomalies/<int:anomaly_id>')
@require_role('admin')
def view_anomaly(anomaly_id):
    try:
        anomaly = AnomalyDetection.query.get_or_404(anomaly_id)
        
        # Get user information
        user = User.query.get(anomaly.user_id)
        
        # Extract patient MRN from details if available
        patient_mrn = None
        if 'Record' in anomaly.details:
            # Try to extract record ID from details like "Record 2 failed integrity check"
            import re
            record_match = re.search(r'Record (\d+)', anomaly.details)
            if record_match:
                record_id = int(record_match.group(1))
                medical_record = MedicalRecord.query.get(record_id)
                if medical_record and medical_record.patient:
                    patient_mrn = medical_record.patient.medical_record_number
        
        return render_template('view_anomaly.html', anomaly=anomaly, user=user, patient_mrn=patient_mrn)
    except Exception as e:
        logger.error(f"Error viewing anomaly: {str(e)}")
        flash('An error occurred while viewing the anomaly', 'error')
        return redirect(url_for('main.anomalies'))

@main_bp.route('/patients/export/<int:patient_id>', methods=['GET', 'POST'])
@require_role('doctor')
def export_patient_data(patient_id):
    try:
        patient = Patient.query.get_or_404(patient_id)
        form = ExportForm()
        
        if form.validate_on_submit():
            format = form.format.data
            include_audit = form.includeAudit.data == 'yes'
            
            # Get all medical records for this patient
            records = MedicalRecord.query.filter_by(patient_id=patient_id).order_by(
                MedicalRecord.created_at).all()
            
            # Get audit trail if requested
            audit_logs = []
            if include_audit:
                audit_logs = AuditLog.query.filter_by(
                    table_name='medical_record'
                ).filter(
                    AuditLog.record_id.in_([r.id for r in records])
                ).order_by(AuditLog.timestamp).all()
            
            # Log audit action
            log_audit_action(session['user_id'], 'export', 'patient_data', patient_id, db.session)
            
            # For now, we'll just redirect back with a success message
            # In a real implementation, this would generate and return the actual export file
            flash(f'Patient data export initiated in {format.upper()} format. In a full implementation, this would generate and download the file.')
            return redirect(url_for('main.view_patient', patient_id=patient.id))
        
        return render_template('export_patient.html', form=form, patient=patient)
    except Exception as e:
        logger.error(f"Error exporting patient data: {str(e)}")
        flash('An error occurred while preparing the export', 'error')
        return redirect(url_for('main.view_patient', patient_id=patient_id))

@main_bp.route('/patients/summary/<int:patient_id>')
@require_role('doctor')
def patient_summary(patient_id):
    try:
        patient = Patient.query.get_or_404(patient_id)
        
        # Get all medical records for this patient
        all_records = MedicalRecord.query.filter_by(patient_id=patient_id).order_by(
            MedicalRecord.created_at).all()
        
        # Get recent records (last 5)
        recent_records = MedicalRecord.query.filter_by(patient_id=patient_id).order_by(
            desc(MedicalRecord.created_at)).limit(5).all()
        
        # Get statistics
        total_records = len(all_records)
        doctors_count = len(set(record.doctor_id for record in all_records))
        
        # Count unique conditions and medications
        conditions = set()
        medications = set()
        for record in all_records:
            conditions.add(record.diagnosis.lower())
            if record.prescription:
                medications.add(record.prescription.lower())
        
        conditions_count = len(conditions)
        medications_count = len(medications)
        
        # Log audit action
        log_audit_action(session['user_id'], 'view', 'patient_summary', patient_id, db.session)
        
        return render_template('patient_summary.html', 
                             patient=patient,
                             all_records=all_records,
                             recent_records=recent_records,
                             total_records=total_records,
                             doctors_count=doctors_count,
                             conditions_count=conditions_count,
                             medications_count=medications_count)
    except Exception as e:
        logger.error(f"Error generating patient summary: {str(e)}")
        flash('An error occurred while generating the patient summary', 'error')
        return redirect(url_for('main.view_patient', patient_id=patient_id))
