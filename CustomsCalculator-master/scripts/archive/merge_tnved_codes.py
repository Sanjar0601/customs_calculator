import pandas as pd
import re


def clean_code(code):
	"""Удаляет пробелы и оставляет только цифры"""
	if pd.isna(code): return None
	return re.sub(r'\D', '', str(code))


def get_parent(code):
	"""Создает родительский код для иерархии"""
	if not code: return None
	code_len = len(code)
	if code_len == 10:
		return code[:6]
	elif code_len > 6:
		return code[:6]
	elif code_len == 6:
		return code[:4]
	elif code_len == 5:
		return code[:4]
	elif code_len == 4:
		return code[:2]
	return None


# 1. Загружаем файл изменений (DOC/HTML)
# Pandas умеет читать таблицы прямо из Word-файлов, если они сохранены как HTML
# (ваш файл 349.doc по структуре является HTML)
with open('../../media/tnved/349 04.06.2025.doc', 'r', encoding='utf-8', errors='ignore') as f:
	dfs = pd.read_html(f.read())

df_changes = dfs[0]
# Назначаем колонки (0-Unit, 1-Desc, 2-New, 3-Old, 4-Note)
df_changes.columns = ['unit', 'description_uz', 'new_code', 'old_code', 'note']

# Очищаем коды
df_changes['new_code_clean'] = df_changes['new_code'].apply(clean_code)
df_changes['old_code_clean'] = df_changes['old_code'].apply(clean_code)

# Создаем карту изменений: Старый -> [Новый1, Новый2...]
old_to_new_map = {}
new_code_info = {}  # Словарь для описаний новых кодов

for _, row in df_changes.iterrows():
	n_code = row['new_code_clean']
	o_code = row['old_code_clean']
	desc = str(row['description_uz']).strip()
	
	if n_code:
		new_code_info[n_code] = desc  # Сохраняем узбекское описание на всякий случай
	
	if o_code and n_code:
		if o_code not in old_to_new_map:
			old_to_new_map[o_code] = []
		old_to_new_map[o_code].append(n_code)

# 2. Загружаем старую базу (CSV)
df_old = pd.read_csv('../media/tnved_base_2023.csv', dtype=str)
df_old['code'] = df_old['code'].apply(clean_code)

final_rows = []
processed_new_codes = set()

# 3. Объединяем данные
for _, row in df_old.iterrows():
	code = row['code']
	desc = row['description']
	
	if code in old_to_new_map:
		# Если код изменился, берем новые коды, но оставляем СТАРОЕ описание (Русское)
		new_codes_list = old_to_new_map[code]
		for new_c in new_codes_list:
			final_rows.append({'code': new_c, 'description': desc})
			processed_new_codes.add(new_c)
	else:
		# Если изменений нет, оставляем как есть
		final_rows.append({'code': code, 'description': desc})
		processed_new_codes.add(code)

# 4. Добавляем абсолютно новые коды (которых не было в старой базе)
for n_code, uz_desc in new_code_info.items():
	if n_code not in processed_new_codes and len(str(n_code)) >= 4:
		# Добавляем с меткой [UZ], так как русского перевода нет
		final_rows.append({'code': n_code, 'description': f"[UZ] {uz_desc}"})

# 5. Собираем DataFrame и добавляем ID и Parent
df_final = pd.DataFrame(final_rows)
df_final['parent_code'] = df_final['code'].apply(get_parent)
df_final['id'] = range(1, len(df_final) + 1)

# Сохраняем
df_final = df_final[['id', 'code', 'description', 'parent_code']]
df_final.to_csv('merged_tnved_database.csv', index=False)
print("Готово!")