from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from app.core.database import get_session
from app.services.calculator import DutyCalculator
from app.schemas.calculation import CalculationRequest, CalculationResponse

router = APIRouter()


@router.post("/calculate", response_model=CalculationResponse)
def calculate_duty(
		request: CalculationRequest,
		session: Session = Depends(get_session)
):
	"""
	Полный расчет таможенных платежей:
	1. Импортная пошлина (по коду ТН ВЭД)
	2. Акцизный налог (если применимо)
	3. НДС (12% от базы)
	4. Таможенный сбор (0.2%)
	"""
	calculator = DutyCalculator(session)
	
	# Передаем новые поля (manufacturing_year, power_hp) в сервис
	result = calculator.calculate(
		tn_code=request.tn_code,
		customs_value=request.customs_value,
		weight_kg=request.weight_kg,
		quantity_pcs=request.quantity_pcs,
		volume_cm3=request.volume_cm3,
		liter_qty=request.liter_qty,
		origin_country_code=request.origin_country_code,
		# Новые аргументы:
		manufacturing_year=request.manufacturing_year,
		power_hp=request.power_hp
	)
	
	if result.get("error"):
		raise HTTPException(status_code=404, detail=result["error"])
	
	return result