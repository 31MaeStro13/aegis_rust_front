# 🦀 Техническое задание: Расчётное ядро Aegis Core (Rust / PyO3)

## 1. Цель проекта
Разработать автономную высокопроизводительную библиотеку на **Rust** с биндингами к Python через **PyO3** (`aegis_core`), которая заменит расчёты на Python/NumPy в B2B Wealth Terminal.

### Ключевые требования:
* **Производительность:** Расчёт комплексного портфеля (до 10 000+ позиций) за время < 5 мс.
* **Совместимость:** 100% сохранение контрактов данных `CalculationEngineProtocol` (`backend/apps/core/engine_adapter.py`).
* **Безопасность:** Отсутствие паник (`panic!`), безопасная обработка деления на ноль, пустых портфелей, NaN и бесконечностей.

---

## 2. Архитектура и стек технологий
* **Язык:** Rust (edition 2021).
* **Связка с Python:** `pyo3` (>= 0.21), сборка через `maturin`.
* **Сериализация:** `serde`, `serde_json`.
* **Расположение:** `crates/aegis_core/`.

---

## 3. Базовые структуры данных (DTO)

```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PositionInput {
    pub ticker: String,
    pub name: String,
    pub instrument_type: String, // "share", "bond", "etf", "currency", "other"
    pub quantity: f64,
    pub current_price: f64,
    pub total_value: f64,        // Если <= 0, вычислять как quantity * current_price
    pub weight: f64,             // Доля в портфеле (0.0 .. 100.0)
    pub currency: String,
}
```

---

## 4. Обязательные функции ядра (API)

### 4.1. `calculate_hhi` (Индекс концентрации Херфиндаля-Хиршмана)
* **Входные данные:** `positions: Vec<PositionInput>`
* **Математическая модель:**
  $$HHI = \sum_{i=1}^{N} (w_i)^2$$
  где $w_i \in [0; 100]$ — процентный вес каждого актива. Диапазон $HHI \in [0; 10\,000]$.
* **Выходная структура `HHIResult`:**
  * `hhi: f64` — значение индекса (округление до 2 знаков).
  * `level: String` — категория концентрации:
    * `HHI < 1500` $\rightarrow$ `"low"` (высокая диверсификация).
    * `1500 <= HHI <= 2500` $\rightarrow$ `"moderate"` (умеренная концентрация).
    * `HHI > 2500` $\rightarrow$ `"high"` (критическая концентрация).
  * `top_holding_pct: f64` — вес крупнейшей позиции в процентах.

### 4.2. `calculate_allocation` (Аллокация по классам активов)
* **Входные данные:** `positions: Vec<PositionInput>`
* **Логика:** Суммирование стоимости по группам: `share` (акции), `bond` (облигации), `etf` (фонды), `currency` (деньги/ликвидность), `other`.
* **Выходные данные:** `HashMap<String, f64>` — нормализованные доли каждого класса (сумма долей = 1.0).

### 4.3. `simulate_stress` (Стресс-тестирование просадки рынка)
* **Входные данные:**
  * `positions: Vec<PositionInput>`
  * `drop_pct: f64` (по умолчанию `0.15` — падение рисковых активов на 15%)
* **Логика:**
  * Защитные активы (`bond`, `currency`) имеют просадку 0.0%.
  * Рисковые активы (`share`, `etf`) теряют `drop_pct` от своей стоимости.
* **Выходная структура `StressResult`:**
  * `loss_amount: f64` — абсолютные потери портфеля в валюте (рублях).
  * `simulated_total: f64` — итоговая стоимость портфеля после рыночного шока.
  * `market_drop_percent: f64` — процент рыночного шока.
  * `safe_capital: f64` — объем защитного капитала (облигации + ликвидность).

### 4.4. `simulate_rebalance` (Ребалансировка в ОФЗ-флоатеры под ставку ЦБ)
* **Входные данные:**
  * `positions: Vec<PositionInput>`
  * `shift_pct: f64` (по умолчанию `0.20` — вывод 20% из акций/ETF в ОФЗ)
  * `target_rate: f64` (ставка ЦБ / купон флоатеров, напр. `0.19` = 19%)
* **Логика:**
  * Высвобождение капитала из рисковых активов: `capital_to_shift = risky_total * shift_pct`.
  * Направление средств в защитные бонды с доходностью `target_rate`.
  * Расчёт гарантированного годового купонного дохода.
* **Выходная структура `RebalanceResult`:**
  * `shifted_amount: f64` — объем перераспределенных средств.
  * `annual_passive_income: f64` — гарантированный годовой купонный доход.
  * `new_bond_weight_pct: f64` — новая совокупная доля облигаций в портфеле.

### 4.5. `calculate_risk_metrics` (Sharpe Ratio, Volatility, Max Drawdown)
* **Входные данные:**
  * `equity_curve: Vec<f64>` — временной ряд стоимости портфеля.
  * `risk_free_rate: f64` (безрисковая ставка, default `0.19`).
* **Логика:**
  * Дневные доходности: $R_t = \frac{E_t - E_{t-1}}{E_{t-1}}$
  * Годовая волатильность: $\sigma_{ann} = \text{std}(R) \times \sqrt{252}$
  * Годовая доходность: $R_{ann}$
  * Коэффициент Шарпа: $\frac{R_{ann} - R_f}{\sigma_{ann}}$
  * Максимальная просадка (MDD): $\max_{t} \left( \frac{\text{Peak}_t - E_t}{\text{Peak}_t} \right)$
* **Выходная структура `RiskMetricsResult`:**
  * `sharpe_ratio: f64`
  * `volatility_annual: f64`
  * `max_drawdown_pct: f64`

---

## 5. Требования к тестированию (Тесты обязательны!)

Покрытие кода должно составлять **не менее 90%**. Обязательны следующие тесты:

### 5.1. Unit-тесты Rust (`cargo test`):
1. `test_hhi_single_stock`: портфель из 1 акции $\rightarrow HHI = 10\,000$, уровень `"high"`.
2. `test_hhi_diversified`: портфель из 10 равных бумаг по 10% $\rightarrow HHI = 1\,000$, уровень `"low"`.
3. `test_stress_all_bonds`: портфель только из ОФЗ $\rightarrow$ `loss_amount == 0.0`.
4. `test_zero_and_empty_handling`: пустой список позиций или нулевые балансы не приводят к панике, возвращают 0.0.
5. `test_mdd_and_sharpe_calculation`: проверка формул Шарпа и просадки на эталонном массиве цен.

### 5.2. Интеграционные тесты Python/Rust (`pytest`):
1. Проверка загрузки модуля через `backend/apps/core/engine_adapter.py`.
2. Сверка численных результатов Rust-ядра с эталонным `PythonCalculationEngine` до 4-го знака после запятой.

---

## 6. Итоговые артефакты поставки:
1. Исходный код в `crates/aegis_core/` (`Cargo.toml`, `src/lib.rs`, `src/metrics.rs`).
2. Зелёные тесты `cargo test`.
3. Скомпилированный бинарный модуль `.so` / `.pyd` через `maturin develop`.
