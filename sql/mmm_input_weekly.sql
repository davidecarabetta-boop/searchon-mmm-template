-- Vista standard di input MMM (una per cliente).
-- Una riga per settimana, solo dati aggregati, nessun dato personale.
-- Copiare, adattare le CTE alle sorgenti del cliente e creare la vista:
--   bq query --use_legacy_sql=false < sql/mmm_input_weekly.sql
--
-- Convenzioni (vedi docs/03_schema_dati.md):
--   settimana             DATE, lunedì della settimana (ISO), nessun buco
--   <kpi>                 es. revenue o conversioni, >= 0
--   spend_<canale>        spesa del canale nella settimana, valuta del cliente, >= 0
--   impr_<canale>         impression del canale (consigliate), >= 0
--   controlli             variabili non media: promo, prezzo, festività, ecc.

CREATE OR REPLACE VIEW `PROGETTO.mmm.mmm_input_weekly` AS
WITH
calendario AS (
  SELECT settimana
  FROM UNNEST(GENERATE_DATE_ARRAY(DATE '2023-01-02', DATE_TRUNC(CURRENT_DATE(), ISOWEEK) - 7, INTERVAL 1 WEEK)) AS settimana
),
kpi AS (
  -- es. ricavi da GA4 export o da gestionale
  SELECT DATE_TRUNC(data_ordine, ISOWEEK) AS settimana, SUM(ricavo) AS revenue
  FROM `PROGETTO.DATASET.ordini`
  GROUP BY 1
),
google_ads AS (
  SELECT DATE_TRUNC(segments_date, ISOWEEK) AS settimana,
         SUM(metrics_cost_micros) / 1e6 AS spend_google_search,
         SUM(metrics_impressions) AS impr_google_search
  FROM `PROGETTO.google_ads.p_ads_CampaignBasicStats_XXXXXXXXXX`
  GROUP BY 1
),
meta AS (
  SELECT DATE_TRUNC(date_start, ISOWEEK) AS settimana,
         SUM(spend) AS spend_meta,
         SUM(impressions) AS impr_meta
  FROM `PROGETTO.meta_ads.insights`
  GROUP BY 1
),
controlli AS (
  SELECT settimana,
         MAX(promo_attiva) AS promo_flag
  FROM `PROGETTO.DATASET.calendario_promo`
  GROUP BY 1
)
SELECT
  c.settimana,
  COALESCE(k.revenue, 0) AS revenue,
  COALESCE(g.spend_google_search, 0) AS spend_google_search,
  COALESCE(g.impr_google_search, 0) AS impr_google_search,
  COALESCE(m.spend_meta, 0) AS spend_meta,
  COALESCE(m.impr_meta, 0) AS impr_meta,
  COALESCE(x.promo_flag, 0) AS promo_flag
FROM calendario c
LEFT JOIN kpi k USING (settimana)
LEFT JOIN google_ads g USING (settimana)
LEFT JOIN meta m USING (settimana)
LEFT JOIN controlli x USING (settimana)
ORDER BY c.settimana;
