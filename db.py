from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from models import Base

# ------------------------------
# Database setup
# ------------------------------
DATABASE_URL = "sqlite:///./capstone_repo.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

# ------------------------------
# Dependency
# ------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_db_session() -> Session:
    db = SessionLocal()
    return db