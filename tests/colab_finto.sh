#!/usr/bin/env bash
# Finta Colab CLI per collaudare scripts/colab_run.sh senza account Google né GPU.
# Esegue tutto in locale dentro $MMM_REMOTE_ROOT. Uso:
#   MMM_REMOTE_ROOT=/tmp/vm COLAB_BIN=tests/colab_finto.sh scripts/colab_run.sh configs/test_sintetico.yaml --rapido
set -euo pipefail
cmd="$1"; shift
args=()
while [ $# -gt 0 ]; do
  case "$1" in
    -s|--gpu|-o|--timeout|--env) [ "$1" = "-o" ] && out="$2"; shift 2 ;;
    -f) file="$2"; shift 2 ;;
    *) args+=("$1"); shift ;;
  esac
done
case "$cmd" in
  new) mkdir -p "$MMM_REMOTE_ROOT"; echo "[finto] sessione creata" ;;
  auth|install|stop) echo "[finto] $cmd" ;;
  upload) cp "${args[0]}" "${args[1]}" ;;
  download) cp "${args[0]}" "${args[1]}" ;;
  exec) python3 "$file" ;;
  log) echo '{"cells": [], "metadata": {}, "nbformat": 4, "nbformat_minor": 5}' > "$out" ;;
  *) echo "[finto] comando non gestito: $cmd" >&2; exit 1 ;;
esac
