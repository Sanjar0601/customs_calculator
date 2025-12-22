import httpx
from datetime import datetime
from sqlmodel import Session, select

from app.models.currency import Currency, CurrencyRate
from app.schemas.currency import CurrencySchema

CBU_URL = "https://cbu.uz/uz/arkhiv-kursov-valyut/json/"


class CurrencyClient:
	async def fetch_rates(self):
		async with httpx.AsyncClient() as client:
			response = await client.get(CBU_URL)
			response.raise_for_status()
			return response.json()
	
	async def update_rates(self, session: Session):
		raw_data = await self.fetch_rates()
		updated_count = 0
		
		# Интересующие валюты (можно убрать фильтр)
		# target_char_codes = ["USD", "EUR", "RUB", "CNY", "GBP", "JPY", "CHF", "KRW", "AZN", "BDT", "", "", ""]
		
		for item in raw_data:
			# Валидация входных данных
			cbu_item = CurrencySchema(**item)
			
			# if cbu_item.Ccy not in target_char_codes:
			# 	continue
			
			# 1. Поиск валюты
			statement = select(Currency).where(Currency.char_code == cbu_item.Ccy)
			currency = session.exec(statement).first()
			
			# Если валюты нет - создаем
			if not currency:
				currency = Currency(
					code=cbu_item.Code,
					char_code=cbu_item.Ccy,
					name=cbu_item.CcyNm_RU,
					nominal=int(cbu_item.Nominal)
				)
				session.add(currency)
				session.commit()
				session.refresh(currency)
			
			# 2. Обработка даты и курса
			rate_date = datetime.strptime(cbu_item.Date, "%d.%m.%Y").date()
			rate_value = float(cbu_item.Rate)
			
			# 3. Проверка на дубликат (есть ли курс на эту дату?)
			stmt_rate = select(CurrencyRate).where(
				CurrencyRate.currency_id == currency.id,
				CurrencyRate.date == rate_date
			)
			existing_rate = session.exec(stmt_rate).first()
			
			if not existing_rate:
				new_rate = CurrencyRate(
					currency_id=currency.id,
					rate=rate_value,
					date=rate_date
				)
				session.add(new_rate)
				updated_count += 1
		
		session.commit()
		return {"status": "success", "new_rates_added": updated_count}