import logging
from datetime import date, datetime, time, timedelta
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.electricity import ElectricityRecord
from app.models.recharge import RechargeRecord
from app.models.intraday_balance import IntradayBalanceRecord

logger = logging.getLogger("wattdash.calculator")

# Recharge delay protection: recharges registered within this window (seconds)
# are considered "recent" and may not yet be reflected by the school gateway.
RECHARGE_GRACE_PERIOD_SECONDS = 30 * 60  # 30 minutes

# If consumption exceeds this threshold (in degrees/kWh), and there are recent
# recharges, the calculator will exclude those recharges to avoid false spikes.
ABNORMAL_CONSUMPTION_THRESHOLD = 50.0  # 50 kWh (~25 Yuan) per day


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
                # ========== RECHARGE DELAY PROTECTION ==========
                # Check if the consumption is abnormally high AND there are recently
                # registered recharges. If so, the gateway may not have reflected the
                # recharge yet, causing a false consumption spike.
                if consumption > ABNORMAL_CONSUMPTION_THRESHOLD:
                    now = datetime.utcnow()
                    grace_cutoff = now - timedelta(seconds=RECHARGE_GRACE_PERIOD_SECONDS)
                    
                    # Split recharges into "stable" (registered before grace period) and "recent"
                    recent_recharges = [r for r in unsettled_recharges if r.created_at and r.created_at > grace_cutoff]
                    stable_recharges = [r for r in unsettled_recharges if r not in recent_recharges]
                    
                    if recent_recharges:
                        recent_sum = sum(r.amount for r in recent_recharges)
                        stable_sum = sum(r.amount for r in stable_recharges)
                        stable_sum_degrees = stable_sum * 2.0
                        
                        # Recalculate without recent recharges
                        consumption_without_recent = prev_balance + stable_sum_degrees - today_balance
                        
                        logger.warning(
                            f"Recharge delay protection triggered! "
                            f"Full consumption={consumption:.2f} degrees exceeds threshold={ABNORMAL_CONSUMPTION_THRESHOLD}. "
                            f"Recent recharges ({recent_sum} Yuan, {len(recent_recharges)} records) within {RECHARGE_GRACE_PERIOD_SECONDS}s grace period. "
                            f"Recalculated without recent: {consumption_without_recent:.2f} degrees."
                        )
                        
                        # Use the recalculated value (may be negative if no stable recharges exist,
                        # in which case it will be handled by the normal anomaly logic below)
                        if consumption_without_recent >= 0:
                            consumption = consumption_without_recent
                            # Only settle stable recharges; recent ones stay unsettled
                            for r in stable_recharges:
                                r.is_settled = True
                                r.settled_at = datetime.utcnow()
                            # Recent recharges remain is_settled=False for next sync cycle
                            logger.info(
                                f"Settled {len(stable_recharges)} stable recharges. "
                                f"Deferred {len(recent_recharges)} recent recharges ({recent_sum} Yuan) to next sync."
                            )
                        else:
                            # Even without recent recharges, balance increased without explanation
                            # → treat as normal anomaly (balance increase without recharge)
                            is_abnormal = True
                            anomaly_reason = (
                                f"充值延迟保护：排除近期充值后余额仍异常增加"
                                f"（昨日 {prev_balance:.2f} 度 + 已稳定充值 {stable_sum_degrees:.2f} 度 "
                                f"- 今日 {today_balance:.2f} 度 = {consumption_without_recent:.2f} 度）。"
                                f"近期充值 {recent_sum} 元已暂缓结算，待下次同步自动消化。"
                            )
                            consumption = None
                    else:
                        # All recharges are "stable" (old enough), high consumption is genuine
                        logger.info(f"Recharge of {recharge_sum} Yuan ({recharge_sum_degrees} degrees) found. Consumption calculated: {consumption} degrees")
                        for r in unsettled_recharges:
                            r.is_settled = True
                            r.settled_at = datetime.utcnow()
                else:
                    # Normal case: consumption within reasonable bounds
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
    def recalculate_today(db: Session) -> dict:
        """
        Manually recalculate today's electricity record by:
        1. Resetting all recharges settled today to unsettled
        2. Using the latest intraday balance snapshot to recalculate
        
        Returns a dict with the result status and updated record info.
        """
        today_date = date.today()
        start_of_today = datetime.combine(today_date, time.min)
        
        # 1. Reset all recharges settled today back to unsettled
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
        reset_count = len(settled_today)
        for r in settled_today:
            r.is_settled = False
            r.settled_at = None
        db.flush()
        
        # 2. Get the latest intraday balance snapshot for today
        from datetime import timezone
        shanghai_tz = timezone(timedelta(hours=8))
        
        local_today_start = datetime(today_date.year, today_date.month, today_date.day, 0, 0, 0, tzinfo=shanghai_tz)
        utc_today_start = local_today_start.astimezone(timezone.utc).replace(tzinfo=None)
        
        latest_intraday = (
            db.query(IntradayBalanceRecord)
            .filter(IntradayBalanceRecord.query_time >= utc_today_start)
            .order_by(IntradayBalanceRecord.query_time.desc())
            .first()
        )
        
        if not latest_intraday:
            existing_today = (
                db.query(ElectricityRecord)
                .filter(ElectricityRecord.record_date == today_date)
                .first()
            )
            if existing_today:
                today_balance = existing_today.balance
            else:
                db.rollback()
                return {
                    "status": "error",
                    "msg": "今日暂无同步记录，无法重新计算。请先执行一键刷新获取最新数据。"
                }
        else:
            today_balance = latest_intraday.balance
        
        # 3. Recalculate using the standard calculation method
        record = CalculatorService.calculate_daily_consumption(db, today_balance, today_date)
        
        result = {
            "status": "success",
            "msg": f"重算完成！已重置 {reset_count} 条充值结算记录。",
            "record": {
                "record_date": record.record_date.isoformat(),
                "balance": record.balance,
                "consumption": record.consumption,
                "is_abnormal": record.is_abnormal,
                "anomaly_reason": record.anomaly_reason
            }
        }
        
        if record.is_abnormal:
            result["msg"] += f" 当前仍存在异常：{record.anomaly_reason}"
        else:
            cons_str = f"{record.consumption:.2f} 度" if record.consumption is not None else "-- 度"
            result["msg"] += f" 今日耗电量修正为: {cons_str}。"
            
        return result

    @staticmethod
    def recalculate_after_recharge_deletion(db: Session, target_date: date) -> dict:
        """
        Recalculate consumption after a recharge record has been deleted/revoked.
        If target_date is today or in future, triggers full recalculate_today.
        If target_date is in the past, recalculates that historical day's consumption.
        """
        today_date = date.today()
        
        if target_date >= today_date:
            return CalculatorService.recalculate_today(db)
            
        # Target date is in the past
        existing_record = (
            db.query(ElectricityRecord)
            .filter(ElectricityRecord.record_date == target_date)
            .first()
        )
        if not existing_record:
            # If no record existed for that day, try to recalculate today
            return CalculatorService.recalculate_today(db)
            
        # Find previous normal record before target_date
        prev_record = (
            db.query(ElectricityRecord)
            .filter(
                and_(
                    ElectricityRecord.record_date < target_date,
                    ElectricityRecord.is_abnormal == False
                )
            )
            .order_by(ElectricityRecord.record_date.desc())
            .first()
        )
        
        if not prev_record:
            return {
                "status": "warning",
                "msg": f"未找到 {target_date} 之前的基准记录，无法自动重算历史耗电。"
            }
            
        day_start = datetime.combine(target_date, time.min)
        day_end = datetime.combine(target_date, time.max)
        day_recharges = (
            db.query(RechargeRecord)
            .filter(
                and_(
                    RechargeRecord.recharge_date >= day_start,
                    RechargeRecord.recharge_date <= day_end
                )
            )
            .all()
        )
        recharge_sum = sum(r.amount for r in day_recharges)
        recharge_sum_degrees = recharge_sum * 2.0
        
        consumption = prev_record.balance + recharge_sum_degrees - existing_record.balance
        if consumption >= 0:
            existing_record.consumption = consumption
            existing_record.is_abnormal = False
            existing_record.anomaly_reason = None
            for r in day_recharges:
                r.is_settled = True
                r.settled_at = datetime.utcnow()
            db.commit()
            return {
                "status": "success",
                "msg": f"历史充值记录撤回成功！{target_date} 耗电量已重新计算为 {consumption:.2f} 度。"
            }
        else:
            existing_record.consumption = None
            existing_record.is_abnormal = True
            existing_record.anomaly_reason = (
                f"撤销充值后计算耗电量为负数（昨日 {prev_record.balance:.2f} + "
                f"剩余充值 {recharge_sum_degrees:.2f} - 今日 {existing_record.balance:.2f} = {consumption:.2f} 度）"
            )
            db.commit()
            return {
                "status": "warning",
                "msg": f"充值撤回后，{target_date} 出现数据异常：{existing_record.anomaly_reason}"
            }

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
