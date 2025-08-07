from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Get database URL from environment or config
def get_database_url():
    return os.getenv("DATABASE_URL", "sqlite:///./healthcare_dev.db")

# Create engine dynamically
def create_database_engine():
    return create_engine(get_database_url())

# Create engine instance
engine = create_database_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def recreate_engine():
    """Recreate the engine with updated database URL"""
    global engine, SessionLocal
    engine = create_database_engine()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) 