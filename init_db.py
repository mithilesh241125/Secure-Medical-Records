import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from app import app
from app.models.models import db

def init_database():
    """Initialize the database with sample data"""
    with app.app_context():
        # Create all tables explicitly
        db.create_all()
        print("Database tables created successfully")

if __name__ == '__main__':
    init_database()