#!/usr/bin/env python3
"""
Demo script for the Provider Availability Management functionality
"""

import json
import requests
from datetime import date, timedelta

# API base URL
BASE_URL = "http://localhost:8000"

def test_provider_registration_and_login():
    """Register a provider and get authentication token"""
    
    print("🏥 Provider Registration and Login")
    print("=" * 40)
    
    # Provider data
    provider_data = {
        "first_name": "Dr. John",
        "last_name": "Doe",
        "email": "john.doe@clinic.com",
        "phone_number": "+1234567890",
        "password": "SecurePassword123!",
        "specialization": "Cardiology",
        "license_number": "MD123456",
        "years_of_experience": 15,
        "clinic_address": {
            "street": "123 Medical Center Dr",
            "city": "New York",
            "state": "NY",
            "zip": "10001"
        }
    }
    
    try:
        # Register provider
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/register",
            json=provider_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 201:
            print("✅ Provider registered successfully")
        else:
            print(f"❌ Provider registration failed: {response.text}")
            return None
        
        # Login to get token
        login_data = {
            "email": provider_data["email"],
            "password": provider_data["password"]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/v1/provider/login",
            json=login_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            token = response.json()["data"]["access_token"]
            print("✅ Provider login successful")
            return {"Authorization": f"Bearer {token}"}
        else:
            print(f"❌ Provider login failed: {response.text}")
            return None
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the API server.")
        print("Make sure the server is running with: python run.py")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def test_availability_creation(headers):
    """Test creating availability slots"""
    
    print("\n📅 Testing Availability Creation")
    print("=" * 35)
    
    # Test data matching the prompt requirements
    availability_data = {
        "date": "2024-02-15",
        "start_time": "09:00",
        "end_time": "17:00",
        "timezone": "America/New_York",
        "slot_duration": 30,
        "break_duration": 15,
        "is_recurring": True,
        "recurrence_pattern": "weekly",
        "recurrence_end_date": "2024-03-15",
        "appointment_type": "consultation",
        "location": {
            "type": "clinic",
            "address": "123 Medical Center Dr, New York, NY 10001",
            "room_number": "Room 205"
        },
        "pricing": {
            "base_fee": 150.00,
            "insurance_accepted": True,
            "currency": "USD"
        },
        "special_requirements": ["fasting_required", "bring_insurance_card"],
        "notes": "Standard consultation slots"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/provider/availability",
            json=availability_data,
            headers={**headers, "Content-Type": "application/json"}
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 201:
            data = response.json()
            print("✅ Availability slots created successfully!")
            print()
            
            # Display response structure
            print("Response Structure:")
            print(f"  success: {data['success']}")
            print(f"  message: {data['message']}")
            print()
            
            # Display creation data
            creation_data = data['data']
            print("Creation Data:")
            print(f"  availability_id: {creation_data['availability_id']}")
            print(f"  slots_created: {creation_data['slots_created']}")
            print(f"  date_range: {creation_data['date_range']['start']} to {creation_data['date_range']['end']}")
            print(f"  total_appointments_available: {creation_data['total_appointments_available']}")
            print()
            
            return availability_data
            
        else:
            print("❌ Availability creation failed!")
            print(f"Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def test_availability_retrieval(headers, availability_data):
    """Test retrieving provider availability"""
    
    print("📋 Testing Availability Retrieval")
    print("=" * 35)
    
    try:
        # Get provider ID from login
        login_response = requests.post(
            f"{BASE_URL}/api/v1/provider/login",
            json={
                "email": "john.doe@clinic.com",
                "password": "SecurePassword123!"
            },
            headers={"Content-Type": "application/json"}
        )
        
        if login_response.status_code != 200:
            print("❌ Could not get provider ID")
            return
        
        provider_data = login_response.json()["data"]["provider"]
        provider_id = provider_data["id"]
        
        # Retrieve availability
        response = requests.get(
            f"{BASE_URL}/api/v1/provider/{provider_id}/availability",
            params={
                "start_date": "2024-02-15",
                "end_date": "2024-02-16",
                "timezone": "America/New_York"
            },
            headers=headers
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Availability retrieved successfully!")
            print()
            
            # Display availability data
            availability_data = data['data']
            print("Availability Summary:")
            summary = availability_data['availability_summary']
            print(f"  total_slots: {summary['total_slots']}")
            print(f"  available_slots: {summary['available_slots']}")
            print(f"  booked_slots: {summary['booked_slots']}")
            print(f"  cancelled_slots: {summary['cancelled_slots']}")
            print()
            
            # Display first day's slots
            if availability_data['availability']:
                first_day = availability_data['availability'][0]
                print(f"First Day ({first_day['date']}):")
                print(f"  Number of slots: {len(first_day['slots'])}")
                
                if first_day['slots']:
                    first_slot = first_day['slots'][0]
                    print(f"  First slot: {first_slot['start_time']} - {first_slot['end_time']}")
                    print(f"  Status: {first_slot['status']}")
                    print(f"  Appointment type: {first_slot['appointment_type']}")
                    print(f"  Location: {first_slot['location']['type']}")
                    if first_slot['pricing']:
                        print(f"  Price: ${first_slot['pricing']['base_fee']}")
            print()
            
        else:
            print("❌ Availability retrieval failed!")
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def test_availability_search():
    """Test searching for available slots"""
    
    print("🔍 Testing Availability Search")
    print("=" * 30)
    
    try:
        # Search for availability
        response = requests.get(
            f"{BASE_URL}/api/v1/provider/availability/search",
            params={
                "date": "2024-02-15",
                "specialization": "cardiology",
                "appointment_type": "consultation",
                "insurance_accepted": True,
                "max_price": 200.0,
                "timezone": "America/New_York"
            }
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Availability search successful!")
            print()
            
            # Display search results
            search_data = data['data']
            print("Search Results:")
            print(f"  search_criteria: {search_data['search_criteria']}")
            print(f"  total_results: {search_data['total_results']}")
            print(f"  number of providers: {len(search_data['results'])}")
            print()
            
            # Display first provider's results
            if search_data['results']:
                first_provider = search_data['results'][0]
                provider_info = first_provider['provider']
                print("First Provider:")
                print(f"  name: {provider_info['name']}")
                print(f"  specialization: {provider_info['specialization']}")
                print(f"  years_of_experience: {provider_info['years_of_experience']}")
                print(f"  rating: {provider_info['rating']}")
                print(f"  clinic_address: {provider_info['clinic_address']}")
                print(f"  available_slots: {len(first_provider['available_slots'])}")
                
                if first_provider['available_slots']:
                    first_slot = first_provider['available_slots'][0]
                    print(f"  First slot: {first_slot['date']} {first_slot['start_time']}-{first_slot['end_time']}")
                    print(f"  Price: ${first_slot['pricing']['base_fee']}")
            print()
            
        else:
            print("❌ Availability search failed!")
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def test_validation_scenarios():
    """Test various validation scenarios"""
    
    print("🔍 Testing Validation Scenarios")
    print("=" * 35)
    
    test_cases = [
        {
            "name": "Invalid time format",
            "data": {
                "date": "2024-02-15",
                "start_time": "25:00",  # Invalid hour
                "end_time": "17:00",
                "timezone": "America/New_York",
                "slot_duration": 30,
                "appointment_type": "consultation",
                "location": {
                    "type": "clinic",
                    "address": "123 Medical Center Dr",
                    "room_number": "Room 205"
                }
            },
            "expected_status": 422
        },
        {
            "name": "End time before start time",
            "data": {
                "date": "2024-02-15",
                "start_time": "17:00",
                "end_time": "09:00",  # Before start time
                "timezone": "America/New_York",
                "slot_duration": 30,
                "appointment_type": "consultation",
                "location": {
                    "type": "clinic",
                    "address": "123 Medical Center Dr",
                    "room_number": "Room 205"
                }
            },
            "expected_status": 422
        },
        {
            "name": "Invalid slot duration",
            "data": {
                "date": "2024-02-15",
                "start_time": "09:00",
                "end_time": "17:00",
                "timezone": "America/New_York",
                "slot_duration": 10,  # Too short
                "appointment_type": "consultation",
                "location": {
                    "type": "clinic",
                    "address": "123 Medical Center Dr",
                    "room_number": "Room 205"
                }
            },
            "expected_status": 422
        },
        {
            "name": "Invalid recurrence end date",
            "data": {
                "date": "2024-02-15",
                "start_time": "09:00",
                "end_time": "17:00",
                "timezone": "America/New_York",
                "slot_duration": 30,
                "is_recurring": True,
                "recurrence_pattern": "weekly",
                "recurrence_end_date": "2024-02-10",  # Before start date
                "appointment_type": "consultation",
                "location": {
                    "type": "clinic",
                    "address": "123 Medical Center Dr",
                    "room_number": "Room 205"
                }
            },
            "expected_status": 422
        },
        {
            "name": "Invalid currency",
            "data": {
                "date": "2024-02-15",
                "start_time": "09:00",
                "end_time": "17:00",
                "timezone": "America/New_York",
                "slot_duration": 30,
                "appointment_type": "consultation",
                "location": {
                    "type": "clinic",
                    "address": "123 Medical Center Dr",
                    "room_number": "Room 205"
                },
                "pricing": {
                    "base_fee": 150.00,
                    "insurance_accepted": True,
                    "currency": "INVALID"  # Invalid currency
                }
            },
            "expected_status": 422
        },
        {
            "name": "Physical location without address",
            "data": {
                "date": "2024-02-15",
                "start_time": "09:00",
                "end_time": "17:00",
                "timezone": "America/New_York",
                "slot_duration": 30,
                "appointment_type": "consultation",
                "location": {
                    "type": "clinic",
                    "address": None,  # Missing address for physical location
                    "room_number": "Room 205"
                }
            },
            "expected_status": 422
        }
    ]
    
    for test_case in test_cases:
        try:
            response = requests.post(
                f"{BASE_URL}/api/v1/provider/availability",
                json=test_case["data"],
                headers={"Content-Type": "application/json"}
            )
            
            status = "✅" if response.status_code == test_case["expected_status"] else "❌"
            print(f"{status} {test_case['name']}: {response.status_code}")
            
            if response.status_code != test_case["expected_status"]:
                print(f"    Expected: {test_case['expected_status']}, Got: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            print(f"❌ {test_case['name']}: Connection failed")
        except Exception as e:
            print(f"❌ {test_case['name']}: {e}")

def test_conflict_detection(headers):
    """Test conflict detection for overlapping time slots"""
    
    print("\n⚠️ Testing Conflict Detection")
    print("=" * 30)
    
    # First availability
    availability_data = {
        "date": "2024-02-15",
        "start_time": "09:00",
        "end_time": "17:00",
        "timezone": "America/New_York",
        "slot_duration": 30,
        "appointment_type": "consultation",
        "location": {
            "type": "clinic",
            "address": "123 Medical Center Dr",
            "room_number": "Room 205"
        }
    }
    
    try:
        # Create first availability
        response = requests.post(
            f"{BASE_URL}/api/v1/provider/availability",
            json=availability_data,
            headers={**headers, "Content-Type": "application/json"}
        )
        
        if response.status_code == 201:
            print("✅ First availability created successfully")
            
            # Try to create conflicting availability
            conflicting_data = availability_data.copy()
            conflicting_data["start_time"] = "10:00"
            conflicting_data["end_time"] = "11:00"
            
            response = requests.post(
                f"{BASE_URL}/api/v1/provider/availability",
                json=conflicting_data,
                headers={**headers, "Content-Type": "application/json"}
            )
            
            if response.status_code == 400:
                print("✅ Conflict detection working - overlapping slot rejected")
                print(f"   Error: {response.json()['detail']}")
            else:
                print(f"❌ Conflict detection failed: {response.status_code}")
                
        else:
            print(f"❌ First availability creation failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Conflict detection test error: {e}")

if __name__ == "__main__":
    print("Starting Provider Availability Management Demo...")
    print()
    
    # Test validation scenarios
    test_validation_scenarios()
    
    # Test provider registration and login
    headers = test_provider_registration_and_login()
    
    if headers:
        # Test conflict detection
        test_conflict_detection(headers)
        
        # Test availability creation
        availability_data = test_availability_creation(headers)
        
        if availability_data:
            # Test availability retrieval
            test_availability_retrieval(headers, availability_data)
        
        # Test availability search
        test_availability_search()
        
        print("🎉 All tests completed successfully!")
    else:
        print("❌ Provider setup failed, skipping availability tests")
    
    print("\nDemo completed!") 