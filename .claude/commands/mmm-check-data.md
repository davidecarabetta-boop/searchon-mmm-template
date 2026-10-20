---
description: Controlla la qualità della vista BigQuery prima della stima
argument-hint: configs/<cliente>.yaml
---

Esegui il check dati per `$ARGUMENTS`:

```bash
.venv/bin/python -m mmm.check $ARGUMENTS
```

- Il check legge la vista BigQuery con le credenziali Google di chi lancia (`gcloud auth application-default login`).
  Se fallisce per autenticazione o permessi, spiega quale ruolo manca (BigQuery Data Viewer e Job User sul progetto).
- Riporta all'utente esito, errori bloccanti e avvisi, con una frase su cosa fare per ciascuno.
  Per i dettagli leggi solo il `check.md` prodotto: non interrogare i dati in altro modo.
- Esito KO: non proporre la stima finché gli errori non sono risolti (di solito vanno corretti nella vista BigQuery).
- Esito OK o OK con avvisi: proponi `/mmm-run $ARGUMENTS`.
