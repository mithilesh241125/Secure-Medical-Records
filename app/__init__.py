import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta

# Load environment variables from .env file
load_dotenv()

# Initialize SQLAlchemy
db = SQLAlchemy()

# Initialize CSRF protection
csrf = CSRFProtect()

def format_datetime_utc(value, format='%Y-%m-%d %H:%M'):
    """Format a UTC datetime object to local timezone"""
    if value is None:
        return ""
    # Assume the value is in UTC
    if isinstance(value, datetime):
        # Make sure the datetime is timezone-aware
        if value.tzinfo is None:
            # Assume it's UTC
            utc_value = value.replace(tzinfo=timezone.utc)
        else:
            utc_value = value
        
        # Convert to IST (UTC+5:30)
        ist_offset = timedelta(hours=5, minutes=30)
        local_value = utc_value + ist_offset
        
        return local_value.strftime(format)
    return value

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
    # Use absolute path to ensure database is created in the current directory
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'medical_records.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Add template filter
    app.jinja_env.filters['datetime_utc'] = format_datetime_utc
    
    # Initialize database
    db.init_app(app)
    
    # Initialize CSRF protection
    csrf.init_app(app)
    
    # Import and register blueprints
    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    
    # Create tables
    with app.app_context():
        db.create_all()
    
    return app

# Create the app and database tables when this module is imported
app = create_app()