from typing import List
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlmodel import Session, select

from app.core.database import get_session
from app.models import TnVedCode
from app.services.search import search_tnved_smart
from app.schemas.tnved import TnVedRichResponse

router = APIRouter()


@router.get("/tnved/code/{code}", response_model=TnVedCode)
def get_code_details(code: str, db: Session = Depends(get_session)):
	"""
	Получение информации о товаре.
	Поля is_util_applicable и calc_metadata вернутся автоматически,
	так как они есть в модели TnVedCode.
	"""
	statement = select(TnVedCode).where(TnVedCode.code == code)
	item = db.exec(statement).first()
	
	if not item:
		raise HTTPException(status_code=404, detail="Code not found")
	
	return item


@router.get("/tnved/search", response_model=List[TnVedRichResponse])
def search_goods(
		q: str = Query(..., min_length=2, description="Код или описание"),
		limit: int = 20,
		db: Session = Depends(get_session)
):
	raw_results = search_tnved_smart(session=db, query=q, limit=limit)
	
	response = []
	for item, score in raw_results:
		# ВАЖНО: Добавляем маппинг новых полей
		tnved_data = TnVedRichResponse(
			id=item.id,
			code=item.code,
			description=item.description,
			unit=item.unit,
			unit2=item.unit2,
			# Прокидываем данные для утильсбора
			is_util_applicable=item.is_util_applicable,
			calc_metadata=item.calc_metadata,
			
			match_percentage=score,
			rates=item.rates
		)
		response.append(tnved_data)
	
	return response