import requests
import time
import json
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:8000"
VIDEO_PATH = r"C:\Users\anand\Downloads\gum.mp4"
POLL_INTERVAL = 2  # seconds between status checks
MAX_WAIT_TIME = 300  # maximum wait time in seconds (5 minutes)

def test_video_analysis_pipeline():
    """Complete test of the video analysis pipeline"""
    
    print("🎬 Video Analysis API Test")
    print("=" * 50)
    
    # Step 1: Check if video file exists
    if not Path(VIDEO_PATH).exists():
        print(f"❌ Error: Video file not found at {VIDEO_PATH}")
        return False
    
    print(f"📁 Video file: {Path(VIDEO_PATH).name}")
    print(f"📊 File size: {Path(VIDEO_PATH).stat().st_size / (1024*1024):.2f} MB")
    
    try:
        # Step 2: Upload video and start job
        print("\n🚀 Step 1: Uploading video and starting analysis job...")
        
        with open(VIDEO_PATH, "rb") as f:
            files = {"file": f}
            response = requests.post(f"{BASE_URL}/v1/analyze", files=files)
        
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ Upload failed: {response.text}")
            return False
        
        job_data = response.json()
        job_id = job_data["jobId"]
        status_url = job_data["statusUrl"]
        
        print(f"   ✅ Job created successfully!")
        print(f"   Job ID: {job_id}")
        print(f"   Status URL: {status_url}")
        
        # Step 3: Poll job status
        print(f"\n⏳ Step 2: Polling job status (checking every {POLL_INTERVAL}s)...")
        
        start_time = time.time()
        status = "PENDING"
        
        while status in ["PENDING", "PROCESSING"]:
            # Check if we've exceeded max wait time
            if time.time() - start_time > MAX_WAIT_TIME:
                print(f"❌ Timeout: Job took longer than {MAX_WAIT_TIME} seconds")
                return False
            
            # Get current status
            status_response = requests.get(f"{BASE_URL}/v1/analyze/status/{job_id}")
            
            if status_response.status_code != 200:
                print(f"❌ Status check failed: {status_response.text}")
                return False
            
            status_data = status_response.json()
            status = status_data["status"]
            elapsed_time = time.time() - start_time
            
            print(f"   [{elapsed_time:.1f}s] Status: {status}")
            
            if status == "PROCESSING":
                print("   🔄 Video is being chunked and analyzed...")
            
            time.sleep(POLL_INTERVAL)
        
        # Step 4: Check final result
        print(f"\n🎯 Step 3: Final result...")
        
        # Get final status
        final_response = requests.get(f"{BASE_URL}/v1/analyze/status/{job_id}")
        final_data = final_response.json()
        
        if final_data["status"] == "COMPLETE":
            print("   ✅ Job completed successfully!")
            print(f"   Total processing time: {time.time() - start_time:.1f} seconds")
            
            # Display report summary
            if "report" in final_data and final_data["report"]:
                report = final_data["report"]
                print(f"\n📄 Generated Report Preview (first 500 chars):")
                print("-" * 50)
                print(report[:500] + "..." if len(report) > 500 else report)
                print("-" * 50)
                
                # Save report to file for inspection
                report_filename = f"test_report_{job_id[:8]}.txt"
                with open(report_filename, 'w', encoding='utf-8') as f:
                    f.write(report)
                print(f"   💾 Full report saved to: {report_filename}")
                
                return True
            else:
                print("   ⚠️  Job completed but no report was generated")
                return False
                
        elif final_data["status"] == "FAILED":
            print("   ❌ Job failed!")
            if "error" in final_data:
                print(f"   Error details: {final_data['error']}")
            return False
        
        else:
            print(f"   ❓ Unexpected final status: {final_data['status']}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection Error: Make sure the FastAPI server is running on localhost:8000")
        print("   Start server with: uvicorn main:app --reload --port 8000")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return False

def test_health_check():
    """Test the health check endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✅ Health check passed")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except:
        print("❌ Health check failed: Server not responding")
        return False

def test_invalid_file():
    """Test uploading an invalid file type"""
    print("\n🧪 Testing invalid file upload...")
    
    # Create a dummy text file
    dummy_content = b"This is not a video file"
    files = {"file": ("test.txt", dummy_content, "text/plain")}
    
    try:
        response = requests.post(f"{BASE_URL}/v1/analyze", files=files)
        if response.status_code == 400:
            print("   ✅ Correctly rejected non-video file")
            return True
        else:
            print(f"   ❌ Should have rejected non-video file, got: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Error testing invalid file: {str(e)}")
        return False

def test_nonexistent_job():
    """Test checking status of non-existent job"""
    print("\n🧪 Testing non-existent job lookup...")
    
    fake_job_id = "00000000-0000-0000-0000-000000000000"
    
    try:
        response = requests.get(f"{BASE_URL}/v1/analyze/status/{fake_job_id}")
        if response.status_code == 404:
            print("   ✅ Correctly returned 404 for non-existent job")
            return True
        else:
            print(f"   ❌ Should have returned 404, got: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Error testing non-existent job: {str(e)}")
        return False

if __name__ == "__main__":
    print("Starting comprehensive API tests...\n")
    
    # Run all tests
    tests_passed = 0
    total_tests = 4
    
    # Test 1: Health check
    if test_health_check():
        tests_passed += 1
    
    # Test 2: Invalid file upload
    if test_invalid_file():
        tests_passed += 1
    
    # Test 3: Non-existent job
    if test_nonexistent_job():
        tests_passed += 1
    
    # Test 4: Main pipeline test
    if test_video_analysis_pipeline():
        tests_passed += 1
    
    # Summary
    print("\n" + "=" * 50)
    print(f"🏁 Test Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 All tests passed! Your API is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
    
    # Additional helpful info
    print("\n💡 Helpful Commands:")
    print("   Start server: uvicorn main:app --reload --port 8000")
    print("   Check server logs for detailed processing information")
    print("   Reports are saved in the 'reports/' directory")