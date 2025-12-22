# app/schemas/rates.py
from typing import Optional
from pydantic import BaseModel
from app.models.rates import RateType, ExciseType


class TariffRateBase(BaseModel):
	rate_type: RateType
	ad_valorem_rate: float
	specific_rate: Optional[float] = None
	specific_currency: str = "USD"
	specific_unit: Optional[str] = None
	
	excise_type: ExciseType
	excise_ad_valorem_rate: float
	excise_specific_rate: Optional[float] = None
	excise_currency: str = "UZS"
	
	vat_rate: float


class TariffRateRead(TariffRateBase):
	id: int
	tn_ved_code_id: int
	
	class Config:
		from_attributes = True


# Схема для ответа о статусе синхронизации
class SyncStatus(BaseModel):
	status: str
	message: str
	processed_files: Optional[str] = None
	total_rates: Optional[int] = None