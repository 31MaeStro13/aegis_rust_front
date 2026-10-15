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

Все возвращаемые структуры и поля должны на 100% совпадать с контрактами `CalculationEngineProtocol` (`backend/apps/core/engine_adapter.py`) и DRF сериализаторами.

### 4.1. `calculate_hhi` (Индекс концентрации Херфиндаля-Хиршмана)
* **Входные данные:** `positions: Vec<PositionInput>`
* **Математическая модель:**
  $$HHI = \sum_{i=1}^{N} (w_i)^2$$
  где $w_i \in [0; 100]$ — процентный вес каждого актива. Диапазон $HHI \in [0; 10\,000]$.
* **Выходная структура `HHIResult`:**
```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HHIResult {
    pub hhi_index: f64,              // Значение индекса, округление до 1 знака (напр. 3120.5)
    pub concentration_level: String, // "low" | "medium" | "high" (Внимание: строго "medium", НЕ "moderate"!)
    pub concentration_label: String, // "Низкая концентрация (Хорошая диверсификация)" | "Умеренная концентрация" | "Высокая концентрация (Повышенный риск)"
    pub top_asset_share_pct: f64,    // Доля крупнейшей позиции в процентах (напр. 38.0)
    pub top_5_share_pct: f64,        // Суммарная доля топ-5 позиций в процентах (напр. 72.5)
}
```
* **Градации концентрации:**
  * `HHI < 1500` $\rightarrow$ `"low"`, `"Низкая концентрация (Хорошая диверсификация)"`
  * `1500 <= HHI < 2500` $\rightarrow$ `"medium"`, `"Умеренная концентрация"`
  * `HHI >= 2500` $\rightarrow$ `"high"`, `"Высокая концентрация (Повышенный риск)"`

### 4.2. `calculate_allocation` (Аллокация по классам активов)
* **Входные данные:** `positions: Vec<PositionInput>`
* **Логика:** Суммирование стоимости позиций по классам: `share`, `bond`, `etf`, `currency` (деньги/кэш), `other` и расчёт их нормализованных долей в портфеле (в долях от 1.0, сумма долей = 1.0).
* **Выходные данные:** `HashMap<String, f64>` (контракт `engine_adapter.py` / `sector_allocation`).
```rust
// Возвращает HashMap со стандартизированными сингулярными ключами и долями от 1.0:
// "share"    => 0.621 (доля акций)
// "bond"     => 0.379 (доля облигаций)
// "etf"      => 0.000 (доля фондов)
// "currency" => 0.000 (доля ликвидности / кэша)
// "other"    => 0.000 (прочие активы)
pub fn calculate_allocation(positions: &[PositionInput]) -> HashMap<String, f64>
```
> **Внимание:** Ключи строго в единственном числе (`share`, `bond`, `etf`, `currency`, `other`), а значения — доли в диапазоне `0.0 .. 1.0`. Преобразование в проценты ($0.0 \dots 100.0\%$) и сериализацию во множественное число (`shares`, `bonds`, `currencies`) выполняет контроллер `views.py`.

### 4.3. `simulate_stress` (Стресс-тестирование просадки)
* **Входные данные:**
  * `positions: Vec<PositionInput>`
  * `drop_pct: f64` (по умолчанию `0.15` — падение рисковой позиции на 15%)
* **Логика:** Нахождение крупнейшей позиции (`top_holding`), расчёт просадки по ней `loss_rub = top_value * drop_pct` и расчёт `loss_pct` от всего портфеля.
* **Выходная структура `StressSimulationResult`:**
```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StressSimulationResult {
    pub scenario: String,        // "stress"
    pub top_ticker: String,      // Тикер крупнейшей позиции (напр. "SBER")
    pub top_value: f64,          // Оценка крупнейшей позиции в рублях
    pub drop_pct: f64,           // Процент падения в % (напр. 15.0)
    pub loss_rub: f64,           // Абсолютный убыток в рублях
    pub loss_pct: f64,           // Процент потерь от совокупного капитала
    pub stressed_total: f64,     // Оценка портфеля после стресс-шока
}
```

