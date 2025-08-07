from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.schemas import (
    AppointmentCreate,
    AppointmentUpdate,
    AppointmentResponse,
    AppointmentListResponse,
    AppointmentDetailResponse,
    AppointmentCreateResponse,
    AppointmentCancelRequest,
    AppointmentCancelResponse,
    AppointmentRescheduleRequest,
    AppointmentRescheduleResponse
)
from app.crud import (
    get_appointment_by_id,
    get_appointments_by_patient,
    get_appointments_by_provider,
    create_appointment,
    update_appointment,
    cancel_appointment,
    reschedule_appointment,
    get_patient_by_id,
    get_provider_by_id
)
from app.dependencies import get_current_active_patient, get_current_active_provider
from app.models import AppointmentStatus

router = APIRouter(tags=["Appointments"])


@router.post("/appointments", response_model=AppointmentCreateResponse, status_code=status.HTTP_201_CREATED)
def book_appointment(
    appointment_data: AppointmentCreate,
    db: Session = Depends(get_db),
    current_patient = Depends(get_current_active_patient)
):
    """
    Book a new appointment
    
    - **slot_id**: ID of the appointment slot to book
    - **appointment_type**: Type of appointment (consultation, follow_up, emergency, telemedicine)
    - **symptoms**: Patient symptoms (optional)
    - **contact_phone**: Contact phone number (optional)
    - **contact_email**: Contact email (optional)
    - **insurance_coverage**: Insurance coverage amount (optional)
    - **patient_payment**: Patient payment amount (optional)
    """
    try:
        appointment = create_appointment(
            db=db,
            patient_id=str(current_patient.id),
            appointment_data=appointment_data.dict()
        )
        
        return AppointmentCreateResponse(
            success=True,
            message="Appointment booked successfully",
            data=appointment
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to book appointment"
        )


