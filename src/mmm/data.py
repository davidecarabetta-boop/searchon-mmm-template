"""Caricamento del dataset da BigQuery (standard) o da CSV (solo test)."""

from __future__ import annotations

import pandas as pd

from .config import colonne_richieste


def _query_bigquery(cfg: dict) -> pd.DataFrame:
    from google.cloud import bigquery  # import lazy: serve solo con sorgente bigquery

    src = cfg["sorgente"]
    cols = colonne_richieste(cfg)
    data_col = cfg["colonna_data"]
    tabella = f"`{src['progetto']}.{src['dataset']}.{src['vista']}`"
    sql = (
        f"SELECT {', '.join(f'`{c}`' for c in cols)} FROM {tabella} "
        f"WHERE `{data_col}` BETWEEN @inizio AND @fine ORDER BY `{data_col}`"
    )
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("inizio", "DATE", cfg["periodo"]["inizio"]),
            bigquery.ScalarQueryParameter("fine", "DATE", cfg["periodo"]["fine"]),
        ]
    )
    client = bigquery.Client(
        project=src.get("progetto_fatturazione") or src["progetto"],
        location=src.get("location"),
    )
    return client.query(sql, job_config=job_config).to_dataframe()


def _read_csv(cfg: dict) -> pd.DataFrame:
    df = pd.read_csv(cfg["sorgente"]["percorso"])
    data_col = cfg["colonna_data"]
    df[data_col] = pd.to_datetime(df[data_col]).dt.date
    mask = (df[data_col] >= cfg["periodo"]["inizio"]) & (df[data_col] <= cfg["periodo"]["fine"])
    return df.loc[mask].sort_values(data_col).reset_index(drop=True)


def carica_dataset(cfg: dict) -> pd.DataFrame:
    """Restituisce il dataset settimanale con le sole colonne previste dal YAML."""
    if cfg["sorgente"]["tipo"] == "bigquery":
        df = _query_bigquery(cfg)
    else:
        df = _read_csv(cfg)
    mancanti = [c for c in colonne_richieste(cfg) if c not in df.columns]
    if mancanti:
        raise ValueError(f"Colonne previste dal YAML ma assenti nella sorgente: {mancanti}")
    df[cfg["colonna_data"]] = pd.to_datetime(df[cfg["colonna_data"]])
    return df[colonne_richieste(cfg)].copy()
