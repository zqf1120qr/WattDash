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
        
        # 4. Today and yesterday consumption
        today_record = db.query(ElectricityRecord).filter(ElectricityRecord.record_date == today).first()
        today_consumption = round(today_record.consumption, 2) if (today_record and today_record.consumption is not None) else None
        today_consumption_yuan = round(today_consumption * 0.5, 2) if today_consumption is not None else None
        
        yesterday = today - timedelta(days=1)
        yesterday_record = db.query(ElectricityRecord).filter(ElectricityRecord.record_date == yesterday).first()
        yesterday_consumption = round(yesterday_record.consumption, 2) if (yesterday_record and yesterday_record.consumption is not None) else None
        yesterday_consumption_yuan = round(yesterday_consumption * 0.5, 2) if yesterday_consumption is not None else None
        
        # 5. 7-day average and endurance estimation
        seven_days_ago = today - timedelta(days=7)
        seven_days_records = (
            db.query(ElectricityRecord)
            .filter(
                and_(
                    ElectricityRecord.record_date >= seven_days_ago,
                    ElectricityRecord.consumption != None
                )
            )
            .all()
        )
        if seven_days_records:
            seven_day_avg = round(sum(r.consumption for r in seven_days_records) / len(seven_days_records), 2)
        elif month_usage > 0:
            seven_day_avg = round(month_usage / (today.day or 1), 2)
        else:
            seven_day_avg = 0.0
            
        seven_day_avg_yuan = round(seven_day_avg * 0.5, 2)
        
        if seven_day_avg > 0 and balance > 0:
            estimated_days_left = round(balance / seven_day_avg, 1)
            estimated_end_date = (today + timedelta(days=int(estimated_days_left))).strftime("%m月%d日")
        else:
            estimated_days_left = None
            estimated_end_date = None
            
        # 6. Usage diagnosis & adjustment tips
        if seven_day_avg < 3.0:
            usage_level = "low"
            usage_level_label = "极省节能"
            adjustment_advice = "寝室用电非常节约，能耗指标优秀，保持良好习惯即可！"
        elif seven_day_avg <= 7.0:
            usage_level = "normal"
            usage_level_label = "正常用电"
            adjustment_advice = "生活用电处于正常合理区间。建议空调保持在 26℃，夜间配合定时或睡眠模式。"
        else:
            usage_level = "high"
            usage_level_label = "用电偏高"
            adjustment_advice = "近期日均用电偏高！建议排查空调长时间低温运行、大功率设备待机或排插常开未关。"
            
        recharge_reminder = None
        if estimated_days_left is not None and estimated_days_left < 3.0:
            recharge_reminder = f"当前余额预计仅剩约 {estimated_days_left} 天，请及时充值以免夜间断电！"
            
        return {
            "latest_balance": balance,
            "latest_balance_yuan": round(balance * 0.5, 2),
            "update_time": update_time,
            "month_cumulative_consumption": round(month_usage, 2),
            "month_cumulative_consumption_yuan": round(month_usage * 0.5, 2),
            "has_anomaly": has_anomaly,
            "anomaly_reason": anomaly_reason,
            "today_consumption": today_consumption,
            "today_consumption_yuan": today_consumption_yuan,
            "yesterday_consumption": yesterday_consumption,
            "yesterday_consumption_yuan": yesterday_consumption_yuan,
            "seven_day_avg": seven_day_avg,
            "seven_day_avg_yuan": seven_day_avg_yuan,
            "estimated_days_left": estimated_days_left,
            "estimated_end_date": estimated_end_date,
            "usage_level": usage_level,
            "usage_level_label": usage_level_label,
            "adjustment_advice": adjustment_advice,
            "recharge_reminder": recharge_reminder
        }

    @staticmethod
    def get_daily_records(db: Session, limit: int = 15) -> List[Dict[str, Any]]:
        """
        Fetch daily consumption details for the past N records with day-over-day changes,
        energy classification tags, and associated recharge info.
        """
        records = (
            db.query(ElectricityRecord)
            .order_by(ElectricityRecord.record_date.desc())
            .limit(limit + 1)
            .all()
        )
        if not records:
            return []
            
        min_date = records[-1].record_date
        max_date = records[0].record_date
        start_dt = datetime.combine(min_date, datetime.min.time())
        end_dt = datetime.combine(max_date, datetime.max.time())
        
        recharges = (
            db.query(RechargeRecord)
            .filter(and_(RechargeRecord.recharge_date >= start_dt, RechargeRecord.recharge_date <= end_dt))
            .all()
        )
        
        recharge_map = {}
        for r in recharges:
            if r.recharge_date:
                d = r.recharge_date.date()
                recharge_map[d] = recharge_map.get(d, 0.0) + r.amount

        today = date.today()
        yesterday = today - timedelta(days=1)
        weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        
        record_map = {r.record_date: r for r in records}
        display_records = records[:limit]
        results = []
        
        for r in display_records:
            r_date = r.record_date
            if r_date == today:
                date_label = "今天"
            elif r_date == yesterday:
                date_label = "昨天"
            else:
                date_label = weekdays[r_date.weekday()]
                
            cons = round(r.consumption, 2) if r.consumption is not None else None
            cons_yuan = round(cons * 0.5, 2) if cons is not None else None
            
            prev_cal_date = r_date - timedelta(days=1)
            prev_r = record_map.get(prev_cal_date)
            
            diff_from_yesterday = None
            diff_percent = None
            if cons is not None and prev_r and prev_r.consumption is not None:
                diff_from_yesterday = round(cons - prev_r.consumption, 2)
                if prev_r.consumption > 0:
                    diff_percent = round((diff_from_yesterday / prev_r.consumption) * 100, 1)
                else:
                    diff_percent = 0.0
                    
            if cons is None:
                energy_level = "unknown"
                energy_level_label = "计算中"
            elif cons < 3.0:
                energy_level = "low"
                energy_level_label = "极省"
            elif cons <= 7.0:
                energy_level = "normal"
                energy_level_label = "正常"
            else:
                energy_level = "high"
                energy_level_label = "偏高"
                
            results.append({
                "id": r.id,
                "record_date": r_date.isoformat(),
                "date_display": r_date.strftime("%m-%d"),
                "date_label": date_label,
                "consumption": cons,
                "consumption_yuan": cons_yuan,
                "balance": round(r.balance, 2),
                "balance_yuan": round(r.balance * 0.5, 2),
                "is_abnormal": r.is_abnormal,
                "anomaly_reason": r.anomaly_reason,
                "diff_from_yesterday": diff_from_yesterday,
                "diff_percent": diff_percent,
                "recharge_amount": round(recharge_map.get(r_date, 0.0), 2) if recharge_map.get(r_date, 0.0) > 0 else None,
                "energy_level": energy_level,
                "energy_level_label": energy_level_label
            })
            
        return results

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
