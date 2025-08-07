#!/usr/bin/env python3
"""
Demo script for the new Provider Login functionality
"""

import json
import requests
from datetime import datetime

# API base URL
BASE_URL = "http://localhost:8000"

def test_provider_login():
    """Test the new provider login endpoint"""
    
    print("🏥 Healthcare Provider Login Demo")
    print("=" * 50)
    
    # Test data
    login_data = {
        "email": "john.doe@clinic.com",
        "password": "SecurePassword123!"
    }
    
    print(f"Testing login with email: {login_data['email']}")
    print()
    
    try:
        # Make the login request
        response = requests.post(
            f"{BASE_URL}/api/v1/provider/login",
            json=login_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Login Successful!")
            print()
            
            # Display response structure
            print("Response Structure:")
            print(f"  success: {data['success']}")
            print(f"  message: {data['message']}")
            print()
            
            # Display token information
            token_data = data['data']
            print("Token Information:")
            print(f"  access_token: {token_data['access_token'][:50]}...")
            print(f"  expires_in: {token_data['expires_in']} seconds")
            print(f"  token_type: {token_data['token_type']}")
            print()
            
            # Display provider information
            provider = token_data['provider']
            print("Provider Information:")
            print(f"  ID: {provider['id']}")
            print(f"  Name: {provider['first_name']} {provider['last_name']}")
            print(f"  Email: {provider['email']}")
            print(f"  Specialization: {provider['specialization']}")
            print(f"  License: {provider['license_number']}")
            print(f"  Verification Status: {provider['verification_status']}")
            print(f"  Active: {provider['is_active']}")
            print()
            
            # Verify JWT token payload
            import jwt
            from app.config import settings
            
            try:
                payload = jwt.decode(
                    token_data['access_token'], 
                    settings.secret_key, 
                    algorithms=[settings.algorithm]
                )
                print("JWT Token Payload:")
                print(f"  provider_id: {payload['provider_id']}")
                print(f"  email: {payload['email']}")
                print(f"  role: {payload['role']}")
                print(f"  specialization: {payload['specialization']}")
                print(f"  expires: {datetime.fromtimestamp(payload['exp'])}")
                print()
                
            except Exception as e:
                print(f"❌ JWT verification failed: {e}")
                
        else:
            print("❌ Login Failed!")
            print(f"Error: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the API server.")
        print("Make sure the server is running with: python run.py")
    except Exception as e:
        print(f"❌ Error: {e}")

def test_validation():
    """Test input validation"""
    
    print("🔍 Testing Input Validation")
    print("=" * 30)
    
    test_cases = [
        {
            "name": "Invalid email format",
            "data": {"email": "invalid-email", "password": "SecurePassword123!"},
            "expected_status": 422
        },
        {
            "name": "Empty password",
            "data": {"email": "test@example.com", "password": ""},
            "expected_status": 422
        },
        {
            "name": "Missing email",
            "data": {"password": "SecurePassword123!"},
            "expected_status": 422
        },
        {
            "name": "Missing password",
            "data": {"email": "test@example.com"},
            "expected_status": 422
        }
    ]
    
    for test_case in test_cases:
        try:
            response = requests.post(
                f"{BASE_URL}/api/v1/provider/login",
                json=test_case["data"],
                headers={"Content-Type": "application/json"}
            )
            
            status = "✅" if response.status_code == test_case["expected_status"] else "❌"
            print(f"{status} {test_case['name']}: {response.status_code}")
            
        except requests.exceptions.ConnectionError:
            print(f"❌ {test_case['name']}: Connection failed")
        except Exception as e:
            print(f"❌ {test_case['name']}: {e}")

if __name__ == "__main__":
    print("Starting Provider Login Demo...")
    print()
    
    # Test validation first
    test_validation()
    print()
    
    # Test actual login
    test_provider_login()
    
    print("Demo completed!") 