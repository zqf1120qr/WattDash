from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    
    # Campus login credentials
    student_id = Column(String, nullable=True)
    gateway_password = Column(String, nullable=True)
    
    # Room parameters config JSON: {"aid": "...", "area": {...}, "building": {...}, "room": {...}}
    query_config = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
