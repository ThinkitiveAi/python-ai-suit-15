import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import get_db, Base
from app.models import Provider, VerificationStatus
from app.security import get_password_hash, create_access_token

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_providers.db"
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
def sample_provider_data():
    return {
        "first_name": "Jane",
        "last_name": "Smith",
        "email": "jane.smith@example.com",
        "phone_number": "+1987654321",
        "password": "SecurePass123!",
        "specialization": "Neurology",
        "license_number": "MD789012",
        "years_of_experience": 15,
        "clinic_address": {
            "street": "456 Neurology Ave",
            "city": "Los Angeles",
            "state": "CA",
            "zip": "90210"
        }
    }

@pytest.fixture
def authenticated_headers(sample_provider_data):
    """Create authenticated headers for testing"""
    # Register provider
    response = client.post("/api/v1/auth/register", json=sample_provider_data)
    assert response.status_code == 201
    
    # Login to get token
    login_data = {
        "username": sample_provider_data["email"],
        "password": sample_provider_data["password"]
    }
    response = client.post("/api/v1/auth/login", data=login_data)
    assert response.status_code == 200
    
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

class TestProviderProfile:
    """Test provider profile endpoints"""
    
    def test_get_current_provider_profile(self, authenticated_headers):
        """Test getting current provider's profile"""
        response = client.get("/api/v1/providers/me", headers=authenticated_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["first_name"] == "Jane"
        assert data["email"] == "jane.smith@example.com"
        assert "password" not in data  # Password should not be returned
        assert data["verification_status"] == "pending"
        assert data["is_active"] is True
    
    def test_get_profile_without_authentication(self):
        """Test getting profile without authentication"""
        response = client.get("/api/v1/providers/me")
        assert response.status_code == 401
        assert "Not authenticated" in response.json()["detail"]
    
    def test_get_profile_with_invalid_token(self):
        """Test getting profile with invalid token"""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/api/v1/providers/me", headers=headers)
        assert response.status_code == 401
        assert "Could not validate credentials" in response.json()["detail"]

class TestProviderVerification:
    """Test provider verification functionality"""
    
    def test_get_provider_by_id(self, authenticated_headers, sample_provider_data):
        """Test getting provider by ID"""
        # First get the provider's own profile to get the ID
        response = client.get("/api/v1/providers/me", headers=authenticated_headers)
        assert response.status_code == 200
        provider_id = response.json()["id"]
        
        # Get provider by ID
        response = client.get(f"/api/v1/providers/{provider_id}", headers=authenticated_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == provider_id
        assert data["first_name"] == "Jane"
        assert data["email"] == "jane.smith@example.com"
    
    def test_get_nonexistent_provider(self, authenticated_headers):
        """Test getting non-existent provider"""
        response = client.get("/api/v1/providers/nonexistent-id", headers=authenticated_headers)
        assert response.status_code == 404
        assert "Provider not found" in response.json()["detail"]
    
    def test_verify_provider(self, authenticated_headers, sample_provider_data):
        """Test verifying a provider"""
        # First get the provider's own profile to get the ID
        response = client.get("/api/v1/providers/me", headers=authenticated_headers)
        assert response.status_code == 200
        provider_id = response.json()["id"]
        
        # Verify the provider
        verification_data = {"verification_status": "verified"}
        response = client.put(
            f"/api/v1/providers/{provider_id}/verify",
            json=verification_data,
            headers=authenticated_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["verification_status"] == "verified"
    
    def test_reject_provider(self, authenticated_headers, sample_provider_data):
        """Test rejecting a provider"""
        # First get the provider's own profile to get the ID
        response = client.get("/api/v1/providers/me", headers=authenticated_headers)
        assert response.status_code == 200
        provider_id = response.json()["id"]
        
        # Reject the provider
        verification_data = {"verification_status": "rejected"}
        response = client.put(
            f"/api/v1/providers/{provider_id}/verify",
            json=verification_data,
            headers=authenticated_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["verification_status"] == "rejected"
    
    def test_verify_nonexistent_provider(self, authenticated_headers):
        """Test verifying non-existent provider"""
        verification_data = {"verification_status": "verified"}
        response = client.put(
            "/api/v1/providers/nonexistent-id/verify",
            json=verification_data,
            headers=authenticated_headers
        )
        assert response.status_code == 404
        assert "Provider not found" in response.json()["detail"]

class TestPendingVerification:
    """Test pending verification functionality"""
    
    def test_get_pending_verification_providers(self, authenticated_headers):
        """Test getting providers pending verification"""
        response = client.get("/api/v1/providers/pending-verification", headers=authenticated_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        # Should include the current provider since they start with pending status
        assert len(data) >= 1
    
    def test_get_pending_verification_without_auth(self):
        """Test getting pending verification without authentication"""
        response = client.get("/api/v1/providers/pending-verification")
        assert response.status_code == 401
        assert "Not authenticated" in response.json()["detail"]

class TestProviderDataIntegrity:
    """Test data integrity and security"""
    
    def test_password_not_returned_in_responses(self, authenticated_headers):
        """Test that passwords are never returned in API responses"""
        response = client.get("/api/v1/providers/me", headers=authenticated_headers)
        assert response.status_code == 200
        
        data = response.json()
        # Check that password-related fields are not present
        assert "password" not in data
        assert "password_hash" not in data
    
    def test_sensitive_data_protection(self, authenticated_headers, sample_provider_data):
        """Test that sensitive data is properly protected"""
        # Register another provider
        other_provider_data = sample_provider_data.copy()
        other_provider_data["email"] = "other@example.com"
        other_provider_data["phone_number"] = "+1111111111"
        other_provider_data["license_number"] = "MD111111"
        
        response = client.post("/api/v1/auth/register", json=other_provider_data)
        assert response.status_code == 201
        other_provider_id = response.json()["id"]
        
        # Try to access other provider's data
        response = client.get(f"/api/v1/providers/{other_provider_id}", headers=authenticated_headers)
        assert response.status_code == 200
        
        data = response.json()
        # Should not contain sensitive information
        assert "password" not in data
        assert "password_hash" not in data
        # Should contain public information
        assert data["first_name"] == "Jane"
        assert data["specialization"] == "Neurology" 