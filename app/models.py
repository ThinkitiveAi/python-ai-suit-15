from sqlalchemy import Column, String, Integer, Boolean, DateTime, Enum, Date, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
import uuid
import os
from app.database import Base


class VerificationStatus(str, enum.Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


class Gender(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"


class RecurrencePattern(str, enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class AvailabilityStatus(str, enum.Enum):
    AVAILABLE = "available"
    BOOKED = "booked"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"
    MAINTENANCE = "maintenance"


class AppointmentType(str, enum.Enum):
    CONSULTATION = "consultation"
    FOLLOW_UP = "follow_up"
    EMERGENCY = "emergency"
    TELEMEDICINE = "telemedicine"


class LocationType(str, enum.Enum):
    CLINIC = "clinic"
    HOSPITAL = "hospital"
    TELEMEDICINE = "telemedicine"
    HOME_VISIT = "home_visit"


class AppointmentStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"
    RESCHEDULED = "rescheduled"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    PARTIAL = "partial"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


# Helper function to determine UUID type based on database
def get_uuid_type():
    """Return appropriate UUID type based on database"""
    database_url = os.getenv("DATABASE_URL", "")
    if "sqlite" in database_url.lower():
        return String(36)  # SQLite doesn't support UUID natively
    else:
        return UUID(as_uuid=True)  # PostgreSQL supports UUID


class Provider(Base):
    __tablename__ = "providers"

    id = Column(get_uuid_type(), primary_key=True, default=uuid.uuid4)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone_number = Column(String(20), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    specialization = Column(String(100), nullable=False)
    license_number = Column(String(50), unique=True, nullable=False, index=True)
    years_of_experience = Column(Integer, nullable=True)
    clinic_address = Column(JSON, nullable=False)
    verification_status = Column(
        Enum(VerificationStatus), 
        default=VerificationStatus.PENDING, 
        nullable=False
    )
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Patient(Base):
    __tablename__ = "patients"

    id = Column(get_uuid_type(), primary_key=True, default=uuid.uuid4)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone_number = Column(String(20), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    date_of_birth = Column(Date, nullable=False)
    gender = Column(Enum(Gender), nullable=False)
    address = Column(JSON, nullable=False)
    emergency_contact = Column(JSON, nullable=True)
    medical_history = Column(JSON, nullable=True)  # Array of strings
    insurance_info = Column(JSON, nullable=True)
    email_verified = Column(Boolean, default=False, nullable=False)
    phone_verified = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ProviderAvailability(Base):
    __tablename__ = "provider_availability"

    id = Column(get_uuid_type(), primary_key=True, default=uuid.uuid4)
    provider_id = Column(get_uuid_type(), ForeignKey("providers.id"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    start_time = Column(String(5), nullable=False)  # HH:mm format
    end_time = Column(String(5), nullable=False)  # HH:mm format
    timezone = Column(String(50), nullable=False)
    is_recurring = Column(Boolean, default=False, nullable=False)
    recurrence_pattern = Column(Enum(RecurrencePattern), nullable=True)
    recurrence_end_date = Column(Date, nullable=True)
    slot_duration = Column(Integer, default=30, nullable=False)  # minutes
    break_duration = Column(Integer, default=0, nullable=False)  # minutes
    status = Column(Enum(AvailabilityStatus), default=AvailabilityStatus.AVAILABLE, nullable=False)
    max_appointments_per_slot = Column(Integer, default=1, nullable=False)
    current_appointments = Column(Integer, default=0, nullable=False)
    appointment_type = Column(Enum(AppointmentType), default=AppointmentType.CONSULTATION, nullable=False)
    location = Column(JSON, nullable=False)
    pricing = Column(JSON, nullable=True)
    notes = Column(Text, nullable=True)
    special_requirements = Column(JSON, nullable=True)  # Array of strings
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    provider = relationship("Provider", backref="availability")
    appointment_slots = relationship("AppointmentSlot", back_populates="availability", cascade="all, delete-orphan")


class AppointmentSlot(Base):
    __tablename__ = "appointment_slots"

    id = Column(get_uuid_type(), primary_key=True, default=uuid.uuid4)
    availability_id = Column(get_uuid_type(), ForeignKey("provider_availability.id"), nullable=False, index=True)
    provider_id = Column(get_uuid_type(), ForeignKey("providers.id"), nullable=False, index=True)
    slot_start_time = Column(DateTime(timezone=True), nullable=False, index=True)
    slot_end_time = Column(DateTime(timezone=True), nullable=False, index=True)
    status = Column(Enum(AvailabilityStatus), default=AvailabilityStatus.AVAILABLE, nullable=False)
    patient_id = Column(get_uuid_type(), ForeignKey("patients.id"), nullable=True, index=True)
    appointment_type = Column(String(50), nullable=False)
    booking_reference = Column(String(100), unique=True, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    availability = relationship("ProviderAvailability", back_populates="appointment_slots")
    provider = relationship("Provider")
    patient = relationship("Patient")
    appointments = relationship("Appointment", back_populates="slot")


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(get_uuid_type(), primary_key=True, default=uuid.uuid4)
    slot_id = Column(get_uuid_type(), ForeignKey("appointment_slots.id"), nullable=False, index=True)
    provider_id = Column(get_uuid_type(), ForeignKey("providers.id"), nullable=False, index=True)
    patient_id = Column(get_uuid_type(), ForeignKey("patients.id"), nullable=False, index=True)
    appointment_type = Column(Enum(AppointmentType), nullable=False)
    status = Column(Enum(AppointmentStatus), default=AppointmentStatus.SCHEDULED, nullable=False)
    payment_status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)
    
    # Appointment details
    scheduled_start_time = Column(DateTime(timezone=True), nullable=False, index=True)
    scheduled_end_time = Column(DateTime(timezone=True), nullable=False, index=True)
    actual_start_time = Column(DateTime(timezone=True), nullable=True)
    actual_end_time = Column(DateTime(timezone=True), nullable=True)
    
    # Location and contact info
    location = Column(JSON, nullable=False)  # Location details
    contact_phone = Column(String(20), nullable=True)
    contact_email = Column(String(255), nullable=True)
    
    # Medical information
    symptoms = Column(Text, nullable=True)
    medical_notes = Column(Text, nullable=True)
    prescription = Column(Text, nullable=True)
    follow_up_required = Column(Boolean, default=False, nullable=False)
    follow_up_date = Column(Date, nullable=True)
    
    # Financial information
    base_fee = Column(Numeric(10, 2), nullable=False)
    insurance_coverage = Column(Numeric(10, 2), default=0, nullable=False)
    patient_payment = Column(Numeric(10, 2), default=0, nullable=False)
    currency = Column(String(3), default="USD", nullable=False)
    
    # Booking and cancellation
    booking_reference = Column(String(100), unique=True, nullable=False, index=True)
    cancellation_reason = Column(Text, nullable=True)
    cancelled_by = Column(String(50), nullable=True)  # "patient", "provider", "admin"
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    
    # Notifications
    reminder_sent = Column(Boolean, default=False, nullable=False)
    reminder_sent_at = Column(DateTime(timezone=True), nullable=True)
    confirmation_sent = Column(Boolean, default=False, nullable=False)
    confirmation_sent_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    slot = relationship("AppointmentSlot", back_populates="appointments")
    provider = relationship("Provider")
    patient = relationship("Patient") 