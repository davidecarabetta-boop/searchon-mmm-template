"""Report SearchOn di un run MMM e aggiornamento della documentazione del run.

Legge i file aggregati prodotti da mmm.fit (nessun accesso ai dati grezzi né a
Meridian), produce grafici, report.md, report.html autonomo e RUN.md, e aggiunge
il run a docs/registro_run.md.

Uso:  python -m mmm.report configs/cliente.yaml [--run-dir DIR]
      (senza --run-dir usa l'ultimo run del cliente)
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import html
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import yaml  # noqa: E402

from . import __version__  # noqa: E402
from .config import load_config  # noqa: E402
from .runs import aggiorna_registro, ultimo_run_dir  # noqa: E402

from matplotlib.ticker import FuncFormatter  # noqa: E402

BLU, ARANCIO, GRIGIO = "#2a6fdb", "#e8833a", "#9aa3ad"
MIGLIAIA = FuncFormatter(lambda v, _: f"{v:,.0f}".replace(",", "."))


def _fmt_eur(x: float) -> str:
    return f"{x:,.0f}".replace(",", ".")


def _salva(fig, path: Path) -> Path:
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return path


def grafici(run_dir: Path, cfg: dict) -> dict[str, Path]:
    g = run_dir / "grafici"
    g.mkdir(exist_ok=True)
    out = {}
    canali = pd.read_csv(run_dir / "metriche_canali.csv")
    canali = canali[canali["canale"] != "All Channels"]

    # Quota spesa vs quota contributo
    fig, ax = plt.subplots(figsize=(7, 3.6))
    x = range(len(canali))
    contrib_share = canali["incremental_outcome_mean"] / canali["incremental_outcome_mean"].sum() * 100
    ax.bar([i - 0.2 for i in x], canali["pct_of_spend"], width=0.4, color=GRIGIO, label="% spesa")
    ax.bar([i + 0.2 for i in x], contrib_share, width=0.4, color=BLU, label="% contributo media")
    ax.set_xticks(list(x), canali["canale"])
    ax.set_ylabel("%")
    ax.set_title("Quota di spesa vs quota di contributo incrementale")
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    out["quote"] = _salva(fig, g / "quote_spesa_contributo.png")

    # ROI con intervallo
    fig, ax = plt.subplots(figsize=(7, 3.4))
    c = canali.sort_values("roi_mean")
    ax.errorbar(c["roi_mean"], c["canale"],
                xerr=[c["roi_mean"] - c["roi_ci_lo"], c["roi_ci_hi"] - c["roi_mean"]],
                fmt="o", color=BLU, ecolor=GRIGIO, capsize=4)
    ax.axvline(1, color=ARANCIO, lw=1, ls="--")
    ax.set_xlabel("ROI (media e intervallo di credibilità 90%)")
    ax.set_title("ROI per canale")
    ax.spines[["top", "right"]].set_visible(False)
    out["roi"] = _salva(fig, g / "roi.png")

    # Fit settimanale
    fp = run_dir / "fit_settimanale.csv"
    if fp.exists():
        f = pd.read_csv(fp)
        m = f[f["metric"] == "mean"].copy()
        m["time"] = pd.to_datetime(m["time"])
        fig, ax = plt.subplots(figsize=(8, 3.4))
        ax.plot(m["time"], m["actual"], color="#333", lw=1.2, label="Osservato")
        ax.plot(m["time"], m["expected"], color=BLU, lw=1.2, label="Atteso dal modello")
        ax.plot(m["time"], m["baseline"], color=GRIGIO, lw=1, ls="--", label="Baseline")
        h = cfg["modello"]["holdout_settimane"]
        if h:
            ax.axvspan(m["time"].iloc[-h], m["time"].iloc[-1], color=ARANCIO, alpha=0.12, label="Holdout")
        ax.yaxis.set_major_formatter(MIGLIAIA)
        ax.set_title("KPI osservato vs atteso")
        ax.legend(frameon=False, ncol=4, fontsize=8)
        ax.spines[["top", "right"]].set_visible(False)
        out["fit"] = _salva(fig, g / "fit_settimanale.png")

    # Curve di risposta
    rp = run_dir / "curve_risposta.csv"
    if rp.exists():
        r = pd.read_csv(rp)
        r = r[r["metric"] == "mean"]
        fig, ax = plt.subplots(figsize=(7, 3.6))
        for ch, d in r.groupby("channel"):
            ax.plot(d["spend"], d["incremental_outcome"], label=ch)
            attuale = d[d["spend_multiplier"].sub(1).abs() < 1e-9]
            if len(attuale):
                ax.scatter(attuale["spend"], attuale["incremental_outcome"], s=18)
        ax.xaxis.set_major_formatter(MIGLIAIA)
        ax.yaxis.set_major_formatter(MIGLIAIA)
        ax.set_xlabel("Spesa nel periodo")
        ax.set_ylabel("Outcome incrementale")
        ax.set_title("Curve di risposta (punto = spesa attuale)")
        ax.legend(frameon=False)
        ax.spines[["top", "right"]].set_visible(False)
        out["curve"] = _salva(fig, g / "curve_risposta.png")

    # Budget
    bp = run_dir / "budget_ottimizzato.csv"
    if bp.exists():
        b = pd.read_csv(bp)
        fig, ax = plt.subplots(figsize=(7, 3.4))
        x = range(len(b))
        ax.bar([i - 0.2 for i in x], b["spesa_attuale"], width=0.4, color=GRIGIO, label="Attuale")
        ax.bar([i + 0.2 for i in x], b["spesa_ottimizzata"], width=0.4, color=BLU, label="Ottimizzata")
        ax.set_xticks(list(x), b["canale"])
        ax.yaxis.set_major_formatter(MIGLIAIA)
        ax.set_title(f"Allocazione a budget invariato (±{cfg['ottimizzazione']['variazione_max_pct']}% per canale)")
        ax.legend(frameon=False)
        ax.spines[["top", "right"]].set_visible(False)
        out["budget"] = _salva(fig, g / "budget.png")
    return out


def _metrica(acc: list[dict], metric: str, insieme: str):
    for r in acc:
        if r["metric"] == metric and r["evaluation_set"] == insieme:
            return r["value"]
    return None


def componi_markdown(cfg: dict, ris: dict, check: dict, run_dir: Path, figs: dict) -> str:
    canali = pd.read_csv(run_dir / "metriche_canali.csv")
    canali = canali[canali["canale"] != "All Channels"]
    acc = ris.get("accuratezza", [])
    r2_tr, r2_te = _metrica(acc, "R_Squared", "Train"), _metrica(acc, "R_Squared", "Test")
    mape_tr, mape_te = _metrica(acc, "MAPE", "Train"), _metrica(acc, "MAPE", "Test")
    test = ris.get("modalita", "").startswith("rapido")

    righe = [f"# MMM {cfg['cliente']}: report del run `{run_dir.name}`", ""]
    if test:
        righe += ["> **Run di test con campionamento ridotto: i numeri NON sono utilizzabili.**", ""]
    righe += [
        f"Periodo {cfg['periodo']['inizio']} → {cfg['periodo']['fine']}, KPI `{cfg['kpi']['colonna']}` "
        f"({cfg['kpi']['tipo']}), {len(cfg['canali'])} canali, autore {ris.get('autore')}.",
        "",
        "## Qualità del modello",
        "",
        "| Controllo | Valore | Esito |",
        "|---|---|---|",
        f"| Check dati | {check.get('esito', 'n.d.')} | {'✅' if check.get('esito','').startswith('OK') else '⚠️'} |",
        f"| Hardware | {(ris.get('hardware') or {}).get('gpu') or 'CPU'} | "
        f"{'✅' if (ris.get('hardware') or {}).get('gpu_disponibile') else '⚠️ senza GPU'} |",
        f"| R-hat massimo | {ris.get('rhat_max')} | {'✅' if ris.get('convergenza_ok') else '❌ non converge'} |",
    ]
    if r2_tr is not None:
        righe.append(f"| R² train / holdout | {r2_tr:.2f} / {r2_te:.2f} | |")
    if mape_tr is not None:
        righe.append(f"| MAPE train / holdout | {mape_tr:.1%} / {mape_te:.1%} | "
                     f"{'✅' if mape_te is not None and mape_te < 0.15 else '⚠️ verificare'} |")
    righe += ["", "## Risultati per canale", "",
              "| Canale | Spesa | % spesa | % contributo | ROI (int. 90%) | ROI marginale |",
              "|---|---|---|---|---|---|"]
    for _, c in canali.iterrows():
        righe.append(
            f"| {c['canale']} | {_fmt_eur(c['spend'])} | {c['pct_of_spend']:.1f}% | "
            f"{c['pct_of_contribution_mean']:.1f}% | {c['roi_mean']:.2f} ({c['roi_ci_lo']:.2f}–{c['roi_ci_hi']:.2f}) | "
            f"{c.get('mroi_mean', float('nan')):.2f} |"
        )
    righe.append("")
    for chiave, titolo in (("quote", "Spesa vs contributo"), ("roi", "ROI"), ("fit", "Fit del modello"),
                           ("curve", "Curve di risposta"), ("budget", "Ottimizzazione budget")):
        if chiave in figs:
            righe += [f"### {titolo}", "", f"![{titolo}]({figs[chiave].relative_to(run_dir).as_posix()})", ""]
    if "ottimizzazione" in ris:
        o = ris["ottimizzazione"]
        delta = (o["outcome_ottimizzato"] / o["outcome_attuale"] - 1) * 100 if o["outcome_attuale"] else 0
        righe += [f"A budget invariato, con variazioni massime del ±{o['vincolo_pct']}% per canale, "
                  f"la riallocazione stimata porta l'outcome incrementale da {_fmt_eur(o['outcome_attuale'])} "
                  f"a {_fmt_eur(o['outcome_ottimizzato'])} ({delta:+.1f}%).", ""]
    righe += [
        "## Come leggere questi numeri",
        "",
        "- Gli intervalli sono di credibilità al 90%: un canale con intervallo ROI molto ampio va validato "
        "con un lift test prima di spostare budget.",
        "- I risultati dipendono dalle prior di ROI e dalla qualità della vista BigQuery: vedi `RUN.md`.",
        "",
    ]
    return "\n".join(righe)


def markdown_a_html(md: str, run_dir: Path, titolo: str) -> str:
    """Conversione minima e autonoma (immagini incorporate) senza dipendenze extra."""
    corpo, in_tab, in_lista = [], False, False
    for riga in md.splitlines():
        if riga.startswith("|"):
            celle = [html.escape(c.strip()) for c in riga.strip("|").split("|")]
            if set("".join(celle)) <= set("-: "):
                continue
            if not in_tab:
                corpo.append("<table>")
                corpo.append("<tr>" + "".join(f"<th>{c}</th>" for c in celle) + "</tr>")
                in_tab = True
            else:
                corpo.append("<tr>" + "".join(f"<td>{c}</td>" for c in celle) + "</tr>")
            continue
        if in_tab:
            corpo.append("</table>")
            in_tab = False
        if riga.startswith("- "):
            if not in_lista:
                corpo.append("<ul>")
                in_lista = True
            corpo.append(f"<li>{html.escape(riga[2:])}</li>")
            continue
        if in_lista:
            corpo.append("</ul>")
            in_lista = False
        if riga.startswith("!["):
            src = riga[riga.index("(") + 1:-1]
            b64 = base64.b64encode((run_dir / src).read_bytes()).decode()
            corpo.append(f'<img alt="" src="data:image/png;base64,{b64}">')
        elif riga.startswith("### "):
            corpo.append(f"<h3>{html.escape(riga[4:])}</h3>")
        elif riga.startswith("## "):
            corpo.append(f"<h2>{html.escape(riga[3:])}</h2>")
        elif riga.startswith("# "):
            corpo.append(f"<h1>{html.escape(riga[2:])}</h1>")
        elif riga.startswith("> "):
            corpo.append(f"<p class='warn'>{html.escape(riga[2:]).replace('**', '')}</p>")
        elif riga.strip():
            corpo.append(f"<p>{html.escape(riga).replace('**', '')}</p>")
    if in_tab:
        corpo.append("</table>")
    if in_lista:
        corpo.append("</ul>")
    css = ("body{font-family:system-ui,sans-serif;max-width:900px;margin:32px auto;padding:0 16px;color:#1d2228}"
           "table{border-collapse:collapse;margin:12px 0;width:100%}th,td{border-bottom:1px solid #dde1e6;"
           "padding:6px 8px;text-align:left;font-size:14px}th{background:#f3f5f7}img{max-width:100%}"
           ".warn{background:#fff4e5;border-left:4px solid #e8833a;padding:8px 12px}")
    return (f"<!doctype html><html lang='it'><head><meta charset='utf-8'><title>{html.escape(titolo)}</title>"
            f"<style>{css}</style></head><body>{''.join(corpo)}</body></html>")


def scrivi_run_md(cfg: dict, ris: dict, check: dict, run_dir: Path, config_path: Path) -> None:
    """Documentazione del run: cosa è stato lanciato, con cosa, e con quale esito."""
    try:
        import importlib.metadata as md

        mer = md.version("google-meridian")
    except Exception:  # noqa: BLE001
        mer = "n.d."
    cfg_txt = config_path.read_text(encoding="utf-8")
    righe = [
        f"# Run `{run_dir.name}`: {cfg['cliente']}",
        "",
        f"- Autore: {ris.get('autore')}",
        f"- Inizio / fine stima: {ris.get('inizio')} / {ris.get('fine')}",
        f"- Modalità: {ris.get('modalita')}",
        f"- Hardware: {ris.get('hardware')}",
        f"- Campionamento: {ris.get('campionamento')} ({ris.get('secondi_campionamento')} s)",
        f"- Pipeline searchon-mmm {__version__}, Meridian {ris.get('versione_meridian', mer)}",
        f"- Sorgente dati: {cfg['sorgente']['tipo']} "
        + (f"`{cfg['sorgente'].get('progetto')}.{cfg['sorgente'].get('dataset')}.{cfg['sorgente'].get('vista')}`"
           if cfg["sorgente"]["tipo"] == "bigquery" else f"`{cfg['sorgente'].get('percorso')}`"),
        f"- Esito check dati: {check.get('esito', 'n.d.')}",
        f"- R-hat massimo: {ris.get('rhat_max')} ({'converge' if ris.get('convergenza_ok') else 'NON converge'})",
        "",
        "## Parametri con R-hat più alto",
        "",
        *[f"- {k}: {v}" for k, v in list(ris.get("rhat_per_parametro", {}).items())[:5]],
        "",
        "## Configurazione usata",
        "",
        "```yaml",
        cfg_txt.rstrip(),
        "```",
        "",
    ]
    errs = {k: v for k, v in ris.items() if k.endswith("_errore")}
    if errs:
        righe += ["## Passaggi non riusciti", "", *[f"- {k}: {v}" for k, v in errs.items()], ""]
    # La sezione Decisioni è scritta a mano (o da Claude): va conservata quando il report viene rigenerato
    decisioni = "- nessuna decisione di metodo registrata"
    esistente = run_dir / "RUN.md"
    if esistente.exists():
        testo = esistente.read_text(encoding="utf-8")
        if "## Decisioni" in testo:
            decisioni = testo.split("## Decisioni", 1)[1].strip() or decisioni
    righe += ["## Decisioni", "", decisioni, ""]
    (run_dir / "RUN.md").write_text("\n".join(righe), encoding="utf-8")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Report MMM SearchOn")
    p.add_argument("config")
    p.add_argument("--run-dir", default=None)
    p.add_argument("--no-registro", action="store_true", help="Non aggiornare docs/registro_run.md")
    a = p.parse_args(argv)

    cfg = load_config(a.config)
    run_dir = Path(a.run_dir) if a.run_dir else ultimo_run_dir(cfg)
    rj = run_dir / "risultati.json"
    if not rj.exists():
        print(f"Manca {rj}: il run non è stato stimato o scaricato")
        return 1
    ris = json.loads(rj.read_text(encoding="utf-8"))
    cj = run_dir / "check.json"
    check = json.loads(cj.read_text(encoding="utf-8")) if cj.exists() else {}

    figs = grafici(run_dir, cfg)
    md = componi_markdown(cfg, ris, check, run_dir, figs)
    (run_dir / "report.md").write_text(md, encoding="utf-8")
    (run_dir / "report.html").write_text(
        markdown_a_html(md, run_dir, f"MMM {cfg['cliente']} {run_dir.name}"), encoding="utf-8")
    scrivi_run_md(cfg, ris, check, run_dir, Path(a.config))

    if not a.no_registro:
        acc = ris.get("accuratezza", [])
        mape = _metrica(acc, "MAPE", "Test")
        esito = "test" if ris.get("modalita", "").startswith("rapido") else (
            "ok" if ris.get("convergenza_ok") else "non converge")
        aggiorna_registro(run_dir, {
            "data": dt.date.today().isoformat(),
            "cliente": cfg["cliente"],
            "autore": ris.get("autore"),
            "esito": esito,
            "rhat_max": ris.get("rhat_max"),
            "mape_holdout": f"{mape:.1%}" if mape is not None else "",
            "note": "",
        })
    print(f"Report: {run_dir / 'report.html'}")
    print(f"Documentazione run: {run_dir / 'RUN.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
