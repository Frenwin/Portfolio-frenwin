<div align="center">

# Data & AI Portfolio — 16 Projects in 4 Weeks

**Frenwin** · Data Science @ Telkom University · AI Engineer (NLP & Computer Vision)

[![Progress](https://img.shields.io/badge/progress-1%20of%2016%20projects-2ea44f)](#progress)
[![Built in public](https://img.shields.io/badge/built%20in%20public-daily%20commits-blue)](DEVLOG.md)
[![License: MIT](https://img.shields.io/badge/license-MIT-lightgrey)](LICENSE)

[LinkedIn](https://www.linkedin.com/in/frenwin) · [Website](https://frenwin.vercel.app/) · [Roadmap](ROADMAP.md) · [Devlog](DEVLOG.md)

</div>

---

## Why this portfolio exists

Most portfolios show a single model in a notebook. Real data work is a chain: data has to be **collected and trusted**, then **explained**, then used to **make decisions**, and finally turned into **products**. If one link is weak, everything after it is wrong.

This repository walks that chain **one role per week**. Each project takes one to two days, uses tools that data teams actually run, and ships with runnable code, tests or evaluation, and results with real numbers.

## The four weeks at a glance

```mermaid
flowchart LR
    W1["<b>Week 1 · Data Engineer</b><br/>Make data reliable"] --> W2["<b>Week 2 · Data Analyst</b><br/>Explain what happened"]
    W2 --> W3["<b>Week 3 · Data Scientist</b><br/>Decide what to do next"]
    W3 --> W4["<b>Week 4 · AI Engineer</b><br/>Ship intelligent features"]
```

| Week | Role | Purpose | The question it answers |
| :---: | --- | --- | --- |
| 1 | [Data Engineer](01-data-engineer/) | **Make data reliable**: move, model and test data so everyone downstream can trust it | *Is the data correct, complete and on time?* |
| 2 | [Data Analyst](02-data-analyst/) | **Explain what happened**: turn tables into metrics, dashboards and recommendations | *What is happening in the business, and why?* |
| 3 | [Data Scientist](03-data-scientist/) | **Decide what to do next**: test changes, predict outcomes, measure cause and effect | *Did this change work, and what will happen if we act?* |
| 4 | [AI Engineer](04-ai-engineer/) | **Ship intelligent features**: put language and vision models into products that are evaluated and deployed | *How do we turn a model into something people can use?* |

## Progress

**1 of 16 projects done** · `█░░░░░░░░░░░░░░░` · daily log in [DEVLOG.md](DEVLOG.md)

Status: ✅ Done · 🔄 In progress · ⬜ Planned

### Week 1 · Data Engineer — make data reliable

| # | Project | What it proves | Status |
| --- | --- | --- | :---: |
| DE-1 | [**Batch ELT to a star-schema warehouse**](01-data-engineer/de-01-elt-airflow-dbt/) | Orchestrated, idempotent pipeline with Airflow + dbt, 70 data tests, SCD2, CI | ✅ |
| DE-2 | Lakehouse with bronze/silver/gold layers | Large-file processing with PySpark and Delta Lake | ⬜ |
| DE-3 | Real-time streaming pipeline | Event processing with Kafka and Spark Structured Streaming | ⬜ |
| DE-4 | Change Data Capture | Replicating a live database with Debezium | ⬜ |

### Week 2 · Data Analyst — explain what happened

| # | Project | What it proves | Status |
| --- | --- | --- | :---: |
| DA-1 | SQL business case study | Answering business questions with CTEs and window functions | ⬜ |
| DA-2 | Executive sales dashboard | Data modeling and DAX in Power BI | ⬜ |
| DA-3 | Product funnel & cohort retention | Product analytics on real GA4 data | ⬜ |
| DA-4 | Customer segmentation + insight deck | RFM segments turned into a campaign recommendation | ⬜ |

### Week 3 · Data Scientist — decide what to do next

| # | Project | What it proves | Status |
| --- | --- | --- | :---: |
| DS-1 | A/B test, end to end | Experiment design, power analysis, SRM checks, CUPED | ⬜ |
| DS-2 | Credit risk scoring | Explainable ML with a threshold set by business cost | ⬜ |
| DS-3 | Retail demand forecasting | Time series models backtested against a baseline | ⬜ |
| DS-4 | Marketing uplift modeling | Targeting customers who change behaviour because of a promo | ⬜ |

### Week 4 · AI Engineer — ship intelligent features

| # | Project | What it proves | Status |
| --- | --- | --- | :---: |
| AI-1 | RAG over Indonesian regulations | Retrieval with citations, measured by an evaluation set | ⬜ |
| AI-2 | Text-to-SQL analytics agent | Tool-calling agent with guardrails and tracing | ⬜ |
| AI-3 | Indonesian NLP fine-tuning | Prompting vs IndoBERT vs LoRA on accuracy, latency and cost | ⬜ |
| AI-4 | Object detection on edge | YOLO exported to ONNX and benchmarked on CPU | ⬜ |

## Latest highlight — DE-1

> Loads **1.55M rows** from 9 raw files into a tested star-schema warehouse in **~30 seconds**, re-runs without duplicating data, and runs **70 data tests** on every build.

- Found that `review_id` in the source is not unique and that **252 customers changed address**; both are modeled correctly instead of silently breaking joins.
- The cleaned model already shows a business signal: **late orders average a 2.27 review score versus 4.29 when delivered on time.**
- One command to run (`docker compose up`), CI on every push.

[Read the project →](01-data-engineer/de-01-elt-airflow-dbt/)

## What you will find in every project

| Section | Why it is there |
| --- | --- |
| **Problem** | The business reason the project matters |
| **Architecture / approach** | A diagram of how it works and why these tools were chosen |
| **Results** | A table of real numbers, compared with a baseline where it applies |
| **How to run** | Five commands or fewer from a fresh clone |
| **Key decisions** | Trade-offs, so a reviewer can see the reasoning, not only the code |
| **Limitations & next steps** | What is not solved yet, stated plainly |

## Repository structure

```text
.
├── 01-data-engineer/     Week 1 projects
├── 02-data-analyst/      Week 2 projects
├── 03-data-scientist/    Week 3 projects
├── 04-ai-engineer/       Week 4 projects
├── templates/            README template used by every project
├── scripts/              new-project and daily-push helpers
├── ROADMAP.md            the full 4-week plan (Bahasa Indonesia)
└── DEVLOG.md             what was done each day
```

## License

Code is [MIT](LICENSE). Datasets keep their own licenses, listed in each project.
