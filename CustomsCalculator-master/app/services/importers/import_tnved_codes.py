import re

import pandas as pd
from sqlmodel import Session, select, SQLModel

from app.core.database import engine
from app.models import TnVedCode
from app.core.config import settings

def parse_calc_metadata(code: str, description: str) -> dict:
	"""
	Анализирует код и описание товара, возвращая словарь параметров
	для расчета утильсбора.
	"""
	metadata = {}
	desc_lower = description.lower()
	code_str = str(code).strip()
	
	# --- Определение категории транспорта ---
	if code_str.startswith("8703"):
		metadata["type"] = "M1"  # Легковые
	elif code_str.startswith("8701"):
		metadata["type"] = "tractor"  # Тракторы
	elif code_str.startswith("8704"):
		metadata["type"] = "N"  # Грузовики
	elif code_str.startswith("8702"):
		metadata["type"] = "M2_M3"  # Автобусы
	elif code_str.startswith("8705"):
		metadata["type"] = "special"  # Спецтехника
	elif code_str.startswith("4011") or code_str.startswith("4012"):
		metadata["type"] = "tire"  # Шины
		return metadata  # Для шин описание парсить сложно, там важен вес (ввод пользователя)
	else:
		# Если это не автотранспорт, возвращаем пустой dict (утиль не нужен)
		return {}
	
	# --- Парсинг параметров из описания ---
	
	# 1. Тип двигателя (Электро / Гибрид)
	if "электрическим двигателем" in desc_lower and "внутреннего сгорания" not in desc_lower:
		metadata["engine_type"] = "electric"
	elif "гибрид" in desc_lower or ("электрическим двигателем" in desc_lower and "внутреннего сгорания" in desc_lower):
		metadata["engine_type"] = "hybrid"
	else:
		metadata["engine_type"] = "ice"  # ДВС (Internal Combustion Engine)
	
	# 2. Объем двигателя (см3)
	# Ищем цифры перед 'см' или 'см?' или 'см3'. Учитываем артефакт кодировки '?'
	# Пример в CSV: "более 1500см?" или "более 3000см?"
	volume_matches = re.findall(r'(\d+)\s*см', desc_lower)
	if volume_matches:
		# Обычно в описании диапазоны "более X, но не более Y".
		# Нам для утиля часто важна верхняя граница или сам факт попадания в диапазон.
		# Сохраним все найденные числа как список, чтобы потом анализировать.
		volumes = [int(v) for v in volume_matches]
		metadata["volumes_mentioned"] = volumes
		metadata["engine_volume_max"] = max(volumes)  # Берем максимальное упомянутое число как ориентир
	
	# 3. Мощность (кВт или л.с.)
	# Пример: "мощностью более 18кВт"
	power_kw = re.search(r'(\d+)\s*квт', desc_lower)
	power_hp = re.search(r'(\d+)\s*л\.?с', desc_lower)  # л.с. или лс
	
	if power_kw:
		metadata["power_kw"] = int(power_kw.group(1))
	if power_hp:
		metadata["power_hp"] = int(power_hp.group(1))
	
	# 4. Возраст (новые / б/у)
	if "новые" in desc_lower:
		metadata["condition"] = "new"
		metadata["age_group"] = "0-3"
	elif "бывшие в эксплуатации" in desc_lower:
		metadata["condition"] = "used"
		# Пытаемся найти точный возраст
		# "с момента выпуска которых прошло более 7лет"
		age_match = re.search(r'прошло более (\d+)\s*лет', desc_lower)
		if age_match:
			years = int(age_match.group(1))
			metadata["age_group"] = f">{years}"
		else:
			metadata["age_group"] = "3+"  # Дефолт для б/у
	
	# 5. Тоннаж (для грузовиков)
	# Пример: "полной массой транспортного средства не более 5т"
	weight_match = re.search(r'массой.*?(\d+(?:[.,]\d+)?)\s*т', desc_lower)
	if weight_match:
		# Заменяем запятую на точку для float
		w_str = weight_match.group(1).replace(',', '.')
		metadata["weight_ton"] = float(w_str)
	
	return metadata


# Словарь для маппинга единиц
UNIT_MAPPING = {
	'кг': 'kg',
	'г': 'g',
	'т': 't',
	'шт': 'pcs',
	'100 шт': '100_pcs',
	'1000 шт': '1000_pcs',
	'пар': 'pair',
	'л': 'l',
	'мл': 'ml',
	'1000 л.': '1000_l',
	'л100% сп.': 'l_alc_100',
	'м': 'm',
	'м2': 'm2',
	'1000 м2': '1000_m2',
	'м3': 'm3',
	'1000 кВтч': '1000_kwh',
	'кюри': 'ci',
	'кар': 'carat',
	'кг 90% с/в': 'kg_90_dry',
	'кг H2O2': 'kg_h2o2',
	'кг K2O': 'kg_k2o',
	'кг N': 'kg_n',
	'кг NаОH': 'kg_naoh',
	'кг P2O5': 'kg_p2o5',
	'кг U': 'kg_u',
	'кг КОH': 'kg_koh',
	'г Д/И': 'g_di'
}


def normalize_unit(value):
	if pd.isna(value) or value == "" or str(value).lower() == 'nan':
		return None
	val_str = str(value).strip()
	return UNIT_MAPPING.get(val_str, val_str)


def import_tnved_codes(csv_file_path):
	print("🚀 Начинаем процесс импорта с парсингом метаданных...")
	
	# Создаем таблицы (включая обновленную структуру с JSON)
	SQLModel.metadata.create_all(engine)
	
	try:
		df = pd.read_csv(csv_file_path, dtype=str)
		print(f"📂 CSV файл прочитан. Записей: {len(df)}")
	except Exception as e:
		print(f"❌ Ошибка: {e}")
		return
	
	with Session(engine) as session:
		print("⏳ Проверка существующих кодов...")
		existing_codes = set(session.exec(select(TnVedCode.code)).all())
		
		batch = []
		count = 0
		
		for index, row in df.iterrows():
			code_val = str(row['code']).strip()
			
			if code_val in existing_codes:
				continue
			
			# Очистка полей
			parent_val = row.get('parent_code')
			if pd.isna(parent_val) or str(parent_val).lower() in ['nan', '0', '']:
				parent_val = None
			else:
				parent_val = str(parent_val).strip()
			
			desc_val = str(row['description']).strip()
			
			# --- ПАРСИНГ МЕТАДАННЫХ ---
			# Генерируем JSON для логики утильсбора
			calc_meta = parse_calc_metadata(code_val, desc_val)
			
			# Если calc_meta не пустой, значит товар подлежит утильсбору (или проверке)
			is_applicable = bool(calc_meta)
			
			tn_obj = TnVedCode(
				code=code_val,
				description=desc_val,
				unit=normalize_unit(row.get('unit')),
				unit2=normalize_unit(row.get('unit2')),
				parent_code=parent_val,
				# Новые поля
				is_util_applicable=is_applicable,
				calc_metadata=calc_meta
			)
			
			batch.append(tn_obj)
			count += 1
			
			if len(batch) >= 1000:
				session.add_all(batch)
				session.commit()
				batch = []
				print(f"📥 Обработано {count} записей...")
		
		if batch:
			session.add_all(batch)
			session.commit()
		
		print(f"\n🏁 Импорт завершен! Добавлено: {count}")


if __name__ == "__main__":
	# Укажи путь к файлу
	import_tnved_codes(settings.TNVED_DIR / "tnved_codes.csv" )