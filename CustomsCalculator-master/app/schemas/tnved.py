# app/schemas/tnved.py
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from app.schemas.rates import TariffRateRead


# Базовая схема товара
class TnVedBase(BaseModel):
	code: str
	description: str
	unit: Optional[str] = None
	unit2: Optional[str] = None
	
	# --- НОВЫЕ ПОЛЯ ---
	# Флаг: нужно ли считать утильсбор
	is_util_applicable: bool = False
	calc_metadata: Optional[Dict[str, Any]] = None


# Схема для ответа с "Умным поиском"
class TnVedRichResponse(TnVedBase):
	id: int
	match_percentage: float
	rates: List[TariffRateRead] = []
	
	class Config:
		from_attributes = True