import requests
import pandas as pd
import time

# URL твоего источника
API_URL = "https://data.egov.uz/apiPartner/Partner/WebService"


def fetch_tnved_data():
	"""
	Скачивает все коды ТН ВЭД с data.egov.uz
	"""
	params = {
		"token": "693a9662130cda90179000ad",
		"name": "1-012-0008",
		"offset": 0,
		"limit": 12000,  # Ставим с запасом, там 11293
		"lang": "ru"  # Можно попробовать 'ru', если API поддерживает, но 'uz' надежнее
	}
	
	print("⏳ Начинаю загрузку данных...")
	try:
		response = requests.get(API_URL, params=params, timeout=30)
		response.raise_for_status()
		data = response.json()
		
		# Проверяем структуру
		if 'result' in data and 'data' in data['result']:
			records = data['result']['data']
			print(f"✅ Получено {len(records)} записей.")
			return records
		else:
			print("❌ Ошибка структуры ответа API")
			return []
	
	except requests.exceptions.RequestException as e:
		print(f"❌ Ошибка сети: {e}")
		return []


def clean_data(records):
	"""
	Очищает данные и исправляет ведущие нули
	"""
	df = pd.DataFrame(records)
	
	# 1. Исправляем название колонок для удобства
	df = df.rename(columns={
		"TNVED": "code",
		"Наименование товара": "description"
	})
	
	# 2. Исправляем проблему с ведущим нулем (превращаем 101... в 0101...)
	# Логика: если код состоит из 9 цифр, добавляем '0' в начало
	df['code'] = df['code'].astype(str).str.strip()
	df['code'] = df['code'].apply(lambda x: x.zfill(10) if len(x) == 9 else x)
	df['description'] = df['description'].str.replace(' ' , ' ')
	# 3. Удаляем дубликаты, если есть
	df = df.drop_duplicates(subset=['code'])
	
	return df


if __name__ == "__main__":
	raw_data = fetch_tnved_data()
	
	if raw_data:
		df_clean = clean_data(raw_data)
		
		# Посмотрим на результат
		print("\nПример данных:")
		print(df_clean.head())
		
		# Сохраним в CSV (временная база)
		df_clean.to_csv("tnved_base_2023.csv", index=False, encoding='utf-8')
		print(f"\n💾 База сохранена: {len(df_clean)} товаров.")