"""Home view -- project walkthrough landing page."""
import os

import streamlit as st

_HERE = os.path.dirname(os.path.abspath(__file__))
_DIAGRAM = os.path.normpath(
    os.path.join(
        _HERE, "..", "..", "..", "..",
        "documents", "Uber SQL Query Diagram.png",
    )
)


def home_view(name: str) -> None:
    """Render the project walkthrough landing page.

    Walks through the three deliverables (SQL extraction,
    Streamlit dashboard, predictive model) and deployment.

    Args:
        name: Display name of the authenticated user.
    """
    st.title("Uber Eats Mexico -- ATD Analytics")
    st.markdown(f"Hey **{name}**, welcome.")
    st.markdown(
        "This app is a take-home exercise for Uber's Automation "
        "and Analytics team. Here is a quick walkthrough of how "
        "each part was built, from the SQL query all the way to "
        "the live dashboard running on Azure."
    )

    # ----------------------------------------------------------------
    # 1. SQL QUERY
    # ----------------------------------------------------------------
    st.markdown("---")
    st.header("1. Data Extraction")

    st.markdown(
        "The query pulls one week of Mexico delivery data from "
        "four tables and combines them into a single output."
    )

    st.markdown(
        "- **Trip records** and **dispatch metrics** are joined "
        "on `workflow_uuid = jobuuid`, filtered to "
        "`isfinalplan = TRUE`.\n"
        "- **`dwh.dim_city`** filters the results to Mexico.\n"
        "- **`cities_strategy_region`** adds territory and region "
        "for geographic breakdowns.\n"
        "- Distances come in metres and are divided by 1000 to "
        "get kilometres.\n"
        "- The date window uses Airflow's `{{ds}}` to always "
        "target the previous Monday-Sunday week automatically."
    )

    st.markdown(
        "ATD is the difference in minutes between the order's "
        "final state and when the eater placed the request. "
        "During EDA I computed it as "
        "`order_final_state_timestamp_local` minus "
        "`eater_request_timestamp_local` and got values identical "
        "to the pre-calculated ATD column across every row, so "
        "instead of going through `restaurant_offered_timestamp_utc` "
        "and handling the UTC-6 conversion, the dashboard just uses "
        "`eater_request_timestamp_local` directly as the start "
        "timestamp. When deriving the local hour, the UTC offset "
        "is applied per region rather than assuming a fixed UTC-6, "
        "since different parts of Mexico operate under different "
        "time zones."
    )

    st.subheader("Query diagram")
    if os.path.exists(_DIAGRAM):
        st.image(
            _DIAGRAM,
            caption="Join structure of the SQL query",
            use_container_width=True,
        )

    # ----------------------------------------------------------------
    # 2. STREAMLIT DASHBOARD
    # ----------------------------------------------------------------
    st.markdown("---")
    st.header("2. Streamlit Dashboard")

    st.subheader("CSV to Parquet")
    st.markdown(
        "The raw data came as a CSV file. Before the dashboard "
        "reads it, it gets converted to Parquet. Parquet is a "
        "columnar format, which means the app only reads the "
        "columns it actually needs instead of scanning every row "
        "of the whole file. On a dataset this size that makes a "
        "real difference in how fast the app starts up."
    )
    st.markdown(
        "After loading, the data goes through a cleaning step: "
        "it replaces `\\N` sentinel values with proper nulls, "
        "drops rows that are missing critical IDs or timestamps, "
        "removes trips with a zero or negative ATD, and applies "
        "a Tukey 3xIQR outlier fence with a hard cap of 120 "
        "minutes. The whole thing runs once per session and gets "
        "cached, so changing a filter does not reload the file."
    )

    st.markdown(
        "I also tested whether using `eater_request_timestamp_local` "
        "instead of the UTC column would change the ATD values -- "
        "it did not. Every single row matched perfectly:"
    )
    st.code(
        "                 ATD         ATD_2   ATD_diff\n"
        "count  1000000.0000  1000000.0000  1000000.0\n"
        "mean        40.1708       40.1708        0.0\n"
        "std         62.7542       62.7542        0.0\n"
        "min          0.0000        0.0000       -0.0\n"
        "5%          16.0167       16.0167        0.0\n"
        "25%         25.1167       25.1167        0.0\n"
        "50%         33.9333       33.9333        0.0\n"
        "75%         45.6833       45.6833        0.0\n"
        "95%         71.5667       71.5667        0.0\n"
        "99%        112.2333      112.2333        0.0\n"
        "max       8515.7000     8515.7000        0.0",
        language="text",
    )

    st.subheader("App structure")
    st.markdown(
        "The entry point is `app/app.py`, which handles "
        "authentication and routes the user to the correct page. "
        "Everything else lives under `app/tools/`, where each "
        "top-level folder is a self-contained page of the app:"
    )
    st.markdown(
        "- **`tools/home/`** -- this walkthrough page.\n"
        "- **`tools/dashboard/`** -- the ATD analytics dashboard.\n"
        "- **`tools/predictor/`** -- live ATD prediction on "
        "new trips using the trained model."
    )
    st.markdown(
        "Each tool follows the same internal structure to keep "
        "concerns separated:"
    )
    st.markdown(
        "- **`data/`** (`loader.py`, `cleaner.py`) -- reads the "
        "Parquet file, cleans it, and derives helper columns like "
        "`hour_local`, `day_name`, and `total_distance`. "
        "Heavy operations are cached with `@st.cache_data` so "
        "they only run once per session.\n"
        "- **`services/`** (`filters.py`, `metrics.py`, "
        "`aggregations.py`) -- all business logic and "
        "aggregations live here. This layer is pure pandas and "
        "numpy with zero Streamlit imports, which keeps it "
        "independently testable.\n"
        "- **`views/`** -- everything rendered to the screen. "
        "Views call services, services call data, never the "
        "other way around. The dashboard view is further split "
        "into one file per chart and a `kpi_cards.py` module "
        "so each visual can be worked on in isolation."
    )

    st.subheader("What is in the dashboard")
    st.markdown(
        "The sidebar lets you filter by week, territory, courier "
        "type, geo archetype, and ATD range. The main area has "
        "four tabs:"
    )
    st.markdown(
        "- **Performance Overview** -- SLA compliance against the "
        "45-minute threshold, ATD distribution, and a breakdown "
        "of breaches by territory and courier type.\n"
        "- **Time Patterns** -- hourly and day-of-week heatmaps "
        "that show when deliveries tend to be fast or slow.\n"
        "- **Courier and Platform** -- median ATD and volume by "
        "courier type and by the device the merchant used.\n"
        "- **Geographic** -- territory-level ATD, distance, and "
        "SLA comparisons."
    )
    st.markdown(
        "KPI cards at the top show the key numbers for the "
        "selected week alongside a week-over-week delta so it "
        "is easy to spot trends at a glance."
    )

    # ----------------------------------------------------------------
    # 3. PREDICTIVE MODEL
    # ----------------------------------------------------------------
    st.markdown("---")
    st.header("3. Predictive Model for ATD")

    st.markdown(
        "The goal is to predict ATD **before a trip completes** "
        "so operations can flag at-risk deliveries early. "
        "The model is trained on ~990 K historical Mexico trips "
        "from March–April 2025."
    )

    st.subheader("Algorithm — XGBoost (reg:absoluteerror)")
    st.markdown(
        "The deployed model is an **XGBoost** booster trained on the "
        "**top 25 features by LightGBM gain importance**. "
        "A full LightGBM model is first trained on all features to "
        "rank them; then XGBoost re-trains on only the top 25, "
        "producing a leaner model with near-identical accuracy."
    )
    st.markdown(
        "- **`reg:absoluteerror`** matches LightGBM's `regression_l1` "
        "— both minimise MAE, making the comparison fair and keeping "
        "the model robust to ATD's heavy right tail.\n"
        "- **Native categorical support** (`enable_categorical=True`) "
        "handles territory, courier flow, and geo archetype directly "
        "without one-hot encoding.\n"
        "- **Histogram-based splitting** (`tree_method=hist`) trains "
        "on ~800 K rows in minutes on a laptop CPU.\n"
        "- **25 features vs 49** — a 49% smaller feature set with "
        "only +0.06 min MAE compared to the full LightGBM model."
    )

    st.subheader("Feature Engineering (45 features)")
    st.markdown(
        "Features fall into four groups:"
    )
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            "**Time (6)**  \n"
            "`hour_local`, `day_of_week`, `is_weekend`, "
            "`is_peak_hour`, `week_number`, `month`, `time_block`"
            "\n\n"
            "**Distance (8)**  \n"
            "`pickup_distance`, `dropoff_distance`, "
            "`total_distance`, `distance_ratio`, log transforms, "
            "`is_long_trip`"
        )
    with col2:
        st.markdown(
            "**Driver history (16)**  \n"
            "All-time, 30-day, and 7-day expanding/rolling "
            "averages of ATD, SLA rate, and trip count per driver. "
            "Computed with `.expanding().shift(1)` so each row "
            "only sees past trips — no leakage."
            "\n\n"
            "**Encoding (15)**  \n"
            "Category codes + target-encoded medians for "
            "territory, geo archetype, and two interaction "
            "encodings (territory × flow, territory × hour)."
        )

    st.subheader("Training Setup")
    st.markdown(
        "The dataset is split **chronologically** to avoid "
        "future leakage:"
    )
    st.markdown(
        "| Split | Period | Size |\n"
        "|-------|--------|------|\n"
        "| Train | Mar 1 – Mar 30 | ~800 K trips |\n"
        "| Val   | Mar 31 – Apr 13 | ~100 K trips |\n"
        "| Test  | Apr 14 – Apr 27 | ~90 K trips |"
    )
    st.markdown(
        "Target-encoded features (territory median ATD, etc.) "
        "are computed on train-only and mapped to val/test, "
        "with unseen categories filled by the train global median."
    )
    st.markdown(
        "Training uses `num_boost_round=5000` with early stopping "
        "on val MAE (patience 100 rounds) and `learning_rate=0.02` "
        "to allow the model enough rounds to converge."
    )

    st.subheader("Model Selection Process")
    st.markdown(
        "Two models were trained and compared on the same "
        "held-out validation set:"
    )
    st.markdown(
        "| Model | Features | Val MAE | Val RMSE | Val R² |\n"
        "|-------|----------|---------|----------|--------|\n"
        "| LightGBM (all features) | 49 | 9.84 min | 13.78 min | 0.354 |\n"
        "| **XGBoost top-25** *(deployed)* | **25** | **9.90 min** | **13.65 min** | **0.366** |\n"
        "| Baseline (global mean) | — | ~13.1 min | — | — |"
    )
    st.caption(
        "XGBoost was chosen: it uses half the features, has a "
        "marginally better R², and closes the RMSE gap — "
        "at the cost of only +0.06 min MAE vs LightGBM."
    )

    st.subheader("Performance")
    st.code(
        "Metric              XGBoost top-25\n"
        "──────────────────────────────────\n"
        "Val MAE              9.90 min\n"
        "Val RMSE            13.65 min\n"
        "Val R²               0.366\n"
        "Best iteration       662\n"
        "Features used         25\n"
        "SLA threshold         45 min",
        language="text",
    )
    st.caption(
        "An R² of ~0.37 reflects substantial irreducible noise in ATD "
        "(traffic, restaurant prep time, driver behaviour) that no "
        "model can capture without real-time signals. Even so, the "
        "model reduces MAE by ~25% vs the best rule-based baseline."
    )

    st.subheader("Try it live")
    st.markdown(
        "Go to **ATD Predictor** in the sidebar to select trips "
        "from the validation set and see the model's predictions "
        "versus the actual ATD values."
    )

    # ----------------------------------------------------------------
    # 4. DEPLOYMENT
    # ----------------------------------------------------------------
    st.markdown("---")
    st.header("4. Deployment")

    st.markdown(
        "The app runs on an Azure App Service on a B1 tier "
        "instance. Nothing fancy, but it handles a Streamlit app "
        "of this size without any issues."
    )
    st.markdown(
        "Deployments go through GitHub Actions. Every commit to "
        "`main` kicks off a workflow that installs dependencies, "
        "runs Flake8 to catch anything broken, and pushes the "
        "build to the App Service automatically. No manual steps, "
        "no clicking through the Azure portal. Just push and "
        "the live app updates on its own a couple minutes later."
    )
    st.markdown(
        "That short feedback loop was really useful during "
        "development. Fix something, push it, and you can see "
        "the result live almost immediately."
    )
