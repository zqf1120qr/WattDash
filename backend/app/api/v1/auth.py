from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from app.core.database import get_db
from app.core.config import settings
from app.core.security import verify_password, get_password_hash, create_access_token, ALGORITHM
from app.models.user import User
from app.schemas.auth import UserCreate, UserResponse, UserUpdate, Token

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

@router.post("/register", response_model=UserResponse)
def register_user(user_in: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new dashboard user.
    """
    db_user = db.query(User).filter(User.username == user_in.username).first()
    if db_user:
        raise HTTPException(
            status_code=400,
            detail="Username already registered",
        )
    
    hashed_password = get_password_hash(user_in.password)
    new_user = User(
        username=user_in.username,
        hashed_password=hashed_password,
        student_id=user_in.student_id,
        gateway_password=user_in.gateway_password,
        query_config=user_in.query_config,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post("/login", response_model=Token)
def login_access_token(
    db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    OAuth2 compatible token login, retrieve a JWT access token.
    """
    username_clean = form_data.username.strip()
    password_clean = form_data.password.strip()
    
    user = db.query(User).filter(User.username == username_clean).first()
    if not user or not verify_password(password_clean, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect username or password",
        )
    elif not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )
        
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": create_access_token(
            user.username, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }

@router.get("/me", response_model=UserResponse)
def read_user_me(current_user: User = Depends(get_current_user)):
    """
    Get current logged-in user profile.
    """
    return current_user

@router.put("/me", response_model=UserResponse)
def update_user_me(
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update configuration settings, room info or credentials for portal query.
    """
    if user_update.password is not None:
        current_user.hashed_password = get_password_hash(user_update.password)
    if user_update.student_id is not None:
        current_user.student_id = user_update.student_id
    if user_update.gateway_password is not None:
        current_user.gateway_password = user_update.gateway_password
    if user_update.query_config is not None:
        current_user.query_config = user_update.query_config
        
    db.commit()
    db.refresh(current_user)
    return current_user
