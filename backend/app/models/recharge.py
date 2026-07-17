from datetime import datetime
from sqlalchemy import Column, Integer, Float, DateTime, Boolean
from app.core.database import Base

class RechargeRecord(Base):
    __tablename__ = "recharge_records"

    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float, nullable=False)                               # Recharge amount (元)
    recharge_date = Column(DateTime, default=datetime.utcnow, nullable=False) # Actual recharge time
    
    # Settlement flags
    is_settled = Column(Boolean, default=False, index=True)              # Has this recharge been factored into consumption calculation?
    settled_at = Column(DateTime, nullable=True)                         # When it was factored in
    
    created_at = Column(DateTime, default=datetime.utcnow)
