from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status
from app.models import (
    Provider, Patient, ProviderAvailability, AppointmentSlot, Appointment,
    AvailabilityStatus, AppointmentStatus, PaymentStatus
)
from app.schemas import ProviderCreate, PatientCreate
from app.security import get_password_hash
from typing import Optional, List, Dict, Any
import logging
from datetime import datetime, date, time, timedelta
import pytz
from dateutil import rrule
import uuid

# Configure logging for HIPAA compliance
logger = logging.getLogger(__name__)

# Provider CRUD operations
def get_provider_by_email(db: Session, email: str) -> Optional[Provider]:
    """Get provider by email"""
    return db.query(Provider).filter(Provider.email == email).first()


def get_provider_by_phone(db: Session, phone_number: str) -> Optional[Provider]:
    """Get provider by phone number"""
    return db.query(Provider).filter(Provider.phone_number == phone_number).first()


def get_provider_by_license(db: Session, license_number: str) -> Optional[Provider]:
    """Get provider by license number"""
    return db.query(Provider).filter(Provider.license_number == license_number).first()


def create_provider(db: Session, provider: ProviderCreate) -> Provider:
    """Create a new provider with proper duplicate checking"""
    # Check for existing email
    if get_provider_by_email(db, provider.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Check for existing phone number
    if get_provider_by_phone(db, provider.phone_number):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number already registered"
        )
    
    # Check for existing license number
    if get_provider_by_license(db, provider.license_number):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="License number already registered"
        )
    
    # Hash the password
    hashed_password = get_password_hash(provider.password)
    
    # Create provider object
    db_provider = Provider(
        first_name=provider.first_name,
        last_name=provider.last_name,
        email=provider.email,
        phone_number=provider.phone_number,
        password_hash=hashed_password,
        specialization=provider.specialization,
        license_number=provider.license_number,
        years_of_experience=provider.years_of_experience,
        clinic_address=provider.clinic_address.dict()
    )
    
    try:
        db.add(db_provider)
        db.commit()
        db.refresh(db_provider)
        
        # Log successful provider creation (HIPAA compliant)
        logger.info(f"Provider registered successfully: {provider.email}")
        
        return db_provider
    except IntegrityError as e:
        db.rollback()
        # Handle any remaining integrity errors
        if "email" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        elif "phone" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already registered"
            )
        elif "license" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="License number already registered"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration failed due to duplicate data"
            )


def get_provider_by_id(db: Session, provider_id: str) -> Optional[Provider]:
    """Get provider by ID"""
    return db.query(Provider).filter(Provider.id == provider_id).first()


def update_provider_verification_status(
    db: Session, 
    provider_id: str, 
    status: str
) -> Optional[Provider]:
    """Update provider verification status"""
    provider = get_provider_by_id(db, provider_id)
    if not provider:
        return None
    
    provider.verification_status = status
    db.commit()
    db.refresh(provider)
    return provider


# Patient CRUD operations
def get_patient_by_email(db: Session, email: str) -> Optional[Patient]:
    """Get patient by email"""
    return db.query(Patient).filter(Patient.email == email).first()


def get_patient_by_phone(db: Session, phone_number: str) -> Optional[Patient]:
    """Get patient by phone number"""
    return db.query(Patient).filter(Patient.phone_number == phone_number).first()


def get_patient_by_id(db: Session, patient_id: str) -> Optional[Patient]:
    """Get patient by ID"""
    return db.query(Patient).filter(Patient.id == patient_id).first()


