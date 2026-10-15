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
export type AssetType = 'share' | 'bond' | 'etf' | 'currency';

export interface PositionDTO {
  ticker: string;              // Напр. "SBER", "OFZ-26238"
  name: string;                // Напр. "Сбербанк ПАО"
  asset_type: AssetType;       // 'share' | 'bond' | 'etf' | 'currency'
  quantity: number;            // Кол-во лотов/бумаг
  current_price: number;       // Текущая цена за единицу в рублях
  total_value: number;         // quantity * current_price
  share: number;               // Доля в портфеле (от 0.0 до 1.0)
  currency: string;            // По умолчанию "RUB"
}

export interface PortfolioAnalytics {
  total_value: number;                 // Общая стоимость в рублях
  hhi_index: number;                   // Индекс Херфиндаля-Хиршмана (0 - 10000)
  concentration_level: 'low' | 'moderate' | 'high'; // Оценка диверсификации
  asset_allocation: Record<AssetType, number>; // Доли активов: { share: 0.65, bond: 0.25, ... }
  top_holdings: PositionDTO[];         // Топ-5 позиций по стоимости
}

export interface PortfolioUploadResponse {
  positions: PositionDTO[];
  analytics: PortfolioAnalytics;
  client_id?: string;
  account_name: string;
}

export interface StressSimulationResult {
  loss_amount: number;         // Абсолютная просадка портфеля в рублях
  simulated_total: number;     // Новая стоимость портфеля после просадки
  market_drop_percent: number; // Напр. -15.0
  safe_capital: number;        // Стоимость защитных активов (облигации + валюта)
}

export interface RebalanceProposal {
  source_ticker: string;       // Из какого актива забираем средства
  target_ticker: string;       // Куда направляем (напр. "ОФЗ 26238")
  target_name: string;         // "ОФЗ с фикс. купоном"
  rebalance_amount: number;    // Рекомендуемая сумма переноса в рублях
  target_yield_percent: number;// Доходность инструмента (напр. 19.0)
  projected_annual_income: number; // Ожидаемый годовой пассивный доход
  old_hhi: number;             // HHI до ребалансировки
  new_hhi: number;             // Прогнозируемый HHI после ребалансировки
}

export interface SimulationResponse {
  stress: StressSimulationResult;
  rebalance: RebalanceProposal;
}

