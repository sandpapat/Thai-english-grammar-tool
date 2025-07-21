#!/usr/bin/env python3
"""
Concurrent request testing script for Thai-English Grammar Learning Tool.
Tests the application's ability to handle multiple simultaneous requests.
"""

import asyncio
import aiohttp
import time
import json
from concurrent.futures import ThreadPoolExecutor
import threading

# Test configuration
BASE_URL = "http://localhost:5000"
TEST_USERS = [
    {"pseudocode": "12345", "test_type": "normal"},
    {"pseudocode": "67890", "test_type": "normal"}, 
    {"pseudocode": "90001", "test_type": "proficient"},
    {"pseudocode": "91234", "test_type": "proficient"}
]

TEST_INPUTS = [
    "ฉันกินข้าวเช้าทุกวัน",
    "เมื่อวานฉันไปตลาด",
    "พรุ่งนี้ฉันจะไปเรียน",
    "ฉันกำลังทำงาน",
    "ฉันได้อ่านหนังสือแล้ว"
]


class ConcurrencyTester:
    def __init__(self):
        self.results = []
        self.lock = threading.Lock()
        
    def print_status(self, message):
        print(f"[{time.strftime('%H:%M:%S')}] {message}")
    
    async def login_user(self, session, user):
        """Login a test user"""
        login_data = {"pseudocode": user["pseudocode"]}
        
        async with session.post(f"{BASE_URL}/login", data=login_data) as response:
            if response.status == 200:
                self.print_status(f"✅ Logged in user {user['pseudocode']} ({user['test_type']})")
                return True
            else:
                self.print_status(f"❌ Failed to login user {user['pseudocode']}")
                return False
    
    async def test_single_request(self, session, user, text, request_id):
        """Test a single prediction request"""
        start_time = time.time()
        
        try:
            # First login
            if not await self.login_user(session, user):
                return None
            
            # Then make prediction request
            predict_data = {"thai_text": text}
            
            async with session.post(f"{BASE_URL}/predict", data=predict_data) as response:
                end_time = time.time()
                duration = end_time - start_time
                
                result = {
                    "request_id": request_id,
                    "user": user["pseudocode"],
                    "user_type": user["test_type"],
                    "input": text,
                    "status_code": response.status,
                    "duration": duration,
                    "success": response.status == 200,
                    "error": None
                }
                
                if response.status == 429:
                    result["error"] = "Rate limited"
                elif response.status != 200:
                    result["error"] = f"HTTP {response.status}"
                
                with self.lock:
                    self.results.append(result)
                
                status = "✅" if result["success"] else "❌"
                self.print_status(f"{status} Request {request_id}: {user['pseudocode']} -> {response.status} ({duration:.2f}s)")
                
                return result
                
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            
            result = {
                "request_id": request_id,
                "user": user["pseudocode"],
                "user_type": user["test_type"],
                "input": text,
                "status_code": 0,
                "duration": duration,
                "success": False,
                "error": str(e)
            }
            
            with self.lock:
                self.results.append(result)
            
            self.print_status(f"❌ Request {request_id} failed: {str(e)}")
            return result
    
    async def test_health_endpoint(self):
        """Test the health check endpoint"""
        self.print_status("🏥 Testing health endpoint...")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{BASE_URL}/health") as response:
                    if response.status == 200:
                        health_data = await response.json()
                        self.print_status(f"✅ Health check passed")
                        self.print_status(f"   Models loaded: {health_data.get('all_models_loaded', 'unknown')}")
                        self.print_status(f"   Rate limiter: {health_data.get('rate_limiter', {}).get('active_users', 0)} active users")
                        return True
                    else:
                        self.print_status(f"❌ Health check failed: HTTP {response.status}")
                        return False
        except Exception as e:
            self.print_status(f"❌ Health check error: {e}")
            return False
    
    async def run_concurrent_test(self, num_requests=10, max_concurrent=5):
        """Run concurrent request test"""
        self.print_status(f"🚀 Starting concurrent test: {num_requests} requests, {max_concurrent} concurrent")
        
        # First check if server is healthy
        if not await self.test_health_endpoint():
            self.print_status("⚠️  Server may not be ready, continuing anyway...")
        
        tasks = []
        
        # Create connector with connection limits
        connector = aiohttp.TCPConnector(limit=max_concurrent, limit_per_host=max_concurrent)
        
        async with aiohttp.ClientSession(connector=connector) as session:
            # Create test tasks
            for i in range(num_requests):
                user = TEST_USERS[i % len(TEST_USERS)]
                text = TEST_INPUTS[i % len(TEST_INPUTS)]
                task = self.test_single_request(session, user, text, i + 1)
                tasks.append(task)
            
            # Run with limited concurrency
            start_time = time.time()
            
            # Use semaphore to limit concurrent requests
            semaphore = asyncio.Semaphore(max_concurrent)
            
            async def limited_request(task):
                async with semaphore:
                    return await task
            
            # Execute all tasks with concurrency limit
            results = await asyncio.gather(*[limited_request(task) for task in tasks], return_exceptions=True)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            self.print_results(total_time, num_requests, max_concurrent)
    
    def print_results(self, total_time, num_requests, max_concurrent):
        """Print test results summary"""
        self.print_status("=" * 50)
        self.print_status("📊 CONCURRENT REQUEST TEST RESULTS")
        self.print_status("=" * 50)
        
        successful = [r for r in self.results if r["success"]]
        failed = [r for r in self.results if not r["success"]]
        rate_limited = [r for r in self.results if r.get("error") == "Rate limited"]
        
        self.print_status(f"Total requests: {len(self.results)}")
        self.print_status(f"Successful: {len(successful)} ({len(successful)/len(self.results)*100:.1f}%)")
        self.print_status(f"Failed: {len(failed)} ({len(failed)/len(self.results)*100:.1f}%)")
        self.print_status(f"Rate limited: {len(rate_limited)} ({len(rate_limited)/len(self.results)*100:.1f}%)")
        self.print_status(f"Total time: {total_time:.2f}s")
        self.print_status(f"Average time per request: {total_time/num_requests:.2f}s")
        
        if successful:
            avg_duration = sum(r["duration"] for r in successful) / len(successful)
            min_duration = min(r["duration"] for r in successful)
            max_duration = max(r["duration"] for r in successful)
            
            self.print_status(f"Response times - Avg: {avg_duration:.2f}s, Min: {min_duration:.2f}s, Max: {max_duration:.2f}s")
        
        # Print failures
        if failed:
            self.print_status("\n❌ Failed requests:")
            for result in failed:
                self.print_status(f"   Request {result['request_id']}: {result['error']}")
        
        # Rate limiting analysis
        if rate_limited:
            self.print_status(f"\n⚠️  Rate limiting working correctly: {len(rate_limited)} requests blocked")
        
        # Performance assessment
        requests_per_second = num_requests / total_time
        self.print_status(f"\n🚀 Throughput: {requests_per_second:.2f} requests/second")
        
        if len(successful) / len(self.results) > 0.7:
            self.print_status("✅ Concurrency test PASSED - System handles concurrent requests well")
        else:
            self.print_status("⚠️  Concurrency test NEEDS ATTENTION - Many requests failed")


