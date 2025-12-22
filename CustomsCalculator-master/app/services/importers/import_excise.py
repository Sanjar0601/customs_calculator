import json
from sqlmodel import Session, select
from app.models.rates import TariffRate, ExciseType
from app.models.tnved import TnVedCode
from app.core.config import settings


def import_excise_data(session: Session):
	print("🚀 Накладываем акцизы...")
	
	file_path = settings.EXCISE_DIR / "excise_tnved_data.json"
	
	if not file_path.exists():
		print(f"❌ Файл {file_path} не найден!")
		return 0
	
	with open(file_path, "r", encoding="utf-8") as f:
		data = json.load(f)
	
	updated_count = 0
	
	for item in data:
		target_codes = item.get("approx_codes", [])
		
		ex_type = item.get("excise_type", "ad_valorem")
		ex_percent = float(item.get("excise_percent", 0.0))
		ex_spec_amount = float(item.get("excise_specific_amount", 0.0))
		ex_currency = item.get("excise_currency", "UZS")
		ex_unit = item.get("excise_unit")
		
		# Оптимизация: ищем сразу все Rate, у которых коды начинаются с префикса
		# Но так как связь Code -> Rate, придется делать join
		for code_prefix in target_codes:
			statement = (
				select(TariffRate)
				.join(TnVedCode)
				.where(TnVedCode.code.startswith(code_prefix))
			)
			rates = session.exec(statement).all()
			
			for rate in rates:
				rate.excise_type = ExciseType(ex_type)
				rate.excise_ad_valorem_rate = ex_percent
				rate.excise_specific_rate = ex_spec_amount if ex_spec_amount > 0 else None
				rate.excise_currency = ex_currency
				rate.excise_unit = ex_unit
				session.add(rate)
				updated_count += 1
	
	print(f"✅ Акцизы обновлены: {updated_count}")
	return updated_count
