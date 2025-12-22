from typing import Optional
from sqlmodel import SQLModel, Field, Relationship
from enum import Enum


# Enum для типа ставки ПОШЛИНЫ
class RateType(str, Enum):
	AD_VALOREM = "ad_valorem"  # %
	SPECIFIC = "specific"  # $
	MIXED = "mixed"  # max(%, $)
	COMBINED = "combined"  # % + $


# Enum для типа ставки АКЦИЗА (отдельно, чтобы не путать)
class ExciseType(str, Enum):
	AD_VALOREM = "ad_valorem"  # % (например, Сахар)
	SPECIFIC = "specific"  # Сумма (например, Бензин)
	MIXED = "mixed"  # % но не менее Суммы (например, Пиво)
	COMBINED = "combined"  # % + Сумма (например, Сигареты)


class TariffRate(SQLModel, table=True):
	__tablename__ = "tariff_rates"
	
	id: Optional[int] = Field(default=None, primary_key=True)
	tn_ved_code_id: int = Field(foreign_key="tn_ved_codes.id", index=True)
	
	# --- 1. ТАМОЖЕННАЯ ПОШЛИНА (Duty) ---
	rate_type: RateType = Field(default=RateType.AD_VALOREM)
	ad_valorem_rate: float = Field(default=0.0)  # % пошлины
	specific_rate: Optional[float] = Field(default=None)  # Ставка ($/кг)
	specific_currency: str = Field(default="USD")  # Валюта пошлины
	specific_unit: Optional[str] = Field(default=None)  # Ед.изм (kg, l, pcs)
	
	# --- 2. АКЦИЗ (Excise) - Новые поля ---
	# Мы заменяем старый excise_rate: float на полноценную структуру
	excise_type: ExciseType = Field(default=ExciseType.AD_VALOREM)
	
	excise_ad_valorem_rate: float = Field(default=0.0)  # Бывший excise_rate (%)
	
	excise_specific_rate: Optional[float] = Field(default=None)  # Сумма (сум/литр)
	excise_currency: str = Field(default="UZS")  # Валюта акциза (обычно Сум)
	excise_unit: Optional[str] = Field(default=None)  # Ед.изм акциза
	
	# --- 3. НДС (VAT) ---
	vat_rate: float = Field(default=12.0)
	
	# Связи
	tn_ved_code_ref: "TnVedCode" = Relationship(back_populates="rates")