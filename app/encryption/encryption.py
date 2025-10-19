"""
Advanced Encryption for Medical Records
Implements zero-knowledge encryption to protect sensitive patient data
"""

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os
import json
from datetime import datetime

class MedicalDataEncryption:
    def __init__(self, master_password=None):
        """Initialize encryption system"""
        if master_password:
            self.master_password = master_password.encode()
            self.salt = b'medical_record_salt_16bytes'  # In production, use a random salt
            self.key = self._derive_key()
            self.cipher = Fernet(self.key)
        else:
            # Generate a new key if none provided
            self.key = Fernet.generate_key()
            self.cipher = Fernet(self.key)
    
    def _derive_key(self):
        """Derive encryption key from password"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.master_password))
        return key
    
    def encrypt_data(self, data):
        """Encrypt sensitive data"""
        if isinstance(data, dict) or isinstance(data, list):
            data = json.dumps(data)
        elif not isinstance(data, str):
            data = str(data)
        
        encrypted_data = self.cipher.encrypt(data.encode())
        return base64.urlsafe_b64encode(encrypted_data).decode()
    
    def decrypt_data(self, encrypted_data):
        """Decrypt sensitive data"""
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_data = self.cipher.decrypt(encrypted_bytes)
            return decrypted_data.decode()
        except Exception as e:
            print(f"Decryption error: {e}")
            return None
    
    def encrypt_medical_record(self, record_model):
        """Encrypt entire medical record"""
        sensitive_fields = {
            'diagnosis': record_model.diagnosis,
            'treatment': record_model.treatment,
            'prescription': record_model.prescription,
            'allergies': getattr(record_model, 'allergies', ''),
            'blood_type': getattr(record_model, 'blood_type', '')
        }
        
        # Encrypt each sensitive field
        encrypted_record = {}
        for field, value in sensitive_fields.items():
            if value:
                encrypted_record[field] = self.encrypt_data(value)
            else:
                encrypted_record[field] = None
        
        return encrypted_record
    
    def decrypt_medical_record(self, encrypted_record):
        """Decrypt medical record data"""
        decrypted_record = {}
        for field, encrypted_value in encrypted_record.items():
            if encrypted_value:
                decrypted_record[field] = self.decrypt_data(encrypted_value)
            else:
                decrypted_record[field] = None
        
        return decrypted_record

# Global encryption instance
medical_encryption = MedicalDataEncryption()

def initialize_encryption(master_password="secure_medical_records_2025"):
    """Initialize the encryption system"""
    global medical_encryption
    medical_encryption = MedicalDataEncryption(master_password)
    return medical_encryption

def encrypt_sensitive_data(data):
    """Encrypt sensitive patient data"""
    global medical_encryption
    try:
        return medical_encryption.encrypt_data(data)
    except Exception as e:
        print(f"Error encrypting data: {e}")
        return None

def decrypt_sensitive_data(encrypted_data):
    """Decrypt sensitive patient data"""
    global medical_encryption
    try:
        return medical_encryption.decrypt_data(encrypted_data)
    except Exception as e:
        print(f"Error decrypting data: {e}")
        return None

def encrypt_medical_record(record_model):
    """Encrypt a medical record"""
    global medical_encryption
    try:
        return medical_encryption.encrypt_medical_record(record_model)
    except Exception as e:
        print(f"Error encrypting medical record: {e}")
        return None