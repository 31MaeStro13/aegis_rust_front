# 📦 Phase 1 Onboarding Data, Technical Architecture & Benchmark Contracts

**Engineer:** MSc Dotun (Quantitative Financial Analyst & ML Engineer)  
**Project:** Aegis Wealth Terminal (B2B SaaS / On-Premise)  
**Assigned Workspace:** `research/` in `https://github.com/31MaeStro13/aegis_rust_front`

---

## 💬 1. Formal Answers to Your 5 Inquiries

### Question 1: Deliverable Sequencing
* **Answer:** **Yes, strictly complete Phase 1 before advancing to Phase 2.**
* *Rationale:* The mathematical formulas, risk thresholds (VaR, CVaR, Sortino, Duration), and the 2-page executive report blueprint you design in Phase 1 directly dictate the UI cards that the frontend developer (Nikita) and UI designer (Taya) will render.
* *Phase 1 Target Output:* A comprehensive Technical Memo (Markdown/PDF) + a reproducible Jupyter Notebook (`.ipynb`) computing these metrics on the benchmark datasets below.

### Question 2: PositionDTO Schema & Sample Portfolios
* **Answer:** Fully documented below in **Section 2 & 3**. You are provided with:
  1. The canonical Python Pydantic schema for `PositionDTO`.
  2. Three heterogeneous portfolio datasets (Conservative OFZ, Balanced Multi-Asset, and High-Concentration Aggressive).
  3. Ground truth mathematical metrics for baseline verification.

### Question 3: Backend & ML Integration Architecture
* **Answer:** Detailed in **Section 5 (Backend ↔ ML Interface Contract)**.
  * You do not write Django code.
  * Your deliverable for Phase 2 is an isolated **FastAPI Microservice (Sidecar container)** exposing `POST /api/v1/normalize-statement`.
  * The main Django backend communicates with your service via HTTP REST inside the Docker network.

### Question 4: Baseline Parser & Model Constraints
* **Answer:**
  * **Baseline:** Rule-based Pandas heuristic column-matching parser (see **Section 4**).
  * **SLM Preference & Hardware Limits:** Detailed in **Section 6**. Target models must run on standard commodity Linux **CPU (Max 4 GB RAM, < 3.0s latency per statement)** using quantized GGUF (`llama.cpp`) or ONNX Runtime. No enterprise GPUs required.

### Question 5: Timeline & Acceptance Criteria
* **Deadline for Phase 1:** **7 business days** from kickoff.
* **Acceptance Criteria:**
  1. **Mathematical Rigor:** Clear definitions and Python implementations for Historical/Parametric VaR (95%/99%), Expected Shortfall (CVaR), Sortino Ratio, Portfolio Beta ($\beta$ vs. MOEX Total Return Index `MCFTR`), and Bond Modified Duration / YTM.
  2. **Edge Case Protocol:** Actionable methodology for handling stale OTC pricing, illiquid assets, missing trading days, and margin cash deficits.
  3. **2-Page Executive Blueprint:** Visual wireframe or layout proposal for a C-suite client portfolio audit PDF.

---

## 📐 2. Canonical Data Contract: `PositionDTO`

Every raw financial asset extracted from any broker file must conform strictly to this Pydantic model:

```python
from decimal import Decimal
from typing import Literal, Optional
from pydantic import BaseModel, Field

AssetClass = Literal["share", "bond", "etf", "currency", "other"]

class PositionDTO(BaseModel):
    ticker: str = Field(..., description="Exchange ticker symbol, e.g., SBER, SU26238RMFS4")
    name: str = Field(..., description="Full legal name of the asset")
    asset_class: AssetClass = Field(default="other", description="Standard asset category")
    quantity: Decimal = Field(..., ge=0, description="Number of lots or units held")
    current_price: Decimal = Field(..., ge=0, description="Current market price in quote currency")
    total_value: Decimal = Field(default=Decimal("0.0"), description="quantity * current_price")
    weight: float = Field(default=0.0, ge=0.0, le=100.0, description="Portfolio allocation percentage [0, 100]")
    currency: str = Field(default="RUB", description="ISO 4217 currency code")
    average_price: Optional[Decimal] = Field(None, description="Acquisition purchase price")
    expected_yield: Optional[float] = Field(None, description="Annual coupon or dividend yield in %")
```

