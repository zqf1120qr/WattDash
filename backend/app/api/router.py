from fastapi import APIRouter
from app.api.v1 import auth, query, recharge, statistics

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(query.router, prefix="/query", tags=["query"])
api_router.include_router(recharge.router, prefix="/recharge", tags=["recharge"])
api_router.include_router(statistics.router, prefix="/statistics", tags=["statistics"])
