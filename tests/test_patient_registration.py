import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, Column, String, Integer, Boolean, DateTime, Enum, Date
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
import enum
import uuid
from datetime import date, timedelta
from app.main import app
from app.database import get_db, Base
from app.models import Patient, Gender
from app.security import get_password_hash, create_patient_access_token, verify_token_enhanced
from app.schemas import PatientAddress, EmergencyContact, InsuranceInfo
import jwt
from app.config import settings

# Create test-specific model for SQLite compatibility
class TestPatient(Base):
    __tablename__ = "patients"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone_number = Column(String(20), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    date_of_birth = Column(Date, nullable=False)
    gender = Column(String(20), nullable=False)
    address = Column(String(500), nullable=False)  # JSON as string for SQLite
    emergency_contact = Column(String(500), nullable=True)
    medical_history = Column(String(500), nullable=True)
    insurance_info = Column(String(500), nullable=True)
    email_verified = Column(Boolean, default=False, nullable=False)
    phone_verified = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_patient_registration.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# Override the database dependency for testing
app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def valid_patient_data():
    return {
        "first_name": "Jane",
        "last_name": "Smith",
        "email": "jane.smith@email.com",
        "phone_number": "+1234567890",
        "password": "SecurePassword123!",
        "confirm_password": "SecurePassword123!",
        "date_of_birth": "1990-05-15",
        "gender": "female",
        "address": {
            "street": "456 Main Street",
            "city": "Boston",
            "state": "MA",
            "zip": "02101"
        },
        "emergency_contact": {
            "name": "John Smith",
            "phone": "+1234567891",
            "relationship": "spouse"
        },
        "insurance_info": {
            "provider": "Blue Cross",
            "policy_number": "BC123456789"
        }
    }

class TestPatientValidation:
    """Test patient data validation"""
    
    def test_valid_patient_data(self, valid_patient_data):
        """Test that valid patient data passes validation"""
        from app.schemas import PatientCreate
        patient = PatientCreate(**valid_patient_data)
        assert patient.first_name == "Jane"
        assert patient.email == "jane.smith@email.com"
        assert patient.gender == Gender.FEMALE
    
    def test_invalid_email_format(self, valid_patient_data):
        """Test email validation"""
        valid_patient_data["email"] = "invalid-email"
        from app.schemas import PatientCreate
        with pytest.raises(ValueError):
            PatientCreate(**valid_patient_data)
    
    def test_short_first_name(self, valid_patient_data):
        """Test first name minimum length"""
        valid_patient_data["first_name"] = "J"
        from app.schemas import PatientCreate
        with pytest.raises(ValueError):
            PatientCreate(**valid_patient_data)
    
    def test_long_first_name(self, valid_patient_data):
        """Test first name maximum length"""
        valid_patient_data["first_name"] = "A" * 51
        from app.schemas import PatientCreate
        with pytest.raises(ValueError):
            PatientCreate(**valid_patient_data)
    
    def test_weak_password(self, valid_patient_data):
        """Test password complexity requirements"""
        weak_passwords = [
            "short",  # Too short
            "nouppercase123!",  # No uppercase
            "NOLOWERCASE123!",  # No lowercase
            "NoNumbers!",  # No numbers
            "NoSpecial123"  # No special characters
        ]
        
        from app.schemas import PatientCreate
        for password in weak_passwords:
            valid_patient_data["password"] = password
            valid_patient_data["confirm_password"] = password
            with pytest.raises(ValueError):
                PatientCreate(**valid_patient_data)
    
    def test_password_mismatch(self, valid_patient_data):
        """Test password confirmation validation"""
        valid_patient_data["confirm_password"] = "DifferentPassword123!"
        from app.schemas import PatientCreate
        with pytest.raises(ValueError):
            PatientCreate(**valid_patient_data)
    
    def test_invalid_phone_number(self, valid_patient_data):
        """Test phone number validation"""
        invalid_phones = ["123", "1234567890123456", "abc123def"]
        from app.schemas import PatientCreate
        for phone in invalid_phones:
            valid_patient_data["phone_number"] = phone
            with pytest.raises(ValueError):
                PatientCreate(**valid_patient_data)
    
    def test_invalid_zip_code(self, valid_patient_data):
        """Test ZIP code validation"""
        valid_patient_data["address"]["zip"] = "invalid"
        from app.schemas import PatientCreate
        with pytest.raises(ValueError):
            PatientCreate(**valid_patient_data)
    
    def test_future_date_of_birth(self, valid_patient_data):
        """Test date of birth must be in past"""
        tomorrow = date.today() + timedelta(days=1)
        valid_patient_data["date_of_birth"] = tomorrow.isoformat()
        from app.schemas import PatientCreate
        with pytest.raises(ValueError):
            PatientCreate(**valid_patient_data)
    
    def test_underage_patient(self, valid_patient_data):
        """Test COPPA compliance (must be at least 13 years old)"""
        # Set date of birth to make patient 12 years old
        twelve_years_ago = date.today() - timedelta(days=12*365)
        valid_patient_data["date_of_birth"] = twelve_years_ago.isoformat()
        from app.schemas import PatientCreate
        with pytest.raises(ValueError):
            PatientCreate(**valid_patient_data)
    
    def test_valid_age_patient(self, valid_patient_data):
        """Test valid age (13 years old)"""
        # Set date of birth to make patient exactly 13 years old
        thirteen_years_ago = date.today() - timedelta(days=13*365)
        valid_patient_data["date_of_birth"] = thirteen_years_ago.isoformat()
        from app.schemas import PatientCreate
        patient = PatientCreate(**valid_patient_data)
        assert patient.date_of_birth == thirteen_years_ago
    
    def test_invalid_gender(self, valid_patient_data):
        """Test gender enum validation"""
        valid_patient_data["gender"] = "invalid_gender"
        from app.schemas import PatientCreate
        with pytest.raises(ValueError):
            PatientCreate(**valid_patient_data)
    
    def test_valid_genders(self, valid_patient_data):
        """Test all valid gender values"""
        valid_genders = ["male", "female", "other", "prefer_not_to_say"]
        from app.schemas import PatientCreate
        for gender in valid_genders:
            valid_patient_data["gender"] = gender
            patient = PatientCreate(**valid_patient_data)
            assert patient.gender == Gender(gender)

class TestPatientRegistration:
    """Test patient registration endpoints"""
    
    def test_successful_registration(self, valid_patient_data):
        """Test successful patient registration"""
        response = client.post("/api/v1/patient/register", json=valid_patient_data)
        assert response.status_code == 201
        
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Patient registered successfully. Verification email sent."
        assert "data" in data
        
        # Check response data structure
        response_data = data["data"]
        assert "patient_id" in response_data
        assert response_data["email"] == valid_patient_data["email"]
        assert response_data["phone_number"] == valid_patient_data["phone_number"]
        assert response_data["email_verified"] is False
        assert response_data["phone_verified"] is False
        
        # Verify sensitive data is not returned
        assert "password" not in response_data
        assert "password_hash" not in response_data
        assert "date_of_birth" not in response_data
        assert "medical_history" not in response_data
        assert "insurance_info" not in response_data
    
    def test_duplicate_email_registration(self, valid_patient_data):
        """Test registration with duplicate email"""
        # First registration
        response = client.post("/api/v1/patient/register", json=valid_patient_data)
        assert response.status_code == 201
        
        # Second registration with same email
        valid_patient_data["phone_number"] = "+1987654321"
        response = client.post("/api/v1/patient/register", json=valid_patient_data)
        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]
    
    def test_duplicate_phone_registration(self, valid_patient_data):
        """Test registration with duplicate phone number"""
        # First registration
        response = client.post("/api/v1/patient/register", json=valid_patient_data)
        assert response.status_code == 201
        
        # Second registration with same phone
        valid_patient_data["email"] = "different@email.com"
        response = client.post("/api/v1/patient/register", json=valid_patient_data)
        assert response.status_code == 400
        assert "Phone number already registered" in response.json()["detail"]
    
    def test_validation_error_response(self, valid_patient_data):
        """Test validation error response format"""
        valid_patient_data["email"] = "invalid-email"
        response = client.post("/api/v1/patient/register", json=valid_patient_data)
        assert response.status_code == 422
        
        data = response.json()
        assert data["success"] is False
        assert data["message"] == "Validation failed"
        assert "errors" in data
        assert "email" in data["errors"]
    
    def test_missing_required_fields(self, valid_patient_data):
        """Test missing required fields"""
        # Remove required field
        del valid_patient_data["first_name"]
        response = client.post("/api/v1/patient/register", json=valid_patient_data)
        assert response.status_code == 422
        
        data = response.json()
        assert "errors" in data
        assert "first_name" in data["errors"]

