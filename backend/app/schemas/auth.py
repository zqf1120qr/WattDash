from pydantic import BaseModel
from typing import Optional, Dict, Any

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str
    student_id: Optional[str] = None
    gateway_password: Optional[str] = None
    query_config: Optional[Dict[str, Any]] = None

class UserUpdate(BaseModel):
    password: Optional[str] = None
    student_id: Optional[str] = None
    gateway_password: Optional[str] = None
    query_config: Optional[Dict[str, Any]] = None

class UserResponse(UserBase):
    id: int
    student_id: Optional[str] = None
    query_config: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
