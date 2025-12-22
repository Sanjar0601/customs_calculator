# app/crud/crud_rate.py
from typing import Optional
from sqlmodel import Session, select
from app.models.rates import TariffRate


class CRUDRate:
	def get_by_tnved_id(self, db: Session, tnved_id: int) -> Optional[TariffRate]:
		statement = select(TariffRate).where(TariffRate.tn_ved_code_id == tnved_id)
		return db.exec(statement).first()

# Сюда можно добавить методы для создания/удаления, если нужно управлять ставками вручную через админку


rate = CRUDRate()