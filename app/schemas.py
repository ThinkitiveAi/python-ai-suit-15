from pydantic import BaseModel, EmailStr, validator, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date, time
import re
from app.models import (
    VerificationStatus, Gender, RecurrencePattern, AvailabilityStatus, 
    AppointmentType, LocationType, AppointmentStatus, PaymentStatus
)


class ClinicAddress(BaseModel):
    street: str = Field(..., max_length=200, description="Street address")
    city: str = Field(..., max_length=100, description="City")
    state: str = Field(..., max_length=50, description="State")
    zip: str = Field(..., description="ZIP code")

    @validator('zip')
    def validate_zip(cls, v):
        # Basic ZIP validation (US format)
        if not re.match(r'^\d{5}(-\d{4})?$', v):
            raise ValueError('Invalid ZIP code format')
        return v


class PatientAddress(BaseModel):
    street: str = Field(..., max_length=200, description="Street address")
    city: str = Field(..., max_length=100, description="City")
    state: str = Field(..., max_length=50, description="State")
    zip: str = Field(..., description="ZIP code")

    @validator('zip')
    def validate_zip(cls, v):
        # Basic ZIP validation (US format)
        if not re.match(r'^\d{5}(-\d{4})?$', v):
            raise ValueError('Invalid ZIP code format')
        return v


class EmergencyContact(BaseModel):
    name: str = Field(..., max_length=100, description="Emergency contact name")
    phone: str = Field(..., description="Emergency contact phone number")
    relationship: str = Field(..., max_length=50, description="Relationship to patient")

    @validator('phone')
    def validate_phone(cls, v):
        """Validate international phone number format"""
        digits_only = re.sub(r'\D', '', v)
        if len(digits_only) < 10 or len(digits_only) > 15:
            raise ValueError('Phone number must be between 10-15 digits')
        return v


class InsuranceInfo(BaseModel):
    provider: str = Field(..., description="Insurance provider name")
    policy_number: str = Field(..., description="Insurance policy number")


# Provider Availability Schemas
class LocationInfo(BaseModel):
    type: LocationType = Field(..., description="Location type")
    address: Optional[str] = Field(None, max_length=500, description="Physical address")
    room_number: Optional[str] = Field(None, max_length=50, description="Room number")

    @validator('address')
    def validate_address_for_physical_location(cls, v, values):
        if values.get('type') in [LocationType.CLINIC, LocationType.HOSPITAL, LocationType.HOME_VISIT] and not v:
            raise ValueError('Address is required for physical locations')
        return v


class PricingInfo(BaseModel):
    base_fee: float = Field(..., ge=0, description="Base consultation fee")
    insurance_accepted: bool = Field(True, description="Whether insurance is accepted")
    currency: str = Field("USD", max_length=3, description="Currency code")

    @validator('currency')
    def validate_currency(cls, v):
        if not re.match(r'^[A-Z]{3}$', v):
            raise ValueError('Currency must be a 3-letter ISO code')
        return v


