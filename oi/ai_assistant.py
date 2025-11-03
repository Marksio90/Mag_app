# oi/ai_assistant.py
from __future__ import annotations
from typing import Optional, Dict, Any
import os
import streamlit as st
from openai import OpenAI

SYSTEM_PROMPT = """Jesteś asystentem ds. optymalizacji zapasów. Odpowiadasz krótko, po polsku, wyjaśniasz na podstawie przekazanych danych (prognozy, ROP, safety stock). Jeśli czegoś brakuje – powiedz czego."""

def get_client() -> Optional[OpenAI]:
    key = st.session_state.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not key:
        return None
    return OpenAI(api_key=key)

def answer_question(user_msg: str, context: Dict[str, Any]) -> str:
    client = get_client()
    if client is None:
        return "Brak klucza OpenAI – wprowadź go w zakładce Ustawienia."
    # kontekst biznesowy pakujemy w system + user
    ctx_txt = ""
    for k, v in context.items():
        ctx_txt += f"{k}: {v}\n"
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Kontekst:\n{ctx_txt}\n\nPytanie: {user_msg}"},
        ],
        temperature=0.2,
    )
    return completion.choices[0].message.content
