from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class RechargeRecordCreate(BaseModel):
    amount: float
    recharge_date: Optional[datetime] = None

class RechargeRecordResponse(BaseModel):
    id: int
    amount: float
    recharge_date: datetime
    is_settled: bool
    settled_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True
