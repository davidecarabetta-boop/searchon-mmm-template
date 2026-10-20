#!/usr/bin/env bash
# Esegue check + stima MMM su una VM Colab con GPU e riporta i risultati in locale.
#
# Uso:   scripts/colab_run.sh configs/<cliente>.yaml [--rapido]
#
# Passi: valida il YAML -> apre la sessione GPU -> autentica GCP (BigQuery) ->
#        installa le librerie -> carica codice e config -> check + stima sulla VM ->
#        scarica i risultati in outputs/<cliente>/<run_id>/ -> salva il log della
#        sessione -> chiude SEMPRE la sessione (anche in caso di errore) -> genera il report.
set -euo pipefail

CONFIG="${1:?Uso: scripts/colab_run.sh configs/<cliente>.yaml [--rapido]}"
RAPIDO="${2:-}"
REMOTE_ROOT="${MMM_REMOTE_ROOT:-/content}"   # sovrascrivibile solo per i test della pipeline
export PATH="$HOME/.local/bin:$PATH"   # dove uv installa la Colab CLI
COLAB="${COLAB_BIN:-colab}"
command -v "$COLAB" >/dev/null || { echo "Colab CLI non trovata: lanciare ./setup.sh (o: uv tool install google-colab-cli)"; exit 1; }

cd "$(dirname "$0")/.."
PY="${PYTHON:-python3}"
[ -x .venv/bin/python ] && PY=.venv/bin/python
export PYTHONPATH=src

# 1. Validazione configurazione (fallisce qui se il YAML è sbagliato o la GPU non è consentita)
read -r CLIENTE GPU SORGENTE TIMEOUT_MIN < <("$PY" -c "
from mmm.config import load_config; c = load_config('$CONFIG')
print(c['cliente'], c['calcolo']['gpu'], c['sorgente']['tipo'], c['calcolo']['timeout_minuti'])")

RUN_ID="$(date +%Y%m%d-%H%M)"
RUN_DIR="outputs/${CLIENTE}/${RUN_ID}"
SESSIONE="mmm-$(echo "$CLIENTE" | tr -c 'a-zA-Z0-9-\n' '-')-${RUN_ID}"
AUTORE="$(git config user.email 2>/dev/null || echo "${USER:-sconosciuto}")"
TMP="$(mktemp -d)"
mkdir -p "$RUN_DIR"
echo "Run ${RUN_ID} | cliente ${CLIENTE} | GPU ${GPU} | timeout ${TIMEOUT_MIN} min | autore ${AUTORE}"

chiudi() {
  echo "Chiusura sessione ${SESSIONE}..."
  "$COLAB" stop -s "$SESSIONE" >/dev/null 2>&1 || echo "ATTENZIONE: chiudere a mano con: colab stop -s ${SESSIONE}"
  rm -rf "$TMP"
}

# 2. Sessione GPU
"$COLAB" new -s "$SESSIONE" --gpu "$GPU"
trap chiudi EXIT

# 3. Credenziali GCP sulla VM (con l'account Google di chi lancia)
if [ "$SORGENTE" = "bigquery" ]; then
  "$COLAB" auth -s "$SESSIONE"
fi

# 4. Librerie a versione fissa
# shellcheck disable=SC2046
"$COLAB" install -s "$SESSIONE" $(grep -vE '^\s*(#|$)' requirements-colab.txt)

# 5. Pacchetto del job: codice + config (+ dati CSV solo per i test)
mkdir -p "$TMP/job/configs"
cp -R src "$TMP/job/"
cp "$CONFIG" "$TMP/job/configs/run.yaml"
if [ "$SORGENTE" = "csv" ]; then
  CSV="$("$PY" -c "from mmm.config import load_config; print(load_config('$CONFIG')['sorgente']['percorso'])")"
  mkdir -p "$TMP/job/$(dirname "$CSV")"
  cp "$CSV" "$TMP/job/$CSV"
fi
tar -czf "$TMP/job.tgz" -C "$TMP/job" .
"$COLAB" upload -s "$SESSIONE" "$TMP/job.tgz" "${REMOTE_ROOT}/mmm_job.tgz"

# 6. Check + stima sulla VM. Il codice remoto stampa solo diagnostiche aggregate.
FIT_FLAGS=""
[ "$RAPIDO" = "--rapido" ] && FIT_FLAGS="--rapido"
cat > "$TMP/remoto.py" <<PYEOF
import os, subprocess, sys, tarfile, shutil
root = "${REMOTE_ROOT}"
job = os.path.join(root, "mmm_job")
shutil.rmtree(job, ignore_errors=True); os.makedirs(job)
with tarfile.open(os.path.join(root, "mmm_job.tgz")) as t:
    t.extractall(job, filter="data")
env = dict(os.environ, PYTHONPATH="src", MMM_AUTORE="${AUTORE}")
run_dir = "${RUN_DIR}"
def esegui(args):
    print("$", " ".join(args), flush=True)
    return subprocess.run([sys.executable, "-m", *args], cwd=job, env=env).returncode
rc_check = esegui(["mmm.check", "configs/run.yaml", "--run-dir", run_dir])
rc_fit = None
if rc_check == 0:
    rc_fit = esegui(["mmm.fit", "configs/run.yaml", "--run-dir", run_dir] + "${FIT_FLAGS}".split())
else:
    print("Check dati KO: stima non eseguita", flush=True)
with open(os.path.join(job, run_dir, "stato_remoto.txt"), "w") as f:
    f.write(f"check={rc_check}\nfit={rc_fit}\n")
with tarfile.open(os.path.join(root, "mmm_out.tgz"), "w:gz") as t:
    t.add(os.path.join(job, run_dir), arcname=run_dir)
print("PACCHETTO_RISULTATI_PRONTO", flush=True)
PYEOF
# La CLI ha un timeout di default di 30 secondi per exec: va alzato per la stima
"$COLAB" exec -s "$SESSIONE" --timeout "$((TIMEOUT_MIN * 60))" -f "$TMP/remoto.py" | tee "$RUN_DIR/console_remota.log"

# 7. Risultati in locale + log della sessione
"$COLAB" download -s "$SESSIONE" "${REMOTE_ROOT}/mmm_out.tgz" "$TMP/mmm_out.tgz"
tar -xzf "$TMP/mmm_out.tgz" -C .
"$COLAB" log -s "$SESSIONE" -o "$RUN_DIR/sessione_colab.ipynb" || true

STATO="$(cat "$RUN_DIR/stato_remoto.txt" 2>/dev/null || echo 'check=? fit=?')"
echo "Stato remoto: $(echo "$STATO" | tr '\n' ' ')"

# 8. Report + documentazione del run (in locale, senza GPU)
if [ -f "$RUN_DIR/risultati.json" ]; then
  "$PY" -m mmm.report "$CONFIG" --run-dir "$RUN_DIR"
else
  echo "Nessun risultato di stima: vedi $RUN_DIR/check.md e $RUN_DIR/console_remota.log"
  exit 1
fi
