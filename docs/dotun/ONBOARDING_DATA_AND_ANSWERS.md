# 📦 Phase 1 Onboarding Data, Answers & Benchmark Contracts

**Engineer:** MSc Dotun (Quantitative Financial Analyst & ML Engineer)  
**Project:** Aegis Wealth Terminal (B2B SaaS / On-Premise)  
**Assigned Workspace:** `crates/` or `research/` in `https://github.com/31MaeStro13/aegis_rust_front`

---

## 💬 1. Formal Answers to Your 5 Inquiries

### Question 1: Deliverable Sequencing
* **Answer:** **Yes, strictly complete Phase 1 before advancing to Phase 2.**
* *Rationale:* The mathematical formulas, risk thresholds (VaR, CVaR, Sortino, Duration), and the 2-page executive report blueprint you design in Phase 1 directly dictate the UI cards that the frontend developer (Nikita) and UI designer (Anastasia) will render.
* *Phase 1 Target Output:* A comprehensive Technical Memo (Markdown/PDF) + a reproducible Jupyter Notebook (`.ipynb`) computing these metrics on the benchmark datasets below.

### Question 2: PositionDTO Schema & Sample Portfolios
* **Answer:** Fully documented below in **Section 2 & 3**. You are provided with:
  1. The canonical Python Pydantic/dataclass schema for `PositionDTO`.
  2. Three heterogeneous portfolio datasets (Conservative OFZ, Balanced Multi-Asset, and High-Concentration Aggressive).
  3. Ground truth mathematical metrics for baseline verification.

### Question 3: Workspace & Repository Placement
* **Answer:** Your entire quantitative and ML pipeline will reside in the dedicated directory:
  ```text
  research/
  ├── notebooks/              # Jupyter notebooks for Phase 1 & Phase 2
  ├── data/                   # Messy CSVs, clean PositionDTO JSONs
  ├── src/                    # Python modules (metrics.py, parser_baseline.py)
  └── reports/                # Output PDF blueprints and memos
  ```
  *Zero Backend Contamination:* Your work remains decoupled from the internal Django backend. It will be packaged as a standalone analytical engine / microservice module.

### Question 4: Baseline Parser & Model Preferences
* **Answer:**
  * **Baseline Parser:** We currently utilize a deterministic Pandas heuristic column-matching parser (detailed in **Section 4**).
  * **SLM Preference:** For on-premise bank compliance, solutions must run without costly enterprise GPUs. Prioritize lightweight Small Language Models (SLMs) such as **`Qwen-2.5-Coder-1.5B-Instruct`** or **`Llama-3.2-1B-Instruct`** via `vLLM` or `llama.cpp` (GGUF 4-bit quantization).

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
