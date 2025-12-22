# app/api/v1/endpoints/excise.py
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlmodel import Session

from app.core.config import settings
from app.core.database import get_session
from app.schemas.rates import SyncStatus

from app.services.importers.import_excise import import_excise_data

router = APIRouter()


@router.post("/excise/sync", response_model=SyncStatus)
def sync_excise(background_tasks: BackgroundTasks, db: Session = Depends(get_session)):
	try:
	
		count_excise = import_excise_data(session=db)
		db.commit()
		return SyncStatus(
			status="success",
			message=f"База успешно обновлена. Акцизы наложены на {count_excise} позиций.",
			processed_files="excise_tnved_data.json",
			total_rates=count_excise
		)
	
	except Exception as e:
		db.rollback()  # Откат, если что-то упало посередине
		raise HTTPException(status_code=500, detail=f"Ошибка синхронизации: {str(e)}")
