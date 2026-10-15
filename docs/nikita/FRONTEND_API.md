# 📘 Aegis Wealth Terminal — Руководство по интеграции для Frontend-разработчика

Данный документ описывает REST API бэкенда для терминала инвест-советника **Aegis Wealth**.
Бэкенд работает в **Stateless In-Memory** режиме: расчёты ведутся на лету, сессии и клиентские портфели не сохраняются в БД без явного действия пользователя.

---

## 🌐 Базовая информация

* **Base URL**: `http://localhost:8000/api/v1/portfolio/`
* **Swagger UI**: `http://localhost:8000/api/docs/`
* **OpenAPI 3.0 Schema**: `http://localhost:8000/api/schema/`
* **Content-Type**:
  * Загрузка файлов: `multipart/form-data`
  * Аналитические запросы: `application/json`
  * Выгрузка файлов: `text/csv`, `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`, `application/pdf`
* **Ограничение на размер загрузки**: **5 МБ** (HTTP 400 при превышении)
* **Rate Limiting**: 120 запросов/мин на операции расчёта и экспорта (`HTTP 429 Too Many Requests`).

---

## 📐 TypeScript Интерфейсы (Data Contracts)

Скопируйте эти типы в проект фронтенда (`types/portfolio.ts`):

```typescript
export type InstrumentType = 'share' | 'bond' | 'etf' | 'currency' | 'other';

export interface PositionDTO {
  ticker: string;              // Напр. "SBER", "SU26238RMFS4"
  name: string;                // Напр. "Сбербанк ПАО"
  instrument_type: InstrumentType; // 'share' | 'bond' | 'etf' | 'currency' | 'other'
  quantity: number;            // Кол-во лотов/бумаг
  current_price: number;       // Текущая цена за единицу в рублях
  total_value: number;         // quantity * current_price
  weight: number;              // Доля в портфеле в ПРОЦЕНТАХ от 0.0 до 100.0 (напр. 28.5)
  currency: string;            // По умолчанию "RUB"
  average_price?: number;      // Средняя цена покупки
  expected_yield?: number;     // Купонная/дивидендная доходность в %
}

export interface PortfolioAllocation {
  shares: number;       // Доля акций в % (напр. 62.0)
  bonds: number;        // Доля облигаций в % (напр. 24.0)
  etf: number;          // Доля фондов в % (напр. 9.0)
  currencies: number;   // Доля валюты/кэша в % (напр. 5.0)
}

export interface PortfolioAnalytics {
  hhi_index: number;                   // Индекс Херфиндаля-Хиршмана (0 - 10000)
  concentration_level: 'low' | 'medium' | 'high'; // Оценка риска
  concentration_label: string;         // 'Низкая' | 'Умеренная' | 'Высокая'
  top_asset_share_pct: number;         // Доля крупнейшего актива в %
  top_5_share_pct: number;             // Доля топ-5 активов в %
  critical_asset: string | null;       // Напр. "SBER 38.0%"
  allocation: PortfolioAllocation;     // Распределение по классам
}

export interface PortfolioUploadResponse {
  account_name: string;
  total_value: number;
  currency: string;
  positions_count: number;
  analytics: PortfolioAnalytics;
  positions: PositionDTO[];
  warnings: string[];
}

export interface StressSimulationResult {
  scenario: 'stress';
  top_ticker: string;          // Крупнейший актив, подвергшийся стрессу
  top_value: number;           // Начальная стоимость актива
  drop_pct: number;            // Процент падения в % (напр. 15.0)
  loss_rub: number;            // Абсолютный убыток в рублях
  loss_pct: number;            // Относительный убыток портфеля в %
  stressed_total: number;      // Новая стоимость портфеля после просадки
}

export interface RebalanceSimulationResult {
  scenario: 'rebalance';
  shift_amount: number;        // Сумма перевода в облигации
  top_ticker: string;          // Из какого актива забираем средства
  old_hhi: number;             // HHI до ребалансировки
  new_hhi: number;             // Прогнозируемый HHI после ребалансировки
  hhi_reduction: number;       // Снижение риска
  target_instrument: string;   // 'ОФЗ-26240 Флоатер (19%)'
}

export interface PortfolioSimulationRequest {
  scenario: 'stress' | 'rebalance';
  drop_pct?: number;           // Default: 0.15 (для scenario="stress")
  shift_pct?: number;          // Default: 0.20 (для scenario="rebalance")
  positions: PositionDTO[];
}

export interface ClientAccount {
  id: number;
  account_id: string;
  name: string;
  account_type: string;
  status: string;
  total_amount: string;        // Decimal string, e.g. "14250000.00"
}

export interface ClientProfile {
  id: number;
  advisor: number;
  advisor_username: string;
  full_name: string;
  email?: string;
  phone?: string;
  risk_profile: 'conservative' | 'moderate' | 'aggressive';
  notes?: string;
  accounts_count: number;
  total_aum: string;           // Decimal string, e.g. "14250000.00"
  accounts?: ClientAccount[];
  created_at?: string;
  updated_at?: string;
}

// 🔐 Authentication & 2FA Types
export interface LoginRequest {
  username: string;
  password: string;
}

export type LoginResponse =
  | {
      status: 'authenticated';
      is_2fa_enabled: false;
      access: string;
      refresh: string;
    }
  | {
      status: '2fa_required';
      pre_auth_token: string;
      message: string;
    };

export interface Verify2FARequest {
  pre_auth_token: string;
  code: string; // 6 цифр из Google Authenticator
}

export interface Verify2FAResponse {
  status: 'authenticated';
  is_2fa_enabled: true;
  access: string;
  refresh: string;
}

export interface Setup2FAResponse {
  secret: string;
  otpauth_uri: string; // Строка под QR-код
  manual_entry_key: string;
  issuer: string;
  account_name: string;
}
```

