from datetime import datetime
from sqlalchemy import Column, Integer, Float, DateTime
from app.core.database import Base

class IntradayBalanceRecord(Base):
    __tablename__ = "intraday_balance_records"

    id = Column(Integer, primary_key=True, index=True)
    query_time = Column(DateTime, default=datetime.utcnow, index=True)
    balance = Column(Float, nullable=False)  # stored in degrees (度)
