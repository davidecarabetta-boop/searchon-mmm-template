"""Lettura e validazione del file di configurazione YAML del cliente."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import yaml

GPU_STANDARD = {"T4", "L4"}
GPU_COSTOSE = {"A100", "H100", "G4"}


class ConfigError(ValueError):
    pass


def _req(d: dict, key: str, where: str):
    if key not in d or d[key] in (None, ""):
        raise ConfigError(f"Manca il campo obbligatorio '{where}{key}'")
    return d[key]


def load_config(path: str | Path) -> dict:
    path = Path(path)
    if not path.exists():
        raise ConfigError(f"File di configurazione non trovato: {path}")
    cfg = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    _req(cfg, "cliente", "")
    src = _req(cfg, "sorgente", "")
    tipo = _req(src, "tipo", "sorgente.")
    if tipo == "bigquery":
        for k in ("progetto", "dataset", "vista"):
            _req(src, k, "sorgente.")
    elif tipo == "csv":
        _req(src, "percorso", "sorgente.")
    else:
        raise ConfigError("sorgente.tipo deve essere 'bigquery' oppure 'csv'")

    per = _req(cfg, "periodo", "")
    for k in ("inizio", "fine"):
        v = _req(per, k, "periodo.")
        per[k] = v if isinstance(v, dt.date) else dt.date.fromisoformat(str(v))
    if per["inizio"] >= per["fine"]:
        raise ConfigError("periodo.inizio deve essere precedente a periodo.fine")

    cfg.setdefault("colonna_data", "settimana")

    kpi = _req(cfg, "kpi", "")
    _req(kpi, "colonna", "kpi.")
    kpi.setdefault("tipo", "revenue")
    if kpi["tipo"] not in ("revenue", "non_revenue"):
        raise ConfigError("kpi.tipo deve essere 'revenue' oppure 'non_revenue'")

    canali = _req(cfg, "canali", "")
    if not isinstance(canali, list) or len(canali) < 1:
        raise ConfigError("'canali' deve essere una lista con almeno un canale")
    nomi = set()
    for i, c in enumerate(canali):
        _req(c, "nome", f"canali[{i}].")
        _req(c, "spesa", f"canali[{i}].")
        if c["nome"] in nomi:
            raise ConfigError(f"Canale duplicato: {c['nome']}")
        nomi.add(c["nome"])
        c.setdefault("impression", None)

    cfg["controlli"] = cfg.get("controlli") or []

    mod = cfg.setdefault("modello", {})
    mod.setdefault("holdout_settimane", 12)
    mod.setdefault("max_lag_adstock", 8)
    mod.setdefault("knots", None)
    mod.setdefault("roi_prior", {"media": 0.2, "sigma": 0.9})
    camp = mod.setdefault("campionamento", {})
    camp.setdefault("catene", 4)
    camp.setdefault("adapt", 1000)
    camp.setdefault("burnin", 500)
    camp.setdefault("keep", 1000)
    camp.setdefault("seed", 42)
    mod.setdefault("rhat_max", 1.2)

    calc = cfg.setdefault("calcolo", {})
    calc.setdefault("gpu", "T4")
    calc.setdefault("consenti_gpu_costose", False)
    calc.setdefault("timeout_minuti", 180)
    if calc["gpu"] in GPU_COSTOSE and not calc["consenti_gpu_costose"]:
        raise ConfigError(
            f"GPU {calc['gpu']} richiede calcolo.consenti_gpu_costose: true "
            "(e conferma esplicita di chi lancia il modello)"
        )
    if calc["gpu"] not in GPU_STANDARD | GPU_COSTOSE:
        raise ConfigError(f"GPU non riconosciuta: {calc['gpu']}")

    ott = cfg.setdefault("ottimizzazione", {})
    ott.setdefault("variazione_max_pct", 30)

    return cfg


def colonne_richieste(cfg: dict) -> list[str]:
    cols = [cfg["colonna_data"], cfg["kpi"]["colonna"]]
    for c in cfg["canali"]:
        cols.append(c["spesa"])
        if c["impression"]:
            cols.append(c["impression"])
    cols += cfg["controlli"]
    if cfg["kpi"].get("revenue_per_kpi"):
        cols.append(cfg["kpi"]["revenue_per_kpi"])
    # mantiene l'ordine, rimuove duplicati
    return list(dict.fromkeys(cols))
