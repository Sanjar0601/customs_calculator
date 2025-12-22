# app/services/parser_countries.py
import re
import httpx
from bs4 import BeautifulSoup
from sqlmodel import Session, select
from app.models.country import Country, TradeRegimeType
from app.services.iso_mapper import get_iso_code_by_russian_name

LEX_UZ_URL = "https://lex.uz/docs/4911947"


async def sync_countries_from_lexuz(session: Session):
	"""
	Парсит Lex.uz, определяет ISO коды и обновляет БД.
	"""
	async with httpx.AsyncClient() as client:
		response = await client.get(LEX_UZ_URL)
		# Lex.uz иногда отдает win-1251, но обычно utf-8. На всякий случай:
		if "charset=windows-1251" in response.text.lower():
			html_content = response.content.decode("windows-1251")
		else:
			html_content = response.text
	
	soup = BeautifulSoup(html_content, "lxml")
	
	# Списки для стран
	countries_data = []  # List of tuples (name, regime)
	
	# Логика поиска блоков (как обсуждали ранее)
	content_div = soup.find("div", id="divCont")
	if not content_div:
		return {"error": "Content div not found on Lex.uz"}
	
	current_regime = None
	
	for tag in content_div.find_all("div", ):
		text_upper = tag.get_text(strip=True).upper()
		
		if "ПРИЛОЖЕНИЕ № 1" in text_upper:
			current_regime = TradeRegimeType.MOST_FAVORED
			continue
		elif "ПРИЛОЖЕНИЕ № 2" in text_upper:
			current_regime = TradeRegimeType.FREE_TRADE
			continue
		
		if not current_regime:
			continue
		
		a_tag = tag.find("a")
		
		if not a_tag:
			continue
		
		text = a_tag.get_text(strip=True)
		
		match = re.match(r"(\d+)\.\s*(.+)", text)
		
		if match:
			raw_name = match.group(2).strip()
			raw_name = raw_name.replace(";", "").replace(".", "")
			
			if raw_name.endswith("*"):
				raw_name = raw_name[:-1].strip()
			
			countries_data.append((raw_name, current_regime))
	
	# --- Сохранение в БД ---
	processed_count = 0
	errors = []
	
	for name_ru, regime in countries_data:
		iso_code = get_iso_code_by_russian_name(name_ru)
		
		if not iso_code:
			# Если не нашли код, пишем в лог/ошибку, чтобы разработчик добавил в словарь
			errors.append(f"ISO not found for: {name_ru}")
			# Можно пропускать или сохранять с null кодом (я выберу пропуск для чистоты)
			continue
		
		# Проверяем, есть ли страна в БД
		statement = select(Country).where(Country.iso_code == iso_code)
		existing_country = session.exec(statement).first()
		
		if existing_country:
			# Обновляем режим, если изменился
			if existing_country.trade_regime != regime:
				existing_country.trade_regime = regime
				existing_country.name_ru = name_ru  # Обновляем название на актуальное
				session.add(existing_country)
		else:
			# Создаем новую
			new_country = Country(
				name_ru=name_ru,
				iso_code=iso_code,
				trade_regime=regime
			)
			session.add(new_country)
		
		processed_count += 1
	
	session.commit()
	
	return {
		"status": "success",
		"processed": processed_count,
		"errors": errors  # Вернет список стран, которые надо добавить в MANUAL_MAPPING
	}