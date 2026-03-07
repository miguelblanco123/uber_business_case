# SQL Query — Weekly ATD Extraction for Mexico

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
        t.restaurant_offered_timestamp_utc,
        t.order_final_state_timestamp_local + INTERVAL '6' HOUR
    ) / 60.0 AS ATD
FROM tmp.lea_trips_scope_atd_consolidation_v2 t
JOIN delivery_matching.eats_dispatch_metrics_job_message d
    ON  t.workflow_uuid = d.jobuuid
    AND d.isfinalplan   = TRUE
    AND CAST(d.datestr AS DATE) >= DATE_TRUNC('week', DATE('{{ds}}') - INTERVAL '7' DAY)
    AND CAST(d.datestr AS DATE) <  DATE_TRUNC('week', DATE('{{ds}}'))
JOIN dwh.dim_city dc
    ON  d.cityid        = dc.city_id
    AND dc.country_name = 'Mexico'
JOIN kirby_external_data.cities_strategy_region csr
    ON dc.city_id = csr.city_id
```

## Column Sources

| Column | Source Table |
|---|---|
| `region` | `kirby_external_data.cities_strategy_region` |
| `territory` | `kirby_external_data.cities_strategy_region` |
| `country_name` | `dwh.dim_city` |
| `workflow_uuid` | `tmp.lea_trips_scope_atd_consolidation_v2` |
| `driver_uuid` | `tmp.lea_trips_scope_atd_consolidation_v2` |
| `delivery_trip_uuid` | `tmp.lea_trips_scope_atd_consolidation_v2` |
| `courier_flow` | `tmp.lea_trips_scope_atd_consolidation_v2` |
| `restaurant_offered_timestamp_utc` | `tmp.lea_trips_scope_atd_consolidation_v2` |
| `order_final_state_timestamp_local` | `tmp.lea_trips_scope_atd_consolidation_v2` |
| `eater_request_timestamp_local` | `tmp.lea_trips_scope_atd_consolidation_v2` |
| `geo_archetype` | `tmp.lea_trips_scope_atd_consolidation_v2` |
| `merchant_surface` | `tmp.lea_trips_scope_atd_consolidation_v2` |
| `pickup_distance` | `delivery_matching.eats_dispatch_metrics_job_message` (`pickupdistance / 1000`) |
| `dropoff_distance` | `delivery_matching.eats_dispatch_metrics_job_message` (`traveldistance / 1000`) |
| `ATD` | Computed — minutes between `restaurant_offered_timestamp_utc` and `order_final_state_timestamp_local` |

## ATD Formula

```
ATD (min) = (order_final_state_timestamp_local + 6h → UTC) − restaurant_offered_timestamp_utc
            expressed in minutes
```

`order_final_state_timestamp_local` is in Mexico local time (UTC−6), so adding 6 hours converts it
to UTC before subtracting the offer timestamp, which is already in UTC.
