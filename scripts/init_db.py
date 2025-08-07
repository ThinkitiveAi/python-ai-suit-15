#!/usr/bin/env python3
"""
Database initialization script for Healthcare Provider Registration API
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from app.database import Base
from app.config import settings
from app.models import Provider
from app.security import get_password_hash
from app.schemas import ClinicAddress

def init_database():
    """Initialize the database with tables"""
    print("Creating database tables...")
    
    # Create engine
    engine = create_engine(settings.database_url)
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    print("✅ Database tables created successfully!")

def create_sample_data():
    """Create sample provider data for testing"""
    from sqlalchemy.orm import sessionmaker
    
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Check if sample data already exists
        existing_provider = db.query(Provider).filter(Provider.email == "admin@healthcare.com").first()
        if existing_provider:
            print("Sample data already exists, skipping...")
            return
        
        # Create sample provider
        sample_provider = Provider(
            first_name="Admin",
            last_name="User",
            email="admin@healthcare.com",
            phone_number="+1234567890",
            password_hash=get_password_hash("AdminPass123!"),
            specialization="General Medicine",
            license_number="ADMIN001",
            years_of_experience=20,
            clinic_address=ClinicAddress(
                street="123 Healthcare Blvd",
                city="Medical City",
                state="MC",
                zip="12345"
            ).dict(),
            verification_status="verified"
        )
        
        db.add(sample_provider)
        db.commit()
        
        print("✅ Sample data created successfully!")
        print("Admin credentials:")
        print("  Email: admin@healthcare.com")
        print("  Password: AdminPass123!")
        
    except Exception as e:
        print(f"❌ Error creating sample data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("🏥 Healthcare Provider Registration API - Database Initialization")
    print("=" * 60)
    
    try:
        init_database()
        create_sample_data()
        print("\n🎉 Database initialization completed successfully!")
        print("\nNext steps:")
        print("1. Start the server: python run.py")
        print("2. Visit: http://localhost:8000/docs")
        print("3. Test the API with the sample admin account")
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        sys.exit(1) 