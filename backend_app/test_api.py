"""
Comprehensive API Test Suite
Tests all endpoints, Gemini, Mistral, and embeddings
"""
import os
import sys
import requests
import json
import time
from datetime import datetime
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Configuration
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
TEST_PHONE = os.getenv("TEST_PHONE", "+919876543210")

# Colors for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


class APITester:
    """API testing class"""
    
    def __init__(self):
        self.base_url = BASE_URL
        self.token = None
        self.user_id = None
        self.results = {
            "passed": 0,
            "failed": 0,
            "skipped": 0
        }
    
    def log(self, message, level="INFO"):
        """Colored logging"""
        color = {
            "INFO": BLUE,
            "SUCCESS": GREEN,
            "ERROR": RED,
            "WARNING": YELLOW
        }.get(level, RESET)
        print(f"{color}[{level}]{RESET} {message}")
    
    def test(self, name: str, func):
        """Run a test"""
        self.log(f"\n{'='*60}", "INFO")
        self.log(f"TEST: {name}", "INFO")
        self.log(f"{'='*60}", "INFO")
        
        try:
            start = time.time()
            result = func()
            duration = time.time() - start
            
            if result:
                self.results["passed"] += 1
                self.log(f"✓ PASSED ({duration:.2f}s)", "SUCCESS")
                return True
            else:
                self.results["failed"] += 1
                self.log(f"✗ FAILED ({duration:.2f}s)", "ERROR")
                return False
        except Exception as e:
            self.results["failed"] += 1
            self.log(f"✗ EXCEPTION: {e}", "ERROR")
            return False
    
    # ==================== Health Tests ====================
    
    def test_health(self):
        """Test health endpoint"""
        def run():
            response = requests.get(f"{self.base_url}/health")
            self.log(f"Status: {response.status_code}", "INFO")
            self.log(f"Response: {response.json()}", "INFO")
            return response.status_code == 200
        return self.test("Health Check", run)
    
    def test_info(self):
        """Test system info endpoint"""
        def run():
            response = requests.get(f"{self.base_url}/info")
            data = response.json()
            self.log(f"Version: {data.get('version')}", "INFO")
            self.log(f"Embedding: {data.get('embedding_provider')}", "INFO")
            self.log(f"Database: {data.get('database')}", "INFO")
            return response.status_code == 200
        return self.test("System Info", run)
    
    # ==================== Auth Tests ====================
    
    def test_send_otp(self):
        """Test OTP sending"""
        def run():
            response = requests.post(
                f"{self.base_url}/auth/send-otp",
                json={
                    "phone_number": TEST_PHONE,
                    "is_login": False
                }
            )
            data = response.json()
            self.log(f"Response: {data}", "INFO")
            
            if os.getenv("OTP_DEMO_MODE") == "1":
                self.log("Demo mode OTP: 112233", "WARNING")
            
            return response.status_code == 200 and data.get("success")
        return self.test("Send OTP", run)
    
    def test_verify_otp(self):
        """Test OTP verification and registration"""
        def run():
            response = requests.post(
                f"{self.base_url}/auth/verify-otp",
                json={
                    "phone_number": TEST_PHONE,
                    "otp_code": "112233",
                    "shop_name": "Test Kirana Store",
                    "owner_name": "Test Owner",
                    "address": "Test Address",
                    "shop_category": "Kirana"
                }
            )
            data = response.json()
            
            if response.status_code == 200:
                self.token = data.get("access_token")
                self.user_id = data.get("user_id")
                self.log(f"User ID: {self.user_id}", "SUCCESS")
                self.log(f"Token: {self.token[:50]}...", "SUCCESS")
                return True
            
            return False
        return self.test("Verify OTP & Register", run)
    
    def test_get_profile(self):
        """Test get profile"""
        def run():
            if not self.token:
                self.log("No token available, skipping", "WARNING")
                self.results["skipped"] += 1
                return True
            
            response = requests.get(
                f"{self.base_url}/auth/profile",
                headers={"Authorization": f"Bearer {self.token}"}
            )
            data = response.json()
            self.log(f"Profile: {json.dumps(data, indent=2)}", "INFO")
            return response.status_code == 200
        return self.test("Get Profile", run)
    
    # ==================== Items Tests ====================
    
    def test_create_item(self):
        """Test item creation"""
        def run():
            if not self.token:
                self.log("No token available, skipping", "WARNING")
                self.results["skipped"] += 1
                return True
            
            response = requests.post(
                f"{self.base_url}/items/",
                headers={"Authorization": f"Bearer {self.token}"},
                json={
                    "id": "test-item-001",
                    "names": ["Sugar", "चीनी", "Chini"],
                    "price": 50.0,
                    "unit": "kg",
                    "category": "Grocery"
                }
            )
            data = response.json()
            self.log(f"Created item: {data.get('id')}", "INFO")
            return response.status_code == 200
        return self.test("Create Item", run)
    
    def test_get_items(self):
        """Test get all items"""
        def run():
            if not self.token:
                self.log("No token available, skipping", "WARNING")
                self.results["skipped"] += 1
                return True
            
            response = requests.get(
                f"{self.base_url}/items/",
                headers={"Authorization": f"Bearer {self.token}"}
            )
            data = response.json()
            self.log(f"Total items: {len(data)}", "INFO")
            return response.status_code == 200
        return self.test("Get Items", run)
    
    def test_bulk_embed(self):
        """Test bulk embedding generation"""
        def run():
            if not self.token:
                self.log("No token available, skipping", "WARNING")
                self.results["skipped"] += 1
                return True
            
            response = requests.post(
                f"{self.base_url}/items/bulk-embed",
                headers={"Authorization": f"Bearer {self.token}"}
            )
            data = response.json()
            self.log(f"Embedded: {data.get('updated')} items", "INFO")
            return response.status_code == 200 and data.get("success")
        return self.test("Bulk Embed Items", run)
    
    # ==================== Analytics Tests ====================
    
    def test_create_bill(self):
        """Test bill creation"""
        def run():
            if not self.token:
                self.log("No token available, skipping", "WARNING")
                self.results["skipped"] += 1
                return True
            
            response = requests.post(
                f"{self.base_url}/analytics/bills",
                headers={"Authorization": f"Bearer {self.token}"},
                json={
                    "items": [
                        {
                            "name": "Sugar",
                            "quantity": 2,
                            "unit": "kg",
                            "price": 50,
                            "total": 100
                        },
                        {
                            "name": "Rice",
                            "quantity": 5,
                            "unit": "kg",
                            "price": 60,
                            "total": 300
                        }
                    ],
                    "total_amount": 400,
                    "customer_phone": "+919999999999",
                    "customer_name": "Test Customer",
                    "payment_method": "cash"
                }
            )
            data = response.json()
            self.log(f"Bill ID: {data.get('bill_id')}", "INFO")
            return response.status_code == 200 and data.get("success")
        return self.test("Create Bill", run)
    
    def test_get_dashboard(self):
        """Test dashboard analytics"""
        def run():
            if not self.token:
                self.log("No token available, skipping", "WARNING")
                self.results["skipped"] += 1
                return True
            
            response = requests.get(
                f"{self.base_url}/analytics/dashboard?days=30",
                headers={"Authorization": f"Bearer {self.token}"}
            )
            data = response.json()
            
            if response.status_code == 200:
                summary = data.get("summary", {})
                self.log(f"Revenue: ₹{summary.get('total_revenue')}", "INFO")
                self.log(f"Bills: {summary.get('total_bills')}", "INFO")
                self.log(f"Avg Bill: ₹{summary.get('average_bill_value')}", "INFO")
                return True
            
            return False
        return self.test("Dashboard Analytics", run)
    
    # ==================== RAG Tests ====================
    
    def test_rag_status(self):
        """Test RAG pipeline status"""
        def run():
            response = requests.get(f"{self.base_url}/rag/status")
            data = response.json()
            self.log(f"Status: {data.get('status')}", "INFO")
            self.log(f"Embedding: {json.dumps(data.get('embedding'), indent=2)}", "INFO")
            self.log(f"LLM: {json.dumps(data.get('llm'), indent=2)}", "INFO")
            return response.status_code == 200
        return self.test("RAG Status", run)
    
    def test_rag_query(self):
        """Test RAG query"""
        def run():
            if not self.token:
                self.log("No token available, skipping", "WARNING")
                self.results["skipped"] += 1
                return True
            
            response = requests.post(
                f"{self.base_url}/rag/query",
                headers={"Authorization": f"Bearer {self.token}"},
                json={
                    "query": "I need 2 kg sugar and 1 kg salt",
                    "include_analytics": True,
                    "include_customers": False
                }
            )
            data = response.json()
            
            if response.status_code == 200:
                self.log(f"Type: {data.get('type')}", "INFO")
                self.log(f"Message: {data.get('msg')}", "INFO")
                self.log(f"Items: {len(data.get('items', []))}", "INFO")
                
                metadata = data.get('metadata', {})
                self.log(f"Model: {metadata.get('model_used')}", "INFO")
                
                timings = metadata.get('timings', {})
                self.log(f"Timings: {json.dumps(timings, indent=2)}", "INFO")
                
                return True
            
            return False
        return self.test("RAG Query", run)
    
    # ==================== Summary ====================
    
    def print_summary(self):
        """Print test summary"""
        total = self.results["passed"] + self.results["failed"]
        
        print("\n" + "="*60)
        print(f"{BLUE}TEST SUMMARY{RESET}")
        print("="*60)
        print(f"{GREEN}✓ Passed:  {self.results['passed']}{RESET}")
        print(f"{RED}✗ Failed:  {self.results['failed']}{RESET}")
        print(f"{YELLOW}⊘ Skipped: {self.results['skipped']}{RESET}")
        print(f"Total:     {total}")
        
        if total > 0:
            success_rate = (self.results['passed'] / total) * 100
            print(f"\nSuccess Rate: {success_rate:.1f}%")
        
        print("="*60 + "\n")
    
    def run_all(self):
        """Run all tests"""
        print(f"\n{BLUE}{'='*60}{RESET}")
        print(f"{BLUE}API TEST SUITE{RESET}")
        print(f"{BLUE}Base URL: {self.base_url}{RESET}")
        print(f"{BLUE}{'='*60}{RESET}\n")
        
        # Health tests
        self.test_health()
        self.test_info()
        
        # Auth tests
        self.test_send_otp()
        self.test_verify_otp()
        self.test_get_profile()
        
        # Items tests
        self.test_create_item()
        self.test_get_items()
        self.test_bulk_embed()
        
        # Analytics tests
        self.test_create_bill()
        self.test_get_dashboard()
        
        # RAG tests
        self.test_rag_status()
        self.test_rag_query()
        
        # Summary
        self.print_summary()


if __name__ == "__main__":
    tester = APITester()
    tester.run_all()
