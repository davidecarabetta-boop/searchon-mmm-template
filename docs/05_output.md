# 05 · Output di un run

Ogni run crea `outputs/<cliente>/<AAAAMMGG-HHMM>/`.

| File | Contenuto | Nel repository |
|---|---|---|
| `report.html` | Report SearchOn autonomo (grafici incorporati), da condividere | sì |
| `report.md` | Stesso report in Markdown | sì |
| `RUN.md` | Documentazione del run: autore, hardware, versioni, config usata, convergenza, decisioni | sì |
| `check.md` / `check.json` | Esito del controllo dati | sì |
| `risultati.json` | Metadati e metriche di sintesi | sì |
| `metriche_canali.csv` | Spesa, contributo, ROI, ROI marginale, CPIK per canale con intervalli al 90% | sì |
| `accuratezza.csv` | R², MAPE, wMAPE su train, holdout e totale | sì |
| `fit_settimanale.csv` | KPI osservato, atteso e baseline per settimana | sì |
| `curve_risposta.csv` | Curve di risposta per canale | sì |
| `budget_ottimizzato.csv` | Spesa attuale e ottimizzata a budget invariato | sì |
| `grafici/*.png` | Grafici del report | sì |
| `console_remota.log` | Output della VM Colab | sì |
| `modello.pkl` | Modello stimato, per analisi successive | no (pesante) |
| `sessione_colab.ipynb` | Log della sessione Colab | no |

## Come leggere il report

1. **Qualità prima dei risultati**: check dati OK, GPU presente, R-hat sotto soglia, MAPE di holdout ragionevole
   (indicativamente sotto il 15%). Se uno di questi non va, i ROI non vanno presentati al cliente.
2. **ROI con intervallo**: un intervallo che include valori sotto 1 significa che non si può escludere che il canale
   non ripaghi. Prima di spostare budget su o via da un canale incerto, proporre un lift test.
3. **Spesa vs contributo**: canali con contributo molto sopra la quota di spesa sono candidati ad aumentare, e viceversa.
4. **Curve di risposta**: il punto indica la spesa attuale; dove la curva si appiattisce, spesa aggiuntiva rende poco.
5. **Scenario di budget**: è uno scenario a budget invariato con variazioni limitate per canale, non una raccomandazione
   automatica.
