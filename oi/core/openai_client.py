
from __future__ import annotations
from tenacity import retry, stop_after_attempt, wait_exponential
from .utils import get_secret
try:
    from openai import OpenAI
    _HAS_OPENAI = True
except Exception:
    _HAS_OPENAI = False

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=4))
def chat(prompt: str) -> str:
    key = get_secret("OPENAI_API_KEY")
    if not key or not _HAS_OPENAI:
        return "⚠️ Brak klucza OPENAI_API_KEY — dodaj w .env lub st.secrets, aby generować rekomendacje."
    client = OpenAI(api_key=key)
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"system","content":"Jesteś ekspertem ds. prognoz i zapasów."},
                  {"role":"user","content":prompt}],
        temperature=0.2, max_tokens=700
    )
    return resp.choices[0].message.content or ""