@router.get("/appointments", response_model=AppointmentListResponse)
def get_my_appointments(
    status: Optional[AppointmentStatus] = Query(None, description="Filter by appointment status"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    db: Session = Depends(get_db),
    current_patient = Depends(get_current_active_patient)
):
    """
    Get appointments for the current patient
    
    - **status**: Filter by appointment status (scheduled, confirmed, in_progress, completed, cancelled, no_show, rescheduled)
    - **skip**: Number of records to skip for pagination
    - **limit**: Number of records to return (max 1000)
    """
    appointments = get_appointments_by_patient(
        db=db,
        patient_id=str(current_patient.id),
        skip=skip,
        limit=limit,
        status=status
    )
    
    return AppointmentListResponse(
        success=True,
        data=appointments
    )


@router.get("/appointments/{appointment_id}", response_model=AppointmentDetailResponse)
def get_appointment_details(
    appointment_id: str,
    db: Session = Depends(get_db),
    current_patient = Depends(get_current_active_patient)
):
    """
    Get detailed information about a specific appointment
    
    - **appointment_id**: ID of the appointment to retrieve
    """
    appointment = get_appointment_by_id(db, appointment_id)
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    
    # Check if the appointment belongs to the current patient
    if str(appointment.patient_id) != str(current_patient.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return AppointmentDetailResponse(
        success=True,
        data=appointment
    )


@router.put("/appointments/{appointment_id}", response_model=AppointmentDetailResponse)
def update_appointment_details(
    appointment_id: str,
    update_data: AppointmentUpdate,
    db: Session = Depends(get_db),
    current_patient = Depends(get_current_active_patient)
):
    """
    Update appointment details (limited fields for patients)
    
    - **appointment_id**: ID of the appointment to update
    - **symptoms**: Updated patient symptoms
    - **contact_phone**: Updated contact phone number
    - **contact_email**: Updated contact email
    """
    appointment = get_appointment_by_id(db, appointment_id)
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    
    # Check if the appointment belongs to the current patient
    if str(appointment.patient_id) != str(current_patient.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Patients can only update limited fields
    allowed_fields = ['symptoms', 'contact_phone', 'contact_email']
    filtered_data = {k: v for k, v in update_data.dict(exclude_unset=True).items() if k in allowed_fields}
    
    if not filtered_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid fields to update"
        )
    
    updated_appointment = update_appointment(db, appointment_id, filtered_data)
    
    if not updated_appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    
    return AppointmentDetailResponse(
        success=True,
        data=updated_appointment
    )


@router.post("/appointments/{appointment_id}/cancel", response_model=AppointmentCancelResponse)
def cancel_appointment_patient(
    appointment_id: str,
    cancel_request: AppointmentCancelRequest,
    db: Session = Depends(get_db),
    current_patient = Depends(get_current_active_patient)
):
    """
    Cancel an appointment (patient-initiated)
    
    - **appointment_id**: ID of the appointment to cancel
    - **reason**: Reason for cancellation
    """
    appointment = get_appointment_by_id(db, appointment_id)
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    
    # Check if the appointment belongs to the current patient
    if str(appointment.patient_id) != str(current_patient.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    cancelled_appointment = cancel_appointment(
        db=db,
        appointment_id=appointment_id,
        reason=cancel_request.reason,
        cancelled_by="patient"
    )
    
    if not cancelled_appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    
    return AppointmentCancelResponse(
        success=True,
        message="Appointment cancelled successfully",
        data={
            "appointment_id": appointment_id,
            "booking_reference": cancelled_appointment.booking_reference,
            "cancelled_at": cancelled_appointment.cancelled_at,
            "refund_amount": cancelled_appointment.patient_payment
        }
    )


@router.post("/appointments/{appointment_id}/reschedule", response_model=AppointmentRescheduleResponse)
def reschedule_appointment_patient(
    appointment_id: str,
    reschedule_request: AppointmentRescheduleRequest,
    db: Session = Depends(get_db),
    current_patient = Depends(get_current_active_patient)
):
    """
    Reschedule an appointment (patient-initiated)
    
    - **appointment_id**: ID of the appointment to reschedule
    - **new_slot_id**: ID of the new appointment slot
    - **reason**: Reason for rescheduling (optional)
    """
    appointment = get_appointment_by_id(db, appointment_id)
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    
    # Check if the appointment belongs to the current patient
    if str(appointment.patient_id) != str(current_patient.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    rescheduled_appointment = reschedule_appointment(
        db=db,
        appointment_id=appointment_id,
        new_slot_id=reschedule_request.new_slot_id,
        reason=reschedule_request.reason
    )
    
    if not rescheduled_appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    
    return AppointmentRescheduleResponse(
        success=True,
        message="Appointment rescheduled successfully",
        data=rescheduled_appointment
    )


# Provider appointment management endpoints
@router.get("/provider/appointments", response_model=AppointmentListResponse)
def get_provider_appointments(
    status: Optional[AppointmentStatus] = Query(None, description="Filter by appointment status"),
    patient_id: Optional[str] = Query(None, description="Filter by patient ID"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    db: Session = Depends(get_db),
    current_provider = Depends(get_current_active_provider)
):
    """
    Get appointments for the current provider
    
    - **status**: Filter by appointment status
    - **patient_id**: Filter by specific patient ID
    - **skip**: Number of records to skip for pagination
    - **limit**: Number of records to return (max 1000)
    """
    appointments = get_appointments_by_provider(
        db=db,
        provider_id=str(current_provider.id),
        skip=skip,
        limit=limit,
        status=status
    )
    
    # Filter by patient if specified
    if patient_id:
        appointments = [apt for apt in appointments if str(apt.patient_id) == patient_id]
    
    return AppointmentListResponse(
        success=True,
        data=appointments
    )


@router.get("/provider/appointments/{appointment_id}", response_model=AppointmentDetailResponse)
def get_provider_appointment_details(
    appointment_id: str,
    db: Session = Depends(get_db),
    current_provider = Depends(get_current_active_provider)
):
    """
    Get detailed information about a specific appointment (provider view)
    
    - **appointment_id**: ID of the appointment to retrieve
    """
    appointment = get_appointment_by_id(db, appointment_id)
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    
    # Check if the appointment belongs to the current provider
    if str(appointment.provider_id) != str(current_provider.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return AppointmentDetailResponse(
        success=True,
        data=appointment
    )


@router.put("/provider/appointments/{appointment_id}", response_model=AppointmentDetailResponse)
def update_provider_appointment_details(
    appointment_id: str,
    update_data: AppointmentUpdate,
    db: Session = Depends(get_db),
    current_provider = Depends(get_current_active_provider)
):
    """
    Update appointment details (provider view - full access)
    
    - **appointment_id**: ID of the appointment to update
    - **status**: Appointment status
    - **payment_status**: Payment status
    - **medical_notes**: Medical notes
    - **prescription**: Prescription
    - **follow_up_required**: Whether follow-up is required
    - **follow_up_date**: Follow-up date
    - **actual_start_time**: Actual start time
    - **actual_end_time**: Actual end time
    """
    appointment = get_appointment_by_id(db, appointment_id)
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    
    # Check if the appointment belongs to the current provider
    if str(appointment.provider_id) != str(current_provider.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    updated_appointment = update_appointment(db, appointment_id, update_data.dict(exclude_unset=True))
    
    if not updated_appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    
    return AppointmentDetailResponse(
        success=True,
        data=updated_appointment
    )


@router.post("/provider/appointments/{appointment_id}/cancel", response_model=AppointmentCancelResponse)
def cancel_appointment_provider(
    appointment_id: str,
    cancel_request: AppointmentCancelRequest,
    db: Session = Depends(get_db),
    current_provider = Depends(get_current_active_provider)
):
    """
    Cancel an appointment (provider-initiated)
    
    - **appointment_id**: ID of the appointment to cancel
    - **reason**: Reason for cancellation
    """
    appointment = get_appointment_by_id(db, appointment_id)
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    
    # Check if the appointment belongs to the current provider
    if str(appointment.provider_id) != str(current_provider.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    cancelled_appointment = cancel_appointment(
        db=db,
        appointment_id=appointment_id,
        reason=cancel_request.reason,
        cancelled_by="provider"
    )
    
    if not cancelled_appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    
    return AppointmentCancelResponse(
        success=True,
        message="Appointment cancelled successfully",
        data={
            "appointment_id": appointment_id,
            "booking_reference": cancelled_appointment.booking_reference,
            "cancelled_at": cancelled_appointment.cancelled_at,
            "refund_amount": cancelled_appointment.patient_payment
        }
    )


@router.post("/provider/appointments/{appointment_id}/reschedule", response_model=AppointmentRescheduleResponse)
def reschedule_appointment_provider(
    appointment_id: str,
    reschedule_request: AppointmentRescheduleRequest,
    db: Session = Depends(get_db),
    current_provider = Depends(get_current_active_provider)
):
    """
    Reschedule an appointment (provider-initiated)
    
    - **appointment_id**: ID of the appointment to reschedule
    - **new_slot_id**: ID of the new appointment slot
    - **reason**: Reason for rescheduling (optional)
    """
    appointment = get_appointment_by_id(db, appointment_id)
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    
    # Check if the appointment belongs to the current provider
    if str(appointment.provider_id) != str(current_provider.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    rescheduled_appointment = reschedule_appointment(
        db=db,
        appointment_id=appointment_id,
        new_slot_id=reschedule_request.new_slot_id,
        reason=reschedule_request.reason
    )
    
    if not rescheduled_appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    
    return AppointmentRescheduleResponse(
        success=True,
        message="Appointment rescheduled successfully",
        data=rescheduled_appointment
    )


# Public appointment endpoints (for booking without authentication)
@router.get("/public/appointments/{booking_reference}", response_model=AppointmentDetailResponse)
def get_appointment_by_booking_reference(
    booking_reference: str,
    db: Session = Depends(get_db)
):
    """
    Get appointment details by booking reference (public access)
    
    - **booking_reference**: Booking reference number
    """
    from app.crud import get_appointment_by_booking_reference
    
    appointment = get_appointment_by_booking_reference(db, booking_reference)
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    
    return AppointmentDetailResponse(
        success=True,
        data=appointment
    ) 