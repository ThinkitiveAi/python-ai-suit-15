from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
from app.config import settings

# Password hashing context with bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt with configured rounds"""
    return pwd_context.hash(password, rounds=settings.bcrypt_rounds)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token with provider information"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def create_provider_access_token(provider, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token with provider-specific payload"""
    payload = {
        "sub": provider.email,
        "provider_id": str(provider.id),
        "email": provider.email,
        "role": "provider",
        "specialization": provider.specialization
    }
    return create_access_token(payload, expires_delta)


def create_patient_access_token(patient, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token with patient-specific payload"""
    payload = {
        "sub": patient.email,
        "patient_id": str(patient.id),
        "email": patient.email,
        "role": "patient"
    }
    return create_access_token(payload, expires_delta)


def verify_token(token: str) -> Optional[str]:
    """Verify and decode a JWT token"""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        email: str = payload.get("sub")
        if email is None:
            return None
        return email
    except JWTError:
        return None


def verify_token_enhanced(token: str) -> Optional[dict]:
    """Verify and decode a JWT token with enhanced payload"""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        # Verify required fields
        required_fields = ["sub", "email", "role"]
        for field in required_fields:
            if field not in payload:
                return None
        return payload
    except JWTError:
        return None


def authenticate_provider(email: str, password: str, db_provider) -> bool:
    """Authenticate a provider with email and password"""
    if not db_provider:
        return False
    if not verify_password(password, db_provider.password_hash):
        return False
    return True


def authenticate_patient(email: str, password: str, db_patient) -> bool:
    """Authenticate a patient with email and password"""
    if not db_patient:
        return False
    if not verify_password(password, db_patient.password_hash):
        return False
    return True 