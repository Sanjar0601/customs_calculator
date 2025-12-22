import asyncio
import logging
from sqlmodel import Session, select, func

# Импортируем движок и настройки
from app.core.database import engine
from app.core.config import settings
from app.models.tnved import TnVedCode

# Импортируем функции импорта (синхронные)
from app.services.importers.import_tnved_codes import import_tnved_codes
from app.services.importers.import_duties import import_csv_to_db
from app.services.importers.import_excise import import_excise_data
from app.services.parsers.parser_duties import run_duties_parser

# Импортируем функции парсинга (асинхронные)
from app.services.parsers.parser_countries import sync_countries_from_lexuz
from app.services.parsers.parser_currency import CurrencyClient

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def init_async_data(session: Session):
	"""Запуск асинхронных парсеров (Страны, Валюта)"""
	logger.info("🌍 Синхронизация стран с Lex.uz...")
	await sync_countries_from_lexuz(session)
	
	logger.info("💰 Обновление курсов валют ЦБ...")
	client = CurrencyClient()
	await client.update_rates(session)


def main():
	logger.info("🚀 Проверка состояния базы данных...")
	
	with Session(engine) as session:
		# Проверяем, есть ли уже данные в ТН ВЭД
		# Если данные есть, считаем, что инициализация не нужна (чтобы не парсить каждый раз при рестарте)
		count = session.exec(select(func.count(TnVedCode.id))).one()
		
		if count > 0:
			logger.info(f"✅ В базе уже есть {count} кодов ТН ВЭД. Пропускаем инициализацию.")
			return
		
		logger.info("⚡ База пуста. Начинаем первичную инициализацию...")
		
		# 1. Импорт справочника ТН ВЭД (Фундамент)
		# Путь к CSV берем из настроек
		tnved_csv = settings.TNVED_DIR / "tnved_codes.csv"
		if tnved_csv.exists():
			import_tnved_codes(tnved_csv)
		else:
			logger.error(f"❌ Файл {tnved_csv} не найден! Пропускаем импорт кодов.")
			return  # Без кодов дальше идти нет смысла
		
		# 2. Асинхронные задачи (Страны, Валюты)
		# Создаем новую сессию для асинхронного цикла или используем текущую осторожно
		# (в данном случае sync_countries_from_lexuz ожидает session, но внутри httpx асинхронный)
		asyncio.run(init_async_data(session))
		
		# 3. Парсинг и импорт пошлин (Tariff Rates)
		try:
			logger.info("📜 Запуск парсера пошлин (Lex.uz)...")
			duties_csv_path = run_duties_parser()
			
			logger.info(f"📥 Импорт ставок из файла: {duties_csv_path}")
			import_csv_to_db(session=session, csv_path=str(duties_csv_path))
			
			# Сохраняем пошлины перед наложением акцизов
			session.commit()
		except Exception as e:
			logger.error(f"❌ Ошибка при обработке пошлин: {e}")
		
		# 4. Наложение акцизов
		try:
			logger.info("🏷️ Наложение акцизов...")
			import_excise_data(session=session)
			session.commit()
		except Exception as e:
			logger.error(f"❌ Ошибка при наложении акцизов: {e}")
		
		logger.info("🏁 Первичная инициализация успешно завершена!")


if __name__ == "__main__":
	main()