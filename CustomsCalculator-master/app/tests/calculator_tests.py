import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from sqlmodel import Session

# Предположим, твой класс лежит в app/services/calculator.py
from app.services.calculator import DutyCalculator
from app.models import TariffRate, TnVedCode
from app.models.country import TradeRegimeType


@pytest.fixture
def mock_session():
	return MagicMock(spec=Session)


@pytest.fixture
def calculator(mock_session):
	# Мокаем получение курса доллара, чтобы расчеты были стабильными
	with patch.object(DutyCalculator, '_get_usd_rate', return_value=12800.0):
		calc = DutyCalculator(mock_session)
		# Устанавливаем БРВ вручную для тестов
		calc.brv = 412000.0
		return calc


def test_calc_customs_fee_pkm55(calculator):
	"""Проверка сбора за оформление по разным порогам стоимости (ПКМ 55)"""
	# Менее 10к USD -> 1 БРВ
	fee_usd, fee_uzs, _ = calculator._calc_customs_fee(5000)
	assert fee_uzs == 412000.0
	
	# 25к USD -> 2.5 БРВ
	fee_usd, fee_uzs, _ = calculator._calc_customs_fee(25000)
	assert fee_uzs == 412000.0 * 2.5
	
	# Более 1 млн USD -> 25 БРВ
	fee_usd, fee_uzs, _ = calculator._calc_customs_fee(1500000)
	assert fee_uzs == 412000.0 * 25


def test_utilization_fee_tire(calculator):
	"""Тест утильсбора для шин (Приложение 2)"""
	metadata = {"type": "tire"}
	inputs = {"weight": 100}  # 100 кг
	
	# Вес * 0.3% БРВ = 100 * (412000 * 0.003) = 123 600
	usd, uzs, desc = calculator._calc_utilization_fee(metadata, inputs)
	assert uzs == 123600.0
	assert "0.3% БРВ" in desc


def test_utilization_fee_electric_car(calculator):
	"""Тест утильсбора для электромобилей (Приложение 1)"""
	metadata = {"type": "M1", "engine_type": "electric"}
	
	# Новый электромобиль (до 3 лет) -> 30 БРВ
	inputs_new = {"manufacturing_year": datetime.now().year}
	_, uzs_new, _ = calculator._calc_utilization_fee(metadata, inputs_new)
	assert uzs_new == 30 * 412000.0
	
	# Старый электромобиль (> 3 лет) -> 90 БРВ
	inputs_old = {"manufacturing_year": 2015}
	_, uzs_old, _ = calculator._calc_utilization_fee(metadata, inputs_old)
	assert uzs_old == 90 * 412000.0


def test_calculate_free_trade_regime(calculator, mock_session):
	"""Тест режима свободной торговли (Пошлина должна быть 0)"""
	
	# 1. Настраиваем моки для возврата данных из БД
	mock_rate = MagicMock(spec=TariffRate)
	mock_rate.rate_type = "ad_valorem"
	mock_rate.ad_valorem_rate = 15.0
	mock_rate.vat_rate = 12.0
	mock_rate.excise_type = "ad_valorem"
	mock_rate.excise_ad_valorem_rate = 0.0
	
	mock_tn = MagicMock(spec=TnVedCode)
	mock_tn.is_util_applicable = False
	
	# Патчим методы поиска, чтобы не ходить в реальную БД
	with patch.object(calculator, 'get_rate_and_code_recursive', return_value=(mock_rate, mock_tn)):
		with patch.object(calculator, '_get_trade_regime', return_value=TradeRegimeType.FREE_TRADE):
			result = calculator.calculate(
				tn_code="8415109000",
				customs_value=1000.0,  # $1000
				weight_kg=10,
				origin_country_code="RU"
			)
			
			# Ищем пошлину в деталях
			duty_detail = next(d for d in result["details"] if d["name"] == "Импортная пошлина")
			assert duty_detail["amount_usd"] == 0.0
			assert "0%" in duty_detail["rate_source"]


def test_calc_complex_rate_mixed(calculator):
	"""Тест комбинированной ставки: 10%, но не менее 2 евро за кг"""
	# 10% от 1000$ = 100$
	# 2$ за кг при 60кг = 120$
	# Mixed/Mixed_min должен выбрать максимум = 120$
	
	inputs = {"weight": 60}
	val, desc = calculator._calc_complex_rate(
		type_enum="mixed",
		ad_valorem_pct=10.0,
		specific_rate=2.0,
		specific_currency="USD",
		specific_unit="kg",
		base_value_usd=1000.0,
		inputs=inputs
	)
	
	assert val == 120.0
	assert "не менее" in desc


def test_edge_case_zero_values(calculator):
	"""Проверка устойчивости к нулевым входным данным"""
	# Если пришел нулевой вес или объем, калькулятор не должен падать с ZeroDivisionError
	metadata = {"type": "M1", "engine_type": "ice"}
	inputs = {"volume": 0, "manufacturing_year": 2024}
	
	usd, uzs, desc = calculator._calc_utilization_fee(metadata, inputs)
	assert uzs >= 0  # Должен вернуть 0 или минимальную ставку, но не ошибку


def test_pkm55_thresholds(calculator):
	"""Точная проверка границ ПКМ 55"""
	# Ровно 10 000 USD. По коду: elif 10_000 <= customs_value_usd < 20_000
	# Значит при 10k коэффициент должен стать 1.5
	_, uzs_10k, _ = calculator._calc_customs_fee(10000)
	assert uzs_10k == 412000.0 * 1.5
	
	# Почти 10 000 (9999.99)
	_, uzs_9k, _ = calculator._calc_customs_fee(9999.99)
	assert uzs_9k == 412000.0 * 1.0


def test_utilization_tractor_power(calculator):
	"""Проверка логики тракторов по мощности (л.с.)"""
	metadata = {"type": "tractor"}
	
	# Трактор новый, 150 л.с. -> rate_brv должен быть 0 (по твоей логике)
	inputs_new = {"power_hp": 150, "manufacturing_year": 2024}
	_, uzs_new, _ = calculator._calc_utilization_fee(metadata, inputs_new)
	assert uzs_new == 0
	
	# Трактор старый (>3 лет), 150 л.с. -> попадает в категорию 102-177 л.с. (480 БРВ)
	inputs_old = {"power_hp": 150, "manufacturing_year": 2015}
	_, uzs_old, _ = calculator._calc_utilization_fee(metadata, inputs_old)
	assert uzs_old == 480 * 412000.0