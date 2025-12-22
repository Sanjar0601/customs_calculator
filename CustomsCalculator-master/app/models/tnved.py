from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, JSON


# --- Модель Кодов ТН ВЭД (Родитель) ---
class TnVedCode(SQLModel, table=True):
	__tablename__ = "tn_ved_codes"
	
	id: Optional[int] = Field(default=None, primary_key=True)
	code: str = Field(index=True, unique=True, max_length=10)
	description: str
	
	unit: Optional[str] = None
	unit2: Optional[str] = None
	
	parent_code: Optional[str] = Field(default=None, index=True)
	
	# --- НОВЫЕ ПОЛЯ ---
	# Флаг: применяется ли утильсбор к этому коду
	is_util_applicable: bool = Field(default=False, index=True)
	
	# Поле для хранения распарсенных данных (объем, мощность, тип и т.д.)
	# sa_column=Column(JSON) позволяет хранить это как JSONB в PostgreSQL
	calc_metadata: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))
	
	# Связи
	rates: List["TariffRate"] = Relationship(back_populates="tn_ved_code_ref")
	