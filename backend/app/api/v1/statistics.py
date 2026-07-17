from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.models.system_log import SystemLog
from app.services.statistics import StatisticsService
from app.services.log import LogService

router = APIRouter()

class LogCreateSchema(BaseModel):
    message: str
    level: str = "info"

@router.get("/overview")
def get_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get summary stats for the main cards (Latest Balance, Monthly usage, active alerts).
    """
    overview = StatisticsService.get_dashboard_overview(db)
    return overview

@router.get("/trends")
def get_trends(
    days: Optional[int] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get history trends for ECharts (line chart for balance, bar chart for consumption).
    """
    trends = StatisticsService.get_trend_data(db, days=days, start_date_str=start_date, end_date_str=end_date)
    return trends

@router.get("/logs")
def get_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get the latest 100 system logs from the database, sorted by time descending.
    """
    from datetime import timezone, timedelta
    shanghai_tz = timezone(timedelta(hours=8))
    
    logs = (
        db.query(SystemLog)
        .order_by(SystemLog.log_time.desc())
        .limit(100)
        .all()
    )
    return [
        {
            "id": log.id,
            "time": log.log_time.replace(tzinfo=timezone.utc).astimezone(shanghai_tz).strftime("%H:%M:%S") if log.log_time else "",
            "msg": log.message,
            "type": log.level
        }
        for log in logs
    ]

@router.post("/logs")
def add_manual_log(
    req: LogCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Add a manual log entry from the frontend client and return the refreshed logs array.
    """
    from datetime import timezone, timedelta
    shanghai_tz = timezone(timedelta(hours=8))
    
    LogService.add_log(db, req.message, req.level)
    
    # Return updated list of latest 100 logs
    updated_logs = (
        db.query(SystemLog)
        .order_by(SystemLog.log_time.desc())
        .limit(100)
        .all()
    )
    return [
        {
            "id": log.id,
            "time": log.log_time.replace(tzinfo=timezone.utc).astimezone(shanghai_tz).strftime("%H:%M:%S") if log.log_time else "",
            "msg": log.message,
            "type": log.level
        }
        for log in updated_logs
    ]

@router.delete("/logs")
def clear_all_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete all system logs from the database.
    """
    db.query(SystemLog).delete()
    db.commit()
    return []

@router.get("/intraday")
def get_intraday_trends(
    date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get hourly (intraday) balance records for a specific date (defaults to today).
    """
    data = StatisticsService.get_intraday_data(db, date_str=date)
    return data
