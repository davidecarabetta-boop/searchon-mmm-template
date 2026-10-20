# Changelog

Ogni modifica al template va registrata qui (regola in `CLAUDE.md`). Formato: data, cosa, perché.

## Non rilasciato

_(nessuna modifica)_

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