export interface ClientProfile {
  id: string;
  name: string;
  risk_profile: 'Консервативный' | 'Умеренный' | 'Агрессивный';
  total_aum: number;
  unrealized_pnl_pct: number;
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
  * `file`: файл (`.csv` или `.xlsx`, максимум 5MB)
  * `account_name` *(опционально)*: строковое имя счёта (по умолчанию `"Основной портфель"`)
  * `client_id` *(опционально)*: ID выбранного клиента

#### Пример ответа (`HTTP 200 OK`):
```json
{
  "account_name": "Основной портфель",
  "client_id": "client-1",
  "positions": [
    {
      "ticker": "SBER",
      "name": "Сбербанк",
      "asset_type": "share",
      "quantity": 1000.0,
      "current_price": 310.5,
      "total_value": 310500.0,
      "share": 0.621,
      "currency": "RUB"
    },
    {
      "ticker": "SU26238RMFS4",
      "name": "ОФЗ 26238",
      "asset_type": "bond",
      "quantity": 250.0,
      "current_price": 758.0,
      "total_value": 189500.0,
      "share": 0.379,
      "currency": "RUB"
    }
  ],
  "analytics": {
    "total_value": 500000.0,
    "hhi_index": 5292.8,
    "concentration_level": "high",
    "asset_allocation": {
      "share": 0.621,
      "bond": 0.379,
      "etf": 0.0,
      "currency": 0.0
    },
    "top_holdings": [
      {
        "ticker": "SBER",
        "name": "Сбербанк",
        "asset_type": "share",
        "quantity": 1000.0,
        "current_price": 310.5,
        "total_value": 310500.0,
        "share": 0.621,
        "currency": "RUB"
      }
    ]
  }
}
```

---

### 2. Стресс-тестирование и Ребалансировка
Рассчитывает влияние падения рынка акций и формирует предложение по снижению риска портфеля за счёт фиксации доходности в ОФЗ под высокую ставку.

* **URL**: `POST /api/v1/portfolio/simulate/`
* **Content-Type**: `application/json`

#### Тело запроса:
```json
{
  "positions": [
    {
      "ticker": "SBER",
      "name": "Сбербанк",
      "asset_type": "share",
      "quantity": 1000.0,
      "current_price": 310.5,
      "total_value": 310500.0,
      "share": 0.621,
      "currency": "RUB"
    },
    {
      "ticker": "SU26238RMFS4",
      "name": "ОФЗ 26238",
      "asset_type": "bond",
      "quantity": 250.0,
      "current_price": 758.0,
      "total_value": 189500.0,
      "share": 0.379,
      "currency": "RUB"
    }
  ],
  "drop_percent": 15.0,
  "target_ofz_rate": 19.0
}
```

#### Пример ответа (`HTTP 200 OK`):
```json
{
  "stress": {
    "loss_amount": 46575.0,
    "simulated_total": 453425.0,
    "market_drop_percent": 15.0,
    "safe_capital": 189500.0
  },
  "rebalance": {
    "source_ticker": "SBER",
    "target_ticker": "ОФЗ 26238",
    "target_name": "ОФЗ с фиксированным купоном",
    "rebalance_amount": 105000.0,
    "target_yield_percent": 19.0,
    "projected_annual_income": 19950.0,
    "old_hhi": 5292.8,
    "new_hhi": 3450.2
  }
}
```

---

### 3. Экспорт Векторного PDF-Отчёта
Генерирует официальный инвестиционный аудит для клиента с фирменным стилем Aegis Wealth, диаграммами распределения, метриками риска и скриптом советника.

* **URL**: `POST /api/v1/portfolio/export_pdf/`
* **Content-Type**: `application/json`
* **Response Content-Type**: `application/pdf`
* **Заголовки ответа**: `Content-Disposition: attachment; filename="audit_report.pdf"`

#### Тело запроса:
```json
{
  "account_name": "Иван Иванов — Основной",
  "positions": [
    {
      "ticker": "SBER",
      "name": "Сбербанк",
      "asset_type": "share",
      "quantity": 1000.0,
      "current_price": 310.5,
      "total_value": 310500.0,
      "share": 0.621,
      "currency": "RUB"
    }
  ]
}
```

---

### 4. Скачивание шаблонов портфеля
Позволяет пользователю в UI скачать эталонный CSV или XLSX файл с примером колонок.

* **URL**: `GET /api/v1/portfolio/template/?file_format=csv`  
  *(или `file_format=xlsx`)*
* **Response Content-Type**: `text/csv; charset=utf-8` или `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
* **Заголовки ответа**: `Content-Disposition: attachment; filename="portfolio_template.csv"`

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
| **400 Bad Request** | Файл отсутствует / неверный формат / повреждён | `{"error": "Не поддерживаемый формат файла. Загрузите .csv или .xlsx"}` |
| **400 Bad Request** | Размер файла превышает 5 МБ | `{"error": "Размер файла превышает 5 МБ"}` |
| **400 Bad Request** | Пустой список позиций в запросе | `{"positions": ["Обязательное поле."]}` |
| **429 Too Many Requests** | Превышен лимит запросов (Rate Limit) | `{"detail": "Request was throttled. Expected available in 30 seconds."}` |
| **500 Internal Error** | Внутренняя ошибка парсера / движка | `{"error": "Ошибка обработки файла: ..."}` |

---

## 💡 Примечания для Frontend-архитектуры

1. **State Management**: Рекомендуется хранить `PortfolioUploadResponse` в Zustand / Redux / Pinia. При переключении сценариев моделирования отправлять массив `positions` в `POST /simulate/`.
2. **Скачивание PDF**: При получении ответа от `/export_pdf/` создавайте Blob (`new Blob([response.data], { type: 'application/pdf' })`) и скачивайте через виртуальный `<a download>`.
3. **Rust Core Ready**: Все структуры данных являются плоскими и строго типизированными. При миграции движка на Rust схемы запросов и ответов останутся идентичными на 100%.