class TestPatientLogin:
    """Test patient login functionality"""
    
    def test_successful_login(self, valid_patient_data):
        """Test successful patient login"""
        # Register patient first
        response = client.post("/api/v1/patient/register", json=valid_patient_data)
        assert response.status_code == 201
        
        # Login
        login_data = {
            "email": valid_patient_data["email"],
            "password": valid_patient_data["password"]
        }
        response = client.post("/api/v1/patient/login", json=login_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Login successful"
        
        # Check token data
        token_data = data["data"]
        assert "access_token" in token_data
        assert token_data["expires_in"] == 1800  # 30 minutes
        assert token_data["token_type"] == "Bearer"
        
        # Check patient data
        patient_data = token_data["patient"]
        assert patient_data["email"] == valid_patient_data["email"]
        assert patient_data["first_name"] == valid_patient_data["first_name"]
        assert patient_data["last_name"] == valid_patient_data["last_name"]
        assert "password" not in patient_data  # Password should not be returned
    
    def test_invalid_credentials(self, valid_patient_data):
        """Test login with invalid credentials"""
        # Register patient first
        response = client.post("/api/v1/patient/register", json=valid_patient_data)
        assert response.status_code == 201
        
        # Login with wrong password
        login_data = {
            "email": valid_patient_data["email"],
            "password": "wrongpassword"
        }
        response = client.post("/api/v1/patient/login", json=login_data)
        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]
    
    def test_nonexistent_user_login(self):
        """Test login with non-existent user"""
        login_data = {
            "email": "nonexistent@email.com",
            "password": "SecurePassword123!"
        }
        response = client.post("/api/v1/patient/login", json=login_data)
        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]

