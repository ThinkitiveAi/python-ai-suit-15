#!/usr/bin/env python3
"""
Demo script for the Patient Registration functionality
"""

import json
import requests
from datetime import date, timedelta

# API base URL
BASE_URL = "http://localhost:8000"

def test_patient_registration():
    """Test the patient registration endpoint"""
    
    print("🏥 Patient Registration Demo")
    print("=" * 50)
    
    # Test data matching the prompt requirements
    patient_data = {
        "first_name": "Jane",
        "last_name": "Smith",
        "email": "jane.smith@email.com",
        "phone_number": "+1234567890",
        "password": "SecurePassword123!",
        "confirm_password": "SecurePassword123!",
        "date_of_birth": "1990-05-15",
        "gender": "female",
        "address": {
            "street": "456 Main Street",
            "city": "Boston",
            "state": "MA",
            "zip": "02101"
        },
        "emergency_contact": {
            "name": "John Smith",
            "phone": "+1234567891",
            "relationship": "spouse"
        },
        "insurance_info": {
            "provider": "Blue Cross",
            "policy_number": "BC123456789"
        }
    }
    
    print(f"Testing patient registration with email: {patient_data['email']}")
    print()
    
    try:
        # Make the registration request
        response = requests.post(
            f"{BASE_URL}/api/v1/patient/register",
            json=patient_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 201:
            data = response.json()
            print("✅ Patient Registration Successful!")
            print()
            
            # Display response structure
            print("Response Structure:")
            print(f"  success: {data['success']}")
            print(f"  message: {data['message']}")
            print()
            
            # Display patient data
            patient_info = data['data']
            print("Patient Information:")
            print(f"  patient_id: {patient_info['patient_id']}")
            print(f"  email: {patient_info['email']}")
            print(f"  phone_number: {patient_info['phone_number']}")
            print(f"  email_verified: {patient_info['email_verified']}")
            print(f"  phone_verified: {patient_info['phone_verified']}")
            print()
            
            # Verify sensitive data is not returned
            sensitive_fields = ["password", "password_hash", "date_of_birth", "medical_history", "insurance_info"]
            for field in sensitive_fields:
                if field not in patient_info:
                    print(f"  ✅ {field}: Not returned (HIPAA compliant)")
                else:
                    print(f"  ❌ {field}: Should not be returned")
            print()
            
            return patient_data
            
        else:
            print("❌ Patient Registration Failed!")
            print(f"Error: {response.text}")
            return None
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the API server.")
        print("Make sure the server is running with: python run.py")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def test_patient_login(patient_data):
    """Test patient login after registration"""
    
    if not patient_data:
        print("Skipping login test - no patient data available")
        return None
    
    print("🔐 Testing Patient Login")
    print("=" * 30)
    
    login_data = {
        "email": patient_data["email"],
        "password": patient_data["password"]
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/patient/login",
            json=login_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Patient Login Successful!")
            print()
            
            # Display token information
            token_data = data['data']
            print("Token Information:")
            print(f"  access_token: {token_data['access_token'][:50]}...")
            print(f"  expires_in: {token_data['expires_in']} seconds (30 minutes)")
            print(f"  token_type: {token_data['token_type']}")
            print()
            
            # Display patient data from login
            patient_info = token_data['patient']
            print("Patient Information (from login):")
            print(f"  id: {patient_info['id']}")
            print(f"  name: {patient_info['first_name']} {patient_info['last_name']}")
            print(f"  email: {patient_info['email']}")
            print(f"  gender: {patient_info['gender']}")
            print(f"  date_of_birth: {patient_info['date_of_birth']}")
            print(f"  address: {patient_info['address']['city']}, {patient_info['address']['state']}")
            print(f"  emergency_contact: {patient_info['emergency_contact']['name']}")
            print(f"  insurance_provider: {patient_info['insurance_info']['provider']}")
            print()
            
            return token_data['access_token']
            
        else:
            print("❌ Patient Login Failed!")
            print(f"Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Login Error: {e}")
        return None

def test_validation_scenarios():
    """Test various validation scenarios"""
    
    print("🔍 Testing Validation Scenarios")
    print("=" * 40)
    
    test_cases = [
        {
            "name": "Invalid email format",
            "data": {
                "first_name": "Test",
                "last_name": "User",
                "email": "invalid-email",
                "phone_number": "+1234567890",
                "password": "SecurePassword123!",
                "confirm_password": "SecurePassword123!",
                "date_of_birth": "1990-05-15",
                "gender": "male",
                "address": {
                    "street": "123 Test St",
                    "city": "Test City",
                    "state": "TS",
                    "zip": "12345"
                }
            },
            "expected_status": 422
        },
        {
            "name": "Weak password",
            "data": {
                "first_name": "Test",
                "last_name": "User",
                "email": "test@example.com",
                "phone_number": "+1234567890",
                "password": "weak",
                "confirm_password": "weak",
                "date_of_birth": "1990-05-15",
                "gender": "male",
                "address": {
                    "street": "123 Test St",
                    "city": "Test City",
                    "state": "TS",
                    "zip": "12345"
                }
            },
            "expected_status": 422
        },
        {
            "name": "Password mismatch",
            "data": {
                "first_name": "Test",
                "last_name": "User",
                "email": "test@example.com",
                "phone_number": "+1234567890",
                "password": "SecurePassword123!",
                "confirm_password": "DifferentPassword123!",
                "date_of_birth": "1990-05-15",
                "gender": "male",
                "address": {
                    "street": "123 Test St",
                    "city": "Test City",
                    "state": "TS",
                    "zip": "12345"
                }
            },
            "expected_status": 422
        },
        {
            "name": "Underage patient (COPPA violation)",
            "data": {
                "first_name": "Young",
                "last_name": "Patient",
                "email": "young@example.com",
                "phone_number": "+1234567890",
                "password": "SecurePassword123!",
                "confirm_password": "SecurePassword123!",
                "date_of_birth": (date.today() - timedelta(days=12*365)).isoformat(),
                "gender": "male",
                "address": {
                    "street": "123 Test St",
                    "city": "Test City",
                    "state": "TS",
                    "zip": "12345"
                }
            },
            "expected_status": 422
        },
        {
            "name": "Invalid ZIP code",
            "data": {
                "first_name": "Test",
                "last_name": "User",
                "email": "test@example.com",
                "phone_number": "+1234567890",
                "password": "SecurePassword123!",
                "confirm_password": "SecurePassword123!",
                "date_of_birth": "1990-05-15",
                "gender": "male",
                "address": {
                    "street": "123 Test St",
                    "city": "Test City",
                    "state": "TS",
                    "zip": "invalid"
                }
            },
            "expected_status": 422
        },
        {
            "name": "Invalid gender",
            "data": {
                "first_name": "Test",
                "last_name": "User",
                "email": "test@example.com",
                "phone_number": "+1234567890",
                "password": "SecurePassword123!",
                "confirm_password": "SecurePassword123!",
                "date_of_birth": "1990-05-15",
                "gender": "invalid_gender",
                "address": {
                    "street": "123 Test St",
                    "city": "Test City",
                    "state": "TS",
                    "zip": "12345"
                }
            },
            "expected_status": 422
        }
    ]
    
    for test_case in test_cases:
        try:
            response = requests.post(
                f"{BASE_URL}/api/v1/patient/register",
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

def test_duplicate_registration():
    """Test duplicate registration scenarios"""
    
    print("\n🔄 Testing Duplicate Registration")
    print("=" * 35)
    
    # First, register a patient
    patient_data = {
        "first_name": "Duplicate",
        "last_name": "Test",
        "email": "duplicate@example.com",
        "phone_number": "+1234567890",
        "password": "SecurePassword123!",
        "confirm_password": "SecurePassword123!",
        "date_of_birth": "1990-05-15",
        "gender": "male",
        "address": {
            "street": "123 Test St",
            "city": "Test City",
            "state": "TS",
            "zip": "12345"
        }
    }
    
    try:
        # First registration
        response = requests.post(
            f"{BASE_URL}/api/v1/patient/register",
            json=patient_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 201:
            print("✅ First registration successful")
            
            # Try duplicate email
            patient_data["phone_number"] = "+1987654321"
            response = requests.post(
                f"{BASE_URL}/api/v1/patient/register",
                json=patient_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 400:
                print("✅ Duplicate email correctly rejected")
            else:
                print(f"❌ Duplicate email not rejected: {response.status_code}")
            
            # Try duplicate phone
            patient_data["email"] = "different@example.com"
            patient_data["phone_number"] = "+1234567890"  # Original phone
            response = requests.post(
                f"{BASE_URL}/api/v1/patient/register",
                json=patient_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 400:
                print("✅ Duplicate phone correctly rejected")
            else:
                print(f"❌ Duplicate phone not rejected: {response.status_code}")
                
        else:
            print(f"❌ First registration failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Duplicate registration test error: {e}")

if __name__ == "__main__":
    print("Starting Patient Registration Demo...")
    print()
    
    # Test validation scenarios
    test_validation_scenarios()
    
    # Test duplicate registration
    test_duplicate_registration()
    
    # Test successful registration
    patient_data = test_patient_registration()
    
    # Test login if registration was successful
    if patient_data:
        access_token = test_patient_login(patient_data)
        if access_token:
            print("🎉 All tests completed successfully!")
        else:
            print("⚠️  Registration successful but login failed")
    else:
        print("❌ Registration failed, skipping login test")
    
    print("\nDemo completed!") 