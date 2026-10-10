# Registro degli esperimenti

Ogni configurazione provata (anche fallita) va qui: data e ora, parametri, periodo (IS/OOS), risultato principale.
Ogni accesso all'out-of-sample va registrato esplicitamente.

Contatori
- Configurazioni di backtest provate su IS: 0
- Accessi all'OOS: 0

---

## 2026-10-10 10:19 CEST — Download dati e data di split IS/OOS (prima di guardare i prezzi)

**Tipo:** setup, nessun backtest, nessun prezzo ispezionato.

**Dati:** Yahoo Finance via yfinance 1.7.0, `period="max"`, `interval="1d"`, `auto_adjust=True`.
File grezzi: `data/raw/INTC_daily_yahoo.pkl`, `data/raw/AMD_daily_yahoo.pkl`, metadati in `data/raw/prices_metadata.json`.
Script: `scripts/fetch_prices.py`, `scripts/compute_split_date.py`.

**Regola (fissata prima di guardare qualsiasi prezzo o risultato):**
storia comune = date in cui sia INTC sia AMD hanno un Close non mancante.
Il punto al 70% della storia comune viene arrotondato al 1° gennaio più vicino.
In-sample = date < split, out-of-sample = date ≥ split.
Il 70% è stato calcolato in due modi, solo per verificare che l'arrotondamento renda la scelta univoca:
(a) 70% dei giorni di borsa comuni; (b) 70% del tempo di calendario.

**Risultato:**

| Voce | Valore |
|---|---|
| Prima data comune | 1980-03-17 |
| Ultima data comune | 2026-10-09 |
| Giorni di borsa comuni | 11737 |
| Punto 70% (giorni di borsa) | 2012-10-05 → 2013-01-01 |
| Punto 70% (calendario) | 2012-10-19 → 2013-01-01 |
| **Data di split** | **2013-01-01** |
| IS (1980-03-17 … 2012-12-31) | 8273 giorni (70.5%) |
| OOS (2013-01-01 … 2026-10-09) | 3464 giorni (29.5%) |

I due metodi concordano, quindi la data è univoca: **split = 2013-01-01**.

---

## 2026-10-10 10:20 CEST — Download short interest Nasdaq (fase 4, solo dati grezzi)

**Tipo:** setup, nessuna analisi.
Endpoint `api.nasdaq.com/api/quote/<TICKER>/short-interest?assetClass=stocks` con User-Agent da browser: HTTP 200 per INTC e AMD.
File: `data/raw/{INTC,AMD}_short_interest_nasdaq_20261010T082049Z.json`. Script: `scripts/fetch_short_interest.py`.
Copertura: 24 date di settlement bimensili per ciascun titolo, dal 2025-10-15 al 2026-09-30.
**Nota di validazione:** l'intera finestra cade nell'OOS (≥ 2013-01-01). L'analisi della fase 4 usa quindi prezzi OOS
e va fatta solo dopo l'unico run OOS a parametri congelati, senza retroazione sui parametri.
