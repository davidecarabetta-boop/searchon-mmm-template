# Changelog

Ogni modifica al template va registrata qui (regola in `CLAUDE.md`). Formato: data, cosa, perché.

## Non rilasciato

- `notebooks/test_gpu_mmm.ipynb`: notebook autonomo per collaudare Meridian su GPU Colab dal browser
  (codice del template incorporato, dati sintetici), utile finché la Colab CLI non è configurata in WSL.
- Collaudo su GPU reale (2026-10-20, Colab T4): Meridian 2.1.0 usa la GPU tramite JAX, stima completa
  (4 catene × 1000 campioni, 156 settimane, 3 canali) in 174 s di campionamento, R-hat max 1,005, report corretto.
  Gli avvisi `PJRT_Api already exists` su Colab sono innocui. Resta da collaudare l'orchestrazione con la Colab CLI.
- Notebook di test: output non bufferizzato durante la stima e filtro degli avvisi PJRT.
- `setup.sh`: crea `.venv` con uv e Python 3.12 quando il Python di sistema è vecchio (Ubuntu 22.04 in WSL);
  gcloud diventa facoltativo (serve solo al check locale). `docs/01_setup.md`: comandi completi per WSL.

## 0.1.0 · 2026-10-20

Prima versione del template.

- Architettura: vista BigQuery per cliente + YAML + stima Meridian 2.1.0 su VM Colab con GPU tramite Colab CLI
  (google-colab-cli 0.7.x), orchestrata da Claude Code.
- `mmm.check`: controlli di qualità con output solo aggregato.
- `mmm.fit`: stima con holdout temporale, prior ROI configurabile, metriche per canale, accuratezza, curve di
  risposta, ottimizzazione a budget invariato.
- `mmm.report`: report HTML/Markdown, `RUN.md` per run, registro run automatico.
- `scripts/colab_run.sh`: ciclo completo della sessione Colab con chiusura garantita.
- Comandi Claude Code `/mmm-nuovo`, `/mmm-check-data`, `/mmm-run`, `/mmm-report`, `/mmm-docs`.
- Hook di fine turno che impone l'aggiornamento della documentazione.
- Supporto Windows tramite WSL (`docs/01_setup.md`) e `.gitattributes` con fine riga Unix.
- Collaudo: dati sintetici e finta Colab CLI (`tests/`). Pipeline completa verificata in locale su CPU;
  la parte Colab reale va verificata al primo run su GPU.
