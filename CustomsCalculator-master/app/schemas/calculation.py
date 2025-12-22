from typing import Optional, List
from pydantic import BaseModel, Field


# --- Входные данные ---
class CalculationRequest(BaseModel):
	tn_code: str
	customs_value: float
	weight_kg: float
	quantity_pcs: Optional[float] = 0.0
	volume_cm3: Optional[float] = 0.0
	liter_qty: Optional[float] = 0.0
	origin_country_code: Optional[str] = Field(default=None, max_length=2)
	
	# --- НОВЫЕ ПОЛЯ ДЛЯ УТИЛЬСБОРА ---
	# Год выпуска (для определения возраста > 3 лет)
	manufacturing_year: Optional[int] = Field(default=None, description="Год выпуска ТС")
	# Мощность в лошадиных силах (для тракторов и спецтехники)
	power_hp: Optional[float] = Field(default=0.0, description="Мощность двигателя в л.с.")


class DutyComponent(BaseModel):
	name: str
	rate_source: str
	amount_usd: float
	amount_uzs: float


class CalculationResponse(BaseModel):
	tn_code: str
	currency_rate: float
	# Добавляем БРВ, чтобы было прозрачно для пользователя
	brv_rate: Optional[float] = None
	total_payments_usd: float
	total_payments_uzs: float
	details: List[DutyComponent]
	error: Optional[str] = None