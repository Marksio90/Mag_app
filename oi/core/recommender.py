
from __future__ import annotations
from typing import Dict, Any, List
from .openai_client import chat

def business_reco(context: Dict[str, Any]) -> str:
    prompt = f"""
Jesteś seniorem ds. łańcucha dostaw. Na podstawie kontekstu podaj do 10 konkretnych rekomendacji z liczbami.
Kontekst JSON:
{context}
"""
    return chat(prompt)

def supplier_reco(rows: List[Dict[str, Any]]) -> str:
    prompt = f"""
Jesteś audytorem dostawców. Oceń dostawców (mocne/słabe strony, ryzyka) i zaproponuj działania.
Tabela JSON:
{rows}
"""
    return chat(prompt)
