# oi/config.py
from dataclasses import dataclass
from typing import List

@dataclass
class AppConfig:
    date_col: str = "data"
    sku_col: str = "sku"
    qty_col: str = "ilosc"
    location_col: str = "magazyn"
    default_service_level: float = 0.95
    default_lead_time_days: int = 7
    allowed_freq: List[str] = ("D", "W", "M")

CONFIG = AppConfig()
