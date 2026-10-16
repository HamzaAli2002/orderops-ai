# OrderOps AI

An agentic order-resolution system for e-commerce. When a customer orders an item that is out of stock, the agent does not cancel the order. It offers a discounted in-stock substitute by email, waits for the customer's decision, and then either updates the order or refunds it.

Built with FastAPI, LangGraph, SQLAlchemy, Alembic, MySQL and Streamlit.

## Workflow

```
New order
   |
   v
check_fraud_risk --(risk >= threshold)--> flag_manual_audit --> END
   |
   v
validate_inventory --(all in stock)--> finalize_order --> END (fulfilled)
   |
   v (an item is out of stock)
generate_alternative --> send_negotiation --> await_customer_response
                                                      |
                                    customer clicks Accept / Reject in the email
                                                      |
                                                      v
                                              finalize_order
                                  accepted -> item swapped, order fulfilled
                                  rejected -> order refunded
```

- `await_customer_response` uses LangGraph's `interrupt()`. The run genuinely pauses, and `POST /orders` returns with the order in `awaiting_response`.
- The email contains two links (Accept / Reject) that call `GET /orders/{id}/respond`. This resumes the same run with `Command(resume=decision)`. Earlier nodes are not re-executed.
- Clicking a link twice is safe: a negotiation that already has an answer is ignored.
- Every step is written to the `audit_logs` table.

## Tech stack

| Layer | Technology |
|---|---|
| Orchestration | LangGraph (StateGraph, conditional edges, `interrupt` / `Command`) |
| API | FastAPI (async) |
| Database | MySQL 8 |
| ORM / migrations | SQLAlchemy 2 (async, `aiomysql`) and Alembic (`pymysql`) |
| Email | SMTP (`smtplib`, run in a thread) |
| Dashboard | Streamlit with Graphviz |

## Project structure

```
orderops-ai/
├── app/
│   ├── api/
│   │   ├── orders.py          # create/get order, respond endpoints
│   │   ├── negotiations.py    # full negotiation history
│   │   ├── customers.py       # customer list
│   │   ├── products.py        # product list
│   │   └── metrics.py         # revenue recovery
│   ├── services/
│   │   ├── fraud_service.py
│   │   ├── inventory_service.py
│   │   ├── negotiation_service.py   # substitute selection + email body
│   │   └── notification_service.py  # SMTP sending
│   ├── workflow/
│   │   ├── state.py           # OrderState
│   │   ├── nodes.py           # graph nodes
│   │   └── graph.py           # StateGraph wiring
│   ├── config.py              # settings loaded from .env
│   ├── database.py            # async engine, session, Base
│   ├── models.py              # ORM models
│   ├── schemas.py             # Pydantic schemas
│   └── main.py                # FastAPI app
├── migrations/                # Alembic (initial MySQL schema)
├── streamlit_app/             # Dashboard
│   ├── app.py                 # Dashboard page
│   ├── pages/                 # Orders, Negotiations
│   └── lib/                   # API client, theme
├── tests/
├── seed_data.py               # demo data
├── Dockerfile
├── docker-compose.yml
├── alembic.ini
├── requirements.txt
└── .env.example
```

## Database

Six tables, created by `migrations/versions/0001_initial_schema.py`:

| Table | Purpose |
|---|---|
| `customers` | Name, email, phone, preferences |
| `products` | SKU, name, stock, price, category |
| `orders` | Status, risk score, timestamps |
| `order_items` | Product, quantity, stock status per order |
| `negotiations` | Offered substitute, discount, channel, customer response |
| `audit_logs` | Event trail per order |

Order statuses: `pending`, `risk_flagged`, `validating`, `negotiating`, `awaiting_response`, `fulfilled`, `refunded`, `cancelled`.

## Setup

### Prerequisites

