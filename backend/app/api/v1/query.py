from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.models.intraday_balance import IntradayBalanceRecord
from app.services.spider import SpiderService
from app.services.calculator import CalculatorService

router = APIRouter()

class Step2Request(BaseModel):
    session_id: str
    sms_code: str

@router.get("")
def query_electricity(
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    """
    Perform an electricity query. If token is invalid or expired, notify frontend to start MFA login.
    """
    token = SpiderService.read_token()
    if not token:
        return {"status": "expired", "msg": "本地无可用凭证，需重新授权。"}
        
    # Use user's room config if available
    query_config = current_user.query_config
    
    # Execute API query via curl_cffi
    result = SpiderService.execute_query(token, query_config=query_config)
    
    if result.get("status") == "expired":
        return {"status": "expired", "msg": "凭证已过期，请重新登录授权。"}
        
    if result.get("status") == "success":
        power_val = result["power"]
        today_date = date.today()
        
        # Save to intraday (hourly) balance record table
        intraday = IntradayBalanceRecord(balance=power_val)
        db.add(intraday)
        db.commit()
        
        # Calculate daily consumption and check for anomalies
        record = CalculatorService.calculate_daily_consumption(db, power_val, today_date)
        
        return {
            "status": "success",
            "power": power_val,
            "record": {
                "id": record.id,
                "record_date": record.record_date.isoformat(),
                "balance": record.balance,
                "consumption": record.consumption,
                "is_abnormal": record.is_abnormal,
                "anomaly_reason": record.anomaly_reason
            }
        }
        
    return {"status": "error", "msg": result.get("msg", "查询失败")}

@router.post("/login-step1")
def login_step1(current_user: User = Depends(get_current_user)):
    """
    Trigger portal login. Starts headless Chromium, enters credentials, and handles MFA request.
    """
    student_id = current_user.student_id
    gateway_password = current_user.gateway_password
    
    if not student_id or not gateway_password:
        raise HTTPException(
            status_code=400,
            detail="请先在个人设置中配置您的校园网统一身份认证学号与密码！"
        )
        
    result = SpiderService.login_step1(student_id=student_id, password=gateway_password, query_config=current_user.query_config)
    return result

@router.post("/login-step2")
def login_step2(req: Step2Request, current_user: User = Depends(get_current_user)):
    """
    Submit WeChat MFA SMS verification code and trust device.
    """
    result = SpiderService.login_step2(session_id=req.session_id, sms_code=req.sms_code, query_config=current_user.query_config)
    return result
