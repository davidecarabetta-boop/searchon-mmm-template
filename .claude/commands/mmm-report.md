---
description: Rigenera report e documentazione dell'ultimo run (senza ristimare)
argument-hint: configs/<cliente>.yaml [--run-dir outputs/<cliente>/<run_id>]
---

```bash
.venv/bin/python -m mmm.report $ARGUMENTS
```

Poi riassumi all'utente i punti chiave del `report.md` generato: qualità del modello, ROI per canale con intervalli,
scenario di budget e limiti. Non aggiungere numeri che non sono nel report.
