import logging
from datetime import date, datetime, time
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.electricity import ElectricityRecord
from app.models.recharge import RechargeRecord

logger = logging.getLogger("wattdash.calculator")

class CalculatorService:
    @staticmethod
    def calculate_daily_consumption(db: Session, today_balance: float, today_date: date) -> ElectricityRecord:
        """
        Calculate consumption for the given date based on today's balance,
        yesterday's balance, and pending recharges.
        """
        # Find the latest normal (non-abnormal) record before today to use as baseline.
        # This prevents sync failure records (e.g. yesterday's failed run with 0.0 balance) from polluting the baseline.
        prev_record = (
            db.query(ElectricityRecord)
            .filter(
                and_(
                    ElectricityRecord.record_date < today_date,
                    ElectricityRecord.is_abnormal == False
                )
            )
            .order_by(ElectricityRecord.record_date.desc())
            .first()
        )
        
        # If there's an existing record for today_date, we will update it.
        # To avoid double-counting or missing recharges, we temporarily reset 
        # any recharges that were already settled today to 'unsettled'.
        existing_today = (
            db.query(ElectricityRecord)
            .filter(ElectricityRecord.record_date == today_date)
            .first()
        )
        
        start_of_today = datetime.combine(today_date, time.min)
        if existing_today:
            # Find recharges settled today and mark them unsettled temporarily for recalculation
            settled_today = (
                db.query(RechargeRecord)
                .filter(
                    and_(
                        RechargeRecord.is_settled == True,
                        RechargeRecord.settled_at >= start_of_today
                    )
                )
                .all()
            )
            for r in settled_today:
                r.is_settled = False
                r.settled_at = None
            db.flush()
            
        # Get all unsettled recharge records
        unsettled_recharges = (
            db.query(RechargeRecord)
            .filter(RechargeRecord.is_settled == False)
            .order_by(RechargeRecord.recharge_date.asc())
            .all()
        )
        recharge_sum = sum(r.amount for r in unsettled_recharges)
        
        # Bootstrap phase: no previous record
        if not prev_record:
            logger.info("No previous electricity record found. Initializing baseline...")
            if existing_today:
                record = existing_today
                record.balance = today_balance
                record.consumption = 0.0
                record.is_abnormal = False
                record.anomaly_reason = None
            else:
                record = ElectricityRecord(
                    record_date=today_date,
                    balance=today_balance,
                    consumption=0.0,
                    is_abnormal=False
                )
                db.add(record)
            
            # Since there is no baseline, all existing recharges up to today are marked settled
            for r in unsettled_recharges:
                r.is_settled = True
                r.settled_at = datetime.utcnow()
                
            db.commit()
            return record
            
        # Calculation logic
        prev_balance = prev_record.balance
        recharge_sum_degrees = recharge_sum * 2.0
        consumption = prev_balance + recharge_sum_degrees - today_balance
        
        is_abnormal = False
        anomaly_reason = None
        
        if recharge_sum > 0:
            if consumption >= 0:
                # Normal case: user recharged and consumption is positive
                logger.info(f"Recharge of {recharge_sum} Yuan ({recharge_sum_degrees} degrees) found. Consumption calculated: {consumption} degrees")
                for r in unsettled_recharges:
                    r.is_settled = True
                    r.settled_at = datetime.utcnow()
            else:
                # Anomaly: consumption is negative even with recharge (e.g. wrong input)
                logger.warning(f"Abnormal negative consumption: {consumption} (recharge={recharge_sum} Yuan)")
                is_abnormal = True
                anomaly_reason = (
                    f"计算得到的耗电量为负数（昨日 {prev_balance:.2f} 度 + "
                    f"充值折算电量 {recharge_sum_degrees:.2f} 度 - 今日 {today_balance:.2f} 度 = {consumption:.2f} 度）。"
                    f"请核对充值金额。"
                )
                consumption = None
        else:
            # No recharges registered
            if today_balance > prev_balance:
                # Anomaly: balance increased but no recharge recorded
                logger.warning(f"Balance increased from {prev_balance} to {today_balance} without recharge!")
                is_abnormal = True
                anomaly_reason = (
                    f"检测到未登记的余额增加（昨日 {prev_balance:.2f} -> 今日 {today_balance:.2f}），"
                    f"请补录充值金额。"
                )
                consumption = None
            else:
                # Normal day-to-day consumption
                logger.info(f"Normal consumption: {consumption}")
                
        # Save or update record
        if existing_today:
            record = existing_today
            record.balance = today_balance
            record.consumption = consumption
            record.is_abnormal = is_abnormal
            record.anomaly_reason = anomaly_reason
        else:
            record = ElectricityRecord(
                record_date=today_date,
                balance=today_balance,
                consumption=consumption,
                is_abnormal=is_abnormal,
                anomaly_reason=anomaly_reason
            )
            db.add(record)
            
        db.commit()
        return record

    @staticmethod
    def retroactive_settlement(db: Session) -> Optional[ElectricityRecord]:
        """
        Retroactively resolve the latest abnormal electricity record if new recharges are added.
        """
        # Find the latest abnormal record
        abnormal_record = (
            db.query(ElectricityRecord)
            .filter(ElectricityRecord.is_abnormal == True)
            .order_by(ElectricityRecord.record_date.desc())
            .first()
        )
        
        if not abnormal_record:
            return None
            
        # Find the latest normal record prior to the abnormal record
        prev_record = (
            db.query(ElectricityRecord)
            .filter(
                and_(
                    ElectricityRecord.record_date < abnormal_record.record_date,
                    ElectricityRecord.is_abnormal == False
                )
            )
            .order_by(ElectricityRecord.record_date.desc())
            .first()
        )
        
        # Fetch all unsettled recharges
        unsettled_recharges = (
            db.query(RechargeRecord)
            .filter(RechargeRecord.is_settled == False)
            .order_by(RechargeRecord.recharge_date.asc())
            .all()
        )
        recharge_sum = sum(r.amount for r in unsettled_recharges)
        
        if not prev_record:
            logger.info("No previous normal record found during retroactive settlement. Bootstrapping abnormal record as baseline.")
            abnormal_record.consumption = 0.0
            abnormal_record.is_abnormal = False
            abnormal_record.anomaly_reason = None
            
            for r in unsettled_recharges:
                r.is_settled = True
                r.settled_at = datetime.utcnow()
                
            db.commit()
            return abnormal_record
        
        if recharge_sum == 0:
            return None
            
        # Recalculate
        recharge_sum_degrees = recharge_sum * 2.0
        consumption = prev_record.balance + recharge_sum_degrees - abnormal_record.balance
        
        if consumption >= 0:
            logger.info(f"Resolving anomaly for {abnormal_record.record_date}. New consumption: {consumption} degrees")
            abnormal_record.consumption = consumption
            abnormal_record.is_abnormal = False
            abnormal_record.anomaly_reason = None
            
            # Mark all these recharges as settled
            for r in unsettled_recharges:
                r.is_settled = True
                r.settled_at = datetime.utcnow()
                
            db.commit()
            return abnormal_record
        else:
            logger.warning(
                f"Retroactive recalculation still negative: {consumption} degrees "
                f"(prev={prev_record.balance}, recharge={recharge_sum} Yuan, abnormal={abnormal_record.balance})"
            )
            abnormal_record.anomaly_reason = (
                f"补录后计算得到的耗电量仍为负数（昨日 {prev_record.balance:.2f} 度 + "
                f"已补录充值折算电量 {recharge_sum_degrees:.2f} 度 - 今日 {abnormal_record.balance:.2f} 度 = {consumption:.2f} 度）。"
                f"请核对充值金额。"
            )
            db.commit()
            return abnormal_record
