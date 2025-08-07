from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import ProviderCreate, ProviderResponse, Token, ProviderLogin, LoginResponse
from app.crud import create_provider, get_provider_by_email
from app.security import authenticate_provider, create_access_token, create_provider_access_token
from datetime import timedelta
from app.config import settings

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=ProviderResponse, status_code=status.HTTP_201_CREATED)
def register_provider(
    provider: ProviderCreate,
    db: Session = Depends(get_db)
):
    """
    Register a new healthcare provider
    
    - **first_name**: Provider's first name (2-50 characters)
    - **last_name**: Provider's last name (2-50 characters)
    - **email**: Unique email address
    - **phone_number**: Unique phone number in international format
    - **password**: Strong password (8+ chars, uppercase, lowercase, number, special char)
    - **specialization**: Medical specialization (3-100 characters)
    - **license_number**: Unique alphanumeric license number
    - **years_of_experience**: Optional years of experience (0-50)
    - **clinic_address**: Complete clinic address information
    """
    try:
        db_provider = create_provider(db=db, provider=provider)
        return db_provider
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again."
        )


@router.post("/login", response_model=Token)
def login_provider_oauth(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    OAuth2 login for healthcare providers (form data)
    
    - **username**: Email address
    - **password**: Account password
    """
    provider = get_provider_by_email(db, email=form_data.username)
    if not provider or not authenticate_provider(form_data.username, form_data.password, provider):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not provider.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account is inactive"
        )
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": provider.email}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/provider/login", response_model=LoginResponse)
def login_provider(
    login_data: ProviderLogin,
    db: Session = Depends(get_db)
):
    """
    Secure login for healthcare providers
    
    - **email**: Provider's email address (must be valid format)
    - **password**: Provider's password (must be non-empty)
    """
    # Validate email format (already done by Pydantic)
    if not login_data.email or not login_data.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and password are required"
        )
    
    # Get provider by email
    provider = get_provider_by_email(db, email=login_data.email)
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify password using bcrypt
    if not authenticate_provider(login_data.email, login_data.password, provider):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if account is active
    if not provider.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account is inactive"
        )
    
    # Generate JWT access token with 1 hour expiry
    access_token_expires = timedelta(hours=1)
    access_token = create_provider_access_token(provider, expires_delta=access_token_expires)
    
    # Prepare provider data (excluding sensitive information)
    provider_data = {
        "id": str(provider.id),
        "first_name": provider.first_name,
        "last_name": provider.last_name,
        "email": provider.email,
        "phone_number": provider.phone_number,
        "specialization": provider.specialization,
        "license_number": provider.license_number,
        "years_of_experience": provider.years_of_experience,
        "clinic_address": provider.clinic_address,
        "verification_status": provider.verification_status,
        "is_active": provider.is_active,
        "created_at": provider.created_at.isoformat(),
        "updated_at": provider.updated_at.isoformat()
    }
    
    return LoginResponse(
        success=True,
        message="Login successful",
        data={
            "access_token": access_token,
            "expires_in": 3600,  # 1 hour in seconds
            "token_type": "Bearer",
            "provider": provider_data
        }
    ) 