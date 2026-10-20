# Istruzioni per Claude: progetto MMM SearchOn

Questo repository è il template standard SearchOn per i Marketing Mix Model con Google Meridian.
Chiunque nel team lo usa allo stesso modo: stessi passi, stesse librerie, stesso formato di output.

## Architettura (non cambiarla senza che l'utente lo chieda)

- **Dati**: una vista BigQuery per cliente (`mmm_input_weekly`), già aggregata per settimana. Schema in `docs/03_schema_dati.md`.
- **Configurazione**: un file `configs/<cliente>.yaml` per cliente. È l'unica cosa che si compila per un nuovo MMM.
- **Calcolo**: VM Colab con GPU tramite la Colab CLI, orchestrata da `scripts/colab_run.sh`. La stima non gira in locale.
- **Output**: `outputs/<cliente>/<run_id>/` con `report.html`, `RUN.md`, CSV aggregati e grafici.

## Il flusso, in ordine

1. `/mmm-nuovo <cliente>`: crea `configs/<cliente>.yaml` dall'esempio.
2. `/mmm-check-data configs/<cliente>.yaml`: valida la vista BigQuery. Se l'esito è KO ci si ferma.
3. `/mmm-run configs/<cliente>.yaml`: check + stima su GPU Colab, download, report.
4. `/mmm-report configs/<cliente>.yaml`: rigenera il report dell'ultimo run (senza ristimare).

## Regole sui dati

- Non leggere mai righe del dataset: niente `SELECT *` di esplorazione, niente lettura di CSV in `data/`, niente stampa di DataFrame.
  Per capire i dati usa solo l'output di `mmm.check`, che è aggregato.
- Se una vista contiene colonne con dati personali (email, ID utente, telefono…) fermati e avvisa l'utente.
- Non spostare dati del cliente fuori da BigQuery e dalla VM Colab: in locale arrivano solo risultati aggregati.

## Regole sul calcolo

- GPU di default: T4 (o L4). A100/H100 solo se il YAML ha `consenti_gpu_costose: true` **e** l'utente lo conferma in chat.
- La sessione Colab va sempre chiusa: `scripts/colab_run.sh` lo fa da sé. Se lo script si interrompe in modo anomalo,
  esegui `colab sessions` e chiudi con `colab stop -s <nome>` le sessioni `mmm-*` rimaste aperte.
- `--rapido` serve solo a collaudare la pipeline: i suoi numeri non vanno mai mostrati come risultati.
- Se la stima non converge (R-hat sopra soglia) non presentare i risultati come validi: proponi più campioni, meno canali
  o prior diverse, e chiedi all'utente come procedere.

## Documentazione: va SEMPRE tenuta aggiornata

Questa è una regola del team, non un'opzione.

- Ogni modifica a codice, script, SQL, requisiti, comandi o schema del YAML va accompagnata, nella stessa modifica, da:
  1. l'aggiornamento del file in `docs/` che descrive quella parte;
  2. una voce in `CHANGELOG.md` (sezione "Non rilasciato") con cosa è cambiato e perché.
- Ogni run documenta se stesso: `mmm.report` scrive `RUN.md` nella cartella del run e aggiunge una riga a
  `docs/registro_run.md`. Non modificare a mano le righe del registro; le note vanno nella colonna Note.
- Se in un run prendi una decisione di metodo (prior diverse, canali accorpati, settimane escluse), scrivila nella
  sezione "Decisioni" di `RUN.md` del run.
- Un controllo automatico a fine turno (`scripts/verifica_documentazione.py`) segnala modifiche al codice senza
  aggiornamento della documentazione: se scatta, aggiorna i documenti prima di chiudere.

## Comandi utili

```bash
./setup.sh                                            # verifica e prepara l'ambiente (una volta)
.venv/bin/python -m mmm.check configs/<c>.yaml        # check dati
scripts/colab_run.sh configs/<c>.yaml                 # run completo su GPU
.venv/bin/python -m mmm.report configs/<c>.yaml       # report dell'ultimo run
```

Riferimenti: `docs/01_setup.md`, `docs/02_configurazione.md`, `docs/03_schema_dati.md`, `docs/04_manutenzione.md`.
