from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models.user import User
from app.models.recharge import RechargeRecord
from app.schemas.recharge import RechargeRecordCreate, RechargeRecordResponse
from app.services.calculator import CalculatorService
from app.services.log import LogService

router = APIRouter()

@router.post("", response_model=RechargeRecordResponse)
def register_recharge(
    recharge_in: RechargeRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Manually register a recharge. Immediately triggers retroactive calculation
    to attempt to self-heal any existing balance anomalies.
    """
    if recharge_in.amount <= 0:
        raise HTTPException(status_code=400, detail="充值金额必须大于0元")
        
    db_recharge = RechargeRecord(
        amount=recharge_in.amount,
        recharge_date=recharge_in.recharge_date or datetime.utcnow()
    )
    # Fix import of datetime in case it's not imported: we can import inside or globally
    # Let's import datetime globally in this file.
    db.add(db_recharge)
    db.commit()
    db.refresh(db_recharge)
    
    # Trigger retroactive settlement to try to resolve active anomalies
    CalculatorService.retroactive_settlement(db)
    
    return db_recharge

@router.get("", response_model=List[RechargeRecordResponse])
def get_recharges(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get list of manual recharges, ordered by date descending.
    """
    recharges = (
        db.query(RechargeRecord)
        .order_by(RechargeRecord.recharge_date.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return recharges

@router.delete("/{recharge_id}")
def delete_recharge(
    recharge_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Revoke/Delete a manual recharge record and trigger retroactive recalculation.
    """
    db_recharge = db.query(RechargeRecord).filter(RechargeRecord.id == recharge_id).first()
    if not db_recharge:
        raise HTTPException(status_code=404, detail="未找到该充值记录")
        
    amount = db_recharge.amount
    target_date = db_recharge.recharge_date.date() if db_recharge.recharge_date else datetime.utcnow().date()
    
    # Remove from database
    db.delete(db_recharge)
    db.commit()
    
    LogService.add_log(db, f"用户撤销了充值记录 (ID: {recharge_id}, 金额: {amount:.2f} 元)", "warning")
    
    # Automatically recalculate consumption for the affected date
    recalc_result = CalculatorService.recalculate_after_recharge_deletion(db, target_date)
    
    return {
        "status": "success",
        "msg": f"充值记录（{amount:.2f} 元）已成功撤销！{recalc_result.get('msg', '')}",
        "recalc_result": recalc_result
    }
