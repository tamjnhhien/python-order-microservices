from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from databases import Database
from src.models.order import Base

DATABASE_URL = "sqlite:///./orders.db"

# Async database connection
database = Database(DATABASE_URL)

# Sync database connection for table creation
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_tables():
    """Create database tables"""
    Base.metadata.create_all(bind=engine)

async def get_database():
    """Get database connection"""
    return database