# Temporarily commented out to fix import issues
# class ProviderAvailabilityCreate(BaseModel):
#     date: date = Field(..., description="Availability date")
#     start_time: str = Field(..., description="Start time in HH:mm format")
#     end_time: str = Field(..., description="End time in HH:mm format")
#     timezone: str = Field(..., description="Timezone (e.g., America/New_York)")
#     slot_duration: int = Field(30, ge=15, le=120, description="Slot duration in minutes")
#     break_duration: int = Field(0, ge=0, le=60, description="Break duration in minutes")
#     is_recurring: bool = Field(False, description="Whether this is a recurring availability")
#     recurrence_pattern: Optional[RecurrencePattern] = Field(None, description="Recurrence pattern")
#     recurrence_end_date: Optional[date] = None
#     appointment_type: AppointmentType = Field(AppointmentType.CONSULTATION, description="Type of appointment")
#     location: LocationInfo = Field(..., description="Location information")
#     pricing: Optional[PricingInfo] = Field(None, description="Pricing information")
#     special_requirements: Optional[List[str]] = Field(None, description="Special requirements")
#     notes: Optional[str] = Field(None, max_length=500, description="Additional notes")
#     max_appointments_per_slot: int = Field(1, ge=1, le=10, description="Maximum appointments per slot")
# 
#     @validator('start_time', 'end_time')
#     def validate_time_format(cls, v):
#         """Validate time format HH:mm"""
#         if not re.match(r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$', v):
#             raise ValueError('Time must be in HH:mm format (24-hour)')
#         return v
# 
#     @validator('end_time')
#     def validate_end_time_after_start_time(cls, v, values):
#         """Validate end time is after start time"""
#         if 'start_time' in values:
#             start_time = time.fromisoformat(values['start_time'])
#             end_time = time.fromisoformat(v)
#             if end_time <= start_time:
#                 raise ValueError('End time must be after start time')
#         return v
# 
#     @validator('recurrence_end_date')
#     def validate_recurrence_end_date(cls, v, values):
#         """Validate recurrence end date is after start date"""
#         if v and 'date' in values:
#             if v <= values['date']:
#                 raise ValueError('Recurrence end date must be after start date')
#         return v
# 
#     @validator('timezone')
#     def validate_timezone(cls, v):
#         """Basic timezone validation"""
#         valid_timezones = [
#             'America/New_York', 'America/Chicago', 'America/Denver', 'America/Los_Angeles',
#             'Europe/London', 'Europe/Paris', 'Asia/Tokyo', 'Australia/Sydney',
#             'UTC', 'GMT'
#         ]
#         if v not in valid_timezones:
#             # Allow other timezones but log warning
#             pass
#         return v


