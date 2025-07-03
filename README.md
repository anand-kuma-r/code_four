# Video Analysis API

A FastAPI-based backend service that automates the analysis of long-form video evidence using Google Gemini Vision API.

## Features

- **Video Upload & Processing**: Accept video files and process them asynchronously
- **Video Chunking**: Automatically split videos into 5-minute segments using FFmpeg
- **AI Analysis**: Use Google Gemini Vision API to analyze each video segment
- **Report Generation**: Generate consolidated narrative reports from video analysis
- **Persistent Storage**: SQLite database for job tracking and persistence
- **Background Processing**: Asynchronous job processing with real-time status updates

## API Endpoints

### 1. Upload Video for Analysis
```http
POST /v1/analyze
Content-Type: multipart/form-data

file: [video file]
```

**Response:**
```json
{
  "jobId": "uuid-string",
  "statusUrl": "/v1/analyze/status/uuid-string",
  "filename": "video.mp4",
  "fileSize": 1234567
}
```

### 2. Check Job Status
```http
GET /v1/analyze/status/{jobId}
```

**Response:**
```json
{
  "jobId": "uuid-string",
  "status": "PENDING|PROCESSING|COMPLETE|FAILED",
  "created_at": "2024-01-01T12:00:00",
  "updated_at": "2024-01-01T12:05:00",
  "filename": "video.mp4",
  "fileSize": 1234567,
  "chunks_processed": 3,
  "total_chunks": 5,
  "report": "Full analysis report...", // Only if COMPLETE
  "error": "Error message..." // Only if FAILED
}
```

### 3. List All Jobs
```http
GET /v1/jobs?skip=0&limit=100&status=COMPLETE
```

**Query Parameters:**
- `skip`: Number of jobs to skip (pagination)
- `limit`: Maximum number of jobs to return
- `status`: Filter by job status (optional)

### 4. Delete Job
```http
DELETE /v1/jobs/{jobId}
```

### 5. Health Check
```http
GET /health
```

## Installation & Setup

### Prerequisites
- Python 3.8+
- FFmpeg installed and available in PATH
- Google Gemini API key

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Install FFmpeg
**Windows:**
```bash
# Using chocolatey
choco install ffmpeg

# Or download from https://ffmpeg.org/download.html
```

**macOS:**
```bash
brew install ffmpeg
```

**Linux:**
```bash
sudo apt update
sudo apt install ffmpeg
```

### 3. Configure API Key
The Gemini API key is already configured in the code. For production, move it to environment variables.

### 4. Run the Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Test Database Setup
```bash
python test_db.py
```

## Usage Examples

### Upload a Video File
```bash
# Using curl (Git Bash/WSL)
curl -F "file=@/path/to/video.mp4" http://localhost:8000/v1/analyze

# Using Python
import requests

with open("video.mp4", "rb") as f:
    files = {"file": f}
    response = requests.post("http://localhost:8000/v1/analyze", files=files)
    print(response.json())
```

### Check Job Status
```bash
curl http://localhost:8000/v1/analyze/status/{jobId}
```

### List All Jobs
```bash
curl http://localhost:8000/v1/jobs
```

## Project Structure

```
code_four/
├── app/
│   ├── main.py          # FastAPI application and endpoints
│   ├── models.py        # SQLAlchemy models
│   ├── database.py      # Database configuration
│   ├── api/             # API route modules
│   ├── workers/         # Background worker modules
│   └── utils/           # Utility functions
├── uploads/             # Uploaded video files
├── chunks/              # Temporary video chunks
├── reports/             # Generated reports
├── jobs.db              # SQLite database
├── requirements.txt     # Python dependencies
├── test_db.py          # Database test script
└── README.md           # This file
```

## Database Schema

### Jobs Table
- `id`: Primary key (UUID)
- `status`: Job status (PENDING, PROCESSING, COMPLETE, FAILED)
- `created_at`: Job creation timestamp
- `updated_at`: Last update timestamp
- `video_path`: Path to uploaded video file
- `video_filename`: Original filename
- `video_size`: File size in bytes
- `report`: Generated analysis report (text)
- `error`: Error message if failed
- `chunks_processed`: Number of chunks processed
- `total_chunks`: Total number of chunks

## Background Processing

1. **Video Upload**: File is saved to disk and job is created in database
2. **Video Chunking**: FFmpeg splits video into 5-minute segments
3. **AI Analysis**: Each chunk is sent to Gemini Vision API for analysis
4. **Report Generation**: Individual summaries are combined into final report
5. **Status Update**: Job status is updated throughout the process

## Error Handling

- File validation (video format, size limits)
- Database transaction rollback on errors
- Graceful handling of FFmpeg failures
- API error responses with detailed messages

## Development

### Testing
```bash
# Test database functionality
python test_db.py

# Run with auto-reload
uvicorn app.main:app --reload
```

### API Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Production Considerations

- Use environment variables for API keys
- Implement proper logging
- Add authentication/authorization
- Use Redis for job queue management
- Implement file cleanup policies
- Add monitoring and health checks
- Use a production ASGI server (Gunicorn + Uvicorn)