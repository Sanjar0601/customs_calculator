# app/api/v1/endpoints/rates.py
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlmodel import Session

from app.core.database import get_session
from app.schemas.rates import SyncStatus
from app.services.parsers.parser_duties import run_duties_parser
from app.services.importers.import_duties import import_csv_to_db
from app.services.importers.import_excise import import_excise_data

router = APIRouter()


@router.post("/rates/sync", response_model=SyncStatus)
def sync_rates_full(
		background_tasks: BackgroundTasks,  # Можно использовать для асинхронности
		db: Session = Depends(get_session)
):
	"""
	Запускает полный цикл обновления ставок:
	1. Парсинг Lex.uz -> CSV
	2. CSV -> Таблица TariffRates (очистка и вставка)
	3. JSON -> Наложение акцизов
	"""
	try:
		# 1. Парсинг
		csv_path = run_duties_parser()
		
		# 2. Импорт пошлин
		# Передаем путь строкой, так как pandas read_csv умеет работать с Path, но лучше str
		count_duties = import_csv_to_db(session=db, csv_path=str(csv_path))
		
		# 3. Импорт акцизов
		count_excise = import_excise_data(session=db)
		
		# Подтверждаем транзакцию
		db.commit()
		
		return SyncStatus(
			status="success",
			message=f"База успешно обновлена. Акцизы наложены на {count_excise} позиций.",
			processed_files=csv_path.name,
			total_rates=count_duties
		)
	
	except Exception as e:
		db.rollback()  # Откат, если что-то упало посередине
		raise HTTPException(status_code=500, detail=f"Ошибка синхронизации: {str(e)}")