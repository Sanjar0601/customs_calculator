from contextlib import asynccontextmanager

from fastapi import FastAPI, APIRouter
from app.api.v1.endpoints import countries, tnved, calculator, currency, rates, excise
from app.core.database import create_db_and_tables

router = APIRouter()
router.include_router(tnved.router, prefix="/api/v1", tags=["TNVED"])
router.include_router(calculator.router, prefix="/api/v1", tags=["Calculator"])
router.include_router(countries.router, prefix="/api/v1", tags=["Countries"])
router.include_router(currency.router, prefix="/api/v1", tags=["Currency"])
router.include_router(rates.router, prefix="/api/v1", tags=["Rates & Duties"])
router.include_router(excise.router, prefix="/api/v1", tags=["Excise"])

@asynccontextmanager
async def lifespan(app: FastAPI):
	# Событие при запуске
	create_db_and_tables()
	yield
	# Здесь можно сделать действия при выключении, если нужно
	# например закрытие соединений, очистка ресурсов и т.д.