### 4.4. `simulate_rebalance` (Ребалансировка в ОФЗ-флоатеры под ставку ЦБ)
* **Входные данные:**
  * `positions: Vec<PositionInput>`
  * `shift_pct: f64` (по умолчанию `0.20` — перевод 20% из топ-актива в ОФЗ)
  * `target_rate: f64` (ставка ЦБ / доходность флоатеров, по умолчанию `0.19` = 19%)
* **Логика:**
  * Высвобождение капитала из топ-актива: `shift_amount = top_value * shift_pct`.
  * Перевод в защитный инструмент `OFZ-26240` с доходностью `target_rate`.
  * Пересчёт структуры и вычисление нового HHI и величины его снижения (`hhi_reduction`).
* **Выходная структура `RebalanceSimulationResult`:**
```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RebalanceSimulationResult {
    pub scenario: String,          // "rebalance"
    pub shift_amount: f64,         // Объем перераспределяемого капитала в рублях
    pub top_ticker: String,        // Тикер уменьшаемого актива
    pub old_hhi: f64,              // Значение HHI до ребалансировки
    pub new_hhi: f64,              // Значение HHI после ребалансировки
    pub hhi_reduction: f64,        // Снижение HHI (old_hhi - new_hhi)
    pub rebalanced_total: f64,     // Совокупная стоимость портфеля
    pub target_rate_pct: f64,      // Ставка ЦБ в % (напр. 19.0)
    pub annual_yield_rub: f64,     // Ожидаемый годовой купонный доход от флоатеров
}
```

### 4.5. `calculate_risk_metrics` (Sharpe Ratio, Volatility, Max Drawdown)
* **Входные данные:**
  * `equity: Vec<f64>` — временной ряд стоимости портфеля по дням/снимкам.
  * `risk_free_rate: f64` (безрисковая ставка, default `0.19`).
* **Логика:**
  * Вектор дневных лог-доходностей: $R_t = \ln(E_t / E_{t-1})$
  * Годовая волатильность: $\sigma_{ann} = \text{std}(R, \text{ddof}=1) \times \sqrt{252}$
  * Годовая доходность: $\mu_{ann} = \text{mean}(R) \times 252$
  * Коэффициент Шарпа: $(\mu_{ann} - R_f) / \sigma_{ann}$
  * Максимальная просадка (MDD): $\min_t \left( (E_t - \text{Peak}_t) / \text{Peak}_t \right)$
* **Выходная структура `RiskMetricsResult`:**
```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RiskMetricsResult {
    pub max_drawdown: f64,         // Историческая просадка в долях (напр. -0.092 для -9.2%)
    pub annual_volatility: f64,    // Годовая волатильность в долях (напр. 0.178 для 17.8%)
    pub sharpe_ratio: f64,         // Коэффициент Шарпа (напр. 1.42)
}
```

---

## 5. Требования к тестированию (Тесты обязательны!)

Покрытие кода должно составлять **не менее 90%**. Обязательны следующие тесты:

### 5.1. Unit-тесты Rust (`cargo test`):
1. `test_hhi_single_stock`: портфель из 1 акции $\rightarrow HHI = 10\,000$, уровень `"high"`.
2. `test_hhi_diversified`: портфель из 10 равных бумаг по 10% $\rightarrow HHI = 1\,000$, уровень `"low"`.
3. `test_hhi_medium_range`: портфель с HHI 2000 $\rightarrow$ уровень строго `"medium"`.
4. `test_stress_calculation`: проверка совпадения `loss_rub` и `loss_pct`.
5. `test_zero_and_empty_handling`: пустой список позиций или нулевые балансы не приводят к панике, возвращают 0.0.
6. `test_mdd_and_sharpe_calculation`: проверка формул Шарпа и просадки на эталонном массиве цен.

### 5.2. Интеграционные тесты Python/Rust (`pytest`):
1. Проверка загрузки модуля через `backend/apps/core/engine_adapter.py`.
2. Сверка численных результатов Rust-ядра с эталонным `PythonCalculationEngine` до 4-го знака после запятой.

---

## 6. Итоговые артефакты поставки:
1. Исходный код в `crates/aegis_core/` (`Cargo.toml`, `src/lib.rs`, `src/metrics.rs`).
2. Зелёные тесты `cargo test`.
3. Скомпилированный бинарный модуль `.so` / `.pyd` через `maturin develop`.
