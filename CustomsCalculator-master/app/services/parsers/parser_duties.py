# app/services/parsers/parser_duties.py
import csv
import re
import datetime
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from app.core.config import settings

# TARGET_URL = "https://lex.uz/docs/3802366"
TARGET_URL = "https://lex.uz/docs/7533457"


def clean_text(text):
	if not text:
		return ""
	text = text.replace('\xa0', ' ').replace('\n', ' ').replace('\r', '')
	return re.sub(r'\s+', ' ', text).strip()


def run_duties_parser() -> Path:
	"""
	Парсит lex.uz и возвращает путь к сохраненному CSV файлу.
	"""
	print(f"📡 Подключение к {TARGET_URL}...")
	headers = {
		'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
	}
	response = requests.get(TARGET_URL, headers=headers)
	response.raise_for_status()
	
	# print(response.text)
	
	soup = BeautifulSoup(response.text, 'html.parser')
	
	target_table = None
	for table in soup.find_all('table'):
		# if "ТН ВЭД" in table.get_text() and "Наименование товара" in table.get_text():
		# 	target_table = table                                                # это для русской версии пошлин
		# 	break
		if "ТИФ ТН" in table.get_text() and "Товар номи" in table.get_text():
			target_table = table                                                # это для узбекской версии пошлин
			break
	
	if not target_table:
		raise Exception("Таблица со ставками не найдена на странице.")
	
	rows = target_table.find_all('tr')
	parsed_data = []
	
	for row in rows:
		cells = row.find_all('td')
		if not cells: continue
		
		cell_texts = [clean_text(cell.get_text(separator=' ')) for cell in cells]
		# if "ТН ВЭД" in cell_texts[0]: continue
		if "ТИФ ТН" in cell_texts[0]: continue
		
		if len(cell_texts) >= 3:
			tn_ved_code = cell_texts[0]
			product_name = cell_texts[1]
			rate = cell_texts[2]
			
			if not tn_ved_code: continue
			
			parsed_data.append({
				"tn_code": tn_ved_code,
				"name": str(product_name),
				"rate": rate
			})
	
	# Убедимся, что папка существует
	settings.DUTIES_DIR.mkdir(parents=True, exist_ok=True)
	
	now = datetime.datetime.now()
	filename = settings.DUTIES_DIR / f'duties_{now.strftime("%Y-%m-%d-%H-%M")}.csv'
	
	with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
		writer = csv.DictWriter(f, fieldnames=["tn_code", "name", "rate"], delimiter=';')
		writer.writeheader()
		writer.writerows(parsed_data)
	
	print(f"✅ Парсинг завершен. Файл: {filename}")
	return filename


