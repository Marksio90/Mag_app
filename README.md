
# Optimal Inventory Planner — v2

Refactor: uruchamianie przez **`streamlit run app.py`** (pliki w głównym folderze).  
Dodano: **backtesty (MAPE/RMSE/RMSSE), selekcja modelu per SKU, optymalizacja polityki (service level / EOQ / koszt całkowity)**,
oraz **eksport raportów do PDF i PPTX** (z wykresami).

## Start
```bash
pip install -r requirements.txt
copy .env.example .env   # lub cp .env.example .env
# uzupełnij OPENAI_API_KEY w .env (opcjonalnie)
streamlit run app.py
```

## Struktura
```
app.py                 # główny launcher Streamlit
pages/
  01_Load_Data.py
  02_Demand_Forecast.py
  03_Inventory_Optimization.py
  04_Supplier_Scoring.py
  05_Reports_Export.py
  06_Settings.py
oi/                    # pakiet z logiką
  __init__.py
  assets/theme.css
  data/sample_*.csv
  core/{utils,data_io,classification,forecasting,inventory,recommender,openai_client,backtest,exporting,optimizer}.py
configs/config.yaml
```

## Wymagania do eksportu
- **PNG wykresów**: wymagany pakiet `kaleido` (jest w requirements).
- **PDF**: `reportlab`
- **PPTX**: `python-pptx`
```bash
pip install -r requirements.txt
```
