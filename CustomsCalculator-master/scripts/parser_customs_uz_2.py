import requests
import time
import json

import urllib3

# ================= НАСТРОЙКИ =================
CURRENT_JSESSIONID = "DB698FC325486785722821A50BF5352C"  # Проверьте актуальность!
TARGET_URL = "https://tarif.customs.uz/JqueryDatatablePluginDemo"

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# Начинаем с того места, где остановились
START_INDEX = 7000
BATCH_SIZE = 100  # Можно оставить 100, это оптимально
OUTPUT_FILE = '../media/tnved/customs_data_part2_v2.json'  # Пишем в новый файл
# =============================================

headers = {
	"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
	"Accept": "application/json, text/javascript, */*; q=0.01",
	"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
	"X-Requested-With": "XMLHttpRequest",
	"Origin": "https://tarif.customs.uz",
	"Referer": "https://tarif.customs.uz/spravochnik/viewDatatable.jsp?lang=ru_Ru",
	"Cookie": f"JSESSIONID={CURRENT_JSESSIONID}",
}


def fetch_data_with_retry(start_index, retries=3):
	"""
	Запрашивает данные с механизмом повторных попыток при ошибке.
	"""
	payload = {
		"sEcho": 1,
		"iColumns": 4,
		"sColumns": ",,,",
		"iDisplayStart": start_index,
		"iDisplayLength": BATCH_SIZE,
		"mDataProp_0": 0, "sSearch_0": "", "bRegex_0": "false", "bSearchable_0": "true", "bSortable_0": "true",
		"mDataProp_1": 1, "sSearch_1": "", "bRegex_1": "false", "bSearchable_1": "true", "bSortable_1": "true",
		"mDataProp_2": 2, "sSearch_2": "", "bRegex_2": "false", "bSearchable_2": "true", "bSortable_2": "true",
		"mDataProp_3": 3, "sSearch_3": "", "bRegex_3": "false", "bSearchable_3": "true", "bSortable_3": "true",
		"sSearch": "", "bRegex": "false", "iSortCol_0": 0, "sSortDir_0": "asc", "iSortingCols": 1
	}
	
	for attempt in range(1, retries + 1):
		try:
			response = requests.post(TARGET_URL, headers=headers, data=payload, timeout=30, verify=False)
			if response.status_code == 200:
				return response.json()
			else:
				print(f"Ошибка сервера {response.status_code}. Попытка {attempt}/{retries}...")
		except Exception as e:
			print(f"Ошибка сети: {e}. Попытка {attempt}/{retries}...")
		
		time.sleep(3)  # Ждем 3 секунды перед повтором
	
	return None


def main():
	all_records = []
	current_start = START_INDEX
	# Ставим заведомо большее число, чтобы зайти в цикл, потом оно обновится реальным
	total_records = START_INDEX + 1
	
	print(f"Продолжаем парсинг с позиции {START_INDEX}...")
	
	while current_start < total_records:
		print(f"Загрузка: {current_start} - {current_start + BATCH_SIZE}...", end=" ")
		
		data = fetch_data_with_retry(current_start)
		
		if not data:
			print("\n❌ Не удалось получить данные после 3 попыток. Остановка.")
			break
		
		rows = data.get('aaData', [])
		
		if not rows:
			print("\nДанные закончились или пустой ответ.")
			break
		
		all_records.extend(rows)
		
		# Обновляем общее количество
		total_records = int(data.get('iTotalDisplayRecords', data.get('iTotalRecords', 0)))
		print(f"OK. (Скачано в этом сеансе: {len(all_records)})")
		
		current_start += BATCH_SIZE
		time.sleep(0.5)
	
	# Сохранение во ВТОРОЙ файл
	with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
		json.dump(all_records, f, ensure_ascii=False, indent=4)
	
	print(f"\n✅ Готово! Вторая часть сохранена в '{OUTPUT_FILE}' ({len(all_records)} записей).")


if __name__ == "__main__":
	main()