# Progetto BlackSwan Quants – Take-home (pairs trading)

## Contesto
- Take-home di selezione per BlackSwan Quants: 12 ore in un solo giorno. Il compito è volutamente più grande del tempo disponibile.
- Criteri di valutazione, in ordine di peso:
  1. onestà della validazione (il criterio principale);
  2. solidità del ragionamento a ogni passo;
  3. qualità della presentazione (un grafico chiaro batte un muro di numeri);
  4. profitto, che conta per ultimo.
- Cerca un segnale reale con il massimo impegno. Un risultato negativo è accettabile SOLO dopo tentativi seri e documentati, e solo se accompagnato da una diagnosi del perché il segnale fallisce (deriva del β, perdita di stazionarietà, periodi specifici). "Non funziona" senza prove e senza diagnosi non è accettabile.
- Sono alle prime armi. Spiegami le scelte in modo semplice, senza semplificare la matematica.
- Ambiente: Windows, VS Code, Python 3.12 con uv.
- Coppia scelta: INTC/AMD (A = INTC, B = AMD). Regressione: PriceA = α + β·PriceB. La scelta è fissata e non va invertita.
- Split in-sample / out-of-sample: regola 70/30 sulla storia comune, arrotondata al 1° gennaio più vicino. Data: 2013-01-01 (IS = date < 2013-01-01, OOS = date ≥ 2013-01-01; vedi EXPERIMENTS.md). Fissata prima di guardare qualsiasi prezzo o risultato.
- Traccia completa e linee guida di programmazione: vedi i PDF in docs/.

## Fasi (per ogni fase scegliere UN solo metodo e farlo bene)
1. **Dati**: download da Yahoo Finance; grafico dei due prezzi, del rapporto o della differenza nel tempo; correlazione dei rendimenti giornalieri.
2. **Spread e segnale** (la fase che pesa di più): OLS PriceA = α + β·PriceB, Spread = PriceA − β·PriceB, z-score rolling, long/short/uscita, validazione IS/OOS.
3. **Stabilità della relazione**: correlazione rolling (metodo semplice) oppure β rolling + ADF rolling (metodo medio). Verificare se il segnale della fase 2 rende peggio nei periodi "deboli".
4. **Short interest**: api.nasdaq.com/api/quote/<TICKER>/short-interest (circa 12 mesi, dati bimensili). Potrebbe servire un header User-Agent da browser.
5. **Simulazione**: block bootstrap congiunto (gli stessi blocchi di giorni per entrambi i titoli) oppure processo OU sullo spread. Rieseguire il segnale sui percorsi simulati.
6. **Estensioni**: solo se le fasi 1–5 sono solide.

## Regole di validazione (non negoziabili)
- Tutto ciò che viene stimato (α, β, scelta dei parametri) si stima SOLO sull'in-sample.
- Lo z-score usa solo dati passati.
- Il segnale calcolato alla chiusura del giorno t viene eseguito al giorno t+1 (shift(1)).
- La griglia dei parametri si dichiara PRIMA di eseguirla e va scritta in EXPERIMENTS.md. Si mostra sempre la griglia intera (ad esempio una heatmap dello Sharpe per soglia × lookback), mai solo la configurazione migliore.
- Registro degli esperimenti: ogni configurazione provata, anche quelle fallite, va in EXPERIMENTS.md con data e ora, parametri, periodo (IS o OOS) e risultato principale. Il numero totale di tentativi va riportato nel writeup.
- L'out-of-sample si esegue UNA sola volta, alla fine, con i parametri congelati. Ogni accesso all'OOS va registrato. Non tornare indietro a modificare i parametri dopo averlo visto.
- Sensibilità: se piccole variazioni dei parametri fanno crollare il risultato, va detto esplicitamente.
- Metriche da riportare: rendimento annualizzato, volatilità, Sharpe, max drawdown, numero di trade, win rate, durata media delle posizioni.
- Non inventare risultati: ogni numero nel writeup deve uscire da codice eseguito.

## Linee guida di codice (dal documento BSQ, versione adatta a un giorno di lavoro)
Da applicare:
- Docstring in stile NumPy (Parameters, Returns, Raises, Notes) sulle funzioni pubbliche.
- PEP 8, type hints precisi, `from __future__ import annotations`. Lint e formattazione con ruff, controllo dei tipi con mypy.
- Eccezioni custom per gli errori attesi (ad esempio DataFetchError) invece di Exception generiche.
- `assert` per gli invarianti: nessun NaN nei segnali, posizioni in {-1, 0, 1}, date IS < date OOS, eccetera.
- Cutoff temporale esplicito (parametro `as_of` o `end`) in ogni funzione che stima qualcosa.
- Checkpoint dei dati in data/ (parquet o pickle), così non si riscarica ogni volta. I dati sono piccoli e vanno committati nel repository per la riproducibilità.
- `logging.getLogger(__name__)` nei moduli, niente print (consentiti solo nei notebook).
- Grafici con Plotly, salvati anche in reports/figures/.
- pytest per le funzioni chiave: OLS, z-score, backtest, metriche.
- uv.lock nel repository; commit in stile conventional (feat:, fix:, docs:, test:, chore:).

Da NON fare (fuori scala per un giorno): PySide6, SQLite, pydantic-settings, CI.

## Struttura del progetto
- src/pairs/: data.py, spread.py, signal.py, backtest.py, metrics.py, stability.py, short_interest.py, simulation.py
- notebooks/: 01_data, 02_signal, 03_stability, 04_short_interest, 05_simulation (un notebook per fase, che importa da src/)
- tests/, data/raw/, data/processed/, reports/figures/
- EXPERIMENTS.md (registro dei tentativi), WRITEUP.md (mezza pagina finale)

## Come lavorare
- Prima di un task grande, proponi un piano breve e aspetta la mia conferma.
- Procedi per piccoli passi verificabili; dopo ogni passo dimmi come controllare che funzioni.
- Ordine: prima una pipeline minima completa per le fasi 1–2, poi le fasi 3–5.
- Se la traccia è ambigua, chiedimi invece di supporre.
- Non cancellare i file che hai prodotto, perché servono per la disclosure sull'uso dell'AI. Se un file è superato, spostalo in archive/.
- Dopo ogni passo funzionante suggerisci un commit. Non fare push senza chiedermelo.