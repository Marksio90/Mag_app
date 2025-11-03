# oi/__init__.py
"""
oi – Operations Intelligence / Inventory Optimization core package

Ten pakiet spina całą logikę domenową aplikacji:
- config            – wspólna konfiguracja i stałe domenowe
- utils             – inicjalizacja sesji, ogólne helpery Streamlit/Python
- data_ingestion    – wczytywanie wielu plików (sprzedaż, dostawy, produkcja, stany)
- preprocessing     – normalizacja, mapowanie kolumn, agregacje czasowe
- forecasting       – prognozowanie popytu (fallback + haki pod modele zaawansowane)
- optimization      – ROP, safety stock, EOQ i inne polityki uzupełnień
- simulation        – Monte Carlo i testowanie strategii
- ai_assistant      – integracja z OpenAI, copilot magazynowy
- ui_components     – wspólne komponenty UI dla Streamlit

Z założenia:
- moduły mają być możliwie niezależne,
- w UI importujemy tylko to, czego potrzebujemy,
- tutaj trzymamy **publiczny interfejs** pakietu.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any, Dict

# wersjonowanie pakietu – przyda się w logach / stopce / telemetry
__version__ = "0.1.0"

# deklaracja publicznych submodułów – to będzie użyte np. w autogenerowanych docs
__all__ = [
    "config",
    "utils",
    "data_ingestion",
    "preprocessing",
    "forecasting",
    "optimization",
    "simulation",
    "ai_assistant",
    "ui_components",
    "get_submodule",
    "__version__",
]

# opcjonalny cache, żeby nie importować w kółko
_loaded_modules: Dict[str, Any] = {}


def get_submodule(name: str) -> Any:
    """
    Lazy loader dla podmodułów oi.
    Umożliwia np. dynamiczne włączanie modułów w zależności od konfiguracji
    albo trybu działania (lokalny / produkcyjny).

    Przykład:
        forecasting = get_submodule("forecasting")
        res = forecasting.forecast_sku(...)

    Jeśli moduł nie istnieje – rzuci KeyError, żeby łatwo to wychwycić w UI.
    """
    if name in _loaded_modules:
        return _loaded_modules[name]

    full_name = f"oi.{name}"
    try:
        mod = import_module(full_name)
    except ModuleNotFoundError as exc:
        raise KeyError(f"Moduł '{name}' nie jest dostępny w pakiecie 'oi'.") from exc

    _loaded_modules[name] = mod
    return mod


# ─────────────────────────────────────────────────────────────────────────────
# Ewentualne wstępne inicjalizacje pakietu (telemetria, rejestr modeli, itd.)
# Na razie zostawiamy puste, ale mamy miejsce na "bootstrap" całego oi.
# ─────────────────────────────────────────────────────────────────────────────
def _bootstrap() -> None:
    # tu możesz np. w przyszłości:
    # - załadować domyślną konfigurację z pliku YAML
    # - zarejestrować dostępne algorytmy prognozujące
    # - odpalić walidację środowiska (czy jest pandas, numpy, openai)
    # na razie nie robimy nic, żeby nie spowalniać startu Streamlita
    return


_bootstrap()