async def main():
    """Main test function"""
    print("🧪 Thai-English App Concurrency Tester")
    print("=" * 50)
    
    tester = ConcurrencyTester()
    
    # Test scenarios
    scenarios = [
        {"name": "Light load", "requests": 5, "concurrent": 2},
        {"name": "Medium load", "requests": 10, "concurrent": 4}, 
        {"name": "Heavy load", "requests": 15, "concurrent": 6}
    ]
    
    for scenario in scenarios:
        print(f"\n🎯 Testing scenario: {scenario['name']}")
        tester.results = []  # Reset results
        
        await tester.run_concurrent_test(
            num_requests=scenario["requests"],
            max_concurrent=scenario["concurrent"]
        )
        
        # Wait between scenarios
        print("\n⏳ Waiting 10 seconds before next scenario...")
        await asyncio.sleep(10)
    
    print("\n🎉 All concurrency tests completed!")
    print("\n💡 Key takeaways:")
    print("   - Rate limiting should block some requests (this is expected)")
    print("   - Thread safety prevents crashes during concurrent access")
    print("   - Response times may vary due to model inference time")
    print("   - Check server logs for any error messages")


if __name__ == "__main__":
    print("Before running this test:")
    print("1. Make sure the application is running: python app.py or ./start_production.sh")
    print("2. Ensure test users exist in the database")
    print("3. The health endpoint should be accessible")
    print()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()