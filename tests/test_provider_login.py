import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, Column, String, Integer, Boolean, DateTime, Enum
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
import enum
import uuid
from app.main import app
from app.database import get_db, Base
from app.models import Provider, VerificationStatus
from app.security import get_password_hash, create_provider_access_token, verify_token_enhanced
from app.schemas import ClinicAddress
import jwt
from app.config import settings

# Create test-specific model for SQLite compatibility
class TestProvider(Base):
    __tablename__ = "providers"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone_number = Column(String(20), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    specialization = Column(String(100), nullable=False)
    license_number = Column(String(50), unique=True, nullable=False, index=True)
    years_of_experience = Column(Integer, nullable=True)
    clinic_address = Column(String(500), nullable=False)  # JSON as string for SQLite
    verification_status = Column(
        String(20), 
        default=VerificationStatus.PENDING, 
        nullable=False
    )
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_provider_login.db"
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
def sample_provider_data():
    return {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@clinic.com",
        "phone_number": "+1234567890",
        "password": "SecurePassword123!",
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

@pytest.fixture
def registered_provider(sample_provider_data):
    """Register a provider and return the data"""
    response = client.post("/api/v1/auth/register", json=sample_provider_data)
    assert response.status_code == 201
    return sample_provider_data

class TestProviderLoginEndpoint:
    """Test the new provider login endpoint"""
    
    def test_successful_login(self, registered_provider):
        """Test successful login with valid credentials"""
        login_data = {
            "email": registered_provider["email"],
            "password": registered_provider["password"]
        }
        
        response = client.post("/api/v1/provider/login", json=login_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Login successful"
        assert "data" in data
        
        # Check token data
        token_data = data["data"]
        assert "access_token" in token_data
        assert token_data["expires_in"] == 3600  # 1 hour
        assert token_data["token_type"] == "Bearer"
        
        # Check provider data
        provider_data = token_data["provider"]
        assert provider_data["email"] == registered_provider["email"]
        assert provider_data["first_name"] == registered_provider["first_name"]
        assert provider_data["last_name"] == registered_provider["last_name"]
        assert provider_data["specialization"] == registered_provider["specialization"]
        assert "password" not in provider_data  # Password should not be returned
        assert "password_hash" not in provider_data
    
    def test_invalid_email_format(self, registered_provider):
        """Test login with invalid email format"""
        login_data = {
            "email": "invalid-email-format",
            "password": registered_provider["password"]
        }
        
        response = client.post("/api/v1/provider/login", json=login_data)
        assert response.status_code == 422  # Validation error
    
    def test_empty_password(self, registered_provider):
        """Test login with empty password"""
        login_data = {
            "email": registered_provider["email"],
            "password": ""
        }
        
        response = client.post("/api/v1/provider/login", json=login_data)
        assert response.status_code == 422  # Validation error
    
    def test_missing_email(self, registered_provider):
        """Test login with missing email"""
        login_data = {
            "password": registered_provider["password"]
        }
        
        response = client.post("/api/v1/provider/login", json=login_data)
        assert response.status_code == 422  # Validation error
    
    def test_missing_password(self, registered_provider):
        """Test login with missing password"""
        login_data = {
            "email": registered_provider["email"]
        }
        
        response = client.post("/api/v1/provider/login", json=login_data)
        assert response.status_code == 422  # Validation error
    
    def test_incorrect_password(self, registered_provider):
        """Test login with incorrect password"""
        login_data = {
            "email": registered_provider["email"],
            "password": "WrongPassword123!"
        }
        
        response = client.post("/api/v1/provider/login", json=login_data)
        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]
    
    def test_nonexistent_email(self, registered_provider):
        """Test login with non-existent email"""
        login_data = {
            "email": "nonexistent@clinic.com",
            "password": registered_provider["password"]
        }
        
        response = client.post("/api/v1/provider/login", json=login_data)
        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]
    
    def test_inactive_account(self, sample_provider_data):
        """Test login with inactive account"""
        # Register provider
        response = client.post("/api/v1/auth/register", json=sample_provider_data)
        assert response.status_code == 201
        
        # Deactivate the provider (this would normally be done by admin)
        # For testing, we'll simulate this by directly updating the database
        from app.crud import get_provider_by_email
        from app.database import SessionLocal
        db = SessionLocal()
        try:
            provider = get_provider_by_email(db, sample_provider_data["email"])
            if provider:
                provider.is_active = False
                db.commit()
        finally:
            db.close()
        
        # Try to login
        login_data = {
            "email": sample_provider_data["email"],
            "password": sample_provider_data["password"]
        }
        
        response = client.post("/api/v1/provider/login", json=login_data)
        assert response.status_code == 400
        assert "Account is inactive" in response.json()["detail"]

class TestJWTTokenGeneration:
    """Test JWT token generation and validation"""
    
    def test_jwt_token_payload(self, registered_provider):
        """Test that JWT token contains required payload fields"""
        login_data = {
            "email": registered_provider["email"],
            "password": registered_provider["password"]
        }
        
        response = client.post("/api/v1/provider/login", json=login_data)
        assert response.status_code == 200
        
        token = response.json()["data"]["access_token"]
        
        # Decode and verify token payload
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        
        # Check required fields
        assert "sub" in payload  # email
        assert "provider_id" in payload
        assert "email" in payload
        assert "role" in payload
        assert "specialization" in payload
        assert "exp" in payload  # expiration
        
        # Check values
        assert payload["email"] == registered_provider["email"]
        assert payload["role"] == "provider"
        assert payload["specialization"] == registered_provider["specialization"]
    
    def test_jwt_token_expiration(self, registered_provider):
        """Test that JWT token expires after 1 hour"""
        login_data = {
            "email": registered_provider["email"],
            "password": registered_provider["password"]
        }
        
        response = client.post("/api/v1/provider/login", json=login_data)
        assert response.status_code == 200
        
        token = response.json()["data"]["access_token"]
        
        # Decode token to check expiration
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        import time
        current_time = int(time.time())
        expiration_time = payload["exp"]
        
        # Token should expire in approximately 1 hour (3600 seconds)
        time_until_expiry = expiration_time - current_time
        assert 3590 <= time_until_expiry <= 3610  # Allow 10 seconds tolerance
    
    def test_enhanced_token_verification(self, registered_provider):
        """Test enhanced token verification function"""
        login_data = {
            "email": registered_provider["email"],
            "password": registered_provider["password"]
        }
        
        response = client.post("/api/v1/provider/login", json=login_data)
        assert response.status_code == 200
        
        token = response.json()["data"]["access_token"]
        
        # Test enhanced verification
        token_data = verify_token_enhanced(token)
        assert token_data is not None
        assert token_data["email"] == registered_provider["email"]
        assert token_data["role"] == "provider"
        assert token_data["specialization"] == registered_provider["specialization"]
    
    def test_invalid_token_verification(self):
        """Test enhanced token verification with invalid token"""
        # Test with invalid token
        token_data = verify_token_enhanced("invalid.token.here")
        assert token_data is None
        
        # Test with token missing required fields
        incomplete_payload = {"sub": "test@example.com"}
        incomplete_token = jwt.encode(incomplete_payload, settings.secret_key, algorithm=settings.algorithm)
        token_data = verify_token_enhanced(incomplete_token)
        assert token_data is None

class TestAuthenticationLogic:
    """Test authentication logic and bcrypt password verification"""
    
    def test_bcrypt_password_verification(self, registered_provider):
        """Test that bcrypt password verification works correctly"""
        from app.security import verify_password
        from app.crud import get_provider_by_email
        from app.database import SessionLocal
        
        db = SessionLocal()
        try:
            provider = get_provider_by_email(db, registered_provider["email"])
            
            # Test correct password
            assert verify_password(registered_provider["password"], provider.password_hash) is True
            
            # Test incorrect password
            assert verify_password("WrongPassword123!", provider.password_hash) is False
            
        finally:
            db.close()
    
    def test_provider_access_token_creation(self, registered_provider):
        """Test provider-specific access token creation"""
        from app.crud import get_provider_by_email
        from app.database import SessionLocal
        
        db = SessionLocal()
        try:
            provider = get_provider_by_email(db, registered_provider["email"])
            
            # Create provider access token
            token = create_provider_access_token(provider)
            
            # Verify token payload
            payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
            assert payload["email"] == provider.email
            assert payload["provider_id"] == str(provider.id)
            assert payload["role"] == "provider"
            assert payload["specialization"] == provider.specialization
            
        finally:
            db.close()

class TestLoginResponseFormat:
    """Test that login response matches the required format"""
    
    def test_response_structure(self, registered_provider):
        """Test that login response has the correct structure"""
        login_data = {
            "email": registered_provider["email"],
            "password": registered_provider["password"]
        }
        
        response = client.post("/api/v1/provider/login", json=login_data)
        assert response.status_code == 200
        
        data = response.json()
        
        # Check top-level structure
        assert "success" in data
        assert "message" in data
        assert "data" in data
        
        # Check data structure
        token_data = data["data"]
        assert "access_token" in token_data
        assert "expires_in" in token_data
        assert "token_type" in token_data
        assert "provider" in token_data
        
        # Check provider data structure
        provider_data = token_data["provider"]
        required_provider_fields = [
            "id", "first_name", "last_name", "email", "phone_number",
            "specialization", "license_number", "years_of_experience",
            "clinic_address", "verification_status", "is_active",
            "created_at", "updated_at"
        ]
        
        for field in required_provider_fields:
            assert field in provider_data
    
    def test_sensitive_data_not_returned(self, registered_provider):
        """Test that sensitive data is not returned in login response"""
        login_data = {
            "email": registered_provider["email"],
            "password": registered_provider["password"]
        }
        
        response = client.post("/api/v1/provider/login", json=login_data)
        assert response.status_code == 200
        
        provider_data = response.json()["data"]["provider"]
        
        # Check that sensitive fields are not present
        sensitive_fields = ["password", "password_hash"]
        for field in sensitive_fields:
            assert field not in provider_data 