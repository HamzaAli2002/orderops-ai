# OrderOps AI

Autonomous Order Triage & Resolution Agent - checks inventory automatically,
negotiates a substitute item with the customer by email when something is
out of stock (instead of just cancelling the order), and falls back to a
refund if the customer declines or doesn't respond.

Built as a Saylani Agentic AI course project.

---

## 1. Project structure

```
orderops-ai/
├── app/
│   ├── api/
│   │   ├── orders.py            # create/lookup order, negotiation response webhook + email link
│   │   ├── customers.py         # list customers (for the Streamlit dropdown)
│   │   ├── products.py          # list products (for the Streamlit dropdown)
│   │   └── metrics.py           # revenue recovery metric
│   ├── services/
│   │   ├── fraud_service.py
│   │   ├── inventory_service.py
│   │   ├── negotiation_service.py   # builds the negotiation email (with Accept/Reject links)
│   │   └── notification_service.py  # real SMTP send
│   ├── workflow/
│   │   ├── state.py             # LangGraph OrderState
│   │   ├── nodes.py             # node functions (await_customer_response uses interrupt())
│   │   └── graph.py             # StateGraph wiring, conditional edges
│   ├── config.py                 # Settings (reads .env)
│   ├── database.py               # SQLAlchemy async engine, session, Base
│   ├── models.py                  # all ORM models
│   ├── schemas.py                  # Pydantic request/response schemas
│   └── main.py                      # FastAPI app entrypoint
├── migrations/                # Alembic migrations (MySQL schema)
├── streamlit_app/             # Streamlit dashboard (navy/black theme, no emojis)
├── seed_data.py                # seeds ~100 products + ~20 customers into MySQL
├── tests/
├── requirements.txt
├── alembic.ini
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

## 2. How it works

1. A new order comes in through `POST /orders` (or via the Streamlit
   "Create test order" form, which pulls real customers/products from
   MySQL into dropdowns).
2. A LangGraph `StateGraph` runs the order through a pipeline of nodes:
   `check_fraud_risk -> validate_inventory -> generate_alternative ->
   send_negotiation -> await_customer_response -> finalize_order`.
3. If an item is out of stock, the agent picks an in-stock substitute from
   the same category, and emails the customer an offer with a discount and
   two links: **Accept substitute** and **Reject and refund me**.
4. `await_customer_response` calls `langgraph.types.interrupt()` - this is
   a genuine pause. The graph run suspends right there; `POST /orders`
   returns immediately with the order in `awaiting_response` status.
   Nothing upstream (fraud check, inventory check, negotiation) re-runs
   when the customer eventually responds.
5. Clicking either link in the email hits `GET /orders/{id}/respond`,
   which resumes the exact same paused run with
   `Command(resume=decision)` - "accepted" routes to fulfillment (item is
   swapped to the substitute), "rejected" routes to refund. The dashboard
   in Streamlit can do the same thing via `POST /orders/{id}/customer-response`.
6. Everything is logged to `audit_logs`, and recovery performance is
   exposed at `GET /metrics/revenue-recovery`.

See `app/workflow/graph.py` and `app/workflow/nodes.py` for the exact
routing logic and the `interrupt()` call.

**Note on the checkpointer:** it's in-memory (`MemorySaver`), rebuilt as a
process-wide singleton so a paused run survives between the initial
`POST /orders` call and the later resume call (email link click or
Streamlit button). This keeps setup dependency-free (no separate
checkpoint database/driver), but a paused negotiation is lost if the API
process restarts before the customer responds. Swap in a persistent
checkpointer (SQLite/Redis/Postgres) before this goes anywhere near
production.

## 3. Prerequisites

- Python 3.11+
- MySQL 8.x (or Docker, which bundles it)
- An SMTP account to send real negotiation emails (optional - without one,
  emails are printed to the console instead, and the rest of the flow
  still works via the Streamlit Accept/Reject buttons)

## 4. Backend setup

### 4.1 Clone and configure

```bash
git clone <your-repo-url>
cd orderops-ai
cp .env.example .env
```

`.env` defaults already match the bundled Docker MySQL container
(`orderops` / `orderops` / db `orderops`) - leave as-is if using Docker.

### 4.2 SMTP setup (optional but recommended)

To actually receive negotiation emails, fill in `.env`:

```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your.email@gmail.com
SMTP_PASSWORD=<a Gmail App Password, not your normal password>
SMTP_FROM_EMAIL=your.email@gmail.com
```

For Gmail: enable 2-Step Verification on the account, then create an App
Password at myaccount.google.com/apppasswords and use that as
`SMTP_PASSWORD`. Any other SMTP provider (Outlook, SendGrid SMTP relay,
your own mail server) works the same way - just change host/port.

Also set:

```
APP_BASE_URL=http://localhost:8000
TEST_CUSTOMER_EMAIL=you@example.com
```

`APP_BASE_URL` is used to build the Accept/Reject links in the email -
change it if the backend is reachable at a different host/port.
`TEST_CUSTOMER_EMAIL` is only read by `seed_data.py` (see section 6) - set
it to your real inbox so you receive actual negotiation emails during
testing.

Leaving SMTP settings blank is fine - emails are printed to the terminal
instead, and you can still resolve negotiations from the Streamlit
Negotiations page's Accept/Reject buttons.

### 4.3 Run with Docker (recommended)

```bash
docker compose up --build
```

Starts the FastAPI API (port 8000) and MySQL (port 3306).

### 4.4 Run migrations

```bash
docker compose exec api alembic upgrade head
```

Creates all six tables: `customers`, `products`, `orders`, `order_items`,
`negotiations`, `audit_logs`.

### 4.5 Or run locally without Docker

Install and start MySQL yourself, create a database and user matching
your `.env`, then:

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

### 4.6 Verify

```bash
curl http://localhost:8000/health
```

API docs: http://localhost:8000/docs

## 5. Streamlit dashboard setup

```bash
cd streamlit_app
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**Graphviz system package required** for the pipeline diagram:
- Windows: `choco install graphviz`
- Mac: `brew install graphviz`
- Ubuntu/Debian: `sudo apt install graphviz`

