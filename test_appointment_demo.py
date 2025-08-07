#!/usr/bin/env python3
"""
Appointment Management Demo Script

This script demonstrates the complete appointment booking workflow:
1. Register a provider and create availability
2. Register a patient
3. Search for available slots
4. Book an appointment
5. Manage appointments (view, update, cancel, reschedule)
"""

import requests
import json
import time
from datetime import datetime, date, timedelta
from typing import Dict, Any

# Configuration
BASE_URL = "http://localhost:8001"
API_PREFIX = "/api/v1"

def print_response(response: requests.Response, title: str):
    """Print formatted response"""
    print(f"\n{'='*50}")
    print(f"{title}")
    print(f"{'='*50}")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print(f"{'='*50}\n")

def test_provider_registration_and_login() -> str:
    """Register a provider and login to get JWT token"""
    print("🔧 Registering provider...")
    
    provider_data = {
        "first_name": "Dr. Sarah",
        "last_name": "Johnson",
        "email": "sarah.johnson@clinic.com",
        "phone_number": "+1234567890",
        "password": "SecurePass123!",
        "specialization": "Cardiology",
        "license_number": "MD789012",
        "years_of_experience": 15,
        "clinic_address": {
            "street": "456 Medical Center Blvd",
            "city": "Boston",
            "state": "MA",
            "zip": "02108"
        }
    }
    
    response = requests.post(f"{BASE_URL}{API_PREFIX}/auth/register", json=provider_data)
    print_response(response, "Provider Registration")
    
    if response.status_code != 201:
        print("❌ Provider registration failed")
        return None
    
    # Login to get JWT token
    print("🔑 Logging in provider...")
    login_data = {
        "email": "sarah.johnson@clinic.com",
        "password": "SecurePass123!"
    }
    
    response = requests.post(f"{BASE_URL}{API_PREFIX}/provider/login", json=login_data)
    print_response(response, "Provider Login")
    
    if response.status_code != 200:
        print("❌ Provider login failed")
        return None
    
    token = response.json()["data"]["access_token"]
    print(f"✅ Provider logged in successfully. Token: {token[:20]}...")
    return token

def test_availability_creation(provider_token: str) -> Dict[str, Any]:
    """Create availability slots for the provider"""
    print("📅 Creating provider availability...")
    
    availability_data = {
        "date": (date.today() + timedelta(days=7)).isoformat(),  # Next week
        "start_time": "09:00",
        "end_time": "17:00",
        "timezone": "America/New_York",
        "slot_duration": 30,
        "break_duration": 15,
        "is_recurring": True,
        "recurrence_pattern": "weekly",
        "recurrence_end_date": (date.today() + timedelta(weeks=4)).isoformat(),
        "appointment_type": "consultation",
        "location": {
            "type": "clinic",
            "address": "456 Medical Center Blvd, Boston, MA 02108",
            "room_number": "Room 301"
        },
        "pricing": {
            "base_fee": 200.00,
            "insurance_accepted": True,
            "currency": "USD"
        },
        "special_requirements": ["bring_insurance_card", "fasting_required"],
        "notes": "Cardiology consultation slots"
    }
    
    headers = {"Authorization": f"Bearer {provider_token}"}
    response = requests.post(f"{BASE_URL}{API_PREFIX}/provider/availability", json=availability_data, headers=headers)
    print_response(response, "Availability Creation")
    
    if response.status_code != 201:
        print("❌ Availability creation failed")
        return None
    
    return response.json()["data"]

def test_patient_registration_and_login() -> str:
    """Register a patient and login to get JWT token"""
    print("👤 Registering patient...")
    
    patient_data = {
        "first_name": "John",
        "last_name": "Smith",
        "email": "john.smith@email.com",
        "phone_number": "+1987654321",
        "password": "SecurePass123!",
        "confirm_password": "SecurePass123!",
        "date_of_birth": "1985-06-15",
        "gender": "male",
        "address": {
            "street": "123 Main Street",
            "city": "Boston",
            "state": "MA",
            "zip": "02101"
        },
        "emergency_contact": {
            "name": "Jane Smith",
            "phone": "+1987654322",
            "relationship": "spouse"
        },
        "insurance_info": {
            "provider": "Blue Cross Blue Shield",
            "policy_number": "BCBS123456789"
        }
    }
    
    response = requests.post(f"{BASE_URL}{API_PREFIX}/patient/register", json=patient_data)
    print_response(response, "Patient Registration")
    
    if response.status_code != 201:
        print("❌ Patient registration failed")
        return None
    
    # Login to get JWT token
    print("🔑 Logging in patient...")
    login_data = {
        "email": "john.smith@email.com",
        "password": "SecurePass123!"
    }
    
    response = requests.post(f"{BASE_URL}{API_PREFIX}/patient/login", json=login_data)
    print_response(response, "Patient Login")
    
    if response.status_code != 200:
        print("❌ Patient login failed")
        return None
    
    token = response.json()["data"]["access_token"]
    print(f"✅ Patient logged in successfully. Token: {token[:20]}...")
    return token

def test_availability_search() -> Dict[str, Any]:
    """Search for available appointment slots"""
    print("🔍 Searching for available slots...")
    
    search_params = {
        "date": (date.today() + timedelta(days=7)).isoformat(),
        "specialization": "cardiology",
        "appointment_type": "consultation",
        "insurance_accepted": True,
        "max_price": 250,
        "timezone": "America/New_York"
    }
    
    response = requests.get(f"{BASE_URL}{API_PREFIX}/provider/availability/search", params=search_params)
    print_response(response, "Availability Search")
    
    if response.status_code != 200:
        print("❌ Availability search failed")
        return None
    
    return response.json()["data"]

