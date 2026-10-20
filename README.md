# searchon-mmm-template

Template standard SearchOn per i Marketing Mix Model. Ogni persona del team lavora con il proprio account Claude
e il proprio account Google, ma con gli stessi passi, le stesse librerie e lo stesso formato di output.

| Pezzo | Dove | Ruolo |
|---|---|---|
| Dati | Vista BigQuery `mmm_input_weekly` del cliente | Unica fonte, già aggregata per settimana |
| Configurazione | `configs/<cliente>.yaml` | L'unica cosa da compilare per un nuovo MMM |
| Modello | Google Meridian 2.1 (bayesiano) | Adstock, saturazione, ROI, ottimizzazione budget |
| Calcolo | VM Colab con GPU, via Colab CLI | La stima non gira sul portatile |
| Regia | Claude Code + comandi `/mmm-*` | Esegue i passi e tiene aggiornata la documentazione |
| Output | `outputs/<cliente>/<run_id>/` | Report, documentazione del run, CSV aggregati |

## Come si lancia un MMM

```bash
git clone <questo repository> mmm-<cliente> && cd mmm-<cliente>
./setup.sh                      # una volta per computer
claude                          # apre Claude Code nella cartella
```

Poi, dentro Claude Code:

```
/mmm-nuovo cliente_a                        # crea e compila configs/cliente_a.yaml
/mmm-check-data configs/cliente_a.yaml      # valida la vista BigQuery
/mmm-run configs/cliente_a.yaml             # stima su GPU Colab + report
```

Il percorso dei dati è BigQuery → VM Colab → risultati aggregati. Claude vede codice, diagnostiche e risultati,
non le righe del dataset.

## Documentazione

| Documento | Contenuto |
|---|---|
| [docs/01_setup.md](docs/01_setup.md) | Installazione, accessi Google, collaudo |
| [docs/02_configurazione.md](docs/02_configurazione.md) | Tutti i campi del YAML |
| [docs/03_schema_dati.md](docs/03_schema_dati.md) | Contratto della vista BigQuery e controlli del check |
| [docs/04_manutenzione.md](docs/04_manutenzione.md) | Come cambiare il template, regole sulla documentazione, problemi noti |
| [docs/05_output.md](docs/05_output.md) | Cosa contiene una cartella di run e come leggere il report |
| [docs/registro_run.md](docs/registro_run.md) | Elenco di tutti i run, aggiornato in automatico |
| [CHANGELOG.md](CHANGELOG.md) | Storico delle modifiche al template |
| [CLAUDE.md](CLAUDE.md) | Regole che Claude Code segue in questo repository |

La documentazione si aggiorna sempre insieme al codice: è una regola di `CLAUDE.md`, verificata a fine turno da
`scripts/verifica_documentazione.py`.