---

## 🔐 Аутентификация советника (JWT + TOTP 2FA)

Терминал использует **двухэтапную аутентификацию (RFC 6238)**:
* **Access токен**: срок жизни **15 минут** (`Authorization: Bearer <access>`).
* **Refresh токен**: срок жизни **1 день** с автоматической ротацией.

### Сценарий входа:
1. Отправьте `POST /api/v1/auth/login/` (`username`, `password`).
2. Если ответ `status: "2fa_required"`:
   * Сохраните `pre_auth_token` в памяти (действует 3 минуты).
   * Покажите экран ввода 6-значного кода TOTP.
   * Отправьте `POST /api/v1/auth/2fa/verify/` с `{ pre_auth_token, code }`.
   * Получите пару токенов `{ access, refresh }`.
3. Если ответ `status: "authenticated"`:
   * Вы уже вошли! Сохраните `{ access, refresh }`.

### Обновление токена:
* `POST /api/v1/auth/refresh/` с телом `{ "refresh": "<refresh_token>" }` -> возвращает свежий `access` и новый `refresh`.

---

## 📡 Эндпоинты API

### 1. Загрузка портфеля (Drag & Drop)
Принимает выгрузку в формате `.csv` или `.xlsx`. Парсит на лету, нормализует разделители/кодировки и возвращает очищенный список позиций + аналитику HHI.

* **URL**: `POST /api/v1/portfolio/upload/`
* **Content-Type**: `multipart/form-data`
* **Параметры формы**:
  * `file`: брокерский отчёт (`.csv` или `.xlsx`, максимум 5 МБ).
  > **Архитектурная деталь:** Парсинг и скоринг выполняются in-memory на лету. Метод возвращает готовый DTO для отображения в терминале и последующего сценарного моделирования.

#### Пример ответа (`HTTP 200 OK`):
```json
{
  "account_name": "Импорт: broker_statement",
  "total_value": 500000.0,
  "currency": "RUB",
  "positions_count": 2,
  "analytics": {
    "hhi_index": 5292.8,
    "concentration_level": "high",
    "concentration_label": "Высокая концентрация (Повышенный риск)",
    "top_asset_share_pct": 62.1,
    "top_5_share_pct": 100.0,
    "critical_asset": "SBER 62.1%",
    "allocation": {
      "shares": 62.1,
      "bonds": 37.9,
      "etf": 0.0,
      "currencies": 0.0
    }
  },
  "positions": [
    {
      "ticker": "SBER",
      "name": "Сбербанк ПАО",
      "instrument_type": "share",
      "quantity": 1000.0,
      "current_price": 310.5,
      "total_value": 310500.0,
      "weight": 62.1,
      "currency": "RUB",
      "is_critical": true
    },
    {
      "ticker": "SU26238RMFS4",
      "name": "ОФЗ 26238",
      "instrument_type": "bond",
      "quantity": 250.0,
      "current_price": 758.0,
      "total_value": 189500.0,
      "weight": 37.9,
      "currency": "RUB",
      "is_critical": false
    }
  ],
  "warnings": []
}
```

