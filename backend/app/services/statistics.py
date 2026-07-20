from datetime import date, datetime, timedelta, timezone as dt_timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import extract, and_
from app.models.electricity import ElectricityRecord
from app.models.recharge import RechargeRecord
from app.models.intraday_balance import IntradayBalanceRecord

class StatisticsService:
    @staticmethod
    def get_dashboard_overview(db: Session) -> Dict[str, Any]:
        """
        Fetch summary cards data: latest balance, update time, monthly usage, and current warnings.
        """
        # Run a quick retroactive check to self-heal any pending anomalies
        from app.services.calculator import CalculatorService
        try:
            CalculatorService.retroactive_settlement(db)
        except Exception as e:
            import logging
            logging.getLogger("wattdash.statistics").error(f"Error running auto-retroactive settlement: {e}")

        # 1. Fetch latest record
        latest_record = (
            db.query(ElectricityRecord)
            .order_by(ElectricityRecord.record_date.desc())
            .first()
        )
        
        balance = latest_record.balance if latest_record else 0.0
        
        # Fetch the latest successful query time from IntradayBalanceRecord
        latest_success = (
            db.query(IntradayBalanceRecord)
            .order_by(IntradayBalanceRecord.query_time.desc())
            .first()
        )
        
        if latest_success:
            utc_update = latest_success.query_time.replace(tzinfo=dt_timezone.utc)
            local_update = utc_update.astimezone(dt_timezone(timedelta(hours=8)))
            update_time = local_update.strftime("%Y-%m-%d %H:%M:%S")
        elif latest_record and latest_record.updated_at:
            utc_update = latest_record.updated_at.replace(tzinfo=dt_timezone.utc)
            local_update = utc_update.astimezone(dt_timezone(timedelta(hours=8)))
            update_time = local_update.strftime("%Y-%m-%d %H:%M:%S")
        else:
            update_time = "暂无记录"
        
        # 2. Check for active anomalies
        has_anomaly = latest_record.is_abnormal if latest_record else False
        anomaly_reason = latest_record.anomaly_reason if latest_record and latest_record.is_abnormal else None
        
        # 3. Calculate current month cumulative consumption
        today = date.today()
        month_start = date(today.year, today.month, 1)
        
        month_records = (
            db.query(ElectricityRecord)
            .filter(
                and_(
                    ElectricityRecord.record_date >= month_start,
                    ElectricityRecord.consumption != None
                )
            )
            .all()
        )
        month_usage = sum(r.consumption for r in month_records)
        
        return {
            "latest_balance": balance,
            "latest_balance_yuan": round(balance * 0.5, 2),
            "update_time": update_time,
            "month_cumulative_consumption": round(month_usage, 2),
            "month_cumulative_consumption_yuan": round(month_usage * 0.5, 2),
            "has_anomaly": has_anomaly,
            "anomaly_reason": anomaly_reason
        }

    @classmethod
    def get_trend_data(cls, db: Session, days: Optional[int] = 30, start_date_str: Optional[str] = None, end_date_str: Optional[str] = None) -> Dict[str, List[Any]]:
        """
        Fetch trend arrays of past N days or custom date range for ECharts.
        """
        if start_date_str and end_date_str:
            try:
                start_date = date.fromisoformat(start_date_str)
                end_date = date.fromisoformat(end_date_str)
                days = (end_date - start_date).days + 1
                if days <= 0:
                    days = 7
                    start_date = date.today() - timedelta(days=6)
            except ValueError:
                days = 7
                start_date = date.today() - timedelta(days=6)
        else:
            if days is None:
                days = 30
            start_date = date.today() - timedelta(days=days - 1)
            
        records = (
            db.query(ElectricityRecord)
            .filter(and_(ElectricityRecord.record_date >= start_date, ElectricityRecord.record_date <= (start_date + timedelta(days=days - 1))))
            .order_by(ElectricityRecord.record_date.asc())
            .all()
        )
        
        # Format lists for ECharts
        dates = []
        balances = []
        consumptions = []
        
        # Create a dict of existing records for easy lookup
        record_map = {r.record_date: r for r in records}
        
        # Iterate over all dates in range to prevent gaps in charts
        for i in range(days):
            curr_date = start_date + timedelta(days=i)
            date_str = curr_date.strftime("%m-%d")
            dates.append(date_str)
            
            record = record_map.get(curr_date)
            if record:
                balances.append(record.balance)
                consumptions.append(record.consumption)
            else:
                prev_known = balances[-1] if balances else 0.0
                balances.append(prev_known)
                consumptions.append(None)
                
        return {
            "dates": dates,
            "balances": balances,
            "balances_yuan": [round(b * 0.5, 2) for b in balances],
            "consumptions": [round(c, 2) if c is not None else None for c in consumptions],
            "consumptions_yuan": [round(c * 0.5, 2) if c is not None else None for c in consumptions]
        }

    @staticmethod
    def get_intraday_data(db: Session, date_str: Optional[str] = None) -> Dict[str, List[Any]]:
        """
        Fetch intraday (hourly) balance records for a specific date (local Beijing time).
        Also prepends the last query record from the previous day to visualize overnight changes.
        """
        shanghai_tz = dt_timezone(timedelta(hours=8))
        if date_str:
            try:
                local_date = date.fromisoformat(date_str)
                local_now = datetime(local_date.year, local_date.month, local_date.day, 0, 0, 0, tzinfo=shanghai_tz)
            except ValueError:
                local_now = datetime.now(shanghai_tz)
        else:
            local_now = datetime.now(shanghai_tz)
            
        local_today_start = datetime(local_now.year, local_now.month, local_now.day, 0, 0, 0, tzinfo=shanghai_tz)
        local_today_end = datetime(local_now.year, local_now.month, local_now.day, 23, 59, 59, tzinfo=shanghai_tz)
        
        utc_today_start = local_today_start.astimezone(dt_timezone.utc).replace(tzinfo=None)
        utc_today_end = local_today_end.astimezone(dt_timezone.utc).replace(tzinfo=None)
        
        # 1. Fetch target day's records
        records = (
            db.query(IntradayBalanceRecord)
            .filter(and_(IntradayBalanceRecord.query_time >= utc_today_start, IntradayBalanceRecord.query_time <= utc_today_end))
            .order_by(IntradayBalanceRecord.query_time.asc())
            .all()
        )
        
        # 2. Fetch the last record from the previous day
        local_yesterday_start = local_today_start - timedelta(days=1)
        local_yesterday_end = local_today_start - timedelta(seconds=1)
        utc_yesterday_start = local_yesterday_start.astimezone(dt_timezone.utc).replace(tzinfo=None)
        utc_yesterday_end = local_yesterday_end.astimezone(dt_timezone.utc).replace(tzinfo=None)
        
        yesterday_last = (
            db.query(IntradayBalanceRecord)
            .filter(and_(IntradayBalanceRecord.query_time >= utc_yesterday_start, IntradayBalanceRecord.query_time <= utc_yesterday_end))
            .order_by(IntradayBalanceRecord.query_time.desc())
            .first()
        )
        
        records_to_process = []
        if yesterday_last:
            records_to_process.append(yesterday_last)
        records_to_process.extend(records)
        
        times = []
        balances_degrees = []
        balances_yuan = []
        
        for r in records_to_process:
            local_time = r.query_time.replace(tzinfo=dt_timezone.utc).astimezone(shanghai_tz)
            if local_time.date() < local_today_start.date():
                time_str = f"昨日 {local_time.strftime('%H:%M')}"
            else:
                time_str = local_time.strftime("%H:%M")
                
            times.append(time_str)
            balances_degrees.append(round(r.balance, 2))
            balances_yuan.append(round(r.balance * 0.5, 2))
            
        return {
            "times": times,
            "balances": balances_degrees,
            "balances_yuan": balances_yuan
        }
