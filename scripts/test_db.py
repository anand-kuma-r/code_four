#!/usr/bin/env python3
"""
Test script to verify database functionality
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import engine, SessionLocal
from app.models import Job, Base
from datetime import datetime

def test_database():
    """Test database connection and basic operations"""
    print("Testing database setup...")
    
    # Drop and recreate tables to ensure new schema
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("✓ Tables dropped and recreated successfully")
    
    # Test database session
    db = SessionLocal()
    try:
        # Test creating a job
        test_job = Job(
            id="test-job-123",
            status="PENDING",
            created_at=datetime.utcnow(),
            video_path="/test/path/video.mp4",
            video_filename="test_video.mp4",
            video_size=1024,
            chunks_processed=0,
            total_chunks=0
        )
        
        db.add(test_job)
        db.commit()
        print("✓ Job created successfully")
        
        # Test querying the job
        retrieved_job = db.query(Job).filter(Job.id == "test-job-123").first()
        if retrieved_job:
            print(f"✓ Job retrieved: {retrieved_job.status}")
        else:
            print("✗ Failed to retrieve job")
        
        # Test updating the job
        retrieved_job.status = "COMPLETE"
        retrieved_job.report = "Test report content"
        db.commit()
        print("✓ Job updated successfully")
        
        # Clean up
        db.delete(retrieved_job)
        db.commit()
        print("✓ Test job cleaned up")
        
    except Exception as e:
        print(f"✗ Database test failed: {e}")
        db.rollback()
    finally:
        db.close()
    
    print("Database test completed!")

if __name__ == "__main__":
    test_database() 