from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional

class ElectricityRecordBase(BaseModel):
    record_date: date
    balance: float
    consumption: Optional[float] = None
    is_abnormal: bool = False
    anomaly_reason: Optional[str] = None

class ElectricityRecordResponse(ElectricityRecordBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
