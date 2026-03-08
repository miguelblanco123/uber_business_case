# Uber Eats Mexico — ATD Analytics

Take-home exercise for the Uber Automation & Analytics Specialist role.

**Goal**: analyse Actual Time of Delivery (ATD) for Mexico Eats trips,
build a predictive model, and surface insights through an interactive
Streamlit dashboard.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [SQL Query — Weekly ATD Extraction](#2-sql-query--weekly-atd-extraction)
3. [App Architecture & Usage](#3-app-architecture--usage)
4. [Model Training Pipeline](#4-model-training-pipeline)
5. [Deployment](#5-deployment)

---

## 1. Project Overview

The project answers three questions:

| Layer | What it does |
|-------|-------------|
| **SQL** | Extracts a weekly snapshot of Mexico delivery trips with ATD in minutes |
| **Dashboard** | Filters, aggregates, and visualises ATD trends across time, courier flow, geography, and distance |
| **Predictor** | Trains and serves an XGBoost model that predicts ATD for individual trips |

**SLA threshold**: 45 minutes.
**Data**: ~1 M trips, March–April 2025 (`data/raw/BC_A&A_with_ATD.csv`).

---

## 2. SQL Query — Weekly ATD Extraction

**File**: `sql/sql_query.md`

![SQL Query Diagram](documents/Uber%20SQL%20Query%20Diagram.png)

### Purpose

Creates `AA_tables.delivery_atd_weekly` — a weekly snapshot of Mexico
delivery trips enriched with distances, ATD, and regional segmentation.
Designed to run in an Airflow DAG via the `{{ds}}` template variable.

### Source tables

| Table | Role |
|-------|------|
| `tmp.lea_trips_scope_atd_consolidation_v2` | Trip metadata (IDs, timestamps, courier flow, geo/merchant attributes) |
| `delivery_matching.eats_dispatch_metrics_job_message` | Dispatch metrics — pickup and travel distances; filtered to `isfinalplan = TRUE` and the target week window |
| `dwh.dim_city` | City dimension; filtered to `country_name = 'Mexico'` |
| `kirby_external_data.cities_strategy_region` | Adds region and territory segmentation |

### Key calculations

**ATD (minutes)**
```sql
DATE_DIFF(
    'second',
    t.eater_request_timestamp_local,
    t.order_final_state_timestamp_local
) / 60.0 AS ATD
```
Converts the difference between the UTC restaurant-offer timestamp and the
local final-state timestamp (adjusted +6 h for Mexico time) into minutes.

**Distances (km)**
```sql
d.pickupdistance  / 1000.0 AS pickup_distance,
d.traveldistance  / 1000.0 AS dropoff_distance
```

**Week window (Airflow)**
```sql
CAST(d.datestr AS DATE) >= DATE_TRUNC('week', DATE('{{ds}}') - INTERVAL '7' DAY)
AND CAST(d.datestr AS DATE) <  DATE_TRUNC('week', DATE('{{ds}}'))
```
Selects exactly the previous Monday–Sunday relative to the DAG run date.

### Output columns

`region`, `territory`, `country_name`, `workflow_uuid`, `driver_uuid`,
`delivery_trip_uuid`, `courier_flow`, `restaurant_offered_timestamp_utc`,
`order_final_state_timestamp_local`, `eater_request_timestamp_local`,
`geo_archetype`, `merchant_surface`, `pickup_distance`, `dropoff_distance`,
`ATD`

---

### Final Query

```sql
CREATE TABLE AA_tables.delivery_atd_weekly AS
SELECT
    csr.region,
    csr.territory,
    dc.country_name,
    t.workflow_uuid,
    t.driver_uuid,
    t.delivery_trip_uuid,
    t.courier_flow,
    t.restaurant_offered_timestamp_utc,
    t.order_final_state_timestamp_local,
    t.eater_request_timestamp_local,
    t.geo_archetype,
    t.merchant_surface,
    d.pickupdistance / 1000.0 AS pickup_distance,
    d.traveldistance / 1000.0 AS dropoff_distance,
    DATE_DIFF(
        'second',
        t.eater_request_timestamp_local,
        t.order_final_state_timestamp_local
    ) / 60.0 AS ATD
FROM tmp.lea_trips_scope_atd_consolidation_v2 t
JOIN delivery_matching.eats_dispatch_metrics_job_message d
    ON  t.workflow_uuid = d.jobuuid
    AND d.isfinalplan   = TRUE
    AND CAST(d.datestr AS DATE) >= DATE_TRUNC('week', DATE('{{ds}}') - INTERVAL '7' DAY)
    AND CAST(d.datestr AS DATE) < DATE_TRUNC('week', DATE('{{ds}}'))
JOIN dwh.dim_city dc
    ON  d.cityid = dc.city_id
    AND dc.country_name = 'Mexico'
JOIN kirby_external_data.cities_strategy_region csr
    ON dc.city_id = csr.city_id
```
```

## 3. App Architecture & Usage

### Repository layout

```
app/
  app.py                        # Entry point — authentication + routing
  assets/config.yaml            # bcrypt-hashed credentials
  tools/
    home/views/home_view.py     # Project walkthrough page
    dashboard/
      data/
        loader.py               # Parquet loading (@st.cache_data)
        cleaner.py              # Tukey 3×IQR outlier removal
      services/
        filters.py              # Multi-dimension row filtering
        metrics.py              # SLA KPIs (threshold = 45 min)
        aggregations.py         # All chart aggregations (pure pandas)
      views/
        dashboard_view.py       # Main orchestrator — 4 tabs + KPI cards
        kpi_cards.py            # Metric cards with WoW deltas
        sla_analysis.py         # Tab 1: Performance Overview
        time_analysis.py        # Tab 2: Time Patterns
        delivery_analysis.py    # Tab 3: Courier & Platform
        geo_analysis.py         # Tab 4: Geographic
        distance_analysis.py    # Tab 5: Distance Analysis
    predictor/
      data/loader.py            # Model & validation sample loading
      services/predict.py       # Inference logic (pure, no Streamlit)
      views/predictor_view.py   # Prediction UI
data/
  raw/                          # BC_A&A_with_ATD.csv (~1 M trips)
  processed/                    # preprocessed.parquet (dashboard input)
model/
  lgbm_atd_model.pkl            # LightGBM baseline
  xgb_top25_model.pkl           # XGBoost top-25 features (served)
  model_metadata.json           # Feature list, split dates, val metrics
predictor/                      # Retraining pipeline scripts
notebooks/                      # Jupyter notebooks 00–15 (EDA → export)
sql/                            # sql_query.md
```

### 3-layer architecture

```
Views  (Streamlit + Plotly)
  │  orchestrates rendering only
Services  (pure pandas / numpy)
  │  filters, metrics, aggregations — zero Streamlit imports
Data  (I/O + cleaning)
     loader.py reads parquet, derives hour_local; cleaner.py removes outliers
```

**Data layer**
- `loader.py`: reads parquet (local path or Azure Blob via `BLOB_SAS_URL`
  env var), derives `hour_local = (utc_hour + 6) % 24`, cached with
  `@st.cache_data`.
- `cleaner.py`: removes `\N` sentinels, drops rows with missing critical
  columns or ATD ≤ 0, applies Tukey 3×IQR outlier fence (hard floor 120 min).

**Services layer**
- `filters.py`: AND-logic boolean masking across territory, courier flow,
  geo archetype, and ATD range.
- `metrics.py`: computes 5 KPI scalars — total trips, SLA rate (%),
  mean ATD, median ATD, active drivers.
- `aggregations.py`: 20+ pure-pandas functions that power every chart
  (histograms, heatmaps, scatter samples, territory performance matrices,
  daily percentile bands, etc.).

**Views layer**
- `dashboard_view.py`: loads data, builds sidebar filters (week selector,
  territory, courier flow, geo archetype, ATD range slider), renders KPI
  cards with WoW deltas, and delegates to four tab views.

### Running the app

```bash
pip install -r requirements.txt
streamlit run app/app.py
```

Default credentials are in `app/assets/config.yaml`.

---

## 4. Model Training Pipeline

Scripts in `predictor/` map 1-to-1 with notebooks in `notebooks/`.
An orchestrator (`retrain.py`) runs them in order.

![Model Pipeline](documents/Model%20Pipeline.png)

### Pipeline steps

| Step | Script | What it does |
|------|--------|--------------|
| 10 | `step_10_data_cleaning.py` | Loads raw CSV, applies Tukey 3×IQR outlier removal, saves `data/processed/preprocessed.parquet` |
| 11 | `step_11_feature_engineering.py` | Engineers 51 features: temporal (hour, day, peak flag), distance (log-transforms, pickup/dropoff ratio), driver history (rolling 7 d/30 d MAE, SLA rate, trip count), territory/archetype medians, label-encoded categoricals |
| 12 | `step_12_train_test_split.py` | Temporal split — Train: Mar 1–30 (~800 K rows), Val: Mar 31–Apr 13 (~100 K), Test: Apr 14–27 (~90 K) |
| 12.5 | `step_12_5_normalization.py` | Fits `MinMaxScaler` on train numeric features, saves `model/minmax_scaler.pkl` |
| 13 | `step_13_model_training.py` | Trains LightGBM baseline on all 51 features |
| 13.2 | `step_13_2_xgboost_top_features.py` | Trains XGBoost (`reg:absoluteerror`) on top-N features selected by LightGBM gain importance (default N = 25) |
| 14 | `step_14_model_evaluation.py` | Evaluates both models on test set, logs MAE / RMSE / R² / MAPE |
| 15 | `step_15_model_export.py` | Serialises best model + metadata to `model/` |

### Model performance (validation set)

| Metric | Value |
|--------|-------|
| MAE | 9.83 min |
| RMSE | 13.70 min |
| R² | 0.36 |
| MAPE | 32.57 % |
| SLA threshold | 45 min |

The served model is **XGBoost with top-25 features** (`xgb_top25_model.pkl`).

### Retraining via CLI

```bash
# Full pipeline
python predictor/retrain.py

# Partial run (skip slow feature engineering)
python predictor/retrain.py --steps 12 13 13.2 14 15

# Change feature budget
python predictor/retrain.py --top-n 20

# Override data / model directories
python predictor/retrain.py --data-dir /mnt/data --model-dir /mnt/model
```

---

## 5. Deployment

### Local

```bash
pip install -r requirements.txt
streamlit run app/app.py
```

### Azure App Service

1. Push the repository to GitHub.
2. The GitHub Actions .yaml file located in `.github/` builds and deploys the package to Azure App Services. https://uber-business-case-mb.azurewebsites.net/

### Environment & configuration

| File | Purpose |
|------|---------|
| `.streamlit/config.toml` | Streamlit theme — primary `#06C167`, white background, black text |
| `app/assets/config.yaml` | bcrypt-hashed auth credentials |
| `BLOB_SAS_URL` env var | (Optional) Azure Blob Storage URL for remote parquet loading |
