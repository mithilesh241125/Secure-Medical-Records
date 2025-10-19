#!/usr/bin/env python3
"""
Secure Medical Records System - Startup Script
Single command to initialize database and start the application
"""

import sys
import os
import argparse
import subprocess

def initialize_database():
    """Initialize the database with sample data"""
    print("Initializing database...")
    try:
        from app import app
        from app.models.models import db, User, Patient, MedicalRecord
        from app.utils.security import hash_password
        from datetime import date
        
        with app.app_context():
            # Create all tables
            db.create_all()
            
            # Check if admin user already exists
            admin = User.query.filter_by(username='admin').first()
            if not admin:
                print("Creating default users...")
                # Create admin user
                admin = User(
                    username='admin',
                    email='admin@hospital.com',
                    password_hash=hash_password('admin123'),
                    role='admin'
                )
                db.session.add(admin)
                
                # Create doctor user
                doctor = User(
                    username='doctor',
                    email='doctor@hospital.com',
                    password_hash=hash_password('doctor123'),
                    role='doctor'
                )
                db.session.add(doctor)
                
                # Create nurse user
                nurse = User(
                    username='nurse',
                    email='nurse@hospital.com',
                    password_hash=hash_password('nurse123'),
                    role='nurse'
                )
                db.session.add(nurse)
                
                # Create board member user
                board_member = User(
                    username='board',
                    email='board@hospital.com',
                    password_hash=hash_password('board123'),
                    role='board_member'
                )
                db.session.add(board_member)
                
                # Create sample patients
                patient1 = Patient(
                    name='John Doe',
                    dob=date(1980, 5, 15),
                    gender='Male',
                    medical_record_number='MRN000001'
                )
                db.session.add(patient1)
                
                patient2 = Patient(
                    name='Jane Smith',
                    dob=date(1990, 12, 3),
                    gender='Female',
                    medical_record_number='MRN000002'
                )
                db.session.add(patient2)
                
                # Create sample medical records
                record1 = MedicalRecord(
                    patient_id=1,
                    doctor_id=2,
                    diagnosis='Hypertension',
                    treatment='Prescribed medication and lifestyle changes',
                    prescription='Lisinopril 10mg daily'
                )
                record1.record_hash = record1.calculate_hash()
                db.session.add(record1)
                
                record2 = MedicalRecord(
                    patient_id=2,
                    doctor_id=2,
                    diagnosis='Type 2 Diabetes',
                    treatment='Dietary changes and medication',
                    prescription='Metformin 500mg twice daily'
                )
                record2.record_hash = record2.calculate_hash()
                db.session.add(record2)
                
                db.session.commit()
                print("Database initialized with sample data")
                print("\nDefault users created:")
                print("  Admin: username='admin', password='admin123'")
                print("  Doctor: username='doctor', password='doctor123'")
                print("  Nurse: username='nurse', password='nurse123'")
                print("  Board Member: username='board', password='board123'")
            else:
                print("Database already initialized")
                
    except Exception as e:
        print(f"Error initializing database: {e}")
        sys.exit(1)

def start_application():
    """Start the Flask application"""
    print("Starting Secure Medical Records application...")
    print("Access the application at: http://127.0.0.1:5000")
    print("Press CTRL+C to stop the application")
    
    try:
        # Import and run the app
        from app import app
        app.run(debug=True, host='127.0.0.1', port=5000)
    except KeyboardInterrupt:
        print("\nApplication stopped")
    except Exception as e:
        print(f"Error starting application: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='Secure Medical Records System')
    parser.add_argument('--init', action='store_true', help='Initialize database with sample data')
    parser.add_argument('--start', action='store_true', help='Start the application')
    
    args = parser.parse_args()
    
    # If no arguments provided, do both
    if not args.init and not args.start:
        print("Secure Medical Records System")
        print("=" * 40)
        initialize_database()
        print("\n" + "=" * 40)
        start_application()
    else:
        if args.init:
            initialize_database()
        if args.start:
            start_application()

if __name__ == '__main__':
    main()