class TestPatientJWTToken:
    """Test JWT token generation and validation for patients"""
    
    def test_jwt_token_payload(self, valid_patient_data):
        """Test that JWT token contains required payload fields"""
        # Register and login patient
        response = client.post("/api/v1/patient/register", json=valid_patient_data)
        assert response.status_code == 201
        
        login_data = {
            "email": valid_patient_data["email"],
            "password": valid_patient_data["password"]
        }
        response = client.post("/api/v1/patient/login", json=login_data)
        assert response.status_code == 200
        
        token = response.json()["data"]["access_token"]
        
        # Decode and verify token payload
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        
        # Check required fields
        assert "sub" in payload  # email
        assert "patient_id" in payload
        assert "email" in payload
        assert "role" in payload
        assert "exp" in payload  # expiration
        
        # Check values
        assert payload["email"] == valid_patient_data["email"]
        assert payload["role"] == "patient"
    
    def test_jwt_token_expiration(self, valid_patient_data):
        """Test that JWT token expires after 1 hour"""
        # Register and login patient
        response = client.post("/api/v1/patient/register", json=valid_patient_data)
        assert response.status_code == 201
        
        login_data = {
            "email": valid_patient_data["email"],
            "password": valid_patient_data["password"]
        }
        response = client.post("/api/v1/patient/login", json=login_data)
        assert response.status_code == 200
        
        token = response.json()["data"]["access_token"]
        
        # Decode token to check expiration
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        import time
        current_time = int(time.time())
        expiration_time = payload["exp"]
        
        # Token should expire in approximately 30 minutes (1800 seconds)
        time_until_expiry = expiration_time - current_time
        assert 1790 <= time_until_expiry <= 1810  # Allow 10 seconds tolerance

