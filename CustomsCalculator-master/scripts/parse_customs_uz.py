import requests
import time
import json

import urllib3

# ================= НАСТРОЙКИ =================
# Вставьте ваш актуальный JSESSIONID сюда
CURRENT_JSESSIONID = "DB698FC325486785722821A50BF5352C"

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

TARGET_URL = "https://tarif.customs.uz/JqueryDatatablePluginDemo"
# Сколько записей запрашивать за один раз (можно попробовать увеличить до 100 или 200, чтобы ускорить процесс)
BATCH_SIZE = 100
# =============================================

headers = {
	"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
	"Accept": "application/json, text/javascript, */*; q=0.01",
	"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
	"X-Requested-With": "XMLHttpRequest",
	"Origin": "https://tarif.customs.uz",
	"Referer": "https://tarif.customs.uz/spravochnik/viewDatatable.jsp?lang=ru_Ru",
	"Cookie": f"JSESSIONID={CURRENT_JSESSIONID}",
	# Остальные заголовки часто не обязательны, но можно добавить при необходимости
}


def fetch_data(start_index):
	"""
	Функция для получения одной страницы данных
	"""
	payload = {
		"sEcho": 1,  # Счетчик запросов (можно не менять или инкрементировать)
		"iColumns": 4,
		"sColumns": ",,,",
		"iDisplayStart": start_index,  # Смещение (от какой записи начинать)
		"iDisplayLength": BATCH_SIZE,  # Сколько записей брать
		
		# Стандартные параметры DataTables (обычно пустые при базовом запросе)
		"mDataProp_0": 0, "sSearch_0": "", "bRegex_0": "false", "bSearchable_0": "true", "bSortable_0": "true",
		"mDataProp_1": 1, "sSearch_1": "", "bRegex_1": "false", "bSearchable_1": "true", "bSortable_1": "true",
		"mDataProp_2": 2, "sSearch_2": "", "bRegex_2": "false", "bSearchable_2": "true", "bSortable_2": "true",
		"mDataProp_3": 3, "sSearch_3": "", "bRegex_3": "false", "bSearchable_3": "true", "bSortable_3": "true",
		"sSearch": "",
		"bRegex": "false",
		"iSortCol_0": 0,
		"sSortDir_0": "asc",
		"iSortingCols": 1
	}
	
	try:
		response = requests.post(TARGET_URL, headers=headers, data=payload, verify=False)
		response.raise_for_status()  # Проверка на ошибки HTTP
		return response.json()
	except Exception as e:
		print(f"Ошибка при запросе: {e}")
		return None


def main():
	all_records = []
	start = 0
	total_records = 1  # Временное значение, обновится после первого запроса
	
	print("Начинаем парсинг...")
	
	while start < total_records:
		print(f"Загрузка записей с {start} по {start + BATCH_SIZE}...")
		
		data = fetch_data(start)
		
		if not data:
			print("Не удалось получить данные. Остановка.")
			break
		
		# Обычно данные лежат в поле 'aaData' для старых версий DataTables или 'data' для новых
		# Судя по формату запроса, это вероятно старая версия, поэтому ищем 'aaData'
		rows = data.get('aaData', [])
		
		if not rows:
			print("Данные закончились или вернулся пустой список.")
			break
		
		all_records.extend(rows)
		
		# Обновляем общее количество записей из ответа сервера
		total_records = int(data.get('iTotalDisplayRecords', data.get('iTotalRecords', 0)))
		print(f"Всего доступно записей: {total_records}. Скачано: {len(all_records)}")
		
		# Увеличиваем смещение для следующего круга
		start += BATCH_SIZE
		
		# Небольшая пауза, чтобы не дудосить сервер
		time.sleep(0.5)
	
	# Сохранение результата
	with open('../media/tnved/customs_data.json', 'w', encoding='utf-8') as f:
		json.dump(all_records, f, ensure_ascii=False, indent=4)
	
	print(f"Готово! Сохранено {len(all_records)} записей в файл customs_data.json")


if __name__ == "__main__":
	main()