class ProviderAvailabilityUpdate(BaseModel):
    start_time: Optional[str] = Field(None, description="Start time in HH:mm format")
    end_time: Optional[str] = Field(None, description="End time in HH:mm format")
    status: Optional[AvailabilityStatus] = Field(None, description="Availability status")
    notes: Optional[str] = Field(None, max_length=500, description="Additional notes")
    pricing: Optional[PricingInfo] = Field(None, description="Pricing information")
    special_requirements: Optional[List[str]] = Field(None, description="Special requirements")

    @validator('start_time', 'end_time')
    def validate_time_format(cls, v):
        """Validate time format HH:mm"""
        if v and not re.match(r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$', v):
            raise ValueError('Time must be in HH:mm format (24-hour)')
        return v


class AvailabilitySlotResponse(BaseModel):
    slot_id: str
    start_time: str
    end_time: str
    status: AvailabilityStatus
    appointment_type: AppointmentType
    location: LocationInfo
    pricing: Optional[PricingInfo]
    special_requirements: Optional[List[str]]


class DayAvailabilityResponse(BaseModel):
    date: str
    slots: List[AvailabilitySlotResponse]


class ProviderAvailabilityResponse(BaseModel):
    provider_id: str
    availability_summary: Dict[str, int]
    availability: List[DayAvailabilityResponse]


class AvailabilitySearchRequest(BaseModel):
    date: Optional[date] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    specialization: Optional[str] = None
    location: Optional[str] = None
    appointment_type: Optional[AppointmentType] = None
    insurance_accepted: Optional[bool] = None
    max_price: Optional[float] = None
    timezone: Optional[str] = None
    available_only: bool = Field(True, description="Show only available slots")

    @validator('end_date')
    def validate_date_range(cls, v, values):
        """Validate date range"""
        if v and 'start_date' in values and values['start_date']:
            if v <= values['start_date']:
                raise ValueError('End date must be after start date')
        return v


class ProviderSearchInfo(BaseModel):
    id: str
    name: str
    specialization: str
    years_of_experience: Optional[int]
    rating: Optional[float]
    clinic_address: str


class SearchResultSlot(BaseModel):
    slot_id: str
    date: str
    start_time: str
    end_time: str
    appointment_type: AppointmentType
    location: LocationInfo
    pricing: Optional[PricingInfo]
    special_requirements: Optional[List[str]]


class ProviderSearchResult(BaseModel):
    provider: ProviderSearchInfo
    available_slots: List[SearchResultSlot]


class AvailabilitySearchResponse(BaseModel):
    search_criteria: Dict[str, Any]
    total_results: int
    results: List[ProviderSearchResult]


class AvailabilityCreateResponse(BaseModel):
    success: bool = True
    message: str = "Availability slots created successfully"
    data: Dict[str, Any]


class AvailabilityResponse(BaseModel):
    success: bool = True
    data: ProviderAvailabilityResponse


class AvailabilitySearchResponseWrapper(BaseModel):
    success: bool = True
    data: AvailabilitySearchResponse


# Appointment Schemas
class AppointmentCreate(BaseModel):
    slot_id: str = Field(..., description="ID of the appointment slot to book")
    appointment_type: AppointmentType = Field(..., description="Type of appointment")
    symptoms: Optional[str] = Field(None, max_length=1000, description="Patient symptoms")
    contact_phone: Optional[str] = Field(None, description="Contact phone number")
    contact_email: Optional[str] = Field(None, description="Contact email")
    insurance_coverage: Optional[float] = Field(0, ge=0, description="Insurance coverage amount")
    patient_payment: Optional[float] = Field(0, ge=0, description="Patient payment amount")

    @validator('contact_phone')
    def validate_contact_phone(cls, v):
        """Validate phone number format"""
        if v:
            digits_only = re.sub(r'\D', '', v)
            if len(digits_only) < 10 or len(digits_only) > 15:
                raise ValueError('Phone number must be between 10-15 digits')
        return v

    @validator('contact_email')
    def validate_contact_email(cls, v):
        """Validate email format"""
        if v and not re.match(r'^[^@]+@[^@]+\.[^@]+$', v):
            raise ValueError('Invalid email format')
        return v


class AppointmentUpdate(BaseModel):
    status: Optional[AppointmentStatus] = Field(None, description="Appointment status")
    payment_status: Optional[PaymentStatus] = Field(None, description="Payment status")
    symptoms: Optional[str] = Field(None, max_length=1000, description="Patient symptoms")
    medical_notes: Optional[str] = Field(None, max_length=2000, description="Medical notes")
    prescription: Optional[str] = Field(None, max_length=2000, description="Prescription")
    follow_up_required: Optional[bool] = Field(None, description="Whether follow-up is required")
    follow_up_date: Optional[date] = Field(None, description="Follow-up date")
    actual_start_time: Optional[datetime] = Field(None, description="Actual start time")
    actual_end_time: Optional[datetime] = Field(None, description="Actual end time")
    cancellation_reason: Optional[str] = Field(None, max_length=500, description="Cancellation reason")


class AppointmentResponse(BaseModel):
    id: str
    slot_id: str
    provider_id: str
    patient_id: str
    appointment_type: AppointmentType
    status: AppointmentStatus
    payment_status: PaymentStatus
    scheduled_start_time: datetime
    scheduled_end_time: datetime
    actual_start_time: Optional[datetime]
    actual_end_time: Optional[datetime]
    location: Dict[str, Any]
    contact_phone: Optional[str]
    contact_email: Optional[str]
    symptoms: Optional[str]
    medical_notes: Optional[str]
    prescription: Optional[str]
    follow_up_required: bool
    follow_up_date: Optional[date]
    base_fee: float
    insurance_coverage: float
    patient_payment: float
    currency: str
    booking_reference: str
    cancellation_reason: Optional[str]
    cancelled_by: Optional[str]
    cancelled_at: Optional[datetime]
    reminder_sent: bool
    reminder_sent_at: Optional[datetime]
    confirmation_sent: bool
    confirmation_sent_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AppointmentListResponse(BaseModel):
    success: bool = True
    data: List[AppointmentResponse]


class AppointmentDetailResponse(BaseModel):
    success: bool = True
    data: AppointmentResponse


class AppointmentCreateResponse(BaseModel):
    success: bool = True
    message: str = "Appointment booked successfully"
    data: AppointmentResponse


class AppointmentCancelRequest(BaseModel):
    reason: str = Field(..., max_length=500, description="Cancellation reason")


class AppointmentCancelResponse(BaseModel):
    success: bool = True
    message: str = "Appointment cancelled successfully"
    data: Dict[str, Any]


class AppointmentRescheduleRequest(BaseModel):
    new_slot_id: str = Field(..., description="ID of the new appointment slot")
    reason: Optional[str] = Field(None, max_length=500, description="Reschedule reason")


class AppointmentRescheduleResponse(BaseModel):
    success: bool = True
    message: str = "Appointment rescheduled successfully"
    data: AppointmentResponse


# Existing schemas
class ProviderCreate(BaseModel):
    first_name: str = Field(..., min_length=2, max_length=50, description="First name")
    last_name: str = Field(..., min_length=2, max_length=50, description="Last name")
    email: EmailStr = Field(..., description="Email address")
    phone_number: str = Field(..., description="Phone number in international format")
    password: str = Field(..., min_length=8, description="Password")
    specialization: str = Field(..., min_length=3, max_length=100, description="Medical specialization")
    license_number: str = Field(..., description="Medical license number")
    years_of_experience: Optional[int] = Field(None, ge=0, le=50, description="Years of experience")
    clinic_address: ClinicAddress

    @validator('password')
    def validate_password(cls, v):
        """Validate password complexity requirements"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one number')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        return v

    @validator('phone_number')
    def validate_phone(cls, v):
        """Validate international phone number format"""
        # Remove all non-digit characters for validation
        digits_only = re.sub(r'\D', '', v)
        if len(digits_only) < 10 or len(digits_only) > 15:
            raise ValueError('Phone number must be between 10-15 digits')
        return v

    @validator('license_number')
    def validate_license(cls, v):
        """Validate license number format (alphanumeric)"""
        if not re.match(r'^[A-Za-z0-9]+$', v):
            raise ValueError('License number must be alphanumeric')
        return v


class PatientCreate(BaseModel):
    first_name: str = Field(..., min_length=2, max_length=50, description="First name")
    last_name: str = Field(..., min_length=2, max_length=50, description="Last name")
    email: EmailStr = Field(..., description="Email address")
    phone_number: str = Field(..., description="Phone number in international format")
    password: str = Field(..., min_length=8, description="Password")
    confirm_password: str = Field(..., description="Password confirmation")
    date_of_birth: date = Field(..., description="Date of birth")
    gender: Gender = Field(..., description="Gender")
    address: PatientAddress = Field(..., description="Patient address")
    emergency_contact: Optional[EmergencyContact] = Field(None, description="Emergency contact information")
    medical_history: Optional[List[str]] = Field(None, description="Medical history")
    insurance_info: Optional[InsuranceInfo] = Field(None, description="Insurance information")

    @validator('password')
    def validate_password(cls, v):
        """Validate password complexity requirements"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one number')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        return v

    @validator('confirm_password')
    def validate_confirm_password(cls, v, values):
        """Validate password confirmation matches"""
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v

    @validator('phone_number')
    def validate_phone(cls, v):
        """Validate international phone number format"""
        digits_only = re.sub(r'\D', '', v)
        if len(digits_only) < 10 or len(digits_only) > 15:
            raise ValueError('Phone number must be between 10-15 digits')
        return v

    @validator('date_of_birth')
    def validate_date_of_birth(cls, v):
        """Validate date of birth (must be in past and COPPA compliant)"""
        from datetime import date
        today = date.today()
        
        # Check if date is in the past
        if v >= today:
            raise ValueError('Date of birth must be in the past')
        
        # Calculate age for COPPA compliance (must be at least 13 years old)
        age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
        if age < 13:
            raise ValueError('Must be at least 13 years old for COPPA compliance')
        
        return v


class ProviderResponse(BaseModel):
    id: str
    first_name: str
    last_name: str
    email: str
    phone_number: str
    specialization: str
    license_number: str
    years_of_experience: Optional[int]
    clinic_address: ClinicAddress
    verification_status: VerificationStatus
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PatientResponse(BaseModel):
    id: str
    first_name: str
    last_name: str
    email: str
    phone_number: str
    date_of_birth: date
    gender: Gender
    address: PatientAddress
    emergency_contact: Optional[EmergencyContact]
    medical_history: Optional[List[str]]
    insurance_info: Optional[InsuranceInfo]
    email_verified: bool
    phone_verified: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PatientRegistrationResponse(BaseModel):
    success: bool = True
    message: str = "Patient registered successfully. Verification email sent."
    data: dict


class PatientLogin(BaseModel):
    email: EmailStr = Field(..., description="Patient's email address")
    password: str = Field(..., min_length=1, description="Patient's password")


class ProviderLogin(BaseModel):
    email: EmailStr = Field(..., description="Provider's email address")
    password: str = Field(..., min_length=1, description="Provider's password")


class LoginResponse(BaseModel):
    success: bool = True
    message: str = "Login successful"
    data: dict


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


class ValidationErrorResponse(BaseModel):
    success: bool = False
    message: str = "Validation failed"
    errors: dict 