from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from app.core.database import Base

class SystemLog(Base):
    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True, index=True)
    log_time = Column(DateTime, default=datetime.utcnow, index=True)
    level = Column(String, nullable=False)  # "info", "success", "warning", "error"
    message = Column(String, nullable=False)
