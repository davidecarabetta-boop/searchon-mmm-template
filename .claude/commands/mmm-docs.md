---
description: Allinea la documentazione alle ultime modifiche
---

1. Guarda cosa è cambiato con `git status` e `git diff`.
2. Per ogni modifica a codice, script, SQL, comandi, requisiti o schema del YAML, aggiorna il file di `docs/`
   che la descrive (vedi l'indice in `README.md`) e aggiungi una voce in `CHANGELOG.md` sotto "Non rilasciato".
3. Controlla che esempi e comandi citati nei documenti funzionino ancora con il codice attuale.
4. Esegui `python3 scripts/verifica_documentazione.py < /dev/null` e conferma che esce senza errori.
