"""
FHIR Client for HL7 FHIR Integration
"""

from fhirpy import SyncFHIRClient
from fhirpy.lib import BaseResource
import json
from datetime import datetime

class FHIRIntegration:
    def __init__(self, server_url="http://localhost:8080/fhir"):
        """Initialize FHIR client"""
        self.client = SyncFHIRClient(url=server_url)
    
    def patient_to_fhir(self, patient_model):
        """Convert internal patient model to FHIR Patient resource"""
        patient = self.client.resource(
            'Patient',
            identifier=[{
                'system': 'http://hospital.org/patient-identifier',
                'value': patient_model.medical_record_number
            }],
            active=True,
            name=[{
                'use': 'official',
                'family': patient_model.name.split()[-1] if ' ' in patient_model.name else patient_model.name,
                'given': patient_model.name.split()[:-1] if ' ' in patient_model.name else [patient_model.name]
            }],
            gender=patient_model.gender.lower(),
            birthDate=patient_model.dob.isoformat(),
            telecom=[{
                'system': 'phone',
                'value': patient_model.phone,
                'use': 'home'
            }, {
                'system': 'email',
                'value': patient_model.email,
                'use': 'home'
            }] if patient_model.phone or patient_model.email else [],
            address=[{
                'use': 'home',
                'text': patient_model.address
            }] if patient_model.address else [],
            contact=[{
                'relationship': [{
                    'coding': [{
                        'system': 'http://terminology.hl7.org/CodeSystem/v2-0131',
                        'code': 'C'
                    }]
                }],
                'name': {
                    'family': patient_model.emergency_contact_name.split()[-1] if patient_model.emergency_contact_name and ' ' in patient_model.emergency_contact_name else patient_model.emergency_contact_name,
                    'given': patient_model.emergency_contact_name.split()[:-1] if patient_model.emergency_contact_name and ' ' in patient_model.emergency_contact_name else [patient_model.emergency_contact_name]
                },
                'telecom': [{
                    'system': 'phone',
                    'value': patient_model.emergency_contact_phone
                }]
            }] if patient_model.emergency_contact_name else []
        )
        
        return patient
    
    def medical_record_to_fhir(self, record_model, patient_fhir_id):
        """Convert internal medical record to FHIR ClinicalImpression resource"""
        # Create Observation for diagnosis
        observation = self.client.resource(
            'Observation',
            status='final',
            code={
                'coding': [{
                    'system': 'http://hospital.org/diagnosis',
                    'code': 'diagnosis',
                    'display': 'Clinical Diagnosis'
                }],
                'text': record_model.diagnosis
            },
            subject={
                'reference': f'Patient/{patient_fhir_id}'
            },
            effectiveDateTime=datetime.utcnow().isoformat(),
            valueString=record_model.diagnosis
        )
        
        # Create Procedure for treatment
        procedure = self.client.resource(
            'Procedure',
            status='completed',
            code={
                'coding': [{
                    'system': 'http://hospital.org/treatment',
                    'code': 'treatment',
                    'display': 'Medical Treatment'
                }],
                'text': record_model.treatment
            },
            subject={
                'reference': f'Patient/{patient_fhir_id}'
            },
            performedDateTime=datetime.utcnow().isoformat(),
            note=[{
                'text': record_model.treatment
            }]
        )
        
        # Create MedicationRequest for prescription
        if record_model.prescription:
            medication = self.client.resource(
                'MedicationRequest',
                status='active',
                intent='order',
                medicationCodeableConcept={
                    'coding': [{
                        'system': 'http://hospital.org/prescription',
                        'code': 'prescription',
                        'display': 'Prescribed Medication'
                    }],
                    'text': record_model.prescription
                },
                subject={
                    'reference': f'Patient/{patient_fhir_id}'
                },
                authoredOn=datetime.utcnow().isoformat(),
                note=[{
                    'text': record_model.prescription
                }]
            )
            return observation, procedure, medication
        
        return observation, procedure, None
    
    def save_patient(self, patient_model):
        """Save patient to FHIR server"""
        try:
            fhir_patient = self.patient_to_fhir(patient_model)
            fhir_patient.save()
            return fhir_patient
        except Exception as e:
            print(f"Error saving patient to FHIR: {e}")
            return None
    
    def save_medical_record(self, record_model, patient_fhir_id):
        """Save medical record to FHIR server"""
        try:
            observation, procedure, medication = self.medical_record_to_fhir(record_model, patient_fhir_id)
            
            # Save resources
            observation.save()
            procedure.save()
            
            if medication:
                medication.save()
                return observation, procedure, medication
            
            return observation, procedure, None
        except Exception as e:
            print(f"Error saving medical record to FHIR: {e}")
            return None, None, None

# Global FHIR client instance
fhir_client = FHIRIntegration()

def initialize_fhir_client(server_url="http://localhost:8080/fhir"):
    """Initialize the FHIR client"""
    global fhir_client
    fhir_client = FHIRIntegration(server_url)
    return fhir_client

def export_patient_to_fhir(patient_model):
    """Export patient data to FHIR format"""
    global fhir_client
    try:
        return fhir_client.save_patient(patient_model)
    except Exception as e:
        print(f"Error exporting patient to FHIR: {e}")
        return None

def export_medical_record_to_fhir(record_model, patient_fhir_id):
    """Export medical record to FHIR format"""
    global fhir_client
    try:
        return fhir_client.save_medical_record(record_model, patient_fhir_id)
    except Exception as e:
        print(f"Error exporting medical record to FHIR: {e}")
        return None, None, None