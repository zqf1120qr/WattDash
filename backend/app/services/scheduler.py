import logging
from datetime import date, datetime
from apscheduler.schedulers.background import BackgroundScheduler
from app.core.database import SessionLocal
from app.models.electricity import ElectricityRecord
from app.models.recharge import RechargeRecord
from app.models.intraday_balance import IntradayBalanceRecord
from app.services.spider import SpiderService
from app.services.calculator import CalculatorService
from app.services.log import LogService

logger = logging.getLogger("wattdash.scheduler")

scheduler = BackgroundScheduler()

def fetch_and_calculate_daily(is_end_of_day: bool = False):
    """
    Job executed daily at 8:00, 10:00, 12:00, 14:00, 16:00, 18:00, 20:00, 22:00 (hourly snapshots)
    and at 23:30 (end-of-day query and consumption calculation).
    """
    logger.info(f"Scheduler task triggered: Starting daily electricity sync (is_end_of_day={is_end_of_day})...")
    db = SessionLocal()
    time_label = "23:30结汇" if is_end_of_day else "分时查询"
    LogService.add_log(db, f"【定时自动同步】{time_label}任务启动，正在连接网关...", "info")
    today_date = date.today()
    
    try:
        # Get admin credentials and config
        from app.models.user import User
        admin_user = db.query(User).filter(User.username == "admin").first()
        query_config = admin_user.query_config if admin_user else None
        student_id = admin_user.student_id if admin_user else None
        gateway_password = admin_user.gateway_password if admin_user else None

        token = SpiderService.read_token()
        needs_login = not token
        query_result = None

        if token:
            LogService.add_log(db, "【定时自动同步】载入本地凭证成功，正在发送网关 API 请求...", "info")
            result = SpiderService.execute_query(token, query_config=query_config)
            if result.get("status") == "expired":
                logger.warning("Daily sync: Token expired. Triggering silent browser login...")
                LogService.add_log(db, "【定时自动同步】检测到本地凭证已失效，正在启动后台浏览器尝试自动静默登录与 SSO 刷新...", "warning")
                needs_login = True
            else:
                query_result = result

        if needs_login:
            if not student_id or not gateway_password:
                logger.error("Daily sync failed: Missing student_id or gateway_password.")
                LogService.add_log(db, "【定时自动同步】同步失败：学号或网关密码未在设置中配置，无法启动后台自动登录。", "error")
                if is_end_of_day:
                    _record_sync_failure(db, today_date, "未配置网关登录账号或密码")
                return

            # Run headless browser login step1
            login_res = SpiderService.login_step1(student_id, gateway_password, query_config)

            if login_res.get("status") == "success":
                token = SpiderService.read_token()
                if token:
                    LogService.add_log(db, "【定时自动同步】后台静默登录成功！正在使用新凭证重试数据拉取...", "success")
                    query_result = SpiderService.execute_query(token, query_config=query_config)
                else:
                    query_result = {"status": "error", "msg": "自动登录成功但读取新凭证失败"}
            elif login_res.get("status") == "need_sms":
                logger.warning("Daily sync: MFA verification code required.")
                LogService.add_log(db, "【定时自动同步】同步暂停：网关检测到新设备或需二次验证。请前往控制台执行“一键刷新/查询”手动填入企业微信验证码以信任设备。", "warning")
                if is_end_of_day:
                    _record_sync_failure(db, today_date, "网关要求多因子验证，请前往网页手动登录授权")
                return
            else:
                err_msg = login_res.get("msg", "未知网关异常")
                logger.error(f"Daily sync: Auto login failed: {err_msg}")
                LogService.add_log(db, f"【定时自动同步】自动登录失败：{err_msg}", "error")
                if is_end_of_day:
                    _record_sync_failure(db, today_date, f"自动登录失败: {err_msg}")
                return

        # Process the final query result
        if query_result and query_result.get("status") == "success":
            power_val = query_result["power"]

            # Save intraday balance snapshot
            intraday = IntradayBalanceRecord(balance=power_val)
            db.add(intraday)
            db.commit()

            LogService.add_log(db, f"【定时自动同步】同步完成！获取最新余额: {power_val} 度 ({(power_val * 0.5):.2f} 元)。", "success")

            if is_end_of_day:
                record = CalculatorService.calculate_daily_consumption(db, power_val, today_date)
                if record.is_abnormal:
                    LogService.add_log(db, f"【定时自动同步】[自愈计算] 今日用电量异常：{record.anomaly_reason}", "warning")
                else:
                    cons_val = f"{record.consumption:.2f} 度" if record.consumption is not None else "-- 度"
                    LogService.add_log(db, f"【定时自动同步】[自愈计算] 今日耗电量: {cons_val}。", "success")
            else:
                LogService.add_log(db, "【定时自动同步】分时电量记账成功，已存入当日趋势分析表。", "success")
        else:
            err_msg = query_result.get("msg", "未知数据拉取错误") if query_result else "未完成查询"
            logger.error(f"Daily sync failed: {err_msg}")
            LogService.add_log(db, f"【定时自动同步】同步失败：{err_msg}", "error")
            if is_end_of_day:
                _record_sync_failure(db, today_date, f"拉取失败（{err_msg}），请点击手动刷新检查。")

    except Exception as e:
        logger.exception(f"Scheduler job encountered an unhandled exception: {e}")
        LogService.add_log(db, f"【定时自动同步】发生系统异常错误：{str(e)}", "error")
        if is_end_of_day:
            _record_sync_failure(db, today_date, f"系统异常: {str(e)}")
    finally:
        db.close()

def _record_sync_failure(db, record_date: date, reason: str):
    """
    Record an abnormal entry in the database when the automatic background sync fails.
    """
    existing = db.query(ElectricityRecord).filter(ElectricityRecord.record_date == record_date).first()
    
    # We find the latest normal record before today to use its balance as a fallback
    from sqlalchemy import and_
    prev_record = (
        db.query(ElectricityRecord)
        .filter(
            and_(
                ElectricityRecord.record_date < record_date,
                ElectricityRecord.is_abnormal == False
            )
        )
        .order_by(ElectricityRecord.record_date.desc())
        .first()
    )
    fallback_balance = prev_record.balance if prev_record else 0.0
    
    if existing:
        # Avoid overwriting already succeeded values, only override if currently abnormal or null
        if existing.is_abnormal or existing.consumption is None:
            existing.is_abnormal = True
            existing.anomaly_reason = reason
    else:
        new_record = ElectricityRecord(
            record_date=record_date,
            balance=fallback_balance,
            consumption=None,
            is_abnormal=True,
            anomaly_reason=reason
        )
        db.add(new_record)
        
    db.commit()

def start_scheduler():
    """
    Start the background scheduler and add the hourly and daily cron jobs.
    """
    if not scheduler.running:
        # 1. Hourly snapshots at 8, 10, 12, 14, 16, 18, 20, 22:00
        scheduler.add_job(
            fetch_and_calculate_daily,
            trigger='cron',
            hour='8,10,12,14,16,18,20,22',
            minute=0,
            timezone='Asia/Shanghai',
            kwargs={"is_end_of_day": False},
            id='hourly_electricity_sync',
            replace_existing=True
        )
        # 2. Daily end-of-day summary query at 23:30
        scheduler.add_job(
            fetch_and_calculate_daily,
            trigger='cron',
            hour=23,
            minute=30,
            timezone='Asia/Shanghai',
            kwargs={"is_end_of_day": True},
            id='daily_electricity_sync',
            replace_existing=True
        )
        scheduler.start()
        logger.info("Background scheduler started successfully. Hourly and daily sync jobs active.")
