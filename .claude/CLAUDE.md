# Uber Eats Mexico — ATD Analytics · Project Instructions

## Project Overview
Automation & Analytics Specialist take-home exercise.
Goal: analyse Actual Time of Delivery (ATD), build a predictive model,
and surface insights through a Streamlit dashboard.

## Repository Layout
```
app/                    Streamlit application (entry point: app/app.py)
  assets/               config.yaml (auth credentials)
  tools/
    home/               Home view
    dashboard/          ATD Analytics dashboard (3-layer architecture)
      data/             loader.py · cleaner.py
      services/         filters.py · metrics.py · aggregations.py
      views/            dashboard_view.py + 6 chart views + kpi_cards.py
data/
  raw/                  BC_A&A_with_ATD.csv  (~1 M trips, Mar–Apr 2025)
  processed/            preprocessed.parquet  (input to dashboard)
documents/              sql_query.md · adf_pipeline.md
notebooks/              01_eda … 05_business_insights
model/                  lgbm_atd_model.pkl · model_metadata.json
```

## Architecture Rules
- **3-layer**: `data/` → `services/` → `views/`. Never import a view
  from services, never import Streamlit from services or data layers.
- `loader.py` uses `@st.cache_data`. All heavy computation is cached.
- `aggregations.py` is pure pandas/numpy — zero Streamlit imports.

## Code Style
- Python 3.11, PEP 8, **max line length 79 chars** (Flake8 default).
- Type hints on all public functions; docstrings required.
- No wildcard imports.
- Run `flake8 tools/dashboard/` from `app/` before committing.

## Colours & Theme
- Primary green : `#06C167`
- Hover green   : `#04a557`
- Accent gold   : `#FFD700`
- Dark / text   : `#000000`
- SLA / alert   : `#FF4B4B`
- All Plotly figures: `plot_bgcolor` and `paper_bgcolor` = `#FFFFFF`,
  `font_color` = `#000000`.
- Sequential colorscale for encoded bars:
  `["#06C167", "#FFD700", "#000000"]`

## Data Conventions
- Mexico = UTC-6 year-round (DST abolished 2022).
- `hour_local = (restaurant_offered_timestamp_utc.hour + 6) % 24`
- ATD target variable is in **minutes**.
- SLA threshold = **45 min** (`SLA_THRESHOLD_MIN` in `metrics.py`).
- Outlier fence: Tukey 3×IQR with a hard floor of 120 min.

## KPI Card Formatting
- Counts ≥ 1 000 → K suffix  (e.g. `12.3K`)
- Counts ≥ 1 000 000 → M suffix (e.g. `1.2M`)
- ATD values: 1 decimal, unit in the label not the value string.
- WoW deltas shown on all cards; `delta_color="inverse"` for ATD metrics.

## Agents Available
| Agent | Trigger |
|-------|---------|
| `flake8-compliance` | Before any commit; after editing Python files |
| `ui-designer` | After adding or modifying any Plotly chart |
| `perf-optimizer` | When editing loader, cleaner, or aggregations |
| `docs-expert` | "document this", "write docs for", "update the README" |
