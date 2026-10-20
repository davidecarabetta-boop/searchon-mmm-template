"""Gestione delle cartelle di run e del registro run (documentazione automatica)."""

from __future__ import annotations

import datetime as dt
import getpass
import json
import os
from pathlib import Path


def nuovo_run_dir(cfg: dict, base: str | Path = "outputs", run_id: str | None = None) -> Path:
    run_id = run_id or dt.datetime.now().strftime("%Y%m%d-%H%M")
    d = Path(base) / cfg["cliente"] / run_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def ultimo_run_dir(cfg: dict, base: str | Path = "outputs") -> Path:
    d = Path(base) / cfg["cliente"]
    runs = sorted(p for p in d.glob("*") if p.is_dir())
    if not runs:
        raise FileNotFoundError(f"Nessun run trovato in {d}")
    return runs[-1]


def autore() -> str:
    return os.environ.get("MMM_AUTORE") or getpass.getuser()


def scrivi_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def aggiorna_registro(run_dir: Path, riga: dict, registro: str | Path = "docs/registro_run.md") -> None:
    """Aggiunge una riga al registro dei run del repository."""
    registro = Path(registro)
    if not registro.exists():
        registro.parent.mkdir(parents=True, exist_ok=True)
        registro.write_text(
            "# Registro run\n\n"
            "Aggiornato automaticamente da `python -m mmm.report`. Non modificare a mano le righe.\n\n"
            "| Data | Cliente | Run | Autore | Esito | R-hat max | MAPE holdout | Note |\n"
            "|---|---|---|---|---|---|---|---|\n",
            encoding="utf-8",
        )
    testo = registro.read_text(encoding="utf-8")
    run_ref = f"`{run_dir.as_posix()}`"
    if run_ref in testo:
        return
    with registro.open("a", encoding="utf-8") as f:
        f.write(
            f"| {riga.get('data','')} | {riga.get('cliente','')} | {run_ref} | {riga.get('autore','')} "
            f"| {riga.get('esito','')} | {riga.get('rhat_max','')} | {riga.get('mape_holdout','')} "
            f"| {riga.get('note','')} |\n"
        )
