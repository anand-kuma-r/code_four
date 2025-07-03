#!/usr/bin/env python3
"""
Comprehensive testing script for the Video Analysis API
Tests the entire workflow from video upload to report generation
"""
import sys
import os
import time
import requests
import tempfile
import shutil
from pathlib import Path
import subprocess
import json

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import engine, SessionLocal
from app.models import Job, Base

class VideoAnalysisAPITester:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.test_results = []
        self.session = requests.Session()
        
    def log_test(self, test_name, passed, message=""):
        """Log test results"""
        status = "✅ PASS" if passed else "❌ FAIL"
        result = f"{status} {test_name}"
        if message:
            result += f": {message}"
        print(result)
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "message": message
        })
        return passed
    
    def test_health_endpoint(self):
        """Test the health check endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/health")
            if response.status_code == 200:
                data = response.json()
                return self.log_test("Health Check", True, f"Service: {data.get('service')}")
            else:
                return self.log_test("Health Check", False, f"Status code: {response.status_code}")
        except Exception as e:
            return self.log_test("Health Check", False, f"Error: {str(e)}")
    
    def test_database_connection(self):
        """Test database connection and basic operations"""
        try:
            # Test database session
            db = SessionLocal()
            
            # Test creating a job
            test_job = Job(
                id="test-db-job-123",
                status="PENDING",
                video_path="/test/path/video.mp4",
                video_filename="test_video.mp4",
                video_size=1024,
                chunks_processed=0,
                total_chunks=0
            )
            
            db.add(test_job)
            db.commit()
            
            # Test querying
            retrieved_job = db.query(Job).filter(Job.id == "test-db-job-123").first()
            if retrieved_job and retrieved_job.status == "PENDING":
                db.delete(retrieved_job)
                db.commit()
                db.close()
                return self.log_test("Database Operations", True)
            else:
                db.close()
                return self.log_test("Database Operations", False, "Failed to retrieve job")
                
        except Exception as e:
            return self.log_test("Database Operations", False, f"Error: {str(e)}")
    
    def create_test_video(self, duration_seconds=10):
        """Create a test video file using FFmpeg"""
        try:
            # Create a simple test video with a colored background and text
            test_video_path = Path("test_video.mp4")
            
            # FFmpeg command to create a test video
            cmd = [
                'ffmpeg', '-y',  # Overwrite output file
                '-f', 'lavfi',
                '-i', f'testsrc=duration={duration_seconds}:size=320x240:rate=1',
                '-f', 'lavfi',
                '-i', f'sine=frequency=1000:duration={duration_seconds}',
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-shortest',
                str(test_video_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and test_video_path.exists():
                return test_video_path
            else:
                print(f"FFmpeg error: {result.stderr}")
                return None
                
        except Exception as e:
            print(f"Error creating test video: {e}")
            return None
    
    def test_video_upload(self):
        """Test video upload endpoint"""
        try:
            # Create a test video
            test_video = self.create_test_video(duration_seconds=15)  # 15 seconds
            if not test_video:
                return self.log_test("Video Upload", False, "Failed to create test video")
            
            # Upload the video
            with open(test_video, 'rb') as f:
                files = {'file': f}
                response = self.session.post(f"{self.base_url}/v1/analyze", files=files)
            
            # Clean up test video
            test_video.unlink()
            
            if response.status_code == 200:
                data = response.json()
                job_id = data.get('jobId')
                if job_id:
                    self.current_job_id = job_id
                    return self.log_test("Video Upload", True, f"Job ID: {job_id}")
                else:
                    return self.log_test("Video Upload", False, "No job ID in response")
            else:
                return self.log_test("Video Upload", False, f"Status code: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            return self.log_test("Video Upload", False, f"Error: {str(e)}")
    
    def test_job_status_polling(self):
        """Test job status polling"""
        if not hasattr(self, 'current_job_id'):
            return self.log_test("Job Status Polling", False, "No job ID available")
        
        try:
            # Poll for status multiple times
            max_attempts = 10
            for attempt in range(max_attempts):
                response = self.session.get(f"{self.base_url}/v1/analyze/status/{self.current_job_id}")
                
                if response.status_code == 200:
                    data = response.json()
                    status = data.get('status')
                    
                    if status == "COMPLETE":
                        # Check if report is present
                        if 'report' in data and data['report']:
                            return self.log_test("Job Status Polling", True, f"Job completed with report")
                        else:
                            return self.log_test("Job Status Polling", False, "Job completed but no report")
                    
                    elif status == "FAILED":
                        error = data.get('error', 'Unknown error')
                        return self.log_test("Job Status Polling", False, f"Job failed: {error}")
                    
                    elif status in ["PENDING", "PROCESSING"]:
                        print(f"  Job status: {status} (attempt {attempt + 1}/{max_attempts})")
                        time.sleep(2)  # Wait 2 seconds before next poll
                        continue
                    
                    else:
                        return self.log_test("Job Status Polling", False, f"Unknown status: {status}")
                else:
                    return self.log_test("Job Status Polling", False, f"Status code: {response.status_code}")
            
            return self.log_test("Job Status Polling", False, f"Timeout after {max_attempts} attempts")
            
        except Exception as e:
            return self.log_test("Job Status Polling", False, f"Error: {str(e)}")
    
    def test_jobs_listing(self):
        """Test jobs listing endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/v1/jobs")
            
            if response.status_code == 200:
                jobs = response.json()
                if isinstance(jobs, list):
                    return self.log_test("Jobs Listing", True, f"Found {len(jobs)} jobs")
                else:
                    return self.log_test("Jobs Listing", False, "Response is not a list")
            else:
                return self.log_test("Jobs Listing", False, f"Status code: {response.status_code}")
                
        except Exception as e:
            return self.log_test("Jobs Listing", False, f"Error: {str(e)}")
    
    def test_job_deletion(self):
        """Test job deletion endpoint"""
        if not hasattr(self, 'current_job_id'):
            return self.log_test("Job Deletion", False, "No job ID available")
        
        try:
            response = self.session.delete(f"{self.base_url}/v1/jobs/{self.current_job_id}")
            
            if response.status_code == 200:
                data = response.json()
                if 'message' in data:
                    return self.log_test("Job Deletion", True, data['message'])
                else:
                    return self.log_test("Job Deletion", True, "Job deleted successfully")
            else:
                return self.log_test("Job Deletion", False, f"Status code: {response.status_code}")
                
        except Exception as e:
            return self.log_test("Job Deletion", False, f"Error: {str(e)}")
    
    def test_invalid_file_upload(self):
        """Test upload with invalid file type"""
        try:
            # Create a text file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write("This is not a video file")
                temp_file_path = f.name
            
            # Try to upload the text file
            with open(temp_file_path, 'rb') as f:
                files = {'file': f}
                response = self.session.post(f"{self.base_url}/v1/analyze", files=files)
            
            # Clean up
            os.unlink(temp_file_path)
            
            if response.status_code == 400:
                return self.log_test("Invalid File Upload", True, "Correctly rejected non-video file")
            else:
                return self.log_test("Invalid File Upload", False, f"Should have rejected file, got status: {response.status_code}")
                
        except Exception as e:
            return self.log_test("Invalid File Upload", False, f"Error: {str(e)}")
    
    def test_nonexistent_job_status(self):
        """Test status check for non-existent job"""
        try:
            fake_job_id = "non-existent-job-123"
            response = self.session.get(f"{self.base_url}/v1/analyze/status/{fake_job_id}")
            
            if response.status_code == 404:
                return self.log_test("Non-existent Job Status", True, "Correctly returned 404")
            else:
                return self.log_test("Non-existent Job Status", False, f"Expected 404, got: {response.status_code}")
                
        except Exception as e:
            return self.log_test("Non-existent Job Status", False, f"Error: {str(e)}")
    
    def test_file_validation(self):
        """Test various file validation scenarios"""
        tests = [
            {
                "name": "Missing File",
                "files": {},
                "expected_status": 422  # FastAPI validation error
            },
            {
                "name": "Empty File",
                "files": {"file": ("empty.mp4", b"", "video/mp4")},
                "expected_status": 200  # Should accept empty file
            }
        ]
        
        all_passed = True
        for test in tests:
            try:
                response = self.session.post(f"{self.base_url}/v1/analyze", files=test["files"])
                
                if response.status_code == test["expected_status"]:
                    self.log_test(f"File Validation - {test['name']}", True)
                else:
                    self.log_test(f"File Validation - {test['name']}", False, 
                                f"Expected {test['expected_status']}, got {response.status_code}")
                    all_passed = False
                    
            except Exception as e:
                self.log_test(f"File Validation - {test['name']}", False, f"Error: {str(e)}")
                all_passed = False
        
        return all_passed
    
    def test_directory_structure(self):
        """Test that required directories exist"""
        required_dirs = ["uploads", "chunks", "reports"]
        all_exist = True
        
        for dir_name in required_dirs:
            dir_path = Path(dir_name)
            if dir_path.exists() and dir_path.is_dir():
                self.log_test(f"Directory Check - {dir_name}", True)
            else:
                self.log_test(f"Directory Check - {dir_name}", False, "Directory does not exist")
                all_exist = False
        
        return all_exist
    
    def test_database_file(self):
        """Test that database file exists and is accessible"""
        try:
            db_path = Path("jobs.db")
            if db_path.exists():
                # Try to connect to database
                db = SessionLocal()
                db.close()
                return self.log_test("Database File", True, "Database file exists and accessible")
            else:
                return self.log_test("Database File", False, "Database file does not exist")
        except Exception as e:
            return self.log_test("Database File", False, f"Error: {str(e)}")
    
    def run_all_tests(self):
        """Run all tests in sequence"""
        print("🚀 Starting Comprehensive Video Analysis API Tests")
        print("=" * 60)
        
        # Test server connectivity first
        if not self.test_health_endpoint():
            print("\n❌ Server is not running. Please start the server with:")
            print("   uvicorn app.main:app --reload")
            return False
        
        # Infrastructure tests
        print("\n📋 Infrastructure Tests:")
        self.test_database_file()
        self.test_directory_structure()
        self.test_database_connection()
        
        # API endpoint tests
        print("\n🔧 API Endpoint Tests:")
        self.test_invalid_file_upload()
        self.test_file_validation()
        self.test_nonexistent_job_status()
        
        # Main workflow tests
        print("\n🎬 Main Workflow Tests:")
        if self.test_video_upload():
            self.test_job_status_polling()
        
        # Management tests
        print("\n📊 Management Tests:")
        self.test_jobs_listing()
        self.test_job_deletion()
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 Test Summary:")
        
        passed = sum(1 for result in self.test_results if result["passed"])
        total = len(self.test_results)
        
        print(f"✅ Passed: {passed}/{total}")
        print(f"❌ Failed: {total - passed}/{total}")
        
        if passed == total:
            print("\n🎉 All tests passed! Your Video Analysis API is working correctly.")
        else:
            print("\n⚠️  Some tests failed. Check the output above for details.")
        
        return passed == total

def main():
    """Main test runner"""
    tester = VideoAnalysisAPITester()
    success = tester.run_all_tests()
    
    if not success:
        print("\n💡 Troubleshooting Tips:")
        print("1. Make sure the server is running: uvicorn app.main:app --reload")
        print("2. Check that FFmpeg is installed and in your PATH")
        print("3. Verify all required directories exist (uploads, chunks, reports)")
        print("4. Check the server logs for any error messages")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main()) 