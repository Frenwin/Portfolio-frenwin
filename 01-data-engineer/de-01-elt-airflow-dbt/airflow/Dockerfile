FROM apache/airflow:2.10.5-python3.11

# dbt lives in its own virtualenv so its dependencies never conflict with Airflow's.
RUN python -m venv /home/airflow/dbt_venv \
    && /home/airflow/dbt_venv/bin/pip install --no-cache-dir dbt-core==1.12.6 dbt-postgres==1.11.0

ENV DBT_BIN=/home/airflow/dbt_venv/bin/dbt
