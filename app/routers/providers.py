from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import ProviderResponse
from app.crud import get_provider_by_id, update_provider_verification_status
from app.dependencies import get_current_active_provider
from app.models import Provider, VerificationStatus
from typing import List

router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("/me", response_model=ProviderResponse)
def get_current_provider_profile(
    current_provider: Provider = Depends(get_current_active_provider)
):
    """
    Get current provider's profile information
    """
    return current_provider


@router.get("/{provider_id}", response_model=ProviderResponse)
def get_provider_by_id_endpoint(
    provider_id: str,
    db: Session = Depends(get_db),
    current_provider: Provider = Depends(get_current_active_provider)
):
    """
    Get provider information by ID (for admin/verification purposes)
    """
    provider = get_provider_by_id(db, provider_id)
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found"
        )
    return provider


@router.put("/{provider_id}/verify", response_model=ProviderResponse)
def verify_provider(
    provider_id: str,
    verification_status: VerificationStatus,
    db: Session = Depends(get_db),
    current_provider: Provider = Depends(get_current_active_provider)
):
    """
    Update provider verification status (admin only)
    """
    # In a real application, you would check if current_provider has admin privileges
    # For now, we'll allow any authenticated provider to update verification status
    
    provider = update_provider_verification_status(db, provider_id, verification_status)
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found"
        )
    
    return provider


@router.get("/pending-verification", response_model=List[ProviderResponse])
def get_pending_verification_providers(
    db: Session = Depends(get_db),
    current_provider: Provider = Depends(get_current_active_provider)
):
    """
    Get all providers pending verification (admin only)
    """
    # In a real application, you would check if current_provider has admin privileges
    pending_providers = db.query(Provider).filter(
        Provider.verification_status == VerificationStatus.PENDING
    ).all()
    
    return pending_providers 