---

### 2. Стресс-тестирование и Ребалансировка
Рассчитывает влияние падения рынка акций и формирует предложение по снижению риска портфеля за счёт фиксации доходности в ОФЗ под высокую ставку.

* **URL**: `POST /api/v1/portfolio/simulate/`
* **Content-Type**: `application/json`

#### Тело запроса (Сценарий 1: Стресс-тест):
```json
{
  "scenario": "stress",
  "drop_pct": 0.15,
  "positions": [
    {
      "ticker": "SBER",
      "name": "Сбербанк ПАО",
      "instrument_type": "share",
      "quantity": 1000.0,
      "current_price": 310.5,
      "total_value": 310500.0,
      "weight": 62.1,
      "currency": "RUB"
    },
    {
      "ticker": "SU26238RMFS4",
      "name": "ОФЗ 26238",
      "instrument_type": "bond",
      "quantity": 250.0,
      "current_price": 758.0,
      "total_value": 189500.0,
      "weight": 37.9,
      "currency": "RUB"
    }
  ]
}
```

#### Ответ API при стресс-тесте (`HTTP 200 OK`):
```json
{
  "scenario": "stress",
  "top_ticker": "SBER",
  "top_value": 310500.0,
  "drop_pct": 15.0,
  "loss_rub": 46575.0,
  "loss_pct": 9.32,
  "stressed_total": 453425.0
}
```

#### Тело запроса (Сценарий 2: Ребалансировка в ОФЗ):
```json
{
  "scenario": "rebalance",
  "shift_pct": 0.20,
  "positions": [
    {
      "ticker": "SBER",
      "name": "Сбербанк ПАО",
      "instrument_type": "share",
      "quantity": 1000.0,
      "current_price": 310.5,
      "total_value": 310500.0,
      "weight": 62.1,
      "currency": "RUB"
    }
  ]
}
```

#### Ответ API при ребалансировке (`HTTP 200 OK`):
```json
{
  "scenario": "rebalance",
  "shift_amount": 62100.0,
  "top_ticker": "SBER",
  "old_hhi": 3856.4,
  "new_hhi": 2468.1,
  "hhi_reduction": 1388.3,
  "target_instrument": "ОФЗ-26240 Флоатер (19%)"
}
```

---

### 3. Экспорт Векторного PDF-Отчёта
Генерирует официальный инвестиционный аудит для клиента с фирменным стилем Aegis Wealth, диаграммами распределения, метриками риска и скриптом советника.

* **URL**: `POST /api/v1/portfolio/export_pdf/`
* **Content-Type**: `application/json`
* **Response Content-Type**: `application/pdf`
* **Заголовки ответа**: `Content-Disposition: attachment; filename="Aegis_Audit_{Client_Name}.pdf"; filename*=UTF-8''Aegis_Audit_{Client_Name}.pdf`

#### Тело запроса (Параметры отчёта):
```json
{
  "account_name": "Иван Иванов — Основной",
  "positions": [
    {
      "ticker": "SBER",
      "name": "Сбербанк ПАО",
      "instrument_type": "share",
      "quantity": 1000.0,
      "current_price": 310.5,
      "total_value": 310500.0,
      "weight": 62.1,
      "currency": "RUB"
    },
    {
      "ticker": "OFZ-26240",
      "name": "ОФЗ 26240 Флоатер",
      "instrument_type": "bond",
      "quantity": 190.0,
      "current_price": 1000.0,
      "total_value": 190000.0,
      "weight": 37.9,
      "currency": "RUB"
    }
  ],
  "stress_test": {
    "top_ticker": "SBER",
    "drop_pct": 15.0,
    "loss_rub": 46575.0,
    "loss_pct": 9.3,
    "stressed_total": 453925.0
  },
  "rebalance": {
    "top_ticker": "SBER",
    "old_hhi": 5291.6,
    "new_hhi": 3415.2,
    "hhi_reduction": 1876.4
  }
}
```
> **Примечание:** Блоки `stress_test` и `rebalance` являются опциональными. При их передаче они автоматически отрисовываются в PDF-отчете в блоке «Risk Stress-Testing & Rebalance Advisory».

