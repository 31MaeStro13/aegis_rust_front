# 📑 Aegis Wealth Terminal • Quant & ML Engineering Specification

**Target Role:** Quantitative Financial Analyst / ML Engineer (MSc Dotun)  
**Deliverable Format:** Technical memo (Markdown / PDF) + Jupyter Notebook (`.ipynb`) with reproducible data pipelines.  
**Domain:** Wealth Management & Multi-Asset Portfolio Risk Analytics (B2B SaaS / On-Premise)

---

## Executive Summary
**Aegis Wealth Terminal** is an enterprise-grade portfolio management and stress-testing workstation tailored for private wealth advisors, family offices, and Tier-2/3 investment brokers. The core analytical engine operates under a **Zero-Calculation LLM Architecture**: all financial formulas, risk matrices, and Monte Carlo trajectories are deterministically calculated by a compiled analytical core (Python/Rust), while machine learning models are strictly bounded to unstructured data extraction, document layout understanding, and conversational summarization.

---

## 🎯 Phase 1: Financial Model Audit & Domain Discovery (Priority #1)

### 1.1. Current Calculation Core Overview
Our deterministic engine currently implements the following portfolio metrics:

* **Herfindahl-Hirschman Index (HHI):**
  $$HHI = \sum_{i=1}^{N} w_i^2 \quad (w_i \in [0, 100])$$
  *Risk Categorization Thresholds:*
  * $HHI < 1500$: Low concentration risk (Well-diversified)
  * $1500 \le HHI \le 2500$: Moderate concentration risk
  * $HHI > 2500$: High concentration risk (Critical single-asset exposure)

* **Sharpe Ratio:**
  $$\text{Sharpe} = \frac{R_p - R_f}{\sigma_p}$$
  *Current Baseline:* Risk-free rate $R_f$ is pegged to the Central Bank of Russia benchmark key rate ($19.0\%$ annual).

* **Historical Volatility & Maximum Drawdown (MDD):**
  $$\sigma_{\text{ann}} = \sigma_{\text{daily}} \times \sqrt{252}$$
  $$\text{MDD} = \max_{t} \left( \frac{\text{Peak}_t - \text{Trough}_t}{\text{Peak}_t} \right)$$

* **Deterministic Stress Testing Scenario:**
  Simulates a systemic $-15\%$ equity shock while preserving protective capital (sovereign bonds / cash), and models reallocation into floating-rate sovereign notes (OFZ-PK) yielding $R_f$.

---

### 1.2. Required Deliverables for Phase 1:

1. **Gap Analysis & Metric Expansion:**
   * What critical mathematical and risk metrics are indispensable for private wealth advisors managing High-Net-Worth Individuals (HNWI)?
   * *Required evaluations:*
     * **Value-at-Risk (VaR):** Parametric vs. Historical VaR ($95\%$ and $99\%$ 1-day / 10-day horizons) and Conditional Value-at-Risk (CVaR / Expected Shortfall).
     * **Sortino Ratio & Downside Deviation:** Isolating downside tail risk without penalizing upside volatility.
     * **Systematic Risk ($\beta$):** Asset and portfolio beta relative to the benchmark index (MOEX Russia Total Return Index `MCFTR`).
     * **Fixed Income Analytics:** Modified Duration, Effective Duration, and Yield to Maturity (YTM) for bond-heavy conservative allocations.

2. **Edge Cases & Data Integrity Protocol:**
   * Provide mathematical and programmatic guidelines on handling:
     * Illiquid OTC instruments and unlisted assets with stale pricing.
     * Asynchronous price series and missing trading days across asset classes.
     * Negative cash balances (broker margin loans / leverage financing).
     * Corporate actions (stock splits, consolidations, spin-offs) and dividend reinvestment assumptions.

3. **Executive PDF Audit Report Blueprint:**
   * Propose a standard institutional 2-page executive portfolio audit sheet structure compliant with Basel III and Central Bank advisory standards (Asset Allocation Pie, Risk Thermometer, Top-5 Holdings Concentration, Scenario Stress Table).

---

## 🤖 Phase 2: Smart Ingestion AI (Data Normalization Pipeline) (Priority #2)

### 2.1. The Business Problem
Brokerage statements arrive in non-standardized, volatile tabular formats:
* Arbitrary and localized column headers (`"Тикер"`, `"Инструмент"`, `"Symbol"`, `"ISIN"`, `"Код актива"`).
* Complex multi-row merged cells, multi-currency cash balances, metadata banners, and variable decimal/date formats.
* Hardcoded heuristic regex/pandas parsers break whenever a broker alters their export schema.

### 2.2. The Target Output (`PositionDTO`)
Every raw tabular extract must be deterministically parsed and normalized into our canonical JSON schema:

```json
{
  "ticker": "SBER",
  "name": "Sberbank PJSC",
  "instrument_type": "share",
  "quantity": 1500.0,
  "current_price": 280.5,
  "total_value": 420750.0,
  "weight": 28.5,
  "currency": "RUB"
}
```

*Valid `instrument_type` enumerations:* `["share", "bond", "etf", "currency", "other"]`.

---

### 2.3. ML Engineering Roadmap:

1. **Synthetic Tabular Data Synthesis:**
   * Build a generator script producing 100+ messy, realistic financial statement variations (CSV/XLSX) incorporating real-world artifacts (merged cells, multi-currency sections, empty rows, trailing totals) paired with ground truth `PositionDTO` labels.

2. **Small Language Model (SLM) Benchmarking:**
   * Evaluate lightweight local models capable of fast CPU / low-VRAM on-premise execution (e.g., `Qwen-2.5-Coder-1.5B-Instruct`, `Llama-3.2-1B-Instruct`, or document-layout vision models).
   * Benchmark parsing latency, memory footprint, and format adherence.

3. **Fine-Tuning / LoRA Pipeline:**
   * Set up a training harness using PyTorch, Hugging Face `transformers`, and `peft` (LoRA/QLoRA).
   * Target: **$>98\%$ deterministic field extraction accuracy** and $100\%$ valid JSON syntax constrained by our Pydantic schema.

---

## 🛠️ Repository & Environment Setup

* **External Development Workspace:** `https://github.com/31MaeStro13/aegis_rust_front`
* **Local Backend API Reference:** `docs/FRONTEND_API.md`
* **Rust Computation Engine Spec:** `docs/RUST_CORE_SPEC.md`
* **Python Runtime:** Python 3.12 (managed via `uv`), PyTorch, Pandas, Scipy, Scikit-learn.