---

## 📊 3. Ground Truth Benchmark Datasets for Phase 1 Testing

### Dataset A: High-Concentration Retail Portfolio (High Risk)
*Profile: Heavily skewed into Russian equities, dangerously high HHI.*

```json
[
  {
    "ticker": "SBER",
    "name": "Sberbank PJSC",
    "asset_class": "share",
    "quantity": 15000,
    "current_price": 305.50,
    "total_value": 4582500.00,
    "weight": 45.825,
    "currency": "RUB"
  },
  {
    "ticker": "GAZP",
    "name": "Gazprom PJSC",
    "asset_class": "share",
    "quantity": 20000,
    "current_price": 130.20,
    "total_value": 2604000.00,
    "weight": 26.040,
    "currency": "RUB"
  },
  {
    "ticker": "LKOH",
    "name": "Lukoil PJSC",
    "asset_class": "share",
    "quantity": 300,
    "current_price": 6850.00,
    "total_value": 2055000.00,
    "weight": 20.550,
    "currency": "RUB"
  },
  {
    "ticker": "RUB",
    "name": "Russian Ruble Cash",
    "asset_class": "currency",
    "quantity": 758500,
    "current_price": 1.00,
    "total_value": 758500.00,
    "weight": 7.585,
    "currency": "RUB"
  }
]
```
* **Total Portfolio Value:** `10,000,000.00 RUB`
* **Baseline Deterministic HHI:**
  $$HHI = 45.825^2 + 26.04^2 + 20.55^2 + 7.585^2 = 2099.93 + 678.08 + 422.30 + 57.53 = \mathbf{3257.84} \quad (\text{High Risk} > 2500)$$
* **Baseline Stress Test ($-15\%$ Equity Shock):**
  * Equities value: `9,241,500.00 RUB` $\times 0.15 =$ **$-1,386,225.00$ RUB loss**
  * Protective Capital Preserved: `758,500.00 RUB`

---

### Dataset B: Balanced HNWI Allocation (Moderate Risk)
*Profile: Multi-asset institutional split (Equities, Sovereign OFZ Bonds, Money Market, Gold ETF).*

```json
[
  {
    "ticker": "SU26238RMFS4",
    "name": "OFZ-PD 26238 (Maturity 2041)",
    "asset_class": "bond",
    "quantity": 5000,
    "current_price": 540.20,
    "total_value": 2701000.00,
    "weight": 27.01,
    "currency": "RUB",
    "expected_yield": 16.8
  },
  {
    "ticker": "SU29014RMFS6",
    "name": "OFZ-PK 29014 (Key Rate Floater)",
    "asset_class": "bond",
    "quantity": 2500,
    "current_price": 985.00,
    "total_value": 2462500.00,
    "weight": 24.625,
    "currency": "RUB",
    "expected_yield": 19.5
  },
  {
    "ticker": "LQDT",
    "name": "VIM Liquidity Money Market ETF",
    "asset_class": "etf",
    "quantity": 1200000,
    "current_price": 1.52,
    "total_value": 1824000.00,
    "weight": 18.24,
    "currency": "RUB"
  },
  {
    "ticker": "SBER",
    "name": "Sberbank PJSC",
    "asset_class": "share",
    "quantity": 5000,
    "current_price": 305.50,
    "total_value": 1527500.00,
    "weight": 15.275,
    "currency": "RUB"
  },
  {
    "ticker": "TGLD",
    "name": "T-Capital Physical Gold ETF",
    "asset_class": "etf",
    "quantity": 150000,
    "current_price": 9.90,
    "total_value": 1485000.00,
    "weight": 14.85,
    "currency": "RUB"
  }
]
```
* **Total Portfolio Value:** `10,000,000.00 RUB`
* **Baseline Deterministic HHI:**
  $$HHI = 27.01^2 + 24.625^2 + 18.24^2 + 15.275^2 + 14.85^2 = \mathbf{2122.36} \quad (\text{Moderate Risk} \in [1500, 2500])$$

---

## 🛠️ 4. Existing Baseline Parser (Rule-Based Pandas)

