# app/models/__init__.py
# Импорт моделей, чтобы они были зарегистрированы в реестре ORM
from .tnved import TnVedCode
from .rates import TariffRate, RateType, ExciseType
from .country import Country

__all__ = ["TnVedCode", "TariffRate", "RateType", "ExciseType", 'Country']


