"""Controllo di qualità del dataset rispetto allo schema standard.

Stampa e salva solo diagnostiche aggregate: nessuna riga del dataset finisce
nell'output, quindi Claude vede l'esito del controllo ma non i dati.

Uso:  python -m mmm.check configs/cliente.yaml [--run-dir DIR]
Exit code: 0 = ok o solo avvisi, 1 = errori bloccanti.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .config import load_config
from .data import carica_dataset
from .runs import nuovo_run_dir, scrivi_json

PII_PATTERN = re.compile(
    r"(e_?mail|phone|telefono|cellulare|user_?id|client_?id|customer_?id|codice_?fiscale|"
    r"indirizzo|address|nome_?cliente|cognome|ip_?addr|gclid|fbclid)",
    re.IGNORECASE,
)


def esegui_check(cfg: dict, df: pd.DataFrame) -> dict:
    errori, avvisi, info = [], [], {}
    data_col = cfg["colonna_data"]
    date = pd.to_datetime(df[data_col])

    # Struttura temporale
    info["settimane"] = int(len(df))
    info["dal"] = str(date.min().date()) if len(df) else None
    info["al"] = str(date.max().date()) if len(df) else None
    if date.duplicated().any():
        errori.append(f"{int(date.duplicated().sum())} settimane duplicate: la vista deve avere una riga per settimana")
    diffs = date.drop_duplicates().sort_values().diff().dropna().dt.days
    if len(diffs) and not (diffs == 7).all():
        buchi = int((diffs > 7).sum())
        errori.append(f"Serie non settimanale regolare: {buchi} buchi e passi diversi da 7 giorni")
    if len(df) and date.dt.dayofweek.nunique() > 1:
        errori.append("Le settimane non iniziano tutte lo stesso giorno della settimana")
    if len(df) < 52:
        errori.append(f"Solo {len(df)} settimane: servono almeno 52, consigliate 104+")
    elif len(df) < 104:
        avvisi.append(f"{len(df)} settimane: sufficiente ma sotto le 104 consigliate")

    # PII nei nomi colonna (della vista intera non vediamo nulla: solo le colonne usate)
    sospette = [c for c in df.columns if PII_PATTERN.search(c)]
    if sospette:
        errori.append(f"Colonne con nome da dato personale: {sospette}. La vista deve essere aggregata")

    # Valori per colonna
    numeriche = [c for c in df.columns if c != data_col]
    nulli = {c: int(df[c].isna().sum()) for c in numeriche if df[c].isna().any()}
    if nulli:
        errori.append(f"Valori nulli: {nulli}")
    non_num = [c for c in numeriche if not pd.api.types.is_numeric_dtype(df[c])]
    if non_num:
        errori.append(f"Colonne non numeriche: {non_num}")
    num = [c for c in numeriche if c not in non_num]
    negativi = {c: int((df[c] < 0).sum()) for c in num if (df[c] < 0).any() and c not in cfg["controlli"]}
    if negativi:
        errori.append(f"Valori negativi in KPI/spesa/impression: {negativi}")

    # KPI
    kpi = cfg["kpi"]["colonna"]
    if kpi in num and len(df):
        info["kpi_totale"] = float(df[kpi].sum())
        if df[kpi].std() == 0:
            errori.append("Il KPI è costante")

    # Canali
    canali_info = {}
    spese = []
    for c in cfg["canali"]:
        s = df[c["spesa"]] if c["spesa"] in num else None
        if s is None:
            continue
        spese.append(c["spesa"])
        tot = float(s.sum())
        zero = int((s == 0).sum())
        canali_info[c["nome"]] = {
            "spesa_totale": round(tot, 2),
            "quota_spesa": None,
            "settimane_a_zero": zero,
        }
        if tot == 0:
            errori.append(f"Canale {c['nome']}: spesa totale zero")
        elif zero / max(len(df), 1) > 0.5:
            avvisi.append(f"Canale {c['nome']}: spesa a zero in {zero} settimane su {len(df)}")
        if c["impression"] and c["impression"] in num:
            imp = df[c["impression"]]
            incoerenti = int(((s > 0) & (imp == 0)).sum())
            if incoerenti:
                avvisi.append(f"Canale {c['nome']}: {incoerenti} settimane con spesa ma senza impression")
    tot_spesa = sum(v["spesa_totale"] for v in canali_info.values()) or 1
    for nome, v in canali_info.items():
        v["quota_spesa"] = round(v["spesa_totale"] / tot_spesa, 4)
        if 0 < v["quota_spesa"] < 0.02:
            avvisi.append(f"Canale {nome}: meno del 2% della spesa, stima probabilmente poco informativa")
    info["canali"] = canali_info

    # Collinearità tra spese
    if len(spese) > 1 and len(df) > 2:
        corr = df[spese].corr().abs()
        coppie = [
            (a, b, round(float(corr.loc[a, b]), 3))
            for i, a in enumerate(spese) for b in spese[i + 1:]
            if corr.loc[a, b] > 0.9
        ]
        if coppie:
            avvisi.append(f"Spese molto correlate (>0.9), effetti difficili da separare: {coppie}")

    # Controlli
    for c in cfg["controlli"]:
        if c in num and df[c].std() == 0:
            errori.append(f"Controllo {c} costante: rimuoverlo dal YAML")

    # Rapporto osservazioni / parametri
    n_param = 3 * len(cfg["canali"]) + len(cfg["controlli"]) + 10
    info["rapporto_osservazioni_parametri"] = round(len(df) / n_param, 2)
    if len(df) < 2 * n_param:
        avvisi.append("Poche settimane rispetto al numero di canali e controlli: valuta di accorpare canali")

    holdout = cfg["modello"]["holdout_settimane"]
    if holdout and len(df) - holdout < 52:
        errori.append(f"Con {holdout} settimane di holdout restano meno di 52 settimane per la stima")

    esito = "KO" if errori else ("OK con avvisi" if avvisi else "OK")
    return {"esito": esito, "errori": errori, "avvisi": avvisi, "info": info}


def scrivi_markdown(cfg: dict, risultato: dict, path: Path) -> None:
    r = risultato
    righe = [
        f"# Check dati: {cfg['cliente']}",
        "",
        f"**Esito: {r['esito']}**",
        "",
        f"- Periodo: {r['info'].get('dal')} → {r['info'].get('al')} ({r['info'].get('settimane')} settimane)",
        f"- Rapporto osservazioni/parametri: {r['info'].get('rapporto_osservazioni_parametri')}",
        "",
        "## Errori bloccanti",
        *([f"- {e}" for e in r["errori"]] or ["- nessuno"]),
        "",
        "## Avvisi",
        *([f"- {a}" for a in r["avvisi"]] or ["- nessuno"]),
        "",
        "## Canali",
        "",
        "| Canale | Quota spesa | Settimane a zero |",
        "|---|---|---|",
    ]
    for nome, v in r["info"].get("canali", {}).items():
        righe.append(f"| {nome} | {v['quota_spesa']:.1%} | {v['settimane_a_zero']} |")
    path.write_text("\n".join(righe) + "\n", encoding="utf-8")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Check qualità dati MMM")
    p.add_argument("config")
    p.add_argument("--run-dir", default=None)
    a = p.parse_args(argv)

    cfg = load_config(a.config)
    run_dir = Path(a.run_dir) if a.run_dir else nuovo_run_dir(cfg)
    run_dir.mkdir(parents=True, exist_ok=True)
    df = carica_dataset(cfg)
    r = esegui_check(cfg, df)
    scrivi_json(run_dir / "check.json", r)
    scrivi_markdown(cfg, r, run_dir / "check.md")

    print(f"Esito check: {r['esito']}  ({r['info'].get('settimane')} settimane, "
          f"{r['info'].get('dal')} → {r['info'].get('al')})")
    for e in r["errori"]:
        print(f"  ERRORE: {e}")
    for w in r["avvisi"]:
        print(f"  avviso: {w}")
    print(f"Dettaglio: {run_dir / 'check.md'}")
    return 1 if r["errori"] else 0


if __name__ == "__main__":
    sys.exit(main())
