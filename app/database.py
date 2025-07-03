from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 1) Point at a file in your project root:
DATABASE_URL = "sqlite:///./jobs.db"

# 2) SQLite needs this flag on Windows
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

# 3) Session factory
SessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine
)

# 4) Base class for models
Base = declarative_base()

# 5) Dependency for FastAPI
from fastapi import Depends
from sqlalchemy.orm import Session

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