```bash
cp .env.example .env      # sets API_BASE_URL=http://localhost:8000
streamlit run app.py
```

Opens at http://localhost:8501. Start the FastAPI backend first, and seed
the database (section 6) or the dropdowns will be empty.

Pages:
- **Dashboard** (`app.py`) - KPI cards, agent pipeline diagram
- **Orders** - "Look up order" (status, pipeline position, negotiation
  history), or "Create test order" with live customer/product dropdowns
  pulled from MySQL
- **Negotiations** - view an order's negotiations and Accept/Reject them
  directly (does the same thing as clicking the email links)

## 6. Seeding demo data

The database starts empty. Seed ~20 customers and ~100 products across 8
categories:

```bash
python seed_data.py
```

Safe to run multiple times (skips anything that already exists, matched
by email/SKU). About 30% of products are randomly out of stock, so
ordering one of those triggers the negotiation/email flow; the rest go
straight to fulfillment.

One customer is special: it uses whatever email you set as
`TEST_CUSTOMER_EMAIL` in `.env`, so ordering as that customer sends a real
negotiation email to your own inbox (if SMTP is configured). Every other
seeded customer gets a placeholder `name@example.com` address.

The script prints the seeded IDs and a couple of example out-of-stock /
in-stock product IDs when it finishes - useful if you want to call the
API directly instead of going through Streamlit.

## 7. Testing

```bash
pytest
```

## 8. What's a stub vs. what's real

Real and wired up: FastAPI routes, SQLAlchemy models, Alembic migration,
LangGraph state machine with a genuine `interrupt()`/`Command(resume=...)`
pause-and-resume (verified end-to-end: fraud check does NOT re-run on
resume), real SMTP email with clickable Accept/Reject links, the
Streamlit dashboard talking to the live API with real MySQL-backed
dropdowns.

Intentionally stubbed - replace before production use:
- `app/services/fraud_service.py` - random risk score
- `app/services/negotiation_service.py` - naive same-category product
  match and a templated email; replace with real similarity search and
  an LLM call (`LLM_PROVIDER` / `OPENAI_API_KEY` / `GOOGLE_API_KEY` are
  already in `.env` for this)
- The checkpointer is in-memory (see the note in section 2)
- No timeout sweeper job for negotiations that never get a reply (the
  email says "24 hours", but nothing currently enforces that)
- No auth on any route

## 9. Pushing this project to GitHub

1. Create an empty repo on GitHub (no README/license, you already have
   files locally).
2. From the `orderops-ai/` folder:

   ```bash
   git init
   git add .
   git commit -m "Initial commit: OrderOps AI backend + Streamlit dashboard"
   git branch -M main
   git remote add origin https://github.com/<your-username>/orderops-ai.git
   git push -u origin main
   ```

3. If GitHub asks for authentication: Settings -> Developer settings ->
   Personal access tokens -> generate one with `repo` scope, use it in
   place of your password when prompted (or use `gh auth login` if you
   have the GitHub CLI).

4. Going forward:

   ```bash
   git add .
   git commit -m "Describe what changed"
   git push
   ```

**Before pushing:** double-check `.env` is in `.gitignore` (it is by
default) so your real SMTP password and other secrets never get
committed.

## 10. Environment variables reference

See `.env.example` (backend) and `streamlit_app/.env.example` (dashboard)
for the full list - MySQL connection, `APP_BASE_URL`, SMTP settings,
`TEST_CUSTOMER_EMAIL`, LLM provider keys, negotiation discount/timeout
policy, and the fraud risk threshold.
