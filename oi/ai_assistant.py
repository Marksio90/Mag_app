# oi/ai_assistant.py
from __future__ import annotations

import os
from typing import Optional, Dict, Any, List

import streamlit as st
from openai import OpenAI, OpenAIError

# ─────────────────────────────────────────────────────────────
# Stałe / domyślne ustawienia
# ─────────────────────────────────────────────────────────────

# System prompt dopasowany do aplikacji magazynowej
SYSTEM_PROMPT = (
    "Jesteś ekspertem ds. prognozowania popytu i optymalizacji zapasów w łańcuchu dostaw. "
    "Odpowiadasz po polsku, zwięźle, ale merytorycznie. "
    "Uzasadniasz rekomendacje używając pojęć: popyt prognozowany, zapas bezpieczeństwa, poziom obsługi, ROP, EOQ. "
    "Jeśli brakuje danych (np. lead time, aktualny stan, poziom obsługi), wyraźnie powiedz czego brakuje i jak to zdobyć."
)

# domyślny model – zgodny z tym, co użyłeś wcześniej
DEFAULT_MODEL = "gpt-4o-mini"

# ile maksymalnie linii kontekstu wysyłamy do modelu
MAX_CONTEXT_LINES = 80


# ─────────────────────────────────────────────────────────────
# Pomocnicze funkcje
# ─────────────────────────────────────────────────────────────

def _get_api_key() -> Optional[str]:
    """
    Pobiera klucz z sesji Streamlit albo ze zmiennej środowiskowej.
    Umożliwia elastyczne przechowywanie klucza (lokalnie / w .env).
    """
    return st.session_state.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")


def get_client() -> Optional[OpenAI]:
    """
    Zwraca obiekt klienta OpenAI albo None jeśli nie ma klucza.
    Nie rzuca wyjątku – UI może wtedy wyświetlić komunikat.
    """
    key = _get_api_key()
    if not key:
        return None
    return OpenAI(api_key=key)


def _dict_to_context_text(context: Dict[str, Any]) -> str:
    """
    Zamienia słownik kontekstu na czytelny tekst.
    Przydaje się gdy przekazujemy prognozę, ROP, itp.
    Ograniczamy długość, żeby nie wysyłać potworów do modelu.
    """
    lines: List[str] = []
    for k, v in context.items():
        # ucinamy bardzo długie wartości
        v_str = str(v)
        if len(v_str) > 400:
            v_str = v_str[:400] + " …(ucięto)"
        lines.append(f"{k}: {v_str}")

    # ograniczamy do MAX_CONTEXT_LINES
    if len(lines) > MAX_CONTEXT_LINES:
        lines = lines[:MAX_CONTEXT_LINES]
        lines.append(f"... (ucięto do {MAX_CONTEXT_LINES} linii)")

    return "\n".join(lines)


def _build_user_message(user_msg: str, context: Dict[str, Any]) -> str:
    """
    Buduje pełny komunikat użytkownika: najpierw kontekst liczbowy,
    potem pytanie użytkownika.
    """
    ctx_txt = _dict_to_context_text(context)
    return f"Kontekst (dane z aplikacji):\n{ctx_txt}\n\nPytanie użytkownika:\n{user_msg}"


# ─────────────────────────────────────────────────────────────
# Publiczne funkcje API do użycia w UI
# ─────────────────────────────────────────────────────────────

def answer_question(
    user_msg: str,
    context: Dict[str, Any],
    model: str = DEFAULT_MODEL,
    temperature: float = 0.2,
) -> str:
    """
    Główna funkcja, której używa UI.
    user_msg – pytanie z inputa w Streamlicie
    context – słownik z danymi biznesowymi (sku, forecast_mean, reorder_point, ...)
    model – można podać inny model jeśli w przyszłości dodamy wybór w ustawieniach
    """
    client = get_client()
    if client is None:
        return "❗ Brak klucza OpenAI – przejdź do zakładki **Ustawienia** i wklej swój OPENAI_API_KEY."

    # budujemy wiadomości
    user_content = _build_user_message(user_msg, context)

    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=temperature,
        )
    except OpenAIError as e:
        # kontrolowany błąd – zwracamy do UI tak, żeby user wiedział co się stało
        return f"❗ Błąd komunikacji z OpenAI: {e}"

    # klasycznie bierzemy pierwszą odpowiedź
    return completion.choices[0].message.content


def explain_recommendation(
    sku: str,
    recommendation: Dict[str, Any],
    model: str = DEFAULT_MODEL,
) -> str:
    """
    Helper, którego możesz użyć np. w zakładce 'Rekomendacje':
    podajesz SKU + słownik z ROP, safety stock itd., a on generuje
    krótkie wyjaśnienie do pokazania menedżerowi.
    """
    client = get_client()
    if client is None:
        return "Brak klucza OpenAI – nie mogę wygenerować wyjaśnienia."

    ctx: Dict[str, Any] = {"sku": sku}
    ctx.update(recommendation)

    user_msg = (
        "Wyjaśnij, dlaczego taka rekomendacja zatowarowania została wygenerowana. "
        "Podkreśl wpływ poziomu obsługi i lead time. Dodaj krótką poradę, co zrobić jeśli firma chce niższy zapas."
    )

    user_content = _build_user_message(user_msg, ctx)

    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0.25,
        )
    except OpenAIError as e:
        return f"❗ Błąd komunikacji z OpenAI: {e}"

    return completion.choices[0].message.content


def raw_chat(user_msg: str, model: str = DEFAULT_MODEL) -> str:
    """
    Prosty tryb: użytkownik chce po prostu pogadać z modelem
    w kontekście łańcucha dostaw, bez wstrzykiwania danych z aplikacji.
    """
    client = get_client()
    if client is None:
        return "Brak klucza OpenAI – wklej go w Ustawieniach."

    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.3,
        )
    except OpenAIError as e:
        return f"❗ Błąd komunikacji z OpenAI: {e}"

    return completion.choices[0].message.content
