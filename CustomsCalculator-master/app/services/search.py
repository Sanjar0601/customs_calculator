# app/services/search.py

from sqlalchemy import func, desc
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload

from app.models.tnved import TnVedCode


def search_tnved_smart(session: Session, query: str, limit: int = 20):
	"""
	Выполняет поиск:
	1. Если query - цифры: ищет по началу кода (точное совпадение = 100%).
	2. Если query - текст: ищет по схожести описания (Trigram Similarity).

	Возвращает список кортежей: (TnVedCode, similarity_score)
	"""
	query = query.strip()
	
	# Жадная загрузка ставок (чтобы не делать N+1 запросов)
	# selectinload эффективен для отношений one-to-many
	stmt = select(TnVedCode).options(selectinload(TnVedCode.rates))
	
	if query.isdigit():
		# --- ЛОГИКА ДЛЯ КОДОВ ---
		# Ищем коды, которые начинаются с введенных цифр
		stmt = stmt.where(TnVedCode.code.startswith(query))
		stmt = stmt.order_by(TnVedCode.code)
		stmt = stmt.limit(limit)
		
		results = session.exec(stmt).all()
		
		# Для кодов "схожесть" считаем условно:
		# Если совпал полностью - 1.0, иначе просто 1.0 (так как мы нашли по startswith)
		# Можно усложнить формулу, но обычно для кодов нужна точность.
		return [(item, 100.0) for item in results]
	
	else:
		# --- ЛОГИКА ДЛЯ ТЕКСТА (Fuzzy Search) ---
		# Используем функцию similarity из pg_trgm
		# similarity возвращает число от 0 до 1
		similarity_score = func.similarity(TnVedCode.description, query).label("score")
		
		stmt = select(TnVedCode, similarity_score)
		
		# Фильтруем совсем плохие совпадения (например, меньше 10%)
		# Можно настроить порог под себя (0.1, 0.2, 0.3)
		stmt = stmt.where(similarity_score > 0.05)
		
		# Сортируем: сначала самые похожие
		stmt = stmt.order_by(desc(similarity_score))
		stmt = stmt.limit(limit)
		
		results = session.exec(stmt).all()
		
		# results будет списком кортежей [(TnVedCode, 0.85), (TnVedCode, 0.42), ...]
		# Преобразуем 0.85 -> 85.0 для удобства
		return [(item, round(score * 100, 1)) for item, score in results]