"""
Test script to diagnose API issues
Run: python test_api_issues.py
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_send_otp():
    """Test POST /auth/send-otp endpoint"""
    print("=" * 60)
    print("TEST 1: POST /auth/send-otp")
    print("=" * 60)
    
    # Test valid request
    print("\n1. Testing with valid phone number:")
    payload = {
        "phone_number": "9876543210",
        "is_login": False
    }
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/auth/send-otp",
            json=payload,
            timeout=5
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test with trailing slash
    print("\n2. Testing with trailing slash:")
    try:
        response = requests.post(
            f"{BASE_URL}/auth/send-otp/",
            json=payload,
            timeout=5
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test invalid phone number
    print("\n3. Testing with invalid phone number:")
    invalid_payload = {
        "phone_number": "123",
        "is_login": False
    }
    print(f"Payload: {json.dumps(invalid_payload, indent=2)}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/auth/send-otp",
            json=invalid_payload,
            timeout=5
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test missing is_login field
    print("\n4. Testing without is_login field:")
    minimal_payload = {
        "phone_number": "9876543210"
    }
    print(f"Payload: {json.dumps(minimal_payload, indent=2)}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/auth/send-otp",
            json=minimal_payload,
            timeout=5
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")


def test_get_items():
    """Test GET /items/ endpoint (requires auth token)"""
    print("\n" + "=" * 60)
    print("TEST 2: GET /items/")
    print("=" * 60)
    
    print("\n1. Testing without auth token:")
    try:
        response = requests.get(
            f"{BASE_URL}/items/",
            timeout=5
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n2. Testing with invalid auth token:")
    try:
        response = requests.get(
            f"{BASE_URL}/items/",
            headers={"Authorization": "Bearer invalid_token"},
            timeout=5
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")


def test_api_docs():
    """Test API documentation endpoints"""
    print("\n" + "=" * 60)
    print("TEST 3: API Documentation")
    print("=" * 60)
    
    print("\n1. Testing /docs (Swagger UI):")
    try:
        response = requests.get(f"{BASE_URL}/docs", timeout=5)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("✅ API docs accessible at http://localhost:8000/docs")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n2. Testing /openapi.json:")
    try:
        response = requests.get(f"{BASE_URL}/openapi.json", timeout=5)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("✅ OpenAPI spec accessible")
            # Check if /auth/send-otp is in the spec
            spec = response.json()
            if "/auth/send-otp" in spec.get("paths", {}):
                print("✅ /auth/send-otp found in API spec")
            else:
                print("❌ /auth/send-otp NOT found in API spec")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    print("API DIAGNOSTIC TESTS")
    print("Testing API endpoints that are failing...\n")
    
    test_send_otp()
    test_get_items()
    test_api_docs()
    
    print("\n" + "=" * 60)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 60)
    print("\nNext Steps:")
    print("1. Check if server is running: http://localhost:8000")
    print("2. Check API docs: http://localhost:8000/docs")
    print("3. Review server logs for detailed errors")
    print("=" * 60)
