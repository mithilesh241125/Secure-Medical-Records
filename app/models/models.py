from datetime import datetime, date
import hashlib
import json
from app import db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False, index=True)  # doctor, nurse, admin, board_member
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    dob = db.Column(db.Date, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    medical_record_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # Additional patient information fields
    phone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(120), nullable=True, index=True)
    address = db.Column(db.Text, nullable=True)
    emergency_contact_name = db.Column(db.String(100), nullable=True)
    emergency_contact_phone = db.Column(db.String(20), nullable=True)
    blood_type = db.Column(db.String(10), nullable=True)
    allergies = db.Column(db.Text, nullable=True)
    
    def __repr__(self):
        return f'<Patient {self.name}>'
    
    @property
    def age(self):
        """Calculate patient age based on date of birth"""
        today = date.today()
        return today.year - self.dob.year - ((today.month, today.day) < (self.dob.month, self.dob.day))

class MedicalRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False, index=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    diagnosis = db.Column(db.Text, nullable=False)
    treatment = db.Column(db.Text, nullable=False)
    prescription = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)
    
    # Encrypted data storage
    encrypted_data = db.Column(db.Text)  # For storing encrypted sensitive fields
    
    # Hash for integrity verification - make it nullable since we set it after creation
    record_hash = db.Column(db.String(64), nullable=True)
    
    patient = db.relationship('Patient', backref=db.backref('medical_records', lazy=True))
    doctor = db.relationship('User', backref=db.backref('medical_records', lazy=True))
    
    def calculate_hash(self):
        """Calculate SHA-256 hash of the record for integrity verification"""
        # Include more fields for better integrity verification
        # Exclude updated_at from hash calculation as it changes on every access
        record_data = {
            'id': self.id,
            'patient_id': self.patient_id,
            'doctor_id': self.doctor_id,
            'diagnosis': self.diagnosis,
            'treatment': self.treatment,
            'prescription': self.prescription,
            # Include created_at for verification but not updated_at
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
        record_str = json.dumps(record_data, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(record_str.encode('utf-8')).hexdigest()
    
    def verify_integrity(self):
        """Verify the integrity of the record with detailed logging"""
        if not self.record_hash:
            return False
        calculated_hash = self.calculate_hash()
        is_valid = self.record_hash == calculated_hash
        
        # Log integrity check results for audit trail
        import logging
        logger = logging.getLogger(__name__)
        if not is_valid:
            logger.warning(f"INTEGRITY CHECK FAILED: Record {self.id} - Stored hash: {self.record_hash} - Calculated hash: {calculated_hash}")
        
        return is_valid
    
    def save(self, session):
        """Save the record and automatically calculate the hash"""
        # Add to session
        session.add(self)
        # Commit first to ensure all fields are populated
        session.commit()
        # Now recalculate hash with committed values
        self.record_hash = self.calculate_hash()
        # Commit again to save the hash
        session.commit()
    
    @property
    def diagnosis_summary(self):
        """Get a summary of the diagnosis (first 50 characters)"""
        return self.diagnosis[:50] + "..." if len(self.diagnosis) > 50 else self.diagnosis
    
    @property
    def treatment_summary(self):
        """Get a summary of the treatment (first 50 characters)"""
        return self.treatment[:50] + "..." if len(self.treatment) > 50 else self.treatment
    
    def decrypt_sensitive_data(self, user_role):
        """Decrypt sensitive data for display to authorized users"""
        try:
            # Only decrypt for board members and admins
            if user_role not in ['board_member', 'admin']:
                return None
            
            # Decrypt the data
            if self.encrypted_data:
                from app.encryption.encryption import decrypt_sensitive_data
                import json
                encrypted_dict = json.loads(self.encrypted_data)
                decrypted_data = {}
                
                for field, encrypted_value in encrypted_dict.items():
                    if encrypted_value:
                        decrypted_data[field] = decrypt_sensitive_data(encrypted_value)
                    else:
                        decrypted_data[field] = None
                
                return decrypted_data
            return None
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error decrypting medical record data: {e}")
            return None

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    action = db.Column(db.String(100), nullable=False, index=True)  # view, create, update, delete
    table_name = db.Column(db.String(50), nullable=False, index=True)
    record_id = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    ip_address = db.Column(db.String(45))  # IPv6 compatible
    
    user = db.relationship('User', backref=db.backref('audit_logs', lazy=True))
    
    def __repr__(self):
        return f'<AuditLog {self.action} on {self.table_name}:{self.record_id}>'

class AnomalyDetection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    action = db.Column(db.String(100), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    ip_address = db.Column(db.String(45))
    details = db.Column(db.Text)
    is_resolved = db.Column(db.Boolean, default=False, index=True)
    
    user = db.relationship('User', backref=db.backref('anomalies', lazy=True))
    
    def __repr__(self):
        return f'<AnomalyDetection {self.action} by {self.user_id}>'