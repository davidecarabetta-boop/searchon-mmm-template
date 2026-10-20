"""Genera un dataset settimanale sintetico con effetti noti, per collaudare la pipeline.

Uso: python tests/genera_dati_sintetici.py [percorso_csv]
"""

import sys

import numpy as np
import pandas as pd

rng = np.random.default_rng(7)
n = 156  # 3 anni
settimane = pd.date_range("2023-01-02", periods=n, freq="W-MON")
t = np.arange(n)

canali = {
    # nome: (spesa media settimanale, ROI vero, decadimento adstock)
    "google_search": (12000, 2.5, 0.3),
    "meta": (9000, 1.6, 0.5),
    "youtube": (5000, 0.9, 0.7),
}

df = pd.DataFrame({"settimana": settimane})
contributo = np.zeros(n)
for nome, (media, roi, decay) in canali.items():
    stagione = 1 + 0.3 * np.sin(2 * np.pi * t / 52 + rng.uniform(0, 6))
    spesa = np.clip(media * stagione * rng.lognormal(0, 0.35, n), 0, None)
    spesa[rng.random(n) < 0.05] = 0  # qualche settimana spenta
    df[f"spend_{nome}"] = spesa.round(2)
    df[f"impr_{nome}"] = (spesa * rng.uniform(80, 120, n)).round()
    ad = np.zeros(n)
    for i in range(n):
        ad[i] = spesa[i] + (decay * ad[i - 1] if i else 0)
    sat = ad / (ad + media * 1.5)
    contributo += roi * media * 2.2 * sat

df["promo_flag"] = (rng.random(n) < 0.12).astype(int)
df["prezzo_medio"] = (50 + 3 * np.sin(2 * np.pi * t / 52) + rng.normal(0, 1, n)).round(2)
base = 120000 + 400 * t + 25000 * np.sin(2 * np.pi * t / 52 + 1)
df["revenue"] = (base + contributo + 15000 * df["promo_flag"]
                 - 1500 * (df["prezzo_medio"] - 50) + rng.normal(0, 6000, n)).round(2)

out = sys.argv[1] if len(sys.argv) > 1 else "data/test/sintetico.csv"
df.to_csv(out, index=False)
print(f"Scritto {out}: {len(df)} settimane, {len(canali)} canali")