---

### 4. Скачивание шаблонов портфеля
Позволяет пользователю в UI скачать эталонный CSV или XLSX файл с примером колонок.

* **URL**: `GET /api/v1/portfolio/template/?file_format=csv`  
  *(или `file_format=xlsx`)*
* **Response Content-Type**: `text/csv; charset=utf-8` или `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
* **Заголовки ответа**: `Content-Disposition: attachment; filename="aegis_template.csv"` (для XLSX: `filename="aegis_template.xlsx"`)

---

### 5. Управление реальными клиентами советника (B2B Multi-Client CRUD)
Позволяет советнику создавать, просматривать и редактировать базу своих клиентов в терминале.

* **URL**: `/api/v1/clients/`
* **Методы**:
  * `GET /api/v1/clients/` — список клиентов текущего советника со сводкой по счетам и AUM.
  * `POST /api/v1/clients/` — регистрация нового клиента советника.
  * `GET /api/v1/clients/{id}/` — карточка клиента с детальным списком привязанных счетов.
  * `PATCH /api/v1/clients/{id}/` — обновление данных (риск-профиль, телефон, заметки).
  * `POST /api/v1/clients/{id}/assign-account/` — привязка инвестиционного счета (`{"account_id": 123}`).

#### Пример ответа карточки клиента (`GET /api/v1/clients/1/`):
```json
{
  "id": 1,
  "advisor": 2,
  "advisor_username": "advisor_ivan",
  "full_name": "Смирнов Алексей Викторович",
  "email": "smirnov@example.com",
  "phone": "+79991112233",
  "risk_profile": "conservative",
  "notes": "Крупный консервативный инвестор",
  "accounts_count": 1,
  "total_aum": "14250000.00",
  "accounts": [
    {
      "id": 10,
      "account_id": "ACC-2001",
      "name": "Основной брокерский счёт (Т-Банк)",
      "account_type": "tinkoff",
      "status": "active",
      "total_amount": "14250000.00"
    }
  ],
  "created_at": "2026-10-11T17:05:00Z",
  "updated_at": "2026-10-11T17:05:00Z"
}
```

---

### 6. Список демо-клиентов (Sandbox)
Для быстрого тестирования аналитического ядра без ввода данных:
* **URL**: `GET /api/v1/portfolio/clients/`

---

## ⚠️ Коды ошибок и обработка

| HTTP Код | Причина | Пример ответа |
| :--- | :--- | :--- |
| **400 Bad Request** | Файл отсутствует / не передан | `{"detail": "Файл не найден. Отправьте файл брокерского отчета в поле 'file'."}` |
| **400 Bad Request** | Неподдерживаемый формат файла | `{"detail": "Не поддерживаемый формат файла. Загрузите .csv или .xlsx"}` |
| **400 Bad Request** | Размер файла превышает 5 МБ | `{"detail": "Размер файла превышает допустимый лимит (5 МБ)."}` |
| **400 Bad Request** | Ошибка валидации структуры / пустой список | `{"detail": "Некорректная структура переданных позиций.", "errors": [...]}` или `{"positions": ["Обязательное поле."]}` |
| **429 Too Many Requests** | Превышен лимит запросов (Rate Limit) | `{"detail": "Request was throttled. Expected available in 30 seconds."}` |
| **500 Internal Error** | Внутренняя ошибка парсера / движка | `{"detail": "Ошибка обработки файла: ..."}` |

---

## 💡 Примечания для Frontend-архитектуры

1. **State Management**: Рекомендуется хранить `PortfolioUploadResponse` в Zustand / Redux / Pinia. При переключении сценариев моделирования отправлять массив `positions` в `POST /simulate/`.
2. **Скачивание PDF**: При получении ответа от `/export_pdf/` создавайте Blob (`new Blob([response.data], { type: 'application/pdf' })`) и скачивайте через виртуальный `<a download>`.
3. **Rust Core Ready**: Все структуры данных являются плоскими и строго типизированными. При миграции движка на Rust схемы запросов и ответов останутся идентичными на 100%.
