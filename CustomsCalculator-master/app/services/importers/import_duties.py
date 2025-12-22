import re
import pandas as pd
from fastapi import Depends
from sqlmodel import Session, select, delete

from app.core.database import get_session
from app.models.rates import TariffRate, RateType
from app.models.tnved import TnVedCode


def normalize_unit(unit_str):
	if not unit_str: return None
	u = str(unit_str).lower()
	
	# Сначала проверяем особый случай с 1000
	if '1000' in u: return '1000_pcs'
	
	# Словарь соответствий: {Код: [список корней на рус и узб]}
	# 'кило' ловит 'килограмм', 'килограмми'
	# 'дон' ловит 'дона', 'донаси' (шт)
	# 'жуфт' ловит 'жуфти' (пара)
	mappings = {
		'kg': ['кило', 'кг'],
		'l': ['литр'],
		'pcs': ['штук', 'шт', 'дон'],
		'pair': ['пар', 'жуфт'],
		'cm3': ['куб', 'см'],
		'm2': ['м2']
	}
	
	for code, keywords in mappings.items():
		if any(k in u for k in keywords):
			return code
	
	return u.strip()


def parse_rate_string(rate_str):
	if pd.isna(rate_str):
		return {"rate_type": "ad_valorem", "ad_valorem_rate": 0.0}

	clean_str = str(rate_str).replace('*', '').strip().lower().replace(',', '.')
	
	# 1. Извлекаем адвалорную ставку (всегда первое число в строке)
	# Работает для '20', '20 + ...', '20, но не менее...'
	first_num = re.search(r'^(\d+(\.\d+)?)', clean_str)
	ad_valorem = float(first_num.group(1)) if first_num else 0.0
	
	# Если строка простая (только число), возвращаем сразу
	if re.fullmatch(r'^[\d\.]+$', clean_str):
		return {"rate_type": "ad_valorem", "ad_valorem_rate": ad_valorem, "specific_rate": None, "specific_unit": None}
	
	# 2. Определяем тип ставки по ключевым символам/словам
	if '+' in clean_str:
		rate_type = "combined"
	# 'менее' (рус) или 'лекин'/'кам' (узб)
	elif any(x in clean_str for x in ['менее', 'лекин', 'кам']):
		rate_type = "mixed"
	else:
		# Если есть мусор, но нет признаков комбо/смешанной, считаем адвалорной
		return {"rate_type": "ad_valorem", "ad_valorem_rate": ad_valorem, "specific_rate": None, "specific_unit": None}
	
	# 3. Извлекаем специфическую ставку
	# Ищем число, которое стоит перед словами "дол", "usd", "ақш"
	# Это работает и для RU ("0.3 долл"), и для UZ ("0.3 ақш")
	spec_match = re.search(r'(\d+(\.\d+)?)\s*(?:дол|usd|ақш)', clean_str)
	specific_rate = float(spec_match.group(1)) if spec_match else 0.0
	
	# 4. Извлекаем единицу измерения (передаем всю строку, функция сама найдет ключевое слово)
	specific_unit = normalize_unit(clean_str)
	
	return {
		"rate_type": rate_type,
		"ad_valorem_rate": ad_valorem,
		"specific_rate": specific_rate,
		"specific_unit": specific_unit
	}


def import_csv_to_db(session: Session, csv_path: str):
	"""
	Импортирует CSV в БД используя переданную сессию.
	"""
	print(f"🚀 Начинаем импорт из {csv_path}")
	
	# 1. Очистка
	session.exec(delete(TariffRate))
	
	# 2. Загрузка кодов (словарь code -> id для скорости)
	raw_codes = session.exec(select(TnVedCode.code, TnVedCode.id)).all()
	db_codes_list = [(code, pid) for code, pid in raw_codes]
	
	# 3. Чтение CSV
	df = pd.read_csv(csv_path, sep=';', dtype={'tn_code': str})
	df['tn_code'] = df['tn_code'].astype(str).str.split(',')
	df = df.explode('tn_code')
	df['tn_code'] = df['tn_code'].str.strip()
	
	rates_buffer = {}
	
	# 4. Логика
	for index, row in df.iterrows():
		source_code = str(row['tn_code']).strip()
		source_len = len(source_code)
		
		target_ids = [pid for code, pid in db_codes_list if code.startswith(source_code)]
		
		if not target_ids: continue
		
		rate_data = parse_rate_string(row['rate'])
		
		for tn_id in target_ids:
			if tn_id in rates_buffer:
				existing_entry = rates_buffer[tn_id]
				if source_len < existing_entry['source_len']:
					continue
			
			tariff = TariffRate(
				tn_ved_code_id=tn_id,
				rate_type=RateType(rate_data['rate_type']),
				ad_valorem_rate=rate_data['ad_valorem_rate'],
				specific_rate=rate_data.get('specific_rate'),
				specific_unit=rate_data.get('specific_unit'),
				specific_currency="USD",
				excise_type="ad_valorem",
				excise_ad_valorem_rate=0.0,
				vat_rate=12.0
			)
			rates_buffer[tn_id] = {
				"rate_obj": tariff,
				"source_len": source_len
			}
	
	# 5. Сохранение
	final_rates_list = [entry['rate_obj'] for entry in rates_buffer.values()]
	
	# Batch save
	batch_size = 2000
	for i in range(0, len(final_rates_list), batch_size):
		batch = final_rates_list[i: i + batch_size]
		session.add_all(batch)
		# Flush нужен, чтобы не забивать память, но commit сделаем в конце в роутере
		session.flush()
	
	print(f"✅ Импортировано ставок: {len(final_rates_list)}")
	return len(final_rates_list)

