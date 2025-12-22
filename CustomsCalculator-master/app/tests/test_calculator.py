from sqlmodel import Session, select
from app.core.database import engine
from app.services.calculator import DutyCalculator


def test_calculation():
	with Session(engine) as session:
		calc = DutyCalculator(session)

		print("--- ТЕСТ 1: Обычный товар (Мясо, 0%) ---")
		params = {
				"tn_code": "8703231101",
				"customs_value": 15000,
				"weight_kg": 1400,
				"volume_cm3": 2400,
				"manufacturing_year": 2020,
				"origin_country_code": "DE"
			}
		res1 = calc.calculate(
			**params
		)
		print(res1)



if __name__ == "__main__":
	test_calculation()