For Phase 2 benchmarking, our current baseline heuristic parser relies on column alias resolution:

```python
COLUMN_ALIASES = {
    "ticker": ["тикер", "код", "symbol", "sec_code", "инструмент", "isin"],
    "name": ["наименование", "бумага", "актив", "name", "security"],
    "quantity": ["кол-во", "количество", "штук", "qty", "volume", "остаток"],
    "current_price": ["текущая цена", "цена", "рыночная цена", "last_price", "price", "курс"],
    "total_value": ["сумма", "стоимость", "рыночная стоимость", "total", "value", "оценка"],
    "asset_class": ["вид актива", "тип", "класс", "type", "asset_type"],
}
```
*Limitation of Baseline:* Whenever an XLSX statement embeds table headers on row 14, aggregates multiple currencies in merged sub-tables, or uses unrecognized aliases, regex/Pandas throws errors or truncates critical holdings. Your Phase 2 ML model will solve this problem.

---

## 🔗 5. Architecture: How Django Backend Connects with ML

To ensure clean isolation and security, the ML engine will operate as an **independent sidecar microservice**:

```text
[Client Web UI] ──> [Django Backend :8000]
                           │
                           ├── 1. Try Fast Pandas Baseline (10ms)
                           │      └── If successful (>95% confidence) ──> Return PositionDTO
                           │
                           └── 2. If Parser Fails / Unknown Format (Fallback)
                                  └── HTTP POST ──> [FastAPI ML Microservice :8001]
                                                    └── Returns validated JSON array
```

### 5.1. Microservice API Contract (FastAPI)
You will package your Phase 2 inference script into a lightweight FastAPI service:

* **Endpoint:** `POST /api/v1/extract-positions`
* **Request Payload (from Django):**
```json
{
  "file_name": "broker_statement_sample.xlsx",
  "file_type": "xlsx", // or "csv"
  "raw_content_base64": "<base64_encoded_file_bytes>",
  "text_chunks": ["optional pre-extracted text/table rows"]
}
```

* **Response Payload (to Django):**
```json
{
  "status": "success",
  "parser_used": "ml_slm_extractor",
  "confidence_score": 0.985,
  "positions": [
    {
      "ticker": "SBER",
      "name": "Sberbank PJSC",
      "asset_class": "share",
      "quantity": 1500.0,
      "current_price": 305.5,
      "total_value": 458250.0,
      "currency": "RUB"
    }
  ],
  "unmapped_rows": []
}
```

---

## 📈 6. Historical Data Source for Phase 1 Metrics (VaR, Beta, Sharpe)

To compute historical risk metrics (252-day volatility, beta vs. benchmark, historical VaR), use the official, free **Moscow Exchange Informational & Statistical Server (MOEX ISS API)**:

* **Official API Docs:** `https://iss.moex.com`
* **Python Libraries (Pre-approved):**
  * `moexalgo` (Official MOEX Python SDK): `pip install moexalgo`
  * `requests` directly against ISS REST endpoints:
    * Stock Price History: `https://iss.moex.com/iss/history/engines/stock/markets/shares/securities/SBER.json?from=2025-01-01`
    * Benchmark Index (`MCFTR` - Total Return Index): `https://iss.moex.com/iss/history/engines/stock/markets/index/securities/MCFTR.json?from=2025-01-01`
* In your Jupyter Notebook, implement a clean caching utility saving downloaded price histories to `research/data/cache/` so notebooks execute offline without hitting MOEX rate limits.

---

## ⚡ 7. Hardware & SLA Constraints (On-Premise Banking Standards)

Your ML solution must deploy inside private bank server environments without discrete Nvidia GPUs:

1. **Host Environment:** Standard Linux x86_64 CPU (4 vCPU cores, 8 GB total server RAM).
2. **RAM Consumption Limit:** The ML service must consume **$\le$ 4.0 GB RAM** at peak load.
3. **Inference Latency SLA:** Statement extraction must complete in **$\le$ 3.0 seconds** per document on CPU.
4. **Execution Runtimes:** Models must be formatted as **GGUF (Q4_K_M or Q8_0)** for `llama.cpp` / `vLLM` CPU backend, or exported to **ONNX Runtime**.
