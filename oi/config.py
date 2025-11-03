# oi/config.py
"""
Centralna konfiguracja aplikacji optymalizacji zatowarowania.

Cel:
- jedno miejsce na nazwy kolumn (data, sku, ilość, magazyn),
- domyślne parametry logistyczne (poziom obsługi, lead time),
- dopuszczalne częstotliwości agregacji,
- możliwość nadpisania konfiguracji zmiennymi środowiskowymi / z pliku.

Uwaga:
moduły typu preprocessing / forecasting / optimization zakładają, że te nazwy
są spójne – więc zmieniaj je tutaj, nie w 5 różnych plikach.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, asdict
from typing import List, Tuple, Dict, Any


def _get_env(key: str, default: str) -> str:
    """Mały helper: pobiera zmienną środowiskową albo daje default."""
    return os.getenv(key, default)


@dataclass(frozen=True)
class AppConfig:
    # ─────────────────────────────────────────
    # Kolumny danych źródłowych
    # ─────────────────────────────────────────
    date_col: str = _get_env("MAGAPP_DATE_COL", "data")
    sku_col: str = _get_env("MAGAPP_SKU_COL", "sku")
    qty_col: str = _get_env("MAGAPP_QTY_COL", "ilosc")
    location_col: str = _get_env("MAGAPP_LOCATION_COL", "magazyn")

    # ─────────────────────────────────────────
    # Parametry logistyczne – domyślne
    # ─────────────────────────────────────────
    default_service_level: float = float(_get_env("MAGAPP_SERVICE_LEVEL", "0.95"))
    default_lead_time_days: int = int(_get_env("MAGAPP_LEAD_TIME_DAYS", "7"))

    # ─────────────────────────────────────────
    # Ekonomia zamówień – można podpiąć w UI
    # ─────────────────────────────────────────
    default_order_cost: float = float(_get_env("MAGAPP_ORDER_COST", "50"))
    default_holding_cost: float = float(_get_env("MAGAPP_HOLDING_COST", "2"))

    # ─────────────────────────────────────────
    # Agregacje czasowe
    # ─────────────────────────────────────────
    allowed_freq: Tuple[str, ...] = ("D", "W", "M")

    # ─────────────────────────────────────────
    # Inne opcje
    # ─────────────────────────────────────────
    # np. domyślny model AI do wyjaśnień
    default_ai_model: str = _get_env("MAGAPP_AI_MODEL", "gpt-4o-mini")

    # Można przechować dodatkowe klucze, np. mapowanie magazynów
    extra: Dict[str, Any] = field(default_factory=dict)

    # ─────────────────────────────────────────
    # Metody pomocnicze
    # ─────────────────────────────────────────
    def to_dict(self) -> Dict[str, Any]:
        """Zrzuca konfigurację do dict – przydaje się np. do wyświetlenia w UI."""
        return asdict(self)

    def with_override(self, **kwargs: Any) -> "AppConfig":
        """
        Tworzy NOWY obiekt configu z podmienionymi polami.
        Dzięki temu nie modyfikujemy globalnego CONFIG w locie,
        tylko robimy kopię “na potrzeby jednej operacji”.
        """
        data = self.to_dict()
        data.update(kwargs)
        # extra musi być dict
        if "extra" in kwargs and kwargs["extra"] is None:
            data["extra"] = {}
        return AppConfig(**data)

    def validate_cols(self, df_cols: List[str]) -> Dict[str, bool]:
        """
        Szybki walidator – czy w dataframe są kolumny, których oczekujemy.
        Można wyświetlić w UI na czerwono, czego brakuje.
        """
        expected = [self.date_col, self.sku_col, self.qty_col]
        if self.location_col:
            expected.append(self.location_col)
        return {col: (col in df_cols) for col in expected}


# globalna instancja, której używają pozostałe moduły
CONFIG = AppConfig()
