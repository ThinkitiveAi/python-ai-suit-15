from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import (
    ProviderAvailabilityUpdate,
    AvailabilityCreateResponse,
    AvailabilityResponse,
    AvailabilitySearchRequest,
    AvailabilitySearchResponse
)
from app.crud import (
    create_provider_availability,
    get_provider_availability,
    update_availability_slot,
    delete_availability_slot,
    search_availability
)
from app.dependencies import get_current_active_provider
from typing import Optional
import logging
from datetime import date

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/provider", tags=["provider-availability"])


@router.post("/availability", response_model=AvailabilityCreateResponse, status_code=status.HTTP_201_CREATED)
def create_availability_slots(
    availability_data: dict,
    db: Session = Depends(get_db),
    current_provider = Depends(get_current_active_provider)
):
    """
    Create availability slots for a healthcare provider
    
    This endpoint allows providers to set their available time slots with support for:
    - Single day or recurring availability
    - Custom slot durations and break times
    - Multiple appointment types
    - Location and pricing information
    - Special requirements and notes
    
    **Features:**
    - Conflict detection to prevent overlapping slots
    - Timezone handling for accurate scheduling
    - Automatic slot generation based on duration settings
    - Support for daily, weekly, and monthly recurrence patterns
    """
    try:
        result = create_provider_availability(
            db=db,
            provider_id=str(current_provider.id),
            availability_data=availability_data
        )
        
        return AvailabilityCreateResponse(
            success=True,
            message="Availability slots created successfully",
            data=result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating availability slots: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create availability slots"
        )


@router.get("/{provider_id}/availability", response_model=AvailabilityResponse)
def get_provider_availability_endpoint(
    provider_id: str,
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    status: Optional[str] = Query(None, description="Filter by status (available/booked/cancelled/blocked)"),
    appointment_type: Optional[str] = Query(None, description="Filter by appointment type"),
    timezone: Optional[str] = Query(None, description="Timezone for display (defaults to provider's timezone)"),
    db: Session = Depends(get_db),
    current_provider = Depends(get_current_active_provider)
):
    """
    Get provider availability for a specific date range
    
    This endpoint retrieves all availability slots for a provider within the specified date range.
    Results are grouped by date and include detailed slot information.
    
    **Features:**
    - Date range filtering
    - Status-based filtering
    - Appointment type filtering
    - Timezone conversion for display
    - Summary statistics
    """
    try:
        # Validate date range
        if end_date <= start_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="End date must be after start date"
            )
        
        # Check if provider is requesting their own availability or has permission
        if str(current_provider.id) != provider_id:
            # In a real application, you might check for admin permissions here
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        result = get_provider_availability(
            db=db,
            provider_id=provider_id,
            start_date=start_date,
            end_date=end_date,
            status_filter=status,
            appointment_type=appointment_type,
            timezone=timezone
        )
        
        return AvailabilityResponse(
            success=True,
            data=result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving provider availability: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve provider availability"
        )


@router.put("/availability/{slot_id}")
def update_availability_slot_endpoint(
    slot_id: str,
    update_data: ProviderAvailabilityUpdate,
    db: Session = Depends(get_db),
    current_provider = Depends(get_current_active_provider)
):
    """
    Update a specific availability slot
    
    This endpoint allows providers to modify individual availability slots.
    Only certain fields can be updated to maintain data integrity.
    
    **Updatable Fields:**
    - Start time and end time
    - Status (available, blocked, maintenance)
    - Notes
    - Pricing information
    - Special requirements
    """
    try:
        # Convert Pydantic model to dict, excluding None values
        update_dict = update_data.dict(exclude_unset=True)
        
        slot = update_availability_slot(
            db=db,
            slot_id=slot_id,
            update_data=update_dict
        )
        
        if not slot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Availability slot not found"
            )
        
        return {
            "success": True,
            "message": "Availability slot updated successfully",
            "data": {
                "slot_id": str(slot.id),
                "status": slot.status.value,
                "updated_at": slot.updated_at.isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating availability slot: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update availability slot"
        )


@router.delete("/availability/{slot_id}")
def delete_availability_slot_endpoint(
    slot_id: str,
    delete_recurring: bool = Query(False, description="Delete all recurring instances"),
    reason: Optional[str] = Query(None, description="Reason for deletion"),
    db: Session = Depends(get_db),
    current_provider = Depends(get_current_active_provider)
):
    """
    Delete an availability slot
    
    This endpoint allows providers to delete availability slots.
    Slots with existing bookings cannot be deleted.
    
    **Options:**
    - Delete single slot or all recurring instances
    - Provide reason for deletion (for audit purposes)
    - Automatic conflict checking
    """
    try:
        success = delete_availability_slot(
            db=db,
            slot_id=slot_id,
            delete_recurring=delete_recurring,
            reason=reason
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Availability slot not found"
            )
        
        return {
            "success": True,
            "message": "Availability slot deleted successfully",
            "data": {
                "slot_id": slot_id,
                "deleted_recurring": delete_recurring,
                "reason": reason
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting availability slot: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete availability slot"
        )


@router.get("/availability/search", response_model=AvailabilitySearchResponse)
def search_availability_endpoint(
    date: Optional[date] = Query(None, description="Specific date to search"),
    start_date: Optional[date] = Query(None, description="Start date for range search"),
    end_date: Optional[date] = Query(None, description="End date for range search"),
    specialization: Optional[str] = Query(None, description="Provider specialization"),
    location: Optional[str] = Query(None, description="Location (city, state, or zip)"),
    appointment_type: Optional[str] = Query(None, description="Type of appointment"),
    insurance_accepted: Optional[bool] = Query(None, description="Whether insurance is accepted"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price"),
    timezone: Optional[str] = Query(None, description="Timezone"),
    available_only: bool = Query(True, description="Show only available slots"),
    db: Session = Depends(get_db)
):
    """
    Search for available appointment slots
    
    This endpoint allows patients to search for available appointment slots based on various criteria.
    Results are grouped by provider and include detailed slot information.
    
    **Search Criteria:**
    - Date range or specific date
    - Provider specialization
    - Location preferences
    - Appointment type
    - Insurance acceptance
    - Price range
    - Timezone preferences
    
    **Features:**
    - Advanced filtering options
    - Provider information included
    - Timezone conversion
    - Pricing and location details
    """
    try:
        # Build search criteria
        search_criteria = {
            "date": date,
            "start_date": start_date,
            "end_date": end_date,
            "specialization": specialization,
            "location": location,
            "appointment_type": appointment_type,
            "insurance_accepted": insurance_accepted,
            "max_price": max_price,
            "timezone": timezone or "UTC",
            "available_only": available_only
        }
        
        # Remove None values
        search_criteria = {k: v for k, v in search_criteria.items() if v is not None}
        
        # Validate date range if both dates provided
        if start_date and end_date and end_date <= start_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="End date must be after start date"
            )
        
        result = search_availability(
            db=db,
            search_criteria=search_criteria
        )
        
        return AvailabilitySearchResponse(
            success=True,
            data=result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching availability: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search availability"
        ) 