import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import get_db, Base
from app.models import Provider
from app.schemas import ProviderCreate, ClinicAddress
from app.security import get_password_hash, verify_password
import re

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def valid_provider_data():
    return {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@example.com",
        "phone_number": "+1234567890",
        "password": "SecurePass123!",
        "specialization": "Cardiology",
        "license_number": "MD123456",
        "years_of_experience": 10,
        "clinic_address": {
            "street": "123 Medical Center Dr",
            "city": "New York",
            "state": "NY",
            "zip": "10001"
        }
    }

class TestProviderValidation:
    """Test provider data validation"""
    
    def test_valid_provider_data(self, valid_provider_data):
        """Test that valid provider data passes validation"""
        provider = ProviderCreate(**valid_provider_data)
        assert provider.first_name == "John"
        assert provider.email == "john.doe@example.com"
    
    def test_invalid_email_format(self, valid_provider_data):
        """Test email validation"""
        valid_provider_data["email"] = "invalid-email"
        with pytest.raises(ValueError):
            ProviderCreate(**valid_provider_data)
    
    def test_short_first_name(self, valid_provider_data):
        """Test first name minimum length"""
        valid_provider_data["first_name"] = "J"
        with pytest.raises(ValueError):
            ProviderCreate(**valid_provider_data)
    
    def test_long_first_name(self, valid_provider_data):
        """Test first name maximum length"""
        valid_provider_data["first_name"] = "A" * 51
        with pytest.raises(ValueError):
            ProviderCreate(**valid_provider_data)
    
    def test_weak_password(self, valid_provider_data):
        """Test password complexity requirements"""
        weak_passwords = [
            "short",  # Too short
            "nouppercase123!",  # No uppercase
            "NOLOWERCASE123!",  # No lowercase
            "NoNumbers!",  # No numbers
            "NoSpecial123"  # No special characters
        ]
        
        for password in weak_passwords:
            valid_provider_data["password"] = password
            with pytest.raises(ValueError):
                ProviderCreate(**valid_provider_data)
    
    def test_invalid_phone_number(self, valid_provider_data):
        """Test phone number validation"""
        invalid_phones = ["123", "1234567890123456", "abc123def"]
        for phone in invalid_phones:
            valid_provider_data["phone_number"] = phone
            with pytest.raises(ValueError):
                ProviderCreate(**valid_provider_data)
    
    def test_invalid_license_number(self, valid_provider_data):
        """Test license number validation"""
        valid_provider_data["license_number"] = "MD-123-456"
        with pytest.raises(ValueError):
            ProviderCreate(**valid_provider_data)
    
    def test_invalid_zip_code(self, valid_provider_data):
        """Test ZIP code validation"""
        valid_provider_data["clinic_address"]["zip"] = "invalid"
        with pytest.raises(ValueError):
            ProviderCreate(**valid_provider_data)
    
    def test_years_experience_range(self, valid_provider_data):
        """Test years of experience range validation"""
        # Test negative value
        valid_provider_data["years_of_experience"] = -1
        with pytest.raises(ValueError):
            ProviderCreate(**valid_provider_data)
        
        # Test value over 50
        valid_provider_data["years_of_experience"] = 51
        with pytest.raises(ValueError):
            ProviderCreate(**valid_provider_data)

class TestPasswordHashing:
    """Test password hashing and verification"""
    
    def test_password_hashing(self):
        """Test that passwords are properly hashed"""
        password = "SecurePass123!"
        hashed = get_password_hash(password)
        
        assert hashed != password
        assert len(hashed) > len(password)
        assert hashed.startswith("$2b$")  # bcrypt format
    
    def test_password_verification(self):
        """Test password verification"""
        password = "SecurePass123!"
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) is True
        assert verify_password("wrongpassword", hashed) is False

class TestProviderRegistration:
    """Test provider registration endpoints"""
    
    def test_successful_registration(self, valid_provider_data):
        """Test successful provider registration"""
        response = client.post("/api/v1/auth/register", json=valid_provider_data)
        assert response.status_code == 201
        
        data = response.json()
        assert data["first_name"] == "John"
        assert data["email"] == "john.doe@example.com"
        assert "password" not in data  # Password should not be returned
        assert data["verification_status"] == "pending"
        assert data["is_active"] is True
    
    def test_duplicate_email_registration(self, valid_provider_data):
        """Test registration with duplicate email"""
        # First registration
        response = client.post("/api/v1/auth/register", json=valid_provider_data)
        assert response.status_code == 201
        
        # Second registration with same email
        valid_provider_data["phone_number"] = "+1987654321"
        valid_provider_data["license_number"] = "MD654321"
        response = client.post("/api/v1/auth/register", json=valid_provider_data)
        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]
    
    def test_duplicate_phone_registration(self, valid_provider_data):
        """Test registration with duplicate phone number"""
        # First registration
        response = client.post("/api/v1/auth/register", json=valid_provider_data)
        assert response.status_code == 201
        
        # Second registration with same phone
        valid_provider_data["email"] = "different@example.com"
        valid_provider_data["license_number"] = "MD654321"
        response = client.post("/api/v1/auth/register", json=valid_provider_data)
        assert response.status_code == 400
        assert "Phone number already registered" in response.json()["detail"]
    
    def test_duplicate_license_registration(self, valid_provider_data):
        """Test registration with duplicate license number"""
        # First registration
        response = client.post("/api/v1/auth/register", json=valid_provider_data)
        assert response.status_code == 201
        
        # Second registration with same license
        valid_provider_data["email"] = "different@example.com"
        valid_provider_data["phone_number"] = "+1987654321"
        response = client.post("/api/v1/auth/register", json=valid_provider_data)
        assert response.status_code == 400
        assert "License number already registered" in response.json()["detail"]
    
    def test_invalid_data_registration(self, valid_provider_data):
        """Test registration with invalid data"""
        valid_provider_data["email"] = "invalid-email"
        response = client.post("/api/v1/auth/register", json=valid_provider_data)
        assert response.status_code == 422  # Validation error

class TestProviderLogin:
    """Test provider login functionality"""
    
    def test_successful_login(self, valid_provider_data):
        """Test successful login"""
        # Register provider first
        response = client.post("/api/v1/auth/register", json=valid_provider_data)
        assert response.status_code == 201
        
        # Login
        login_data = {
            "username": valid_provider_data["email"],
            "password": valid_provider_data["password"]
        }
        response = client.post("/api/v1/auth/login", data=login_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    def test_invalid_credentials(self, valid_provider_data):
        """Test login with invalid credentials"""
        # Register provider first
        response = client.post("/api/v1/auth/register", json=valid_provider_data)
        assert response.status_code == 201
        
        # Login with wrong password
        login_data = {
            "username": valid_provider_data["email"],
            "password": "wrongpassword"
        }
        response = client.post("/api/v1/auth/login", data=login_data)
        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]
    
    def test_nonexistent_user_login(self):
        """Test login with non-existent user"""
        login_data = {
            "username": "nonexistent@example.com",
            "password": "SecurePass123!"
        }
        response = client.post("/api/v1/auth/login", data=login_data)
        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"] 