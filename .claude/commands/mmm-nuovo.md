---
description: Prepara la configurazione di un nuovo MMM cliente
argument-hint: <nome_cliente>
---

Prepara un nuovo MMM per il cliente `$ARGUMENTS`.

1. Se `configs/$ARGUMENTS.yaml` esiste già, fermati e chiedi se va modificato quello esistente.
2. Copia `configs/cliente.example.yaml` in `configs/$ARGUMENTS.yaml` e imposta `cliente: $ARGUMENTS`.
3. Chiedi all'utente, in un'unica domanda, i dati che mancano: progetto/dataset/vista BigQuery, periodo, KPI e tipo,
   canali (nome, colonna spesa, colonna impression), controlli. Non inventare nomi di colonna.
4. Se la vista non esiste ancora, proponi di partire da `sql/mmm_input_weekly.sql` e ricorda lo schema in
   `docs/03_schema_dati.md`. Non eseguire `bq query` senza conferma.
5. Compila il YAML, verificalo con
   `.venv/bin/python -c "from mmm.config import load_config; load_config('configs/$ARGUMENTS.yaml'); print('YAML valido')"`
6. Chiudi indicando il passo successivo: `/mmm-check-data configs/$ARGUMENTS.yaml`.
