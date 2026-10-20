# 01 · Setup

Da fare una volta per computer. Vale per chiunque nel team (es. Davide e Francesco), ciascuno con i propri account.

## Requisiti

| Cosa | Perché | Note |
|---|---|---|
| macOS o Linux | La Colab CLI non supporta Windows | Su Windows: clonare e lavorare dentro WSL (Ubuntu), non da PowerShell |
| Python 3.11+ | Check dati e report in locale | |
| [uv](https://docs.astral.sh/uv/) | Installa la Colab CLI | |
| Claude Code | Regia del flusso | Login con l'account Claude aziendale |
| gcloud | Lettura BigQuery dal computer (solo check) | |
| Account Google | Colab (GPU) e BigQuery | Lo stesso account per entrambi |

## Windows

I PC SearchOn sono Windows: la pipeline va usata dentro WSL (Ubuntu). Da un terminale Ubuntu:

```bash
sudo apt update && sudo apt install -y git curl
curl -LsSf https://astral.sh/uv/install.sh | sh            # uv: gestisce anche Python
curl -fsSL https://claude.ai/install.sh | bash              # Claude Code (versione Linux)
source ~/.bashrc
mkdir -p ~/progetti && cd ~/progetti
cp -r /mnt/c/Users/<utente>/Documents/GitHub/searchon-mmm-template .   # oppure git clone del repository
cd searchon-mmm-template && ./setup.sh
```

- Lavorare nel filesystem di WSL (`~/progetti/`), non in `/mnt/c/`: è più veloce e non rompe i permessi degli script.
  Il file `.gitattributes` forza i fine riga Unix sugli script.
- Non serve il Python di sistema: se è sotto 3.11 (es. Ubuntu 22.04), `setup.sh` fa scaricare a uv Python 3.12.
- gcloud serve solo per `/mmm-check-data` in locale; il run completo su Colab non lo richiede.
- Login: al primo `colab new` la CLI stampa un link; aprirlo nel browser di Windows e incollare il codice nel terminale.

## Passi

1. Clonare il repository e lanciare `./setup.sh`. Lo script controlla gli strumenti, installa la Colab CLI se manca,
   crea `.venv` e fa un collaudo del check su dati sintetici. Rieseguirlo è sicuro.
2. Credenziali BigQuery locali, per il check dati:
   `gcloud auth application-default login`
3. Accesso a Colab: al primo `colab new` la CLI apre il login Google. Usare lo stesso account che ha accesso a BigQuery.
4. Permessi sul progetto BigQuery del cliente (li assegna chi amministra il progetto):
   - `roles/bigquery.dataViewer` sul dataset della vista
   - `roles/bigquery.jobUser` sul progetto che esegue le query
5. Collaudo completo su GPU, con dati sintetici (circa 5 minuti, numeri non utilizzabili):
   `scripts/colab_run.sh configs/test_sintetico.yaml --rapido`

## GPU e piani Colab

- Default: T4. È disponibile anche sul piano gratuito, ma con limiti di tempo e disponibilità.
- L4 è consentita senza conferme. A100 e H100 richiedono `calcolo.consenti_gpu_costose: true` nel YAML e
  conferma in chat; di norma servono un piano a pagamento o unità di calcolo.
- Ogni persona consuma la quota Colab del proprio account.

## Dove passano i dati

- BigQuery → VM Colab (regione non selezionabile con Colab standard) per la stima.
- BigQuery → computer di chi lancia, solo per il check dati, che stampa diagnostiche aggregate.
- Verso Anthropic (Claude) passano codice, diagnostiche e risultati aggregati, non le righe del dataset.
- Se il cliente richiede che i dati restino in UE, valutare Colab Enterprise su Google Cloud: vedi `04_manutenzione.md`.
