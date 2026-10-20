# 03 · Schema dati: la vista BigQuery

Ogni cliente ha una vista `mmm_input_weekly` costruita a partire da `sql/mmm_input_weekly.sql`.
La vista è il contratto tra i dati del cliente e la pipeline: se rispetta lo schema, il resto è standard.

## Regole

| Regola | Dettaglio |
|---|---|
| Granularità | Una riga per settimana, nessun buco, nessun duplicato |
| Settimana | Colonna DATE, lunedì della settimana ISO (`DATE_TRUNC(data, ISOWEEK)`) |
| Storico | Minimo 52 settimane, consigliate 104 o più |
| KPI | Una colonna numerica ≥ 0 (es. `revenue`, `conversioni`) |
| Spesa | `spend_<canale>`, numerica ≥ 0, valuta del cliente; 0 se il canale è spento |
| Esposizione | `impr_<canale>` consigliata, ≥ 0 |
| Controlli | Numerici: flag promo (0/1), prezzo medio, festività, ecc. |
| Valori nulli | Non ammessi: usare `COALESCE(..., 0)` per spese e impression |
| Dati personali | Vietati: nessun ID utente, email, telefono, click ID |

I nomi `spend_<canale>` e `impr_<canale>` usano gli stessi nomi canale delle naming convention SearchOn di misurazione.

## Cosa controlla `mmm.check`

Errori bloccanti (la stima non parte):

- settimane duplicate, buchi o passo diverso da 7 giorni, settimane che iniziano in giorni diversi;
- meno di 52 settimane, o meno di 52 dopo aver tolto l'holdout;
- colonne con nome da dato personale;
- valori nulli, colonne non numeriche, valori negativi in KPI, spese o impression;
- KPI costante, canale con spesa totale zero, controllo costante.

Avvisi (la stima parte, ma il report va letto con cautela):

- tra 52 e 104 settimane;
- canale spento per più di metà delle settimane, o sotto il 2% della spesa totale;
- settimane con spesa ma senza impression;
- spese di canali diversi correlate oltre 0,9;
- poche settimane rispetto al numero di canali e controlli.

Il check stampa e salva solo valori aggregati (`check.md`, `check.json`): nessuna riga del dataset.