- Python 3.11+
- MySQL 8 (local install, MySQL Workbench, or Docker)
- Graphviz system package (needed by the dashboard's pipeline diagram): https://graphviz.org/download/
- An SMTP account (optional, see below)

### 1. Install and configure

```bash
cd orderops-ai
python -m venv venv
venv\Scripts\activate            # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env             # Windows: copy .env.example .env
```

### 2. Create the MySQL database

```sql
CREATE DATABASE orderops;
CREATE USER 'orderops'@'localhost' IDENTIFIED BY 'orderops';
GRANT ALL PRIVILEGES ON orderops.* TO 'orderops'@'localhost';
FLUSH PRIVILEGES;
```

The defaults in `.env.example` match this. If you use different credentials, update `DATABASE_URL` and `ALEMBIC_DATABASE_URL`.

### 3. Run migrations

```bash
alembic upgrade head
```

### 4. Seed demo data

```bash
python seed_data.py
```

Inserts 100 products across 8 categories (about 30% out of stock) and 21 customers. One customer uses the email in `TEST_CUSTOMER_EMAIL`, so set that to your own inbox in `.env` before seeding. The script is safe to re-run.

### 5. Start the API

```bash
uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs

### 6. Start the dashboard

In a second terminal:

```bash
cd streamlit_app
pip install -r requirements.txt
cp .env.example .env
streamlit run app.py
```

Opens at http://localhost:8501.

### Docker (optional)

```bash
docker compose up --build
docker compose exec api alembic upgrade head
```

Inside the API container the database host is `db`, not `localhost`. Set `DATABASE_URL` and `ALEMBIC_DATABASE_URL` in `.env` to use `@db:3306` when running this way.

## Email (SMTP)

Set these in `.env` to send real negotiation emails:

```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your.email@gmail.com
SMTP_PASSWORD=<Gmail App Password>
SMTP_FROM_EMAIL=your.email@gmail.com
APP_BASE_URL=http://localhost:8000
```

For Gmail, turn on 2-Step Verification and create an App Password at myaccount.google.com/apppasswords. `APP_BASE_URL` is used to build the Accept / Reject links, so it must be reachable from wherever the customer opens the email.

If SMTP is not configured, the email is printed to the API terminal instead, and negotiations can still be resolved from the dashboard.

## Dashboard pages

- **Dashboard**: revenue recovery rate, agent pipeline diagram, recent negotiation history.
- **Orders**: look up an order (status, pipeline position, its negotiations), or create a test order using customer and product dropdowns loaded from MySQL.
- **Negotiations**: full negotiation history across all orders, plus Accept / Reject buttons for a given order (same effect as the email links).

## API reference

| Method | Endpoint | Description |
|---|---|---|
| POST | `/orders` | Create an order and run it through the agent |
| GET | `/orders/{id}` | Order with items |
| GET | `/orders/{id}/negotiations` | Negotiations for one order |
| POST | `/orders/{id}/customer-response` | Resume with a decision (JSON body) |
| GET | `/orders/{id}/respond?negotiation_id=&decision=` | Email link handler (`accepted` or `rejected`) |
| GET | `/negotiations?limit=` | Negotiation history, newest first |
| GET | `/customers` | Customer list |
| GET | `/products` | Product list |
| GET | `/metrics/revenue-recovery` | Accepted vs total negotiations |
| GET | `/health` | Health check |

## Configuration

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Async MySQL URL used by the API |
| `ALEMBIC_DATABASE_URL` | Sync MySQL URL used by Alembic |
| `APP_BASE_URL` | Base URL for email links |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`, `SMTP_USE_TLS` | Email delivery |
| `TEST_CUSTOMER_EMAIL` | Real email for the seeded test customer (read by `seed_data.py` only) |
| `NEGOTIATION_DISCOUNT_PCT` | Discount offered on the substitute |
| `FRAUD_RISK_THRESHOLD` | Orders at or above this score go to manual audit |
| `NEGOTIATION_RESPONSE_TIMEOUT_HOURS` | Shown in the email; not enforced yet |
| `LLM_PROVIDER`, `OPENAI_API_KEY`, `GOOGLE_API_KEY` | Reserved for LLM-written offers; not used yet |

The dashboard has its own `streamlit_app/.env` with `API_BASE_URL`.

## Testing

```bash
pytest
```

Covers the graph's conditional routing functions.

## Current limitations

- **Fraud check is a stub.** It returns a random score; replace `fraud_service.py` with real rules or a model.
- **Substitute selection is simple.** It picks any in-stock product from the same category. If none exists, the negotiation cannot be created.
- **Only the first out-of-stock item** in an order is negotiated.
- **Email text is templated.** The LLM settings are in place but not wired up.
- **Paused runs are held in memory** (`MemorySaver`). If the API restarts while a customer has not yet answered, that run is lost. A persistent checkpointer is needed for production.
- **No timeout handling.** An unanswered negotiation stays in `awaiting_response`.
- **Dashboard gaps.** Active orders, pending negotiations and average processing time show placeholders because there is no order-list endpoint yet.
- **No authentication** on any endpoint.