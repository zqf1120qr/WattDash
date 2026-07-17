from datetime import datetime
from sqlalchemy import Column, Integer, Float, Date, DateTime, Boolean, String
from app.core.database import Base

class ElectricityRecord(Base):
    __tablename__ = "electricity_records"

    id = Column(Integer, primary_key=True, index=True)
    record_date = Column(Date, unique=True, index=True, nullable=False)  # One record per day
    balance = Column(Float, nullable=False)                              # Current electricity balance (元)
    consumption = Column(Float, nullable=True)                           # Actual day's consumption (元)
    
    # Anomaly tracking
    is_abnormal = Column(Boolean, default=False, index=True)             # True if balance rose without registration
    anomaly_reason = Column(String, nullable=True)                       # Explanation of why it is marked abnormal
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
