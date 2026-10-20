---
description: Stima l'MMM su GPU Colab e produce il report
argument-hint: configs/<cliente>.yaml [--rapido]
---

Lancia il run completo per `$ARGUMENTS`.

1. Leggi il YAML e riepiloga in due righe: cliente, periodo, canali, GPU. Se la GPU è A100/H100, chiedi conferma
   esplicita prima di proseguire.
2. Verifica che non ci siano sessioni `mmm-*` rimaste aperte con `colab sessions`.
3. Esegui in background (la stima può durare decine di minuti):

   ```bash
   scripts/colab_run.sh $ARGUMENTS
   ```

4. Al termine leggi `RUN.md` e `report.md` nella cartella del run indicata dallo script e riporta:
   convergenza (R-hat), accuratezza sull'holdout, ROI per canale con intervalli, scenario di budget.
   Se il run non converge o la MAPE di holdout supera il 15%, dillo per primo e proponi come procedere.
5. Se durante il run hai preso decisioni di metodo, scrivile nella sezione "Decisioni" di `RUN.md`.
6. Ricorda all'utente di fare commit della cartella del run e di `docs/registro_run.md`.

Se lo script si interrompe, controlla `colab sessions` e chiudi le sessioni `mmm-*` aperte con `colab stop -s <nome>`.
