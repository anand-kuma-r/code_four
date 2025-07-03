# main.py
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
import uuid
import os
import aiofiles
import asyncio
import subprocess
import json
from pathlib import Path
from typing import Dict, Any
import google.generativeai as genai
from datetime import datetime
from sqlalchemy.orm import Session
from .database import engine, Base, get_db
from .models import Job  # ensures model is registered
from dotenv import load_dotenv
# create jobs.db and the jobs table if they don't exist
Base.metadata.create_all(bind=engine)


app = FastAPI()

# Configure Gemini API
load_dotenv()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY environment variable not set")
genai.configure(api_key=GEMINI_API_KEY)

# Make sure directories exist
UPLOAD_DIR = Path("uploads")
CHUNKS_DIR = Path("chunks")
REPORTS_DIR = Path("reports")

for dir_path in [UPLOAD_DIR, CHUNKS_DIR, REPORTS_DIR]:
    dir_path.mkdir(exist_ok=True)

# Gemini prompt for video analysis
GEMINI_PROMPT = """You are a helpful police assistant. Summarize the key events in this video clip for an incident report. Be objective and concise. List the events chronologically."""

@app.post("/v1/analyze")
async def create_analysis_job(
    background_tasks: BackgroundTasks, 
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # 1. Validate file type - check both content type and file extension
    valid_video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v'}
    file_extension = Path(file.filename).suffix.lower() if file.filename else ""
    
    # Check if it's a video by content type OR file extension
    is_video_by_content = file.content_type and file.content_type.startswith("video/")
    is_video_by_extension = file_extension in valid_video_extensions
    
    if not (is_video_by_content or is_video_by_extension):
        raise HTTPException(
            status_code=400, 
            detail=f"Only video files are allowed. Got content-type: {file.content_type}, extension: {file_extension}"
        )

    # 2. Generate a unique job ID
    job_id = str(uuid.uuid4())

    # 3. Save upload to disk
    file_extension = Path(file.filename).suffix if file.filename else ".mp4"
    save_path = UPLOAD_DIR / f"{job_id}{file_extension}"
    
    try:
        file_size = 0
        async with aiofiles.open(save_path, 'wb') as out_file:
            await file.seek(0)
            while content := await file.read(1024 * 1024):  # 1 MB chunks
                await out_file.write(content)
                file_size += len(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # 4. Create job record in database
    db_job = Job(
        id=job_id,
        status="PENDING",
        created_at=datetime.utcnow(),
        video_path=str(save_path),
        video_filename=file.filename,
        video_size=file_size,
        report=None,
        error=None,
        chunks_processed=0,
        total_chunks=0
    )
    
    try:
        db.add(db_job)
        db.commit()
        db.refresh(db_job)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create job record: {str(e)}")

    # 5. Add background task to process the video
    background_tasks.add_task(process_video_job, job_id, save_path)

    # 6. Return job info
    return JSONResponse({
        "jobId": job_id,
        "statusUrl": f"/v1/analyze/status/{job_id}",
        "filename": file.filename,
        "fileSize": file_size
    })

@app.get("/v1/analyze/status/{job_id}")
def get_status(job_id: str, db: Session = Depends(get_db)):
    # Query the database for the job
    db_job = db.query(Job).filter(Job.id == job_id).first()
    
    if db_job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    
    response = {
        "jobId": job_id,
        "status": db_job.status,
        "created_at": db_job.created_at.isoformat() if db_job.created_at else None,
        "updated_at": db_job.updated_at.isoformat() if db_job.updated_at else None,
        "filename": db_job.video_filename,
        "fileSize": db_job.video_size,
        "chunks_processed": db_job.chunks_processed,
        "total_chunks": db_job.total_chunks
    }
    
    if db_job.status == "COMPLETE" and db_job.report:
        response["report"] = db_job.report
    
    if db_job.status == "FAILED" and db_job.error:
        response["error"] = db_job.error
    
    return response

@app.get("/v1/jobs")
def list_jobs(
    skip: int = 0, 
    limit: int = 100, 
    status: str = None,
    db: Session = Depends(get_db)
):
    """List all jobs with optional filtering"""
    query = db.query(Job)
    
    if status:
        query = query.filter(Job.status == status)
    
    jobs = query.offset(skip).limit(limit).all()
    
    return [
        {
            "jobId": job.id,
            "status": job.status,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "updated_at": job.updated_at.isoformat() if job.updated_at else None,
            "filename": job.video_filename,
            "fileSize": job.video_size,
            "chunks_processed": job.chunks_processed,
            "total_chunks": job.total_chunks
        }
        for job in jobs
    ]

@app.delete("/v1/jobs/{job_id}")
def delete_job(job_id: str, db: Session = Depends(get_db)):
    """Delete a job and its associated files"""
    db_job = db.query(Job).filter(Job.id == job_id).first()
    
    if db_job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    
    try:
        # Delete the video file
        if db_job.video_path and os.path.exists(db_job.video_path):
            os.remove(db_job.video_path)
        
        # Delete the report file
        report_path = REPORTS_DIR / f"{job_id}_report.txt"
        if report_path.exists():
            os.remove(report_path)
        
        # Delete chunk directory if it exists
        chunk_dir = CHUNKS_DIR / job_id
        if chunk_dir.exists():
            import shutil
            shutil.rmtree(chunk_dir)
        
        # Delete from database
        db.delete(db_job)
        db.commit()
        
        return {"message": f"Job {job_id} deleted successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete job: {str(e)}")

async def process_video_job(job_id: str, video_path: Path):
    """Background task to process video chunks and generate report"""
    # Get a new database session for this background task
    from .database import SessionLocal
    db = SessionLocal()
    
    try:
        # Update status to PROCESSING
        db_job = db.query(Job).filter(Job.id == job_id).first()
        if db_job:
            db_job.status = "PROCESSING"
            db.commit()
        
        # Step 1: Chunk video using FFmpeg
        print(f"Starting video processing for job {job_id}")
        chunk_paths = await chunk_video_with_ffmpeg(job_id, video_path)
        
        if not chunk_paths:
            raise Exception("No video chunks were created")
        
        print(f"Created {len(chunk_paths)} chunks for job {job_id}")
        
        # Update total chunks count
        db_job = db.query(Job).filter(Job.id == job_id).first()
        if db_job:
            db_job.total_chunks = len(chunk_paths)
            db.commit()
        
        # Step 2: Process each chunk with Gemini API
        summaries = []
        for i, chunk_path in enumerate(chunk_paths):
            print(f"Processing chunk {i+1}/{len(chunk_paths)} for job {job_id}")
            try:
                summary = await analyze_video_chunk_with_gemini(chunk_path, i+1)
                summaries.append(summary)
                
                # Update chunks processed count
                db_job = db.query(Job).filter(Job.id == job_id).first()
                if db_job:
                    db_job.chunks_processed = i + 1
                    db.commit()
                    
            except Exception as e:
                print(f"Error processing chunk {i+1}: {str(e)}")
                summaries.append(f"Error processing chunk {i+1}: {str(e)}")
        
        # Step 3: Combine summaries into final report
        final_report = create_consolidated_report(summaries)
        
        # Step 4: Save report to file
        report_path = REPORTS_DIR / f"{job_id}_report.txt"
        async with aiofiles.open(report_path, 'w') as f:
            await f.write(final_report)
        
        # Step 5: Update job status to COMPLETE in database
        db_job = db.query(Job).filter(Job.id == job_id).first()
        if db_job:
            db_job.status = "COMPLETE"
            db_job.report = final_report
            db_job.chunks_processed = len(chunk_paths)
            db.commit()
        
        print(f"Job {job_id} completed successfully")
        
        # Cleanup chunk files
        for chunk_path in chunk_paths:
            try:
                os.remove(chunk_path)
            except:
                pass
                
    except Exception as e:
        print(f"Error processing job {job_id}: {str(e)}")
        # Update job status to FAILED in database
        db_job = db.query(Job).filter(Job.id == job_id).first()
        if db_job:
            db_job.status = "FAILED"
            db_job.error = str(e)
            db.commit()
    finally:
        db.close()

async def chunk_video_with_ffmpeg(job_id: str, video_path: Path):
    """Split video into 5-minute chunks using FFmpeg"""
    chunk_dir = CHUNKS_DIR / job_id
    chunk_dir.mkdir(exist_ok=True)
    
    # FFmpeg command to split video into 5-minute (300 second) segments
    cmd = [
        'ffmpeg',
        '-i', str(video_path),
        '-c', 'copy',  # Copy streams without re-encoding for speed
        '-f', 'segment',
        '-segment_time', '300',  # 5 minutes = 300 seconds
        '-segment_format', 'mp4',
        '-reset_timestamps', '1',
        str(chunk_dir / 'chunk_%03d.mp4')
    ]
    
    try:
        # Run FFmpeg command
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"FFmpeg output: {result.stdout}")
        
        # Get list of created chunk files
        chunk_files = sorted(chunk_dir.glob('chunk_*.mp4'))
        return chunk_files
        
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg error: {e.stderr}")
        raise Exception(f"Failed to chunk video: {e.stderr}")

async def analyze_video_chunk_with_gemini(chunk_path: Path, chunk_number: int):
    """Send video chunk to Gemini API for analysis"""
    try:
        with open(chunk_path, "rb") as f:
            video_bytes = f.read()

        prompt = GEMINI_PROMPT
        model = genai.GenerativeModel("models/gemini-2.5-flash")

        # Correct structure for video input
        response = model.generate_content([
            {"text": prompt},
            {"inline_data": {"mime_type": "video/mp4", "data": video_bytes}}
        ])

        summary = response.text if hasattr(response, "text") else str(response)
        return summary.strip()

    except Exception as e:
        raise Exception(f"Failed to analyze chunk {chunk_number}: {str(e)}")

def create_consolidated_report(summaries):
    """Combine individual chunk summaries into a final report"""
    report_header = f"""
VIDEO ANALYSIS REPORT
=====================
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Total Segments Analyzed: {len(summaries)}

EXECUTIVE SUMMARY
=================
This report contains a chronological analysis of the submitted video evidence, 
broken down into 5-minute segments for detailed review.

DETAILED ANALYSIS
=================
"""
    
    detailed_sections = []
    for i, summary in enumerate(summaries, 1):
        section = f"""
SEGMENT {i} (Minutes {(i-1)*5}-{i*5})
{'='*40}
{summary}
"""
        detailed_sections.append(section)
    
    report_footer = f"""

CONCLUSION
==========
Analysis complete. {len(summaries)} video segments have been processed and summarized above.
Each segment represents approximately 5 minutes of video content.

Report generated by Video Analysis Service v1.0
"""
    
    return report_header + "\n".join(detailed_sections) + report_footer

# Health check endpoint
@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "video-analysis-api"}