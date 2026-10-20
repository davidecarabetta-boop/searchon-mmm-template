#!/usr/bin/env bash
# Prepara il computer per lanciare MMM SearchOn. Da eseguire una volta (e dopo ogni aggiornamento del template).
# Non tocca i dati dei clienti. Rieseguirlo è sicuro.
set -uo pipefail
cd "$(dirname "$0")"

ok()   { printf "  \033[32m✓\033[0m %s\n" "$1"; }
ko()   { printf "  \033[31m✗\033[0m %s\n" "$1"; ERRORI=$((ERRORI+1)); }
nota() { printf "  \033[33m!\033[0m %s\n" "$1"; }
ERRORI=0

echo "1. Sistema"
case "$(uname -s)" in
  Darwin|Linux) ok "$(uname -s) supportato" ;;
  *) ko "Sistema non supportato dalla Colab CLI: usare macOS, Linux o WSL" ;;
esac

PY=""
for c in python3.13 python3.12 python3.11 python3; do
  if command -v "$c" >/dev/null && "$c" -c 'import sys; sys.exit(sys.version_info < (3,11))'; then PY="$c"; break; fi
done
if [ -n "$PY" ]; then ok "Python: $($PY --version)"
elif command -v uv >/dev/null; then nota "Python di sistema sotto 3.11: uv scaricherà Python 3.12 per .venv"
else ko "Serve Python 3.11+ oppure uv"; fi

echo "2. Strumenti"
command -v uv >/dev/null && ok "uv installato" || ko "uv mancante: curl -LsSf https://astral.sh/uv/install.sh | sh"
command -v claude >/dev/null && ok "Claude Code installato" || nota "Claude Code non trovato: https://docs.claude.com/en/docs/claude-code"
if command -v colab >/dev/null; then
  ok "Colab CLI: $(colab version 2>/dev/null | head -1)"
elif command -v uv >/dev/null; then
  echo "     installo la Colab CLI..."
  uv tool install google-colab-cli >/dev/null 2>&1 && ok "Colab CLI installata" || ko "Installazione Colab CLI non riuscita"
else
  ko "Colab CLI mancante (serve uv)"
fi
command -v gcloud >/dev/null && ok "gcloud installato" || nota "gcloud mancante: serve solo per /mmm-check-data in locale (https://cloud.google.com/sdk/docs/install)"
git config user.email >/dev/null && ok "git user.email: $(git config user.email)" || ko "Impostare: git config --global user.email nome@searchon.it"

echo "3. Ambiente Python locale (.venv)"
if command -v uv >/dev/null; then
  # uv gestisce anche la versione di Python: funziona pure su Ubuntu 22.04 (Python 3.10)
  { [ -x .venv/bin/python ] || uv venv -q --python 3.12 .venv; } \
    && uv pip install -q --python .venv/bin/python -r requirements-local.txt -e . \
    && ok ".venv pronto (check dati e report)" || ko "Creazione .venv con uv non riuscita"
elif [ -n "$PY" ]; then
  [ -d .venv ] || "$PY" -m venv .venv
  .venv/bin/pip install -q --upgrade pip >/dev/null
  .venv/bin/pip install -q -r requirements-local.txt && .venv/bin/pip install -q -e . \
    && ok ".venv pronto (check dati e report)" || ko "Installazione dipendenze locali non riuscita"
fi

echo "4. Accessi Google"
if command -v gcloud >/dev/null; then
  if gcloud auth application-default print-access-token >/dev/null 2>&1; then
    ok "Credenziali BigQuery locali (ADC) presenti"
  else
    nota "Eseguire: gcloud auth application-default login   (serve per /mmm-check-data)"
  fi
fi
nota "La Colab CLI chiederà l'accesso Google al primo 'colab new'"

echo "5. Collaudo locale su dati sintetici"
if [ -x .venv/bin/python ]; then
  mkdir -p data/test
  .venv/bin/python tests/genera_dati_sintetici.py data/test/sintetico.csv >/dev/null \
    && .venv/bin/python -m mmm.check configs/test_sintetico.yaml --run-dir outputs/test_sintetico/setup >/dev/null \
    && ok "Check dati funzionante" || ko "Il check sui dati sintetici non funziona"
fi

echo
if [ "$ERRORI" -eq 0 ]; then
  echo "Pronto. Prova la pipeline completa su GPU (circa 5 minuti, numeri NON utilizzabili):"
  echo "  scripts/colab_run.sh configs/test_sintetico.yaml --rapido"
else
  echo "$ERRORI problemi da risolvere: vedi sopra e docs/01_setup.md"
  exit 1
fi
