from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import (
    PatientCreate, 
    PatientResponse, 
    PatientLogin, 
    LoginResponse, 
    Token,
    PatientRegistrationResponse,
    ValidationErrorResponse
)
from app.crud import create_patient, get_patient_by_email, get_patient_by_id
from app.security import authenticate_patient, create_patient_access_token
from app.dependencies import get_current_active_patient, get_current_active_provider
from datetime import timedelta
from app.config import settings
from pydantic import ValidationError
import logging

# Configure logging for HIPAA compliance
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/patient", tags=["patients"])


@router.post("/register", response_model=PatientRegistrationResponse, status_code=status.HTTP_201_CREATED)
def register_patient(
    patient: PatientCreate,
    db: Session = Depends(get_db)
):
    """
    Register a new patient with comprehensive validation and HIPAA compliance
    
    - **first_name**: Patient's first name (2-50 characters)
    - **last_name**: Patient's last name (2-50 characters)
    - **email**: Unique email address
    - **phone_number**: Unique phone number in international format
    - **password**: Strong password (8+ chars, uppercase, lowercase, number, special char)
    - **confirm_password**: Password confirmation (must match password)
    - **date_of_birth**: Date of birth (must be at least 13 years old for COPPA compliance)
    - **gender**: Gender selection (male/female/other/prefer_not_to_say)
    - **address**: Complete address information
    - **emergency_contact**: Optional emergency contact information
    - **medical_history**: Optional medical history array
    - **insurance_info**: Optional insurance information
    """
    try:
        db_patient = create_patient(db=db, patient=patient)
        
        # Prepare response data (HIPAA compliant - no sensitive information)
        response_data = {
            "patient_id": str(db_patient.id),
            "email": db_patient.email,
            "phone_number": db_patient.phone_number,
            "email_verified": db_patient.email_verified,
            "phone_verified": db_patient.phone_verified
        }
        
        return PatientRegistrationResponse(
            success=True,
            message="Patient registered successfully. Verification email sent.",
            data=response_data
        )
        
    except HTTPException:
        raise
    except ValidationError as e:
        # Handle validation errors with detailed error messages
        error_details = {}
        for error in e.errors():
            field = error["loc"][0] if error["loc"] else "unknown"
            message = error["msg"]
            if field not in error_details:
                error_details[field] = []
            error_details[field].append(message)
        
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "success": False,
                "message": "Validation failed",
                "errors": error_details
            }
        )
    except Exception as e:
        logger.error(f"Patient registration failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again."
        )


@router.post("/login", response_model=LoginResponse)
def login_patient(
    login_data: PatientLogin,
    db: Session = Depends(get_db)
):
    """
    Secure login for patients
    
    - **email**: Patient's email address (must be valid format)
    - **password**: Patient's password (must be non-empty)
    """
    # Validate email format (already done by Pydantic)
    if not login_data.email or not login_data.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and password are required"
        )
    
    # Get patient by email
    patient = get_patient_by_email(db, email=login_data.email)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify password using bcrypt
    if not authenticate_patient(login_data.email, login_data.password, patient):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if account is active
    if not patient.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account is inactive"
        )
    
    # Generate JWT access token with 30 minutes expiry
    access_token_expires = timedelta(minutes=30)
    access_token = create_patient_access_token(patient, expires_delta=access_token_expires)
    
    # Prepare patient data (excluding sensitive information)
    patient_data = {
        "id": str(patient.id),
        "first_name": patient.first_name,
        "last_name": patient.last_name,
        "email": patient.email,
        "phone_number": patient.phone_number,
        "date_of_birth": patient.date_of_birth.isoformat(),
        "gender": patient.gender,
        "address": patient.address,
        "emergency_contact": patient.emergency_contact,
        "medical_history": patient.medical_history,
        "insurance_info": patient.insurance_info,
        "email_verified": patient.email_verified,
        "phone_verified": patient.phone_verified,
        "is_active": patient.is_active,
        "created_at": patient.created_at.isoformat(),
        "updated_at": patient.updated_at.isoformat()
    }
    
    return LoginResponse(
        success=True,
        message="Login successful",
        data={
            "access_token": access_token,
            "expires_in": 1800,  # 30 minutes in seconds
            "token_type": "Bearer",
            "patient": patient_data
        }
    )


@router.post("/login/oauth", response_model=Token)
def login_patient_oauth(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    OAuth2 login for patients (form data)
    
    - **username**: Email address
    - **password**: Account password
    """
    patient = get_patient_by_email(db, email=form_data.username)
    if not patient or not authenticate_patient(form_data.username, form_data.password, patient):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not patient.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account is inactive"
        )
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_patient_access_token(patient, expires_delta=access_token_expires)
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=PatientResponse)
def get_current_patient_profile(
    current_patient = Depends(get_current_active_patient)
):
    """
    Get current patient's profile information
    """
    return current_patient


@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient_by_id_endpoint(
    patient_id: str,
    db: Session = Depends(get_db),
    current_provider = Depends(get_current_active_provider)
):
    """
    Get patient information by ID (provider access only)
    """
    patient = get_patient_by_id(db, patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )
    return patient


@router.put("/{patient_id}/verify-email")
def verify_patient_email(
    patient_id: str,
    db: Session = Depends(get_db),
    current_provider = Depends(get_current_active_provider)
):
    """
    Verify patient email (provider/admin only)
    """
    from app.crud import update_patient_verification_status
    
    patient = update_patient_verification_status(db, patient_id, email_verified=True)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )
    
    return {
        "success": True,
        "message": "Patient email verified successfully",
        "data": {
            "patient_id": str(patient.id),
            "email_verified": patient.email_verified
        }
    }


@router.put("/{patient_id}/verify-phone")
def verify_patient_phone(
    patient_id: str,
    db: Session = Depends(get_db),
    current_provider = Depends(get_current_active_provider)
):
    """
    Verify patient phone (provider/admin only)
    """
    from app.crud import update_patient_verification_status
    
    patient = update_patient_verification_status(db, patient_id, phone_verified=True)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )
    
    return {
        "success": True,
        "message": "Patient phone verified successfully",
        "data": {
            "patient_id": str(patient.id),
            "phone_verified": patient.phone_verified
        }
    }


@router.put("/{patient_id}/deactivate")
def deactivate_patient_account(
    patient_id: str,
    db: Session = Depends(get_db),
    current_provider = Depends(get_current_active_provider)
):
    """
    Deactivate patient account (provider/admin only)
    """
    from app.crud import deactivate_patient
    
    patient = deactivate_patient(db, patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )
    
    return {
        "success": True,
        "message": "Patient account deactivated successfully",
        "data": {
            "patient_id": str(patient.id),
            "is_active": patient.is_active
        }
    } 