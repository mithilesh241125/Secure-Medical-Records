import random
import json
from datetime import datetime, timedelta
from faker import Faker

# Initialize Faker
fake = Faker()

def generate_patient_data(num_patients=100):
    """Generate synthetic patient data"""
    patients = []
    
    genders = ['Male', 'Female', 'Other']
    
    for i in range(num_patients):
        patient = {
            "name": fake.name(),
            "dob": fake.date_of_birth(minimum_age=1, maximum_age=100).strftime('%Y-%m-%d'),
            "gender": random.choice(genders),
            "medical_record_number": f"MRN{random.randint(100000, 999999)}",
            "created_at": fake.date_time_between(start_date='-5y', end_date='now').isoformat()
        }
        patients.append(patient)
    
    return patients

def generate_medical_records(patients, num_records_per_patient=3):
    """Generate synthetic medical records for patients"""
    records = []
    
    diagnoses = [
        "Hypertension", "Diabetes Type 2", "Asthma", "Depression", 
        "Anxiety", "Migraine", "Arthritis", "Allergies", "Bronchitis",
        "Gastroenteritis", "Urinary Tract Infection", "Conjunctivitis",
        "Sinusitis", "Back Pain", "Headache", "Fatigue", "Cough",
        "Fever", "Nausea", "Dizziness"
    ]
    
    treatments = [
        "Prescribed medication", "Lifestyle changes recommended", 
        "Physical therapy", "Follow-up appointment scheduled",
        "Referral to specialist", "Surgery recommended", 
        "Monitoring required", "Dietary changes", "Exercise program",
        "Stress management techniques", "Pain management", 
        "Respiratory therapy", "Counseling sessions"
    ]
    
    prescriptions = [
        "Lisinopril 10mg daily", "Metformin 500mg twice daily",
        "Albuterol inhaler as needed", "Sertraline 50mg daily",
        "Loratadine 10mg daily", "Ibuprofen 400mg as needed",
        "Acetaminophen 500mg as needed", "Atorvastatin 20mg daily",
        "Levothyroxine 75mcg daily", "Amlodipine 5mg daily",
        "Omeprazole 20mg daily", "Metoprolol 25mg twice daily",
        "None", "Aspirin 81mg daily", "Multivitamin daily"
    ]
    
    for patient in patients:
        for _ in range(random.randint(1, num_records_per_patient)):
            record = {
                "patient_mrn": patient["medical_record_number"],
                "doctor_name": fake.name(),
                "diagnosis": random.choice(diagnoses),
                "treatment": random.choice(treatments),
                "prescription": random.choice(prescriptions),
                "created_at": fake.date_time_between(start_date='-2y', end_date='now').isoformat()
            }
            records.append(record)
    
    return records

def save_data_to_json(data, filename):
    """Save data to a JSON file"""
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

if __name__ == "__main__":
    print("Generating synthetic patient data...")
    
    # Generate patients
    patients = generate_patient_data(50)
    save_data_to_json(patients, 'synthetic_patients.json')
    print(f"Generated {len(patients)} patients")
    
    # Generate medical records
    records = generate_medical_records(patients, 5)
    save_data_to_json(records, 'synthetic_medical_records.json')
    print(f"Generated {len(records)} medical records")
    
    print("Data generation complete!")
    print("Files created:")
    print("  - synthetic_patients.json")
    print("  - synthetic_medical_records.json")