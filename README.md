# Zaawansowana aplikacja do prognozowania i optymalizacji zatowarowania

Lokalna aplikacja Streamlit łącząca:
- prognozowanie popytu (ML / TS),
- optymalizację zapasu (ROP, safety stock, EOQ),
- symulacje Monte Carlo,
- AI Copilota (OpenAI) wyjaśniającego decyzje.

## Uruchomienie

```bash
pip install -r requirements.txt
# (opcjonalnie) skopiuj .env.example -> .env i wpisz OPENAI_API_KEY
streamlit run app.py
W aplikacji przejdź do Ustawienia i wklej klucz OpenAI jeśli chcesz mieć asystenta.

Struktura
app.py – punkt wejścia

oi/ – logika domenowa (ingestia, forecasting, optymalizacja, AI)

pages/ – moduły UI