class TestHIPAACompliance:
    """Test HIPAA compliance features"""
    
    def test_sensitive_data_not_logged(self, valid_patient_data, caplog):
        """Test that sensitive data is not logged"""
        with caplog.at_level("INFO"):
            response = client.post("/api/v1/patient/register", json=valid_patient_data)
            assert response.status_code == 201
        
        # Check that sensitive data is not in logs
        log_text = caplog.text
        assert valid_patient_data["password"] not in log_text
        assert valid_patient_data["date_of_birth"] not in log_text
        assert "medical_history" not in log_text.lower()
        assert "insurance_info" not in log_text.lower()
    
    def test_sensitive_data_not_returned(self, valid_patient_data):
        """Test that sensitive data is not returned in responses"""
        response = client.post("/api/v1/patient/register", json=valid_patient_data)
        assert response.status_code == 201
        
        data = response.json()
        response_data = data["data"]
        
        # Check that sensitive fields are not present
        sensitive_fields = ["password", "password_hash", "date_of_birth", "medical_history", "insurance_info"]
        for field in sensitive_fields:
            assert field not in response_data
    
    def test_secure_error_messages(self, valid_patient_data):
        """Test that error messages don't leak sensitive information"""
        # Test with invalid email
        valid_patient_data["email"] = "invalid-email"
        response = client.post("/api/v1/patient/register", json=valid_patient_data)
        assert response.status_code == 422
        
        # Error should not contain sensitive data
        error_text = str(response.json())
        assert valid_patient_data["password"] not in error_text
        assert valid_patient_data["phone_number"] not in error_text

class TestAddressValidation:
    """Test address validation"""
    
    def test_valid_address(self, valid_patient_data):
        """Test valid address format"""
        response = client.post("/api/v1/patient/register", json=valid_patient_data)
        assert response.status_code == 201
    
    def test_invalid_zip_format(self, valid_patient_data):
        """Test invalid ZIP code format"""
        valid_patient_data["address"]["zip"] = "1234"  # Too short
        response = client.post("/api/v1/patient/register", json=valid_patient_data)
        assert response.status_code == 422
        
        data = response.json()
        assert "address" in data["errors"] or "zip" in data["errors"]
    
    def test_long_street_address(self, valid_patient_data):
        """Test street address length limit"""
        valid_patient_data["address"]["street"] = "A" * 201  # Too long
        response = client.post("/api/v1/patient/register", json=valid_patient_data)
        assert response.status_code == 422

class TestEmergencyContactValidation:
    """Test emergency contact validation"""
    
    def test_valid_emergency_contact(self, valid_patient_data):
        """Test valid emergency contact"""
        response = client.post("/api/v1/patient/register", json=valid_patient_data)
        assert response.status_code == 201
    
    def test_invalid_emergency_phone(self, valid_patient_data):
        """Test invalid emergency contact phone"""
        valid_patient_data["emergency_contact"]["phone"] = "123"  # Too short
        response = client.post("/api/v1/patient/register", json=valid_patient_data)
        assert response.status_code == 422
    
    def test_long_emergency_contact_name(self, valid_patient_data):
        """Test emergency contact name length limit"""
        valid_patient_data["emergency_contact"]["name"] = "A" * 101  # Too long
        response = client.post("/api/v1/patient/register", json=valid_patient_data)
        assert response.status_code == 422 