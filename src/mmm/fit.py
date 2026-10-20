"""Stima del modello Meridian e salvataggio dei risultati.

Gira sulla VM Colab con GPU (vedi scripts/colab_run.sh); funziona anche in locale
su CPU per i test. Salva solo risultati aggregati in CSV/JSON nella cartella del run.

Uso:  python -m mmm.fit configs/cliente.yaml --run-dir DIR [--rapido]
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from .config import load_config
from .data import carica_dataset
from .runs import autore, nuovo_run_dir, scrivi_json


def info_hardware() -> dict:
    """Dispositivi visti dal backend di calcolo di Meridian (JAX o TensorFlow)."""
    from meridian import backend

    cb = backend.computation_backend()
    nome_backend = getattr(cb, "name", str(cb))
    gpu = None
    try:
        import jax

        gpus = [d for d in jax.devices() if d.platform == "gpu"]
        gpu = getattr(gpus[0], "device_kind", str(gpus[0])) if gpus else None
    except Exception:  # noqa: BLE001
        pass
    if gpu is None:
        try:
            import tensorflow as tf

            g = tf.config.list_physical_devices("GPU")
            gpu = g[0].name if g else None
        except Exception:  # noqa: BLE001
            pass
    return {"backend": nome_backend, "gpu_disponibile": gpu is not None, "gpu": gpu}


def costruisci_input(cfg: dict, df: pd.DataFrame):
    from meridian.data import load

    df = df.copy()
    data_col = cfg["colonna_data"]
    df[data_col] = pd.to_datetime(df[data_col]).dt.strftime("%Y-%m-%d")

    media_cols, spend_cols, media_map, spend_map = [], [], {}, {}
    for c in cfg["canali"]:
        if c["impression"]:
            mcol = c["impression"]
        else:
            # senza impression la spesa fa anche da variabile di esposizione
            mcol = f"__media_{c['nome']}"
            df[mcol] = df[c["spesa"]]
        media_cols.append(mcol)
        spend_cols.append(c["spesa"])
        media_map[mcol] = c["nome"]
        spend_map[c["spesa"]] = c["nome"]

    coord = load.CoordToColumns(
        time=data_col,
        kpi=cfg["kpi"]["colonna"],
        controls=cfg["controlli"] or None,
        revenue_per_kpi=cfg["kpi"].get("revenue_per_kpi"),
        media=media_cols,
        media_spend=spend_cols,
    )
    loader = load.DataFrameDataLoader(
        df=df,
        coord_to_columns=coord,
        kpi_type=cfg["kpi"]["tipo"],
        media_to_channel=media_map,
        media_spend_to_channel=spend_map,
        currency_code=cfg.get("valuta"),
    )
    return loader.load()


def costruisci_spec(cfg: dict, n_times: int):
    from meridian import backend
    from meridian.model import prior_distribution, spec

    m = cfg["modello"]
    prior = prior_distribution.PriorDistribution(
        roi_m=backend.tfd.LogNormal(
            np.float64(m["roi_prior"]["media"]), np.float64(m["roi_prior"]["sigma"]), name="roi_m"
        )
    )
    holdout_id = None
    if m["holdout_settimane"]:
        holdout_id = np.zeros(n_times, dtype=bool)
        holdout_id[-int(m["holdout_settimane"]):] = True
    return spec.ModelSpec(
        prior=prior,
        max_lag=int(m["max_lag_adstock"]),
        knots=m["knots"],
        holdout_id=holdout_id,
    )


def _ds_to_df(ds, var: str, dist: str = "posterior") -> pd.DataFrame:
    da = ds[var].sel(distribution=dist) if "distribution" in ds[var].dims else ds[var]
    return da.to_pandas() if da.ndim == 2 else da.to_dataframe()


def estrai_risultati(mmm, cfg: dict, run_dir: Path) -> dict:
    from meridian.analysis import analyzer, optimizer

    try:
        an = analyzer.Analyzer(model_context=mmm.model_context, inference_data=mmm.inference_data)
    except TypeError:  # versioni precedenti di Meridian
        an = analyzer.Analyzer(mmm)
    use_kpi = cfg["kpi"]["tipo"] == "non_revenue" and not cfg["kpi"].get("revenue_per_kpi")
    out: dict = {}

    # Convergenza
    rhat = an.get_rhat()
    rhat_max = {
        k: float(np.nanmax(np.asarray(v))) for k, v in rhat.items() if np.isfinite(np.asarray(v)).any()
    }
    out["rhat_max"] = round(max(rhat_max.values()), 4)
    out["rhat_per_parametro"] = {k: round(v, 4) for k, v in sorted(rhat_max.items(), key=lambda x: -x[1])}

    # Accuratezza (train / holdout)
    acc = an.predictive_accuracy().to_dataframe().reset_index()
    acc.to_csv(run_dir / "accuratezza.csv", index=False)
    out["accuratezza"] = acc.to_dict(orient="records")

    # Metriche per canale
    sm = an.summary_metrics(use_kpi=use_kpi, confidence_level=0.9)
    righe = []
    for ch in sm.coords["channel"].values:
        r = {"canale": str(ch)}
        for var in ("spend", "pct_of_spend", "incremental_outcome", "pct_of_contribution", "roi", "mroi", "cpik", "effectiveness"):
            if var not in sm:
                continue
            da = sm[var].sel(channel=ch)
            if "distribution" in da.dims:
                da = da.sel(distribution="posterior")
            if "metric" in da.dims:
                for met in ("mean", "ci_lo", "ci_hi"):
                    if met in da.coords["metric"].values:
                        r[f"{var}_{met}"] = float(da.sel(metric=met))
            else:
                r[var] = float(da)
        righe.append(r)
    canali = pd.DataFrame(righe)
    canali.to_csv(run_dir / "metriche_canali.csv", index=False)

    # Fit settimanale (atteso vs osservato)
    try:
        eva = an.expected_vs_actual_data(confidence_level=0.9).to_dataframe().reset_index()
        eva.to_csv(run_dir / "fit_settimanale.csv", index=False)
    except Exception as e:  # noqa: BLE001
        out["fit_settimanale_errore"] = str(e)

    # Curve di risposta
    try:
        rc = an.response_curves(confidence_level=0.9, use_kpi=use_kpi).to_dataframe().reset_index()
        rc.to_csv(run_dir / "curve_risposta.csv", index=False)
    except Exception as e:  # noqa: BLE001
        out["curve_risposta_errore"] = str(e)

    # Ottimizzazione budget a budget fisso
    try:
        ott = cfg["ottimizzazione"]
        pct = ott["variazione_max_pct"] / 100
        opt = optimizer.BudgetOptimizer(mmm)
        res = opt.optimize(
            fixed_budget=True,
            spend_constraint_lower=pct,
            spend_constraint_upper=pct,
            use_kpi=use_kpi,
        )
        attuale = res.nonoptimized_data
        ottim = res.optimized_data
        b = pd.DataFrame({
            "canale": [str(c) for c in attuale.coords["channel"].values],
            "spesa_attuale": attuale["spend"].values,
            "spesa_ottimizzata": ottim["spend"].values,
        })
        for nome, ds in (("attuale", attuale), ("ottimizzata", ottim)):
            io = ds["incremental_outcome"]
            if "metric" in io.dims:
                io = io.sel(metric="mean")
            b[f"outcome_incrementale_{nome}"] = io.values
        b.to_csv(run_dir / "budget_ottimizzato.csv", index=False)
        out["ottimizzazione"] = {
            "vincolo_pct": ott["variazione_max_pct"],
            "outcome_attuale": float(b["outcome_incrementale_attuale"].sum()),
            "outcome_ottimizzato": float(b["outcome_incrementale_ottimizzata"].sum()),
        }
    except Exception as e:  # noqa: BLE001
        out["ottimizzazione_errore"] = str(e)

    return out


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Stima MMM con Meridian")
    p.add_argument("config")
    p.add_argument("--run-dir", default=None)
    p.add_argument("--rapido", action="store_true",
                   help="Campionamento ridotto per test (risultati NON utilizzabili)")
    a = p.parse_args(argv)

    from meridian.model import model

    cfg = load_config(a.config)
    run_dir = Path(a.run_dir) if a.run_dir else nuovo_run_dir(cfg)
    run_dir.mkdir(parents=True, exist_ok=True)
    camp = dict(cfg["modello"]["campionamento"])
    if a.rapido:
        camp.update(catene=2, adapt=100, burnin=50, keep=100)

    meta = {
        "cliente": cfg["cliente"],
        "autore": autore(),
        "inizio": dt.datetime.now().isoformat(timespec="seconds"),
        "modalita": "rapido (test)" if a.rapido else "completo",
        "campionamento": camp,
        "hardware": info_hardware(),
    }
    print(f"Hardware: {meta['hardware']}")
    if not meta["hardware"]["gpu_disponibile"]:
        print("ATTENZIONE: nessuna GPU vista dal backend, la stima gira su CPU (lenta).")

    df = carica_dataset(cfg)
    data = costruisci_input(cfg, df)
    mmm = model.Meridian(input_data=data, model_spec=costruisci_spec(cfg, len(df)))

    t0 = time.time()
    mmm.sample_prior(500, seed=camp["seed"])
    mmm.sample_posterior(
        n_chains=camp["catene"], n_adapt=camp["adapt"], n_burnin=camp["burnin"],
        n_keep=camp["keep"], seed=camp["seed"],
    )
    meta["secondi_campionamento"] = round(time.time() - t0, 1)
    print(f"Campionamento completato in {meta['secondi_campionamento']} s")

    ris = estrai_risultati(mmm, cfg, run_dir)
    meta.update(ris)
    meta["fine"] = dt.datetime.now().isoformat(timespec="seconds")
    meta["convergenza_ok"] = ris["rhat_max"] <= cfg["modello"]["rhat_max"]

    try:
        model.save_mmm(mmm, str(run_dir / "modello.pkl"))
    except Exception as e:  # noqa: BLE001
        meta["salvataggio_modello_errore"] = str(e)

    scrivi_json(run_dir / "risultati.json", meta)
    print(f"R-hat max: {ris['rhat_max']}  (soglia {cfg['modello']['rhat_max']}) -> "
          f"{'OK' if meta['convergenza_ok'] else 'NON CONVERGE'}")
    print(f"Risultati in {run_dir}")
    return 0 if meta["convergenza_ok"] else 2


if __name__ == "__main__":
    sys.exit(main())
