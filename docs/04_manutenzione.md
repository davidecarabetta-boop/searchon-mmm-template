# 04 · Manutenzione del template

## Regola sulla documentazione

Ogni modifica a codice, script, SQL, comandi, requisiti o schema del YAML si fa insieme a:

1. l'aggiornamento del documento in `docs/` che la descrive;
2. una voce in `CHANGELOG.md` sotto "Non rilasciato".

In Claude Code la regola è in `CLAUDE.md` ed è verificata da un hook di fine turno (`.claude/settings.json` →
`scripts/verifica_documentazione.py`): se il codice è cambiato e i documenti no, Claude viene fermato e deve
aggiornarli. Da terminale: `python3 scripts/verifica_documentazione.py < /dev/null`. Il comando `/mmm-docs` fa
l'allineamento completo.

La documentazione dei singoli run è automatica: `RUN.md` nella cartella del run e una riga in `docs/registro_run.md`.

## Mappa del codice

| File | Ruolo |
|---|---|
| `src/mmm/config.py` | Lettura e validazione del YAML, default |
| `src/mmm/data.py` | Lettura da BigQuery (query parametrica sulle sole colonne del YAML) o da CSV |
| `src/mmm/check.py` | Controlli di qualità, solo output aggregato |
| `src/mmm/fit.py` | Costruzione input Meridian, stima, estrazione risultati in CSV/JSON |
| `src/mmm/report.py` | Grafici, `report.md`, `report.html`, `RUN.md`, registro run |
| `src/mmm/runs.py` | Cartelle dei run e registro |
| `scripts/colab_run.sh` | Orchestrazione della VM Colab: apertura, auth, install, esecuzione, download, chiusura |
| `scripts/verifica_documentazione.py` | Hook sulla documentazione |
| `.claude/commands/` | Comandi `/mmm-nuovo`, `/mmm-check-data`, `/mmm-run`, `/mmm-report`, `/mmm-docs` |
| `.claude/settings.json` | Permessi condivisi e hook |
| `tests/` | Dati sintetici e finta Colab CLI per collaudare la pipeline |

## Collaudo dopo una modifica

```bash
# pipeline completa senza Google né GPU (Colab finta, esecuzione locale su CPU)
MMM_REMOTE_ROOT=$(mktemp -d) COLAB_BIN=tests/colab_finto.sh scripts/colab_run.sh configs/test_sintetico.yaml --rapido
# poi la stessa cosa sulla GPU vera
scripts/colab_run.sh configs/test_sintetico.yaml --rapido
```

Senza Colab CLI (es. prima di configurare WSL) si può collaudare la stima su GPU dal browser con
`notebooks/test_gpu_mmm.ipynb`: aprirlo in Colab (File → Apri blocco note → GitHub), runtime T4, Esegui tutto.
Il notebook incorpora il codice di `src/` al momento della generazione: se `src/` cambia, va rigenerato.

## Aggiornare le versioni

- Meridian è fissato in `requirements-colab.txt`. Prima di cambiare versione: collaudo sintetico, voce nel CHANGELOG
  con la versione precedente e quella nuova. Meridian cambia API tra versioni minori (in 2.x usa JAX come backend
  e precisione float64).
- La Colab CLI si aggiorna con `colab update --install`; se cambia la sintassi dei comandi, aggiornare `colab_run.sh`
  e `tests/colab_finto.sh`.

## Passare a un plugin

Oggi i comandi vivono nel repository (`.claude/commands/`), quindi ogni clone li ha già. Se il team vuole aggiornarli
in un punto solo per tutti i progetti, si possono impacchettare in un plugin `searchon-mmm` accanto a
`searchon-measurement` e `searchon-framework`.

## Problemi noti

| Sintomo | Causa probabile | Soluzione |
|---|---|---|
| `colab new` fallisce o non trova la GPU | Quota o disponibilità Colab | Riprovare più tardi, o usare L4 |
| `Access Denied` su BigQuery | Ruoli mancanti | Vedi `01_setup.md`, passo 4 |
| R-hat oltre soglia | Campionamento corto o modello mal specificato | Più campioni, meno canali, prior motivate |
| MAPE di holdout alta | Cambi strutturali recenti, controlli mancanti | Rivedere controlli e periodo |
| Sessione `mmm-*` rimasta aperta | Interruzione anomala dello script | `colab sessions`, poi `colab stop -s <nome>` |
| `ATTENZIONE: nessuna GPU vista` | Runtime senza GPU o driver non caricati | Verificare `calcolo.gpu` e rilanciare |

## Dati in UE

Colab standard non permette di scegliere la regione della VM. Se un cliente lo richiede, l'alternativa è Colab
Enterprise su Google Cloud, con regione europea e progetto GCP del cliente o di SearchOn: richiede un adattamento di
`colab_run.sh`, da documentare qui quando viene fatto.