def create_patient(db: Session, patient: PatientCreate) -> Patient:
    """Create a new patient with proper duplicate checking and HIPAA compliance"""
    # Check for existing email
    if get_patient_by_email(db, patient.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Check for existing phone number
    if get_patient_by_phone(db, patient.phone_number):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number already registered"
        )
    
    # Hash the password securely
    hashed_password = get_password_hash(patient.password)
    
    # Prepare address data
    address_data = patient.address.dict()
    
    # Prepare emergency contact data (if provided)
    emergency_contact_data = None
    if patient.emergency_contact:
        emergency_contact_data = patient.emergency_contact.dict()
    
    # Prepare insurance info data (if provided)
    insurance_info_data = None
    if patient.insurance_info:
        insurance_info_data = patient.insurance_info.dict()
    
    # Create patient object
    db_patient = Patient(
        first_name=patient.first_name,
        last_name=patient.last_name,
        email=patient.email,
        phone_number=patient.phone_number,
        password_hash=hashed_password,
        date_of_birth=patient.date_of_birth,
        gender=patient.gender,
        address=address_data,
        emergency_contact=emergency_contact_data,
        medical_history=patient.medical_history,
        insurance_info=insurance_info_data
    )
    
    try:
        db.add(db_patient)
        db.commit()
        db.refresh(db_patient)
        
        # Log successful patient creation (HIPAA compliant - no sensitive data)
        logger.info(f"Patient registered successfully: {patient.email}")
        
        return db_patient
    except IntegrityError as e:
        db.rollback()
        # Handle any remaining integrity errors
        if "email" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        elif "phone" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already registered"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration failed due to duplicate data"
            )


def update_patient_verification_status(
    db: Session, 
    patient_id: str, 
    email_verified: bool = None,
    phone_verified: bool = None
) -> Optional[Patient]:
    """Update patient verification status"""
    patient = get_patient_by_id(db, patient_id)
    if not patient:
        return None
    
    if email_verified is not None:
        patient.email_verified = email_verified
    if phone_verified is not None:
        patient.phone_verified = phone_verified
    
    db.commit()
    db.refresh(patient)
    return patient


def get_patients_by_provider(
    db: Session, 
    provider_id: str, 
    skip: int = 0, 
    limit: int = 100
) -> list[Patient]:
    """Get patients associated with a provider (for future implementation)"""
    # This would be implemented when provider-patient relationships are established
    # For now, return empty list
    return []


def deactivate_patient(db: Session, patient_id: str) -> Optional[Patient]:
    """Deactivate a patient account (HIPAA compliant)"""
    patient = get_patient_by_id(db, patient_id)
    if not patient:
        return None
    
    patient.is_active = False
    db.commit()
    db.refresh(patient)
    
    # Log patient deactivation (HIPAA compliant)
    logger.info(f"Patient account deactivated: {patient.email}")
    
    return patient


def update_patient_medical_history(
    db: Session, 
    patient_id: str, 
    medical_history: list[str]
) -> Optional[Patient]:
    """Update patient medical history (HIPAA compliant)"""
    patient = get_patient_by_id(db, patient_id)
    if not patient:
        return None
    
    patient.medical_history = medical_history
    db.commit()
    db.refresh(patient)
    
    # Log medical history update (HIPAA compliant - no sensitive data)
    logger.info(f"Medical history updated for patient: {patient.email}")
    
    return patient