def test_appointment_booking(patient_token: str, slot_id: str) -> Dict[str, Any]:
    """Book an appointment"""
    print("📋 Booking appointment...")
    
    appointment_data = {
        "slot_id": slot_id,
        "appointment_type": "consultation",
        "symptoms": "Chest pain and shortness of breath",
        "contact_phone": "+1987654321",
        "contact_email": "john.smith@email.com",
        "insurance_coverage": 150.00,
        "patient_payment": 50.00
    }
    
    headers = {"Authorization": f"Bearer {patient_token}"}
    response = requests.post(f"{BASE_URL}{API_PREFIX}/appointments", json=appointment_data, headers=headers)
    print_response(response, "Appointment Booking")
    
    if response.status_code != 201:
        print("❌ Appointment booking failed")
        return None
    
    return response.json()["data"]

def test_appointment_management(patient_token: str, appointment_id: str):
    """Test appointment management operations"""
    headers = {"Authorization": f"Bearer {patient_token}"}
    
    # Get appointment details
    print("📖 Getting appointment details...")
    response = requests.get(f"{BASE_URL}{API_PREFIX}/appointments/{appointment_id}", headers=headers)
    print_response(response, "Get Appointment Details")
    
    # Update appointment details
    print("✏️ Updating appointment details...")
    update_data = {
        "symptoms": "Chest pain, shortness of breath, and fatigue"
    }
    response = requests.put(f"{BASE_URL}{API_PREFIX}/appointments/{appointment_id}", json=update_data, headers=headers)
    print_response(response, "Update Appointment Details")
    
    # Get all patient appointments
    print("📋 Getting all patient appointments...")
    response = requests.get(f"{BASE_URL}{API_PREFIX}/appointments", headers=headers)
    print_response(response, "Get All Patient Appointments")

def test_provider_appointment_management(provider_token: str):
    """Test provider appointment management operations"""
    headers = {"Authorization": f"Bearer {provider_token}"}
    
    # Get provider appointments
    print("👨‍⚕️ Getting provider appointments...")
    response = requests.get(f"{BASE_URL}{API_PREFIX}/provider/appointments", headers=headers)
    print_response(response, "Get Provider Appointments")
    
    if response.status_code == 200 and response.json()["data"]:
        appointment_id = response.json()["data"][0]["id"]
        
        # Update appointment status
        print("✏️ Updating appointment status...")
        update_data = {
            "status": "confirmed",
            "medical_notes": "Patient scheduled for cardiology consultation"
        }
        response = requests.put(f"{BASE_URL}{API_PREFIX}/provider/appointments/{appointment_id}", json=update_data, headers=headers)
        print_response(response, "Update Appointment Status")

def test_appointment_cancellation(patient_token: str, appointment_id: str):
    """Test appointment cancellation"""
    print("❌ Cancelling appointment...")
    
    cancel_data = {
        "reason": "Schedule conflict - need to reschedule"
    }
    
    headers = {"Authorization": f"Bearer {patient_token}"}
    response = requests.post(f"{BASE_URL}{API_PREFIX}/appointments/{appointment_id}/cancel", json=cancel_data, headers=headers)
    print_response(response, "Cancel Appointment")

def test_public_appointment_lookup(booking_reference: str):
    """Test public appointment lookup by booking reference"""
    print("🔍 Looking up appointment by booking reference...")
    
    response = requests.get(f"{BASE_URL}{API_PREFIX}/public/appointments/{booking_reference}")
    print_response(response, "Public Appointment Lookup")

def main():
    """Main demo execution"""
    print("🏥 Healthcare Appointment Management Demo")
    print("=" * 60)
    
    try:
        # Step 1: Provider registration and login
        provider_token = test_provider_registration_and_login()
        if not provider_token:
            print("❌ Demo failed at provider registration")
            return
        
        # Step 2: Create availability
        availability_result = test_availability_creation(provider_token)
        if not availability_result:
            print("❌ Demo failed at availability creation")
            return
        
        # Step 3: Patient registration and login
        patient_token = test_patient_registration_and_login()
        if not patient_token:
            print("❌ Demo failed at patient registration")
            return
        
        # Step 4: Search for available slots
        search_result = test_availability_search()
        if not search_result or not search_result["results"]:
            print("❌ Demo failed at availability search")
            return
        
        # Get first available slot
        first_provider = search_result["results"][0]
        if not first_provider["available_slots"]:
            print("❌ No available slots found")
            return
        
        slot_id = first_provider["available_slots"][0]["slot_id"]
        print(f"✅ Found available slot: {slot_id}")
        
        # Step 5: Book appointment
        appointment_result = test_appointment_booking(patient_token, slot_id)
        if not appointment_result:
            print("❌ Demo failed at appointment booking")
            return
        
        appointment_id = appointment_result["id"]
        booking_reference = appointment_result["booking_reference"]
        
        # Step 6: Test appointment management
        test_appointment_management(patient_token, appointment_id)
        
        # Step 7: Test provider appointment management
        test_provider_appointment_management(provider_token)
        
        # Step 8: Test public appointment lookup
        test_public_appointment_lookup(booking_reference)
        
        # Step 9: Test appointment cancellation
        test_appointment_cancellation(patient_token, appointment_id)
        
        print("🎉 Demo completed successfully!")
        print("\n📊 Summary:")
        print(f"   • Provider registered and logged in")
        print(f"   • Availability created with {availability_result['slots_created']} slots")
        print(f"   • Patient registered and logged in")
        print(f"   • Appointment booked: {booking_reference}")
        print(f"   • All management operations tested")
        
    except Exception as e:
        print(f"❌ Demo failed with error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 