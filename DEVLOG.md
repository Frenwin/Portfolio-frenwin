# Devlog

Daily progress log, newest entries at the bottom. Each entry is added by `scripts/daily-push.ps1`.

## 2026-11-10

- Set up portfolio repository: roadmap, role folders, project template and daily push script
- DE-1: done - Airflow + dbt ELT, 1.55M rows, 70 tests, SCD2 customers, CI
- Docs: rewrote portfolio home and week overviews to explain the purpose of each role

## 2026-11-12

- DE-2: done - Delta lakehouse on S3, 9.55M trips, MERGE redesign cut silver 674s to 256s
- DE-3: done - Kafka + Spark streaming, exactly-once 178,736/178,736 rides, crash-tested, Grafana

## 2026-11-13

- DE-4: done - Debezium CDC, 0.52s replica lag, checksum-identical after deletes + schema change, order status SCD2. Week 1 complete
