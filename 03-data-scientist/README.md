# Week 3 · Data Scientist — Decide what to do next

> **Purpose of this week:** prove I can go beyond describing the past: test whether a change really works, predict what will happen, and measure cause and effect, always tied to a business decision.

[← Week 2 · Data Analyst](../02-data-analyst/) · [Portfolio home](../README.md) · [Next: Week 4 · AI Engineer →](../04-ai-engineer/)

## Why this week matters

Analysis shows that two things move together; data science asks whether one *causes* the other and what to do about it. A wrong answer is expensive: shipping a feature that does not help, lending to customers who will default, or sending promos to people who would have bought anyway. Every project here ends with a decision and the cost of getting it wrong.

## The question this week answers

**"Did this change work, and what will happen if we act?"**

| Decision | Project | Method |
| --- | --- | --- |
| Should we ship this change? | **DS-1** A/B test | Randomised experiment with proper statistics |
| Should we approve this loan? | **DS-2** credit risk | Prediction with a threshold set by expected loss |
| How much stock do we need? | **DS-3** forecasting | Time series models backtested against a baseline |
| Who should receive the promo? | **DS-4** uplift | Causal ML that targets people the promo actually persuades |

## Projects

| # | Project | What it proves | Stack | Status |
| --- | --- | --- | --- | :---: |
| DS-1 | A/B test, end to end | Experiment design, power analysis, SRM check, frequentist and Bayesian tests, CUPED | SciPy, Statsmodels, Streamlit | ⬜ |
| DS-2 | Credit risk scoring | Calibrated predictions, SHAP explanations, a threshold chosen by business cost | LightGBM, SHAP, MLflow | ⬜ |
| DS-3 | Retail demand forecasting | Rolling-origin backtests and honest comparison with a naive baseline | LightGBM, statsforecast | ⬜ |
| DS-4 | Marketing uplift modeling | Qini curves and profit from targeting only persuadable customers | causalml / scikit-uplift | ⬜ |

## Skills covered

| Skill | Where it is shown |
| --- | --- |
| Experimental design and A/B testing | DS-1 |
| Statistical inference (frequentist and Bayesian) | DS-1 |
| Supervised ML with explainability | DS-2 |
| Evaluation by business cost, not only accuracy | DS-2, DS-4 |
| Time series forecasting | DS-3 |
| Causal inference and uplift | DS-1, DS-4 |

## What this week hands to the next

Models are evaluated and explained, but they still live in notebooks and reports. Week 4 is about putting models into products that run reliably.
