import logging
from datetime import datetime
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.system_log import SystemLog

logger = logging.getLogger("wattdash.log_service")

class LogService:
    @staticmethod
    def add_log(db: Session, message: str, level: str = "info") -> SystemLog:
        """
        Add a system log to the database. Auto-prunes if database log size exceeds 100 entries.
        """
        log_entry = SystemLog(
            log_time=datetime.utcnow(),
            level=level,
            message=message
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        
        # Auto-prune system logs: keep only the latest 100 entries to prevent database bloating
        try:
            total_logs = db.query(SystemLog).count()
            if total_logs > 100:
                # Find the threshold log entry (the 100th latest log)
                threshold_log = (
                    db.query(SystemLog)
                    .order_by(SystemLog.log_time.desc())
                    .offset(100)
                    .first()
                )
                if threshold_log:
                    db.query(SystemLog).filter(SystemLog.log_time <= threshold_log.log_time).delete()
                    db.commit()
        except Exception as e:
            logger.error(f"Failed to prune system logs: {e}")
            db.rollback()
            
        return log_entry

    @classmethod
    def add_log_background(cls, message: str, level: str = "info") -> None:
        """
        Add a log entry in background threads (e.g. from Scheduler) without needing an active request DB session.
        """
        db = SessionLocal()
        try:
            cls.add_log(db, message, level)
        except Exception as e:
            logger.error(f"Failed to add background log: {e}")
        finally:
            db.close()