# Provider Availability CRUD operations
def create_provider_availability(
    db: Session, 
    provider_id: str, 
    availability_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Create provider availability slots with conflict detection and timezone handling"""
    
    # Check if provider exists
    provider = get_provider_by_id(db, provider_id)
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found"
        )
    
    # Convert times to datetime objects for conflict detection
    start_datetime = datetime.combine(availability_data['date'], time.fromisoformat(availability_data['start_time']))
    end_datetime = datetime.combine(availability_data['date'], time.fromisoformat(availability_data['end_time']))
    
    # Check for overlapping availability slots
    existing_conflicts = db.query(ProviderAvailability).filter(
        ProviderAvailability.provider_id == provider_id,
        ProviderAvailability.date == availability_data['date'],
        ProviderAvailability.status.in_([AvailabilityStatus.AVAILABLE, AvailabilityStatus.BOOKED])
    ).all()
    
    for existing in existing_conflicts:
        existing_start = datetime.combine(existing.date, time.fromisoformat(existing.start_time))
        existing_end = datetime.combine(existing.date, time.fromisoformat(existing.end_time))
        
        if (start_datetime < existing_end and end_datetime > existing_start):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Time slot conflicts with existing availability: {existing.start_time}-{existing.end_time}"
            )
    
    # Generate dates for recurring availability
    dates_to_create = []
    if availability_data.get('is_recurring') and availability_data.get('recurrence_pattern') and availability_data.get('recurrence_end_date'):
        if availability_data['recurrence_pattern'] == "daily":
            rule = rrule.DAILY
        elif availability_data['recurrence_pattern'] == "weekly":
            rule = rrule.WEEKLY
        elif availability_data['recurrence_pattern'] == "monthly":
            rule = rrule.MONTHLY
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid recurrence pattern"
            )
        
        dates_to_create = list(rrule.rrule(
            rule,
            dtstart=availability_data['date'],
            until=availability_data['recurrence_end_date']
        ))
    else:
        dates_to_create = [availability_data['date']]
    
    # Create availability records
    created_availabilities = []
    total_slots_created = 0
    
    for current_date in dates_to_create:
        # Calculate number of slots for this day
        start_time = time.fromisoformat(availability_data['start_time'])
        end_time = time.fromisoformat(availability_data['end_time'])
        
        # Calculate total minutes available
        total_minutes = (end_time.hour * 60 + end_time.minute) - (start_time.hour * 60 + start_time.minute)
        effective_duration = availability_data['slot_duration'] + availability_data['break_duration']
        
        if effective_duration <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid slot duration or break duration"
            )
        
        slots_count = total_minutes // effective_duration
        
        # Create availability record
        availability = ProviderAvailability(
            provider_id=provider_id,
            date=current_date,
            start_time=availability_data['start_time'],
            end_time=availability_data['end_time'],
            timezone=availability_data['timezone'],
            is_recurring=availability_data.get('is_recurring', False),
            recurrence_pattern=availability_data.get('recurrence_pattern'),
            recurrence_end_date=availability_data.get('recurrence_end_date'),
            slot_duration=availability_data['slot_duration'],
            break_duration=availability_data['break_duration'],
            status=AvailabilityStatus.AVAILABLE,
            max_appointments_per_slot=availability_data.get('max_appointments_per_slot', 1),
            appointment_type=availability_data['appointment_type'],
            location=availability_data['location'],
            pricing=availability_data.get('pricing'),
            notes=availability_data.get('notes'),
            special_requirements=availability_data.get('special_requirements')
        )
        
        db.add(availability)
        db.flush()  # Get the ID without committing
        
        # Generate appointment slots
        slots_created = generate_appointment_slots(
            db, availability, slots_count, availability_data['timezone']
        )
        
        created_availabilities.append(availability)
        total_slots_created += slots_created
    
    db.commit()
    
    # Log availability creation
    logger.info(f"Provider {provider_id} created {len(created_availabilities)} availability records with {total_slots_created} slots")
    
    return {
        "availability_id": str(created_availabilities[0].id),
        "slots_created": total_slots_created,
        "date_range": {
            "start": min(dates_to_create).isoformat(),
            "end": max(dates_to_create).isoformat()
        },
        "total_appointments_available": total_slots_created
    }


def generate_appointment_slots(
    db: Session, 
    availability: ProviderAvailability, 
    slots_count: int, 
    timezone_str: str
) -> int:
    """Generate appointment slots for a given availability"""
    
    # Parse timezone
    try:
        tz = pytz.timezone(timezone_str)
    except pytz.exceptions.UnknownTimeZoneError:
        tz = pytz.UTC
    
    # Calculate slot times
    start_time = time.fromisoformat(availability.start_time)
    slot_duration = availability.slot_duration
    break_duration = availability.break_duration
    
    slots_created = 0
    
    for i in range(slots_count):
        # Calculate slot start time
        slot_start_minutes = start_time.hour * 60 + start_time.minute + i * (slot_duration + break_duration)
        slot_start_hour = slot_start_minutes // 60
        slot_start_minute = slot_start_minutes % 60
        
        # Calculate slot end time
        slot_end_minutes = slot_start_minutes + slot_duration
        slot_end_hour = slot_end_minutes // 60
        slot_end_minute = slot_end_minutes % 60
        
        # Create datetime objects with timezone
        slot_start_dt = datetime.combine(availability.date, time(slot_start_hour, slot_start_minute))
        slot_end_dt = datetime.combine(availability.date, time(slot_end_hour, slot_end_minute))
        
        # Localize to timezone
        slot_start_dt = tz.localize(slot_start_dt)
        slot_end_dt = tz.localize(slot_end_dt)
        
        # Convert to UTC for storage
        slot_start_utc = slot_start_dt.astimezone(pytz.UTC)
        slot_end_utc = slot_end_dt.astimezone(pytz.UTC)
        
        # Create appointment slot
        appointment_slot = AppointmentSlot(
            availability_id=availability.id,
            provider_id=availability.provider_id,
            slot_start_time=slot_start_utc,
            slot_end_time=slot_end_utc,
            status=AvailabilityStatus.AVAILABLE,
            appointment_type=availability.appointment_type.value
        )
        
        db.add(appointment_slot)
        slots_created += 1
    
    return slots_created


def get_provider_availability(
    db: Session, 
    provider_id: str, 
    start_date: date, 
    end_date: date,
    status_filter: Optional[str] = None,
    appointment_type: Optional[str] = None,
    timezone: Optional[str] = None
) -> Dict[str, Any]:
    """Get provider availability for a date range"""
    
    # Check if provider exists
    provider = get_provider_by_id(db, provider_id)
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found"
        )
    
    # Build query
    query = db.query(AppointmentSlot).filter(
        AppointmentSlot.provider_id == provider_id,
        AppointmentSlot.slot_start_time >= start_date,
        AppointmentSlot.slot_start_time < end_date + timedelta(days=1)
    )
    
    if status_filter:
        query = query.filter(AppointmentSlot.status == status_filter)
    
    if appointment_type:
        query = query.filter(AppointmentSlot.appointment_type == appointment_type)
    
    slots = query.all()
    
    # Group slots by date
    availability_by_date = {}
    total_slots = len(slots)
    available_slots = 0
    booked_slots = 0
    cancelled_slots = 0
    
    for slot in slots:
        # Convert UTC to local timezone
        local_tz = pytz.timezone(timezone or "UTC")
        slot_start_local = slot.slot_start_time.astimezone(local_tz)
        slot_end_local = slot.slot_end_time.astimezone(local_tz)
        
        date_key = slot_start_local.date().isoformat()
        time_key = slot_start_local.time().strftime("%H:%M")
        
        if date_key not in availability_by_date:
            availability_by_date[date_key] = {"date": date_key, "slots": []}
        
        # Count statuses
        if slot.status == AvailabilityStatus.AVAILABLE:
            available_slots += 1
        elif slot.status == AvailabilityStatus.BOOKED:
            booked_slots += 1
        elif slot.status == AvailabilityStatus.CANCELLED:
            cancelled_slots += 1
        
        # Get availability details
        availability = slot.availability
        
        slot_data = {
            "slot_id": str(slot.id),
            "start_time": time_key,
            "end_time": slot_end_local.time().strftime("%H:%M"),
            "status": slot.status.value,
            "appointment_type": slot.appointment_type,
            "location": availability.location,
            "pricing": availability.pricing,
            "special_requirements": availability.special_requirements
        }
        
        availability_by_date[date_key]["slots"].append(slot_data)
    
    return {
        "provider_id": provider_id,
        "availability_summary": {
            "total_slots": total_slots,
            "available_slots": available_slots,
            "booked_slots": booked_slots,
            "cancelled_slots": cancelled_slots
        },
        "availability": list(availability_by_date.values())
    }


def update_availability_slot(
    db: Session, 
    slot_id: str, 
    update_data: Dict[str, Any]
) -> Optional[AppointmentSlot]:
    """Update a specific availability slot"""
    
    slot = db.query(AppointmentSlot).filter(AppointmentSlot.id == slot_id).first()
    if not slot:
        return None
    
    # Update slot fields
    for field, value in update_data.items():
        if hasattr(slot, field) and value is not None:
            setattr(slot, field, value)
    
    db.commit()
    db.refresh(slot)
    
    logger.info(f"Updated availability slot {slot_id}")
    return slot


def delete_availability_slot(
    db: Session, 
    slot_id: str, 
    delete_recurring: bool = False,
    reason: Optional[str] = None
) -> bool:
    """Delete an availability slot"""
    
    slot = db.query(AppointmentSlot).filter(AppointmentSlot.id == slot_id).first()
    if not slot:
        return False
    
    # Check if slot has bookings
    if slot.status == AvailabilityStatus.BOOKED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete slot with existing bookings"
        )
    
    # Delete recurring instances if requested
    if delete_recurring and slot.availability.is_recurring:
        # Delete all slots from the same availability
        db.query(AppointmentSlot).filter(
            AppointmentSlot.availability_id == slot.availability_id
        ).delete()
        
        # Delete the availability record
        db.query(ProviderAvailability).filter(
            ProviderAvailability.id == slot.availability_id
        ).delete()
    else:
        # Delete only this slot
        db.delete(slot)
    
    db.commit()
    
    logger.info(f"Deleted availability slot {slot_id}, reason: {reason}")
    return True


def search_availability(
    db: Session,
    search_criteria: Dict[str, Any]
) -> Dict[str, Any]:
    """Search for available slots based on criteria"""
    
    # Build base query
    query = db.query(AppointmentSlot).join(ProviderAvailability).join(Provider).filter(
        AppointmentSlot.status == AvailabilityStatus.AVAILABLE,
        Provider.is_active == True
    )
    
    # Apply filters
    if search_criteria.get("date"):
        query = query.filter(AppointmentSlot.slot_start_time >= search_criteria["date"])
        query = query.filter(AppointmentSlot.slot_start_time < search_criteria["date"] + timedelta(days=1))
    
    if search_criteria.get("start_date") and search_criteria.get("end_date"):
        query = query.filter(AppointmentSlot.slot_start_time >= search_criteria["start_date"])
        query = query.filter(AppointmentSlot.slot_start_time < search_criteria["end_date"] + timedelta(days=1))
    
    if search_criteria.get("specialization"):
        query = query.filter(Provider.specialization.ilike(f"%{search_criteria['specialization']}%"))
    
    if search_criteria.get("appointment_type"):
        query = query.filter(AppointmentSlot.appointment_type == search_criteria["appointment_type"])
    
    if search_criteria.get("insurance_accepted") is not None:
        query = query.filter(ProviderAvailability.pricing['insurance_accepted'].astext == str(search_criteria["insurance_accepted"]).lower())
    
    if search_criteria.get("max_price"):
        query = query.filter(ProviderAvailability.pricing['base_fee'].astext.cast(float) <= search_criteria["max_price"])
    
    # Execute query
    slots = query.all()
    
    # Group by provider
    providers = {}
    for slot in slots:
        provider_id = str(slot.provider_id)
        
        if provider_id not in providers:
            provider = slot.provider
            providers[provider_id] = {
                "provider": {
                    "id": str(provider.id),
                    "name": f"Dr. {provider.first_name} {provider.last_name}",
                    "specialization": provider.specialization,
                    "years_of_experience": provider.years_of_experience,
                    "rating": 4.8,  # Placeholder - would come from rating system
                    "clinic_address": f"{provider.clinic_address.get('street', '')}, {provider.clinic_address.get('city', '')}, {provider.clinic_address.get('state', '')}"
                },
                "available_slots": []
            }
        
        # Convert to local timezone
        local_tz = pytz.timezone(search_criteria.get("timezone", "UTC"))
        slot_start_local = slot.slot_start_time.astimezone(local_tz)
        slot_end_local = slot.slot_end_time.astimezone(local_tz)
        
        slot_data = {
            "slot_id": str(slot.id),
            "date": slot_start_local.date().isoformat(),
            "start_time": slot_start_local.time().strftime("%H:%M"),
            "end_time": slot_end_local.time().strftime("%H:%M"),
            "appointment_type": slot.appointment_type,
            "location": slot.availability.location,
            "pricing": slot.availability.pricing,
            "special_requirements": slot.availability.special_requirements
        }
        
        providers[provider_id]["available_slots"].append(slot_data)
    
    return {
        "search_criteria": search_criteria,
        "total_results": len(providers),
        "results": list(providers.values())
    }


# Appointment CRUD operations
def get_appointment_by_id(db: Session, appointment_id: str) -> Optional[Appointment]:
    """Get appointment by ID"""
    return db.query(Appointment).filter(Appointment.id == appointment_id).first()


def get_appointment_by_booking_reference(db: Session, booking_reference: str) -> Optional[Appointment]:
    """Get appointment by booking reference"""
    return db.query(Appointment).filter(Appointment.booking_reference == booking_reference).first()


def get_appointments_by_patient(
    db: Session, 
    patient_id: str, 
    skip: int = 0, 
    limit: int = 100,
    status: Optional[AppointmentStatus] = None
) -> List[Appointment]:
    """Get appointments for a patient"""
    query = db.query(Appointment).filter(Appointment.patient_id == patient_id)
    
    if status:
        query = query.filter(Appointment.status == status)
    
    return query.offset(skip).limit(limit).all()


def get_appointments_by_provider(
    db: Session, 
    provider_id: str, 
    skip: int = 0, 
    limit: int = 100,
    status: Optional[AppointmentStatus] = None
) -> List[Appointment]:
    """Get appointments for a provider"""
    query = db.query(Appointment).filter(Appointment.provider_id == provider_id)
    
    if status:
        query = query.filter(Appointment.status == status)
    
    return query.offset(skip).limit(limit).all()


def create_appointment(
    db: Session, 
    patient_id: str, 
    appointment_data: Dict[str, Any]
) -> Appointment:
    """Create a new appointment booking"""
    
    # Check if patient exists
    patient = get_patient_by_id(db, patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )
    
    # Get the appointment slot
    slot = db.query(AppointmentSlot).filter(AppointmentSlot.id == appointment_data['slot_id']).first()
    if not slot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment slot not found"
        )
    
    # Check if slot is available
    if slot.status != AvailabilityStatus.AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Appointment slot is not available"
        )
    
    # Get provider information
    provider = get_provider_by_id(db, str(slot.provider_id))
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found"
        )
    
    # Get pricing information
    availability = slot.availability
    base_fee = availability.pricing.get('base_fee', 0) if availability.pricing else 0
    currency = availability.pricing.get('currency', 'USD') if availability.pricing else 'USD'
    
    # Calculate payment amounts
    insurance_coverage = appointment_data.get('insurance_coverage', 0)
    patient_payment = appointment_data.get('patient_payment', 0)
    
    # Generate booking reference
    booking_reference = f"APT-{uuid.uuid4().hex[:8].upper()}"
    
    # Create appointment
    appointment = Appointment(
        slot_id=appointment_data['slot_id'],
        provider_id=str(slot.provider_id),
        patient_id=patient_id,
        appointment_type=appointment_data['appointment_type'],
        status=AppointmentStatus.SCHEDULED,
        payment_status=PaymentStatus.PENDING,
        scheduled_start_time=slot.slot_start_time,
        scheduled_end_time=slot.slot_end_time,
        location=availability.location,
        contact_phone=appointment_data.get('contact_phone'),
        contact_email=appointment_data.get('contact_email'),
        symptoms=appointment_data.get('symptoms'),
        base_fee=base_fee,
        insurance_coverage=insurance_coverage,
        patient_payment=patient_payment,
        currency=currency,
        booking_reference=booking_reference
    )
    
    try:
        # Update slot status to booked
        slot.status = AvailabilityStatus.BOOKED
        slot.patient_id = patient_id
        slot.booking_reference = booking_reference
        
        # Update availability current appointments count
        availability.current_appointments += 1
        
        # Add appointment to database
        db.add(appointment)
        db.commit()
        db.refresh(appointment)
        
        # Log appointment creation (HIPAA compliant)
        logger.info(f"Appointment created: {booking_reference} for patient {patient.email}")
        
        return appointment
        
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create appointment"
        )


def update_appointment(
    db: Session, 
    appointment_id: str, 
    update_data: Dict[str, Any]
) -> Optional[Appointment]:
    """Update an appointment"""
    
    appointment = get_appointment_by_id(db, appointment_id)
    if not appointment:
        return None
    
    # Update appointment fields
    for field, value in update_data.items():
        if hasattr(appointment, field) and value is not None:
            setattr(appointment, field, value)
    
    db.commit()
    db.refresh(appointment)
    
    logger.info(f"Updated appointment {appointment_id}")
    return appointment


def cancel_appointment(
    db: Session, 
    appointment_id: str, 
    reason: str,
    cancelled_by: str
) -> Optional[Appointment]:
    """Cancel an appointment"""
    
    appointment = get_appointment_by_id(db, appointment_id)
    if not appointment:
        return None
    
    # Check if appointment can be cancelled
    if appointment.status in [AppointmentStatus.CANCELLED, AppointmentStatus.COMPLETED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Appointment cannot be cancelled"
        )
    
    # Update appointment status
    appointment.status = AppointmentStatus.CANCELLED
    appointment.cancellation_reason = reason
    appointment.cancelled_by = cancelled_by
    appointment.cancelled_at = datetime.utcnow()
    
    # Update slot status back to available
    slot = appointment.slot
    slot.status = AvailabilityStatus.AVAILABLE
    slot.patient_id = None
    slot.booking_reference = None
    
    # Update availability current appointments count
    availability = slot.availability
    availability.current_appointments = max(0, availability.current_appointments - 1)
    
    db.commit()
    db.refresh(appointment)
    
    logger.info(f"Appointment cancelled: {appointment.booking_reference}, reason: {reason}")
    return appointment


def reschedule_appointment(
    db: Session, 
    appointment_id: str, 
    new_slot_id: str,
    reason: Optional[str] = None
) -> Optional[Appointment]:
    """Reschedule an appointment"""
    
    appointment = get_appointment_by_id(db, appointment_id)
    if not appointment:
        return None
    
    # Check if appointment can be rescheduled
    if appointment.status in [AppointmentStatus.CANCELLED, AppointmentStatus.COMPLETED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Appointment cannot be rescheduled"
        )
    
    # Get the new slot
    new_slot = db.query(AppointmentSlot).filter(AppointmentSlot.id == new_slot_id).first()
    if not new_slot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="New appointment slot not found"
        )
    
    # Check if new slot is available
    if new_slot.status != AvailabilityStatus.AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New appointment slot is not available"
        )
    
    # Update old slot status back to available
    old_slot = appointment.slot
    old_slot.status = AvailabilityStatus.AVAILABLE
    old_slot.patient_id = None
    old_slot.booking_reference = None
    
    # Update new slot status to booked
    new_slot.status = AvailabilityStatus.BOOKED
    new_slot.patient_id = appointment.patient_id
    new_slot.booking_reference = appointment.booking_reference
    
    # Update appointment
    appointment.slot_id = new_slot_id
    appointment.scheduled_start_time = new_slot.slot_start_time
    appointment.scheduled_end_time = new_slot.slot_end_time
    appointment.status = AppointmentStatus.RESCHEDULED
    
    db.commit()
    db.refresh(appointment)
    
    logger.info(f"Appointment rescheduled: {appointment.booking_reference}")
    return appointment 