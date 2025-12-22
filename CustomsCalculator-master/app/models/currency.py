from typing import Optional, List
from datetime import date as date_type  # <--- 1. ПЕРЕИМЕНОВЫВАЕМ ИМПОРТ
from sqlmodel import SQLModel, Field, Relationship


# --- Справочник валют (статичные данные) ---
class Currency(SQLModel, table=True):
	__tablename__ = "currencies"
	
	id: Optional[int] = Field(default=None, primary_key=True)
	code: str = Field(index=True, unique=True)  # Цифровой код (840)
	char_code: str = Field(index=True, unique=True)  # Буквенный код (USD)
	name: str  # Название (US Dollar)
	nominal: int = Field(default=1)  # Номинал (1, 10, 100...)
	
	# Связь: Одна валюта имеет много записей истории курсов
	rates: List["CurrencyRate"] = Relationship(back_populates="currency")


# --- История курсов (динамические данные) ---
class CurrencyRate(SQLModel, table=True):
	__tablename__ = "currency_rates"
	
	id: Optional[int] = Field(default=None, primary_key=True)
	
	# Внешний ключ на валюту
	currency_id: int = Field(foreign_key="currencies.id")
	
	rate: float  # Курс к суму
	
	# 2. ИСПОЛЬЗУЕМ ПЕРЕИМЕНОВАННЫЙ ТИП
	date: date_type = Field(index=True)
	
	# Связь обратная
	currency: "Currency" = Relationship(back_populates="rates")