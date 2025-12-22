# app/models/country.py
import enum
from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, DateTime, func


class TradeRegimeType(str, enum.Enum):
	FREE_TRADE = "free_trade"  # СНГ (0% пошлина)
	MOST_FAVORED = "most_favored"  # РНБ (Базовая ставка)
	GENERAL = "general"  # Остальные (Двойная ставка)


class Country(SQLModel, table=True):
	__tablename__ = "countries"
	
	id: Optional[int] = Field(default=None, primary_key=True)
	name_ru: str = Field(index=True, unique=True)  # Название с Lex.uz
	iso_code: str = Field(index=True, max_length=2)  # Код (RU, US, CN)
	
	# Режим торговли
	trade_regime: TradeRegimeType = Field(default=TradeRegimeType.GENERAL)
	
	# Таймстампы (через sa_column для автоматического обновления)
	created_at: Optional[datetime] = Field(
		default=None,
		sa_column=Column(DateTime(timezone=True), server_default=func.now())
	)
	updated_at: Optional[datetime] = Field(
		default=None,
		sa_column=Column(DateTime(timezone=True), onupdate=func.now())
	)