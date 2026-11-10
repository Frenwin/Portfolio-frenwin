# Data & AI Portfolio — 16 Projects in 4 Weeks

> One project every 1–2 days across four roles: **Data Engineer → Data Analyst → Data Scientist → AI Engineer**.
> 16 Nov – 13 Dec 2026 · Built in public, pushed daily.

**Frenwin** — Data Science, Telkom University · AI Engineer (NLP & Computer Vision)
[LinkedIn](https://www.linkedin.com/in/frenwin) · [Website](https://frenwin.vercel.app/)

- Full plan: [ROADMAP.md](ROADMAP.md)
- Daily progress: [DEVLOG.md](DEVLOG.md)

## Progress

| # | Week | Project | Key skills | Status |
| --- | --- | --- | --- | --- |
| DE-1 | 1 | [Batch ELT to a star-schema warehouse](01-data-engineer/de-01-elt-airflow-dbt/) | Airflow, dbt, PostgreSQL, SCD2, CI | Done |
| DE-2 | 1 | [Lakehouse medallion](01-data-engineer/) | PySpark, Delta Lake | Planned |
| DE-3 | 1 | [Real-time streaming pipeline](01-data-engineer/) | Kafka, Spark Streaming, Grafana | Planned |
| DE-4 | 1 | [Change Data Capture](01-data-engineer/) | Debezium, Kafka Connect | Planned |
| DA-1 | 2 | [SQL business case study](02-data-analyst/) | Window functions, CTE, BigQuery | Planned |
| DA-2 | 2 | [Executive sales dashboard](02-data-analyst/) | Power BI, DAX | Planned |
| DA-3 | 2 | [Product funnel & cohort retention](02-data-analyst/) | GA4, funnel, cohort | Planned |
| DA-4 | 2 | [Customer segmentation + insight deck](02-data-analyst/) | RFM, clustering, storytelling | Planned |
| DS-1 | 3 | [A/B test end-to-end](03-data-scientist/) | Power analysis, SRM, CUPED | Planned |
| DS-2 | 3 | [Credit risk scoring](03-data-scientist/) | LightGBM, SHAP, calibration | Planned |
| DS-3 | 3 | [Retail demand forecasting](03-data-scientist/) | Time series CV, LightGBM | Planned |
| DS-4 | 3 | [Marketing uplift modeling](03-data-scientist/) | Causal ML, Qini curve | Planned |
| AI-1 | 4 | [Production RAG on Indonesian regulations](04-ai-engineer/) | Hybrid search, reranker, RAG eval | Planned |
| AI-2 | 4 | [Text-to-SQL analytics agent](04-ai-engineer/) | Tool calling, guardrails, tracing | Planned |
| AI-3 | 4 | [Indonesian NLP fine-tuning](04-ai-engineer/) | LoRA/PEFT, IndoBERT | Planned |
| AI-4 | 4 | [Object detection on edge](04-ai-engineer/) | YOLO, ONNX, benchmarking | Planned |

Status: `Planned` → `In progress` → `Done`. Each project folder has its own README with results, how to run, and a demo.

## Repository structure

```text
.
├── 01-data-engineer/     # Week 1 projects
├── 02-data-analyst/      # Week 2 projects
├── 03-data-scientist/    # Week 3 projects
├── 04-ai-engineer/       # Week 4 projects
├── templates/            # README template for new projects
├── scripts/              # new-project and daily-push helpers
├── ROADMAP.md
└── DEVLOG.md
```

## License

[MIT](LICENSE)
