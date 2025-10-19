"""
Predictive Analytics for Medical Records
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
import json
from datetime import datetime, timedelta
from collections import defaultdict

class MedicalAnalytics:
    def __init__(self):
        self.model = RandomForestRegressor(n_estimators=50, random_state=42)
        self.is_trained = False
        self.feature_names = []
    
    def prepare_data_for_training(self, medical_records):
        """Prepare medical records data for training predictive models"""
        data = []
        for record in medical_records:
            # Extract features from medical records
            features = {
                'record_id': record.id,
                'patient_id': record.patient_id,
                'doctor_id': record.doctor_id,
                'day_of_week': record.created_at.weekday() if record.created_at else 0,
                'month': record.created_at.month if record.created_at else 1,
                'hour': record.created_at.hour if record.created_at else 12,
                'diagnosis_length': len(record.diagnosis) if record.diagnosis else 0,
                'treatment_length': len(record.treatment) if record.treatment else 0,
                'has_prescription': 1 if record.prescription else 0,
                'days_since_created': (datetime.utcnow() - record.created_at).days if record.created_at else 0
            }
            data.append(features)
        
        return pd.DataFrame(data)
    
    def train_patient_risk_model(self, medical_records):
        """Train a model to predict patient risk levels"""
        if len(medical_records) < 10:
            return False
        
        # Prepare data
        df = self.prepare_data_for_training(medical_records)
        
        # Create target variable (simplified risk score based on record complexity)
        df['risk_score'] = (
            df['diagnosis_length'] * 0.3 + 
            df['treatment_length'] * 0.3 + 
            df['has_prescription'] * 10 +
            df['days_since_created'] * 0.1
        )
        
        # Select features for training
        feature_columns = [
            'day_of_week', 'month', 'hour', 
            'diagnosis_length', 'treatment_length', 
            'has_prescription', 'days_since_created'
        ]
        
        self.feature_names = feature_columns
        X = df[feature_columns]
        y = df['risk_score']
        
        # Train the model
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        self.model.fit(X_train, y_train)
        self.is_trained = True
        
        # Calculate model performance
        y_pred = self.model.predict(X_test)
        mse = mean_squared_error(y_test, y_pred)
        
        return {
            'trained': True,
            'mse': mse,
            'samples': len(medical_records)
        }
    
    def predict_patient_risk(self, medical_record):
        """Predict risk score for a medical record"""
        if not self.is_trained:
            return {'risk_score': 0, 'confidence': 0}
        
        # Prepare features for prediction
        features = np.array([[
            medical_record.created_at.weekday() if medical_record.created_at else 0,
            medical_record.created_at.month if medical_record.created_at else 1,
            medical_record.created_at.hour if medical_record.created_at else 12,
            len(medical_record.diagnosis) if medical_record.diagnosis else 0,
            len(medical_record.treatment) if medical_record.treatment else 0,
            1 if medical_record.prescription else 0,
            (datetime.utcnow() - medical_record.created_at).days if medical_record.created_at else 0
        ]])
        
        # Predict risk score
        risk_score = self.model.predict(features)[0]
        
        # Normalize risk score to 0-100 scale
        normalized_risk = min(100, max(0, risk_score))
        
        return {
            'risk_score': round(normalized_risk, 2),
            'confidence': 0.85  # Simplified confidence measure
        }
    
    def analyze_trends(self, medical_records, days=30):
        """Analyze medical record trends over time"""
        if not medical_records:
            return {}
        
        # Filter records from the last N days
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        recent_records = [r for r in medical_records if r.created_at and r.created_at >= cutoff_date]
        
        if not recent_records:
            return {}
        
        # Group by date
        daily_counts = defaultdict(int)
        for record in recent_records:
            date_key = record.created_at.date()
            daily_counts[date_key] += 1
        
        # Calculate trends
        dates = sorted(daily_counts.keys())
        counts = [daily_counts[date] for date in dates]
        
        if len(counts) < 2:
            trend = "stable"
        else:
            # Simple trend calculation
            if counts[-1] > counts[0]:
                trend = "increasing"
            elif counts[-1] < counts[0]:
                trend = "decreasing"
            else:
                trend = "stable"
        
        return {
            'total_records': len(recent_records),
            'average_daily': round(sum(counts) / len(counts), 2),
            'trend': trend,
            'peak_day': max(daily_counts, key=daily_counts.get).isoformat() if daily_counts else None
        }

# Global analytics instance
medical_analytics = MedicalAnalytics()

def initialize_analytics(medical_records):
    """Initialize and train the analytics models"""
    global medical_analytics
    try:
        result = medical_analytics.train_patient_risk_model(medical_records)
        return result
    except Exception as e:
        print(f"Error training analytics models: {e}")
        return {'trained': False, 'error': str(e)}

def predict_risk_for_record(medical_record):
    """Predict risk score for a medical record"""
    global medical_analytics
    try:
        return medical_analytics.predict_patient_risk(medical_record)
    except Exception as e:
        print(f"Error predicting risk: {e}")
        return {'risk_score': 0, 'confidence': 0}

def analyze_medical_trends(medical_records, days=30):
    """Analyze trends in medical records"""
    global medical_analytics
    try:
        return medical_analytics.analyze_trends(medical_records, days)
    except Exception as e:
        print(f"Error analyzing trends: {e}")
        return {}