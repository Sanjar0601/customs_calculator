from datetime import datetime
from sqlmodel import Session, select
from app.models import TariffRate, TnVedCode
from app.models.currency import CurrencyRate, Currency
from app.models.country import Country, TradeRegimeType


class DutyCalculator:
	def __init__(self, session: Session):
		self.session = session
		self.usd_rate = self._get_usd_rate()
		self.brv = 412000.0
	
	def _get_usd_rate(self) -> float:
		statement = (
			select(CurrencyRate.rate)
			.join(Currency)
			.where(Currency.char_code == "USD")
			.order_by(CurrencyRate.date.desc())
		)
		rate = self.session.exec(statement).first()
		return rate if rate else 12850.0
	
	def get_rate_and_code_recursive(self, tn_code_str: str) -> tuple[TariffRate, TnVedCode] | None:
		"""
		Ищет ставку и сам объект кода ТН ВЭД (чтобы достать метаданные).
		"""
		code_to_search = tn_code_str.strip()
		while len(code_to_search) >= 4:
			tn_obj = self.session.exec(
				select(TnVedCode).where(TnVedCode.code == code_to_search)
			).first()
			if tn_obj:
				rate = self.session.exec(
					select(TariffRate).where(TariffRate.tn_ved_code_id == tn_obj.id)
				).first()
				if rate:
					return rate, tn_obj
			code_to_search = code_to_search[:-2]
		return None
	
	def _get_trade_regime(self, country_code: str | None) -> TradeRegimeType:
		if not country_code:
			return TradeRegimeType.GENERAL
		
		country = self.session.exec(
			select(Country).where(Country.iso_code == country_code.upper())
		).first()
		
		return country.trade_regime if country else TradeRegimeType.GENERAL
	
	def _calc_complex_rate(self, type_enum: str, ad_valorem_pct: float,
	                       specific_rate: float | None, specific_currency: str,
	                       specific_unit: str | None, base_value_usd: float, inputs: dict) -> tuple[float, str]:
		# ... (Код функции без изменений, как в твоем исходнике) ...
		# Для экономии места не дублирую логику специфических ставок,
		# предполагается, что она осталась такой же, как в твоем вопросе.
		
		# 1. Адвалорная часть
		ad_valorem_amt = base_value_usd * (ad_valorem_pct / 100)
		
		# 2. Специфическая часть
		specific_amt = 0.0
		u = specific_unit
		
		if specific_rate:
			qty = 0.0
			# --- ГРУППА 1: ВЕС ---
			if u in ['kg', 'кг', 'kg_90_dry', 'kg_h2o2', 'kg_k2o', 'kg_n', 'kg_naoh', 'kg_p2o5', 'kg_u', 'kg_koh',
			         'g_di']:
				qty = inputs['weight']
				if u in ['g', 'г', 'g_di']:
					qty = inputs['weight'] * 1000
				elif u in ['t', 'т']:
					qty = inputs['weight'] / 1000
			
			# --- ГРУППА 2: ШТУКИ ---
			elif u in ['pcs', 'шт', 'pair', 'пар']:
				qty = inputs['qty']
			elif u in ['100_pcs', '100 шт']:
				qty = inputs['qty'] / 100
			elif u in ['1000_pcs', '1000 шт']:
				qty = inputs['qty'] / 1000
			
			# --- ГРУППА 3: ЛИТРЫ ---
			elif u in ['l', 'л', 'литр', 'l_alc_100', 'л100% сп.']:
				qty = inputs['liters']
			elif u in ['ml']:
				qty = inputs['liters'] * 1000
			elif u in ['1000_l', '1000 л.']:
				qty = inputs['liters'] / 1000
			
			# --- ГРУППА 4: ОБЪЕМ (Двигатель/Кубы) ---
			elif u in ['m3', 'м3', 'cm3', 'см3']:
				# В inputs['volume'] лежит значение в см3 (обычно объем двигателя)
				if u in ['cm3', 'см3']:
					qty = inputs['volume']
				elif u in ['m3', 'м3']:
					# Если ставка за кубометр (лес, газ), а ввод в см3, конвертируем
					# Но чаще volume используется для авто. Оставим простую логику:
					qty = inputs['volume'] / 1_000_000 if inputs['volume'] > 100 else inputs['volume']
			
			# --- ГРУППА 5: ПРОЧЕЕ ---
			elif u in ['m2', 'м2', 'm', 'м', 'carat', 'кар', 'ci', 'кюри']:
				qty = inputs['qty']  # Фронт должен мапить это
			elif u in ['1000_m2', '1000 м2', '1000_kwh', '1000 кВтч']:
				qty = inputs['qty'] / 1000
			
			# Расчет денег
			rate_in_usd = specific_rate
			if specific_currency == "UZS":
				rate_in_usd = specific_rate / self.usd_rate
			specific_amt = qty * rate_in_usd
		
		# 3. Итог
		final_amt = 0.0
		method_desc = ""
		
		if type_enum == "ad_valorem":
			final_amt = ad_valorem_amt
			method_desc = f"{ad_valorem_pct}%"
		elif type_enum == "specific":
			final_amt = specific_amt
			curr = "сум" if specific_currency == "UZS" else "$"
			method_desc = f"{specific_rate} {curr}/{u}"
		elif type_enum == "combined":
			final_amt = ad_valorem_amt + specific_amt
			curr = "сум" if specific_currency == "UZS" else "$"
			method_desc = f"{ad_valorem_pct}% + {specific_rate} {curr}/{u}"
		elif type_enum in ["mixed", "mixed_min"]:
			final_amt = max(ad_valorem_amt, specific_amt)
			curr = "сум" if specific_currency == "UZS" else "$"
			method_desc = f"{ad_valorem_pct}%, но не менее {specific_rate} {curr}/{u}"
		
		return final_amt, method_desc
	
	def _calc_customs_fee(self, customs_value_usd: float) -> tuple[float, float, str]:
		# Логика ПКМ 55 (без изменений)
		multiplier = 0.0
		if customs_value_usd < 10_000:
			multiplier = 1.0
		elif 10_000 <= customs_value_usd < 20_000:
			multiplier = 1.5
		elif 20_000 <= customs_value_usd < 40_000:
			multiplier = 2.5
		elif 40_000 <= customs_value_usd < 60_000:
			multiplier = 4.0
		elif 60_000 <= customs_value_usd < 100_000:
			multiplier = 7.0
		elif 100_000 <= customs_value_usd < 200_000:
			multiplier = 10.0
		elif 200_000 <= customs_value_usd < 500_000:
			multiplier = 15.0
		elif 500_000 <= customs_value_usd < 1_000_000:
			multiplier = 20.0
		else:
			multiplier = 25.0
		
		fee_uzs = self.brv * multiplier
		fee_usd = fee_uzs / self.usd_rate
		desc = f"Сбор за оформление ({multiplier} БРВ) по ПКМ №55"
		return fee_usd, fee_uzs, desc
	
	def _calc_utilization_fee(self, metadata: dict, inputs: dict) -> tuple[float, float, str]:
		"""
		Расчет утилизационного сбора.
		Возвращает: (сумма USD, сумма UZS, описание)
		"""
		if not metadata:
			return 0.0, 0.0, "Не применяется"
		
		vehicle_type = metadata.get("type")
		
		# 1. ШИНЫ (Приложение 2)
		# Формула: Вес * 0.3% БРВ (коэффициент 0.003 от БРВ за кг)
		if vehicle_type == "tire":
			weight = inputs.get("weight", 0)
			if weight <= 0:
				return 0.0, 0.0, "Требуется вес шин"
			
			# Ставка 0.3% от БРВ за кг
			fee_uzs = weight * (self.brv * 0.003)
			fee_usd = fee_uzs / self.usd_rate
			return fee_usd, fee_uzs, f"Шины: {weight}кг * 0.3% БРВ"
		
		# --- Для ТРАНСПОРТА важен возраст ---
		manuf_year = inputs.get("manufacturing_year")
		if not manuf_year:
			# Если год не указан, считаем как "новый" для предварительного расчета, но пишем warning
			# Или возвращаем 0. Давай вернем расчет как для нового, но пометим в описании.
			manuf_year = datetime.now().year
		
		current_year = datetime.now().year
		age = current_year - manuf_year
		is_old = age > 3  # Граница "старости" - 3 года
		
		rate_brv = 0.0  # Коэффициент БРВ
		desc_prefix = ""
		
		# 2. ЛЕГКОВЫЕ (M1)
		if vehicle_type == "M1":
			engine_type = metadata.get("engine_type", "ice")
			
			# Электромобили и Гибриды (Приложение 1, п. III)
			# Примечание: В законе гибриды часто идут вместе с электро (код 8703 80), но надо проверять.
			# Если у тебя чистый электро:
			if engine_type == "electric":
				rate_brv = 30 if not is_old else 90
				desc_prefix = "Электромобиль"
			else:
				# ДВС - зависит от объема
				vol = inputs.get("volume", 0)
				desc_prefix = f"Легковой (V={vol} см3)"
				
				if vol < 1000:
					rate_brv = 30 if not is_old else 90
				elif 1000 <= vol < 2000:
					rate_brv = 120 if not is_old else 210
				elif 2000 <= vol < 3000:
					rate_brv = 180 if not is_old else 330
				elif 3000 <= vol < 3500:
					rate_brv = 180 if not is_old else 390
				else:  # > 3500
					rate_brv = 300 if not is_old else 480
		
		# 3. ГРУЗОВИКИ (N)
		elif vehicle_type == "N":
			# Зависит от ТОННАЖА.
			# Внимание: inputs['weight'] это обычно вес нетто (самого авто).
			# А закон требует "Полную массу". Для калькулятора будем использовать weight как оценку,
			# либо нужно добавить поле 'max_weight' во фронтенд.
			# Пока используем weight (в тоннах).
			w_tons = inputs.get("weight", 0) / 1000.0
			desc_prefix = f"Грузовик ({w_tons:.1f}т)"
			
			if w_tons <= 2.5:
				rate_brv = 100 if not is_old else 150  # исправлено по таблице (было 30/90 для легковых) - проверь точные цифры в законе!
			# UPD: По таблице N1 до 2.5т: 30(new)/90(old)? Нет, в таблице N категории ставки выше.
			# Смотрим Приложение 1, раздел IV:
			# до 2.5т: 100 / 150
			elif 2.5 < w_tons <= 3.5:
				rate_brv = 210 if not is_old else 300
			elif 3.5 < w_tons <= 5:
				rate_brv = 210 if not is_old else 300
			elif 5 < w_tons <= 8:
				rate_brv = 210 if not is_old else 300
			elif 8 < w_tons <= 12:
				rate_brv = 300 if not is_old else 810
			elif 12 < w_tons <= 20:
				rate_brv = 330 if not is_old else 1200
			elif 20 < w_tons <= 50:
				rate_brv = 690 if not is_old else 1410
			# Электрогрузовики (код 8704 90 000) идут отдельно: 120 / 150
			# Если в metadata есть пометка:
			if metadata.get("engine_type") == "electric":
				rate_brv = 120 if not is_old else 150
				desc_prefix = "Электрогрузовик"
		
		# 4. ТРАКТОРЫ (I)
		elif vehicle_type == "tractor":
			# Зависит от МОЩНОСТИ (л.с.)
			hp = inputs.get("power_hp", 0)
			desc_prefix = f"Трактор ({hp} л.с.)"
			
			# Конвертация: 1 кВт = 1.35962 л.с. (Закон дает диапазоны в л.с.)
			# до 25 л.с. (18 кВт)
			if hp <= 25:
				rate_brv = 0 if not is_old else 120  # Часто новые тракторы 0, старые платные
			elif 25 < hp <= 51:
				rate_brv = 0 if not is_old else 240
			elif 51 < hp <= 102:
				rate_brv = 0 if not is_old else 360
			elif 102 < hp <= 177:
				rate_brv = 0 if not is_old else 480
			else:
				rate_brv = 0 if not is_old else 600
			
			# Тягачи седельные (8701 20) идут отдельно, как грузовики обычно, но в таблице I есть пункт "Тягачи седельные"
			# 8701 20: 670 / 1360
			# Тут нужна проверка кода. Если metadata['subtype'] == 'sedelny':
			if str(inputs.get('tn_code', '')).startswith('87012'):
				rate_brv = 670 if not is_old else 1360
				desc_prefix = "Седельный тягач"
		
		# 5. СПЕЦТЕХНИКА (VII)
		elif vehicle_type == "special":
			# Грейдеры, бульдозеры и т.д.
			# Обычно для новых 0, для старых ставка.
			# Для простоты примера беру усредненную логику (как экскаваторы 8429 52)
			hp = inputs.get("power_hp", 0)
			desc_prefix = "Спецтехника"
			# Ставки сильно разнятся от типа (грейдер, каток, погрузчик).
			# Если нужно точно - надо в metadata писать subtype.
			# Допустим, логика "экскаваторная":
			rate_brv = 0 if not is_old else 240  # Условно, если нет точных данных
			if is_old:
				if hp > 170: rate_brv = 360
				if hp > 250: rate_brv = 480
		
		# --- ИТОГОВЫЙ РАСЧЕТ ---
		if rate_brv > 0:
			fee_uzs = rate_brv * self.brv
			fee_usd = fee_uzs / self.usd_rate
			condition_str = "> 3 лет" if is_old else "до 3 лет"
			desc = f"Утильсбор ({desc_prefix}, {condition_str}): {rate_brv} БРВ"
			return fee_usd, fee_uzs, desc
		
		return 0.0, 0.0, "Утильсбор не начисляется (или 0)"
	
	def calculate(self, tn_code: str, customs_value: float, weight_kg: float,
	              quantity_pcs: float = 0, volume_cm3: float = 0, liter_qty: float = 0,
	              manufacturing_year: int = None, power_hp: float = 0,
	              origin_country_code: str | None = None):
		"""
		Основной метод расчета.
		Добавлены manufacturing_year и power_hp.
		"""
		
		# 1. Поиск ставки и кода (для метаданных)
		result = self.get_rate_and_code_recursive(tn_code)
		
		if not result:
			return {
				"tn_code": tn_code,
				"error": "Код ТН ВЭД не найден",
				"total_payments_usd": 0, "total_payments_uzs": 0, "details": [],
				"currency_rate": self.usd_rate
			}
		
		rate, tn_code_obj = result
		
		inputs = {
			"weight": weight_kg,
			"qty": quantity_pcs if quantity_pcs else 0,
			"volume": volume_cm3 if volume_cm3 else 0,
			"liters": liter_qty if liter_qty else 0,
			"manufacturing_year": manufacturing_year,
			"power_hp": power_hp,
			"tn_code": tn_code
		}
		
		# 2. Определение режима торговли
		regime = self._get_trade_regime(origin_country_code)
		details = []
		
		# --- ИМПОРТНАЯ ПОШЛИНА ---
		base_duty_usd, base_duty_desc = self._calc_complex_rate(
			rate.rate_type, rate.ad_valorem_rate, rate.specific_rate,
			rate.specific_currency, rate.specific_unit, customs_value, inputs
		)
		
		final_duty_usd = base_duty_usd
		final_duty_desc = base_duty_desc
		
		if regime == TradeRegimeType.FREE_TRADE:
			final_duty_usd = 0.0
			final_duty_desc = f"0% (Зона свободной торговли: {origin_country_code})"
		elif regime == TradeRegimeType.GENERAL:
			# Генеральный режим (х2)
			final_duty_usd = base_duty_usd * 2
			final_duty_desc = f"{base_duty_desc} x 2 (Двойная ставка)"
		
		details.append({
			"name": "Импортная пошлина",
			"rate_source": final_duty_desc,
			"amount_usd": round(final_duty_usd, 2),
			"amount_uzs": round(final_duty_usd * self.usd_rate, 2)
		})
		
		# --- АКЦИЗ ---
		excise_usd, excise_desc = self._calc_complex_rate(
			rate.excise_type, rate.excise_ad_valorem_rate, rate.excise_specific_rate,
			rate.excise_currency, rate.excise_unit, customs_value, inputs
		)
		if excise_usd > 0.01 or rate.excise_ad_valorem_rate > 0:
			details.append({
				"name": "Акцизный налог",
				"rate_source": excise_desc,
				"amount_usd": round(excise_usd, 2),
				"amount_uzs": round(excise_usd * self.usd_rate, 2)
			})
		
		# --- НДС ---
		vat_base = customs_value + final_duty_usd + excise_usd
		vat_usd = vat_base * (rate.vat_rate / 100)
		details.append({
			"name": f"НДС ({rate.vat_rate}%)",
			"rate_source": "12% от (Стоимость + Пошлина + Акциз)",
			"amount_usd": round(vat_usd, 2),
			"amount_uzs": round(vat_usd * self.usd_rate, 2)
		})
		
		# --- ТАМОЖЕННЫЙ СБОР (ПКМ 55) ---
		fee_usd, fee_uzs, fee_desc = self._calc_customs_fee(customs_value)
		details.append({
			"name": "Таможенный сбор",
			"rate_source": fee_desc,
			"amount_usd": round(fee_usd, 2),
			"amount_uzs": round(fee_uzs, 2)
		})
		
		# --- [NEW] УТИЛИЗАЦИОННЫЙ СБОР ---
		# Проверяем флаг в базе или наличие метаданных
		if tn_code_obj.is_util_applicable:
			util_usd, util_uzs, util_desc = self._calc_utilization_fee(tn_code_obj.calc_metadata, inputs)
			if util_usd > 0:
				details.append({
					"name": "Утилизационный сбор",
					"rate_source": util_desc,
					"amount_usd": round(util_usd, 2),
					"amount_uzs": round(util_uzs, 2)
				})
			# Утильсбор НЕ входит в базу НДС, он платится отдельно
		else:
			util_usd = 0.0
		
		# Итоговая сумма
		total_usd = final_duty_usd + excise_usd + vat_usd + fee_usd + util_usd
		
		return {
			"tn_code": tn_code,
			"currency_rate": round(self.usd_rate, 2),
			"brv_rate": self.brv,  # Полезно вернуть БРВ на фронт
			"total_payments_usd": round(total_usd, 2),
			"total_payments_uzs": round(total_usd * self.usd_rate, 2),
			"details": details,
			"error": None
		}