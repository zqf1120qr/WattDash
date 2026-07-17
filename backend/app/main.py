import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import engine, Base, SessionLocal
from app.api.router import api_router
from app.services.scheduler import start_scheduler
from app.models.user import User
from app.core.security import get_password_hash

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("wattdash")

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include main router
app.include_router(api_router, prefix=settings.API_V1_STR)

def init_db():
    Base.metadata.create_all(bind=engine)
    
    # Create default user 'admin' with password 'admin' if empty
    db = SessionLocal()
    try:
        user_count = db.query(User).count()
        if user_count == 0:
            logger.info("Database is empty. Initializing default admin user...")
            admin_user = User(
                username="admin",
                hashed_password=get_password_hash("admin"),
                student_id=None,
                gateway_password=None
            )
            db.add(admin_user)
            db.commit()
            logger.info("Default user 'admin' created with password 'admin'. Please change this on first login.")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
    finally:
        db.close()

@app.on_event("startup")
def startup_event():
    init_db()
    start_scheduler()
    logger.info("WattDash FastAPI backend fully loaded and started.")

@app.get("/")
def read_root():
    return {"message": "Welcome to WattDash API. Visit /docs for documentation."}
