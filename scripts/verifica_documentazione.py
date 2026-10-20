#!/usr/bin/env python3
"""Hook di fine turno per Claude Code: blocca la chiusura se il codice è cambiato
ma la documentazione no.

Regola: se cambiano file in src/, scripts/, sql/, .claude/, requirements*.txt,
setup.sh o configs/cliente.example.yaml, devono cambiare anche CHANGELOG.md e
almeno un file in docs/ (escluso il registro run, che è automatico).

Exit 0 = ok. Exit 2 = Claude riceve il messaggio e aggiorna i documenti.
Si può usare anche da terminale: python3 scripts/verifica_documentazione.py
"""

import json
import os
import subprocess
import sys

CODICE = ("src/", "scripts/", "sql/", ".claude/", "requirements", "setup.sh", "configs/cliente.example.yaml")
ESCLUSI_DOCS = ("docs/registro_run.md",)


def file_modificati(root: str) -> set[str]:
    def git(*args):
        r = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(r.stderr)
        return {l.strip() for l in r.stdout.splitlines() if l.strip()}

    cambiati = git("diff", "--name-only", "HEAD") | git("ls-files", "--others", "--exclude-standard")
    return cambiati


def main() -> int:
    try:
        evento = json.load(sys.stdin) if not sys.stdin.isatty() else {}
    except json.JSONDecodeError:
        evento = {}
    if evento.get("stop_hook_active"):
        return 0  # evita cicli: il secondo tentativo di chiusura passa sempre

    root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    try:
        cambiati = file_modificati(root)
    except Exception:  # noqa: BLE001 - fuori da un repo git o senza commit: non bloccare
        return 0

    codice = sorted(f for f in cambiati if f.startswith(CODICE))
    if not codice:
        return 0
    changelog = "CHANGELOG.md" in cambiati
    docs = any(f.startswith("docs/") and f not in ESCLUSI_DOCS for f in cambiati)
    if changelog and docs:
        return 0

    mancanti = [m for m, ok in (("CHANGELOG.md", changelog), ("un file in docs/", docs)) if not ok]
    print(
        "Documentazione non aggiornata. Sono cambiati: " + ", ".join(codice[:10])
        + f". Aggiorna {' e '.join(mancanti)} descrivendo cosa è cambiato e perché, "
        "come richiesto da CLAUDE.md, poi chiudi il turno.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
