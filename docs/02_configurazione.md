# 02 · Configurazione YAML

Un file `configs/<cliente>.yaml` per cliente, creato da `configs/cliente.example.yaml` (o con `/mmm-nuovo`).
La validazione è in `src/mmm/config.py`: un YAML non valido blocca tutto prima di aprire la sessione GPU.

## Campi

| Campo | Obbligatorio | Default | Descrizione |
|---|---|---|---|
| `cliente` | sì | | Nome breve, minuscolo. Diventa la cartella `outputs/<cliente>/` |
| `valuta` | no | | Codice valuta per il report (es. `EUR`) |
| `sorgente.tipo` | sì | | `bigquery` (standard) o `csv` (solo test) |
| `sorgente.progetto` / `dataset` / `vista` | con bigquery | | Vista di input, vedi `03_schema_dati.md` |
| `sorgente.location` | no | | Es. `EU`. Deve coincidere con quella del dataset |
| `sorgente.progetto_fatturazione` | no | `progetto` | Progetto che esegue e paga le query |
| `sorgente.percorso` | con csv | | Percorso del CSV di test |
| `colonna_data` | no | `settimana` | Colonna DATE della settimana |
| `periodo.inizio` / `fine` | sì | | Intervallo incluso, formato `AAAA-MM-GG` |
| `kpi.colonna` | sì | | Colonna del KPI |
| `kpi.tipo` | no | `revenue` | `revenue` o `non_revenue` (es. lead, conversioni) |
| `kpi.revenue_per_kpi` | no | | Colonna con il valore medio per conversione, solo con `non_revenue` |
| `canali[].nome` | sì | | Nome del canale nel report |
| `canali[].spesa` | sì | | Colonna della spesa |
| `canali[].impression` | no | spesa | Colonna di esposizione. Se assente si usa la spesa |
| `controlli` | no | `[]` | Colonne non media (promo, prezzo, festività…) |
| `modello.holdout_settimane` | no | `12` | Ultime N settimane escluse dalla stima per la validazione. `0` = nessun holdout |
| `modello.max_lag_adstock` | no | `8` | Settimane massime di effetto ritardato |
| `modello.knots` | no | automatico | Nodi per la baseline temporale |
| `modello.roi_prior.media` / `sigma` | no | `0.2` / `0.9` | Prior LogNormal sul ROI (default di Meridian) |
| `modello.campionamento.*` | no | 4 catene, 1000/500/1000 | adapt / burnin / keep del campionamento MCMC |
| `modello.rhat_max` | no | `1.2` | Soglia di convergenza |
| `calcolo.gpu` | no | `T4` | `T4`, `L4`; `A100`, `H100`, `G4` solo con la voce sotto |
| `calcolo.consenti_gpu_costose` | no | `false` | Sblocca le GPU costose |
| `calcolo.timeout_minuti` | no | `180` | Tempo massimo di esecuzione sulla VM (la CLI di default si ferma dopo 30 secondi) |
| `ottimizzazione.variazione_max_pct` | no | `30` | Variazione massima per canale nello scenario a budget invariato |

## Quando cambiare i default

- **Prior ROI**: solo con un motivo esplicito (es. risultati di lift test), da scrivere nella sezione Decisioni di `RUN.md`.
- **Campionamento**: aumentarlo se l'R-hat supera la soglia; costa tempo GPU in proporzione.
- **Holdout**: ridurlo se lo storico è corto, ma mai sotto 8 settimane senza motivo.
