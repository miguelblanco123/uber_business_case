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
