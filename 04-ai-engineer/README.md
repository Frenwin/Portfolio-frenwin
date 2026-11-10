# Week 4 · AI Engineer — Ship intelligent features

> **Purpose of this week:** prove I can turn language and vision models into features that work outside a notebook: evaluated with numbers, served behind an API, and chosen with cost and latency in mind.

[← Week 3 · Data Scientist](../03-data-scientist/) · [Portfolio home](../README.md)

## Why this week matters

This is my core specialisation (NLP and computer vision). A demo that answers three questions well is easy; a system that answers hundreds correctly, cites its sources, refuses unsafe actions and runs fast enough on real hardware is the actual job. Every project here is measured, not just shown.

## The question this week answers

**"How do we turn a model into something people can use?"**

| Product need | Project | What makes it production-grade |
| --- | --- | --- |
| Answer questions from documents | **AI-1** RAG | Hybrid search, reranking, citations, an evaluation set |
| Let non-technical users query data | **AI-2** text-to-SQL agent | Read-only access, guardrails, tracing, execution accuracy |
| Classify Indonesian text cheaply | **AI-3** NLP fine-tuning | Accuracy vs latency vs cost across three approaches |
| Detect objects on limited hardware | **AI-4** edge detection | ONNX export, quantization, FPS benchmark on CPU |

## Projects

| # | Project | What it proves | Stack | Status |
| --- | --- | --- | --- | :---: |
| AI-1 | RAG over Indonesian regulations | Answers with article-level citations, scored on 30 test questions | Vector DB, BM25, reranker, FastAPI, Docker | ⬜ |
| AI-2 | Text-to-SQL analytics agent | A tool-calling agent that is safe on a real database, scored on 25 questions | LLM tool calling, PostgreSQL, tracing | ⬜ |
| AI-3 | Indonesian NLP fine-tuning | When prompting is enough and when fine-tuning pays off | Transformers, PEFT/LoRA, IndoBERT | ⬜ |
| AI-4 | Object detection on edge | A detector that runs in real time on CPU, with the accuracy trade-off measured | Ultralytics YOLO, ONNX Runtime, Gradio | ⬜ |

## Skills covered

| Skill | Where it is shown |
| --- | --- |
| Retrieval-augmented generation and vector search | AI-1 |
| Agents, tool calling and guardrails | AI-2 |
| Evaluating LLMs and models with test sets | AI-1, AI-2, AI-3 |
| Parameter-efficient fine-tuning (LoRA) | AI-3 |
| Computer vision and model optimisation | AI-4 |
| Serving and MLOps (FastAPI, Docker, CI) | all |

## How the four weeks come together

AI-2 queries the warehouse built in Week 1, using the metric definitions written in Week 2. That is the whole chain in one feature: reliable data → clear metrics → a model people can talk to.
