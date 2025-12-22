# app/api/v1/endpoints/countries.py
from typing import List
from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from app.core.database import get_session
from app.models.country import Country
from app.services.parsers.parser_countries import sync_countries_from_lexuz

router = APIRouter()

@router.post("/sync_lexuz")
async def sync_countries(session: Session = Depends(get_session)):
    """
    Запускает парсер Lex.uz.
    """
    result = await sync_countries_from_lexuz(session)
    return result

@router.get("/countries", response_model=List[Country])
def get_countries(session: Session = Depends(get_session)):
    """
    Возвращает список всех стран.
    """
    countries = session.exec(select(Country)).all()
    return countries