from sqlalchemy import Column, String, DateTime, Text, Integer
from .database import Base
from datetime import datetime

class Job(Base):
    __tablename__ = "jobs"

    # same UUID you used before
    id = Column(String, primary_key=True, index=True)

    status     = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    video_path = Column(String, nullable=False)
    video_filename = Column(String, nullable=True)
    video_size = Column(Integer, nullable=True)  # file size in bytes

    # store the full report in text form
    report = Column(Text, nullable=True)
    error  = Column(Text, nullable=True)
    
    # processing metadata
    chunks_processed = Column(Integer, default=0)
    total_chunks = Column(Integer, default=0)
