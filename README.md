# 🏃 Run Smart

![CI](https://github.com/DavidDC0de/Run-Smart/actions/workflows/ci.yml/badge.svg)

> **Train smarter, not just harder.**

Run Smart is a full-stack running training app. Tell it your goal race, race date, goal time, fitness and the days you can run, and it builds a personalised multi-week plan, then explains each week in plain English with AI.

It has a **FastAPI + PostgreSQL** backend and a **React + TypeScript** frontend, with Strava integration (OAuth 2.0) for training data and OpenAI for the explanations.

---

## 🎬 Demo

![Run Smart demo](docs/images/demo.gif)

---

## 📸 Screenshots

### AI workout explanation

![AI Workout Explanation](docs/images/AI_response1.png)

### API documentation (Swagger)

![Swagger API Documentation](docs/images/FastAPI_docs.png)

---

## 🚀 Features

- **Adaptive plan generator**: builds a periodised plan (Base → Build → Race-specific → Taper) for a 5K, 10K, half marathon or marathon, from the race date, goal time, weekly availability and current fitness.
- **Two ways to give your fitness**: enter it yourself, or connect **Strava** and let Run Smart work it out from your real runs.
- **AI week-by-week explanations**: for every week, an explanation of what each session is for and how it should feel. Generated on request with the OpenAI API, then saved, so each week is only ever generated once.
- **Weekly plan view**: all weeks in one list with the current week opened automatically, showing each session's day, type, distance and pace.
- **Accounts**: sign up and log in with JWT authentication. Every user only ever sees their own plans.
- **Strava integration**: connect, sync recent runs, disconnect (which also removes the imported runs).

---

## 🧠 How the training plans work

```text
Base → Build → Race-Specific → Taper
```

| Phase | Focus |
| --- | --- |
| **Base** | Build aerobic capacity, consistent weekly mileage and gradually longer long runs |
| **Build** | Higher volume, plus tempo and interval sessions |
| **Race-specific** | Prepare for the demands of the chosen distance and target pace |
| **Taper** | Reduce volume, keep some intensity, arrive at race day fresh |

The plan changes with the race distance, race date, goal time, current pace, training days per week and which days you can run. The long run always goes on the last day you choose in the week.

### Example request

```json
{
  "goal_race_km": 21,
  "race_date": "2027-04-10",
  "training_days_per_week": 4,
  "available_days": ["Monday", "Thursday", "Friday", "Sunday"],
  "goal_time_min": 125,
  "current_5k_pace": 400
}
```

### Example week from a generated plan

| Day      | Session  | Distance | Target pace |
| -------- | -------- | -------: | ----------: |
| Monday   | Easy run |   4.0 km | 7:40 min/km |
| Thursday | Interval |   4.0 km | 6:30 min/km |
| Friday   | Easy run |   3.0 km | 7:40 min/km |
| Sunday   | Long run |   8.6 km | 7:25 min/km |

```json
{
  "week_number": 1,
  "phase": "base",
  "total_km": 20,
  "sessions": [
    { "day": "Monday",   "type": "easy",     "distance_km": 4.0, "pace_sec_per_km": 460 },
    { "day": "Thursday", "type": "interval", "distance_km": 4.0, "pace_sec_per_km": 390 },
    { "day": "Friday",   "type": "easy",     "distance_km": 3.0, "pace_sec_per_km": 460 },
    { "day": "Sunday",   "type": "long_run", "distance_km": 8.6, "pace_sec_per_km": 445 }
  ]
}
```

Paces are stored in **seconds per km** (460 = 7:40 /km).

---

## 🛠️ Tech stack

| Area | Technology | Why |
| --- | --- | --- |
| API | **FastAPI**, Python | Fast to build, automatic OpenAPI docs, request validation with Pydantic |
| Database | **PostgreSQL**, SQLAlchemy, **Alembic** | Relational data (users, runs, plans, sessions) with versioned migrations |
| Auth | JWT, bcrypt | Stateless login, hashed passwords |
| Integrations | **Strava API** (OAuth 2.0), **OpenAI API** | Real training data, natural-language explanations |
| Frontend | **React**, **TypeScript**, Vite | Type safety end to end |
| Styling | Tailwind CSS | Responsive, mobile-friendly layout |
| Data fetching | TanStack Query, React Router | Loading/error/caching states, protected routes |
| API client | `openapi-typescript` + `openapi-fetch` | Types generated from the backend's own OpenAPI spec |
| Testing | pytest, Vitest | Backend against a real Postgres, frontend unit tests |
| CI | GitHub Actions | Tests, migrations and build on every push |
| Infrastructure | Docker (PostgreSQL) | One command for a local database |

---

## 🏗️ Architecture

```text
        ┌──────────────────────────────┐
        │  React + TypeScript (Vite)   │
        │  typed client from OpenAPI   │
        └──────────────┬───────────────┘
                       │ HTTPS / JSON
                       ▼
        ┌──────────────────────────────┐
        │           FastAPI            │
        └──────────────┬───────────────┘
                       │
     ┌─────────────────┼──────────────────┐
     ▼                 ▼                  ▼
┌──────────┐   ┌───────────────┐   ┌──────────────┐
│   Auth   │   │ Plan generator│   │ Strava OAuth │
│ JWT +    │   │ + AI week     │   │ + run import │
│ bcrypt   │   │ explanations  │   │              │
└──────────┘   └───────┬───────┘   └──────┬───────┘
                       │                  │
                       ▼                  ▼
              ┌────────────────────────────────┐
              │  PostgreSQL (SQLAlchemy +      │
              │  Alembic migrations)           │
              └────────────────────────────────┘
```

### Project layout

```text
Run-Smart/
├── backend/
│   ├── app/
│   │   ├── api/        # routes: user, plans, strava
│   │   ├── core/       # config, database, security
│   │   ├── models/     # SQLAlchemy models
│   │   ├── schemas/    # Pydantic request/response models
│   │   ├── services/   # plan generation, Strava import, AI explanations
│   │   └── tests/      # pytest suite
│   ├── alembic/        # database migrations
│   └── docker-compose.yml
├── frontend/
│   └── src/
│       ├── api/        # typed API client (schema.d.ts is generated)
│       ├── pages/      # login, plans, new plan, plan detail, Strava callback
│       └── components/
└── .github/workflows/ci.yml
```

---

## 🔌 API overview

Interactive docs are served at `http://127.0.0.1:8000/docs` when the backend is running.

| Method | Endpoint | Auth | Description |
| --- | --- | :-: | --- |
| `POST` | `/user/signup` | | Create an account |
| `POST` | `/user/login` | | Log in (form-encoded; the email goes in the `username` field) |
| `POST` | `/plans/generate_manual` | ✅ | Create a plan from manually entered fitness |
| `POST` | `/plans/generate` | ✅ | Create a plan from synced Strava runs |
| `GET` | `/plans` | ✅ | List your plans |
| `GET` | `/plans/{id}` | ✅ | Get one plan with all its weeks |
| `DELETE` | `/plans/{id}` | ✅ | Delete a plan |
| `GET` | `/plans/{id}/weeks/{n}/explanation` | ✅ | AI explanation for a week (generated once, then cached) |
| `GET` | `/strava/status` | ✅ | Is Strava connected? |
| `GET` | `/strava/connect` | ✅ | Get the Strava authorisation URL |
| `GET` | `/strava/callback` | | Strava redirects here, then on to the frontend |
| `GET` | `/strava/sync` | ✅ | Import recent runs |
| `DELETE` | `/strava/disconnect` | ✅ | Disconnect and remove imported runs |
| `GET` | `/health` | | Health check |

---

## ⚙️ Engineering notes

- **Typed end to end.** The frontend's API types are generated from the backend's OpenAPI spec. CI regenerates them and fails if the committed file is out of date, so the two sides cannot silently drift apart.
- **Validated input.** Race distance, date range, training days, day names and pace ranges are validated, so bad input gets a clear `422` rather than a server error.
- **Atomic plan creation.** A plan and all of its sessions are saved in one transaction: either everything is stored or nothing is.
- **AI cost control.** Creating a plan makes no AI call. Explanations are generated only when a week is requested, then stored, so each is paid for once. Failures return a clean error and save nothing.
- **Secure Strava flow.** The OAuth `state` is a signed, expiring token that can't be used as a login token, so a forged callback can't attach a Strava account to someone else. The callback always redirects back to the frontend with a status.
- **Ownership checks.** Another user's plan returns `404`, not `403`, so plan IDs can't be probed.
- **Resilient import.** Only runs are imported (not rides or walks), duplicates are skipped, and a heart-rate-zone failure (non-premium account, rate limit) doesn't stop a run from being saved.

---

## 🐳 Getting started

**Prerequisites:** Python 3.12+, Node.js 20.19+ (or 22), Docker.

### 1. Clone

```bash
git clone https://github.com/DavidDC0de/Run-Smart.git
cd Run-Smart
```

### 2. Start PostgreSQL

```bash
cd backend
docker compose up -d
```

This starts Postgres on port 5432 (user `postgres`, password `postgres`, database `runsmart`).

### 3. Configure the backend

Copy `backend/.env.example` to `backend/.env` and fill it in:

```env
SECRET_KEY=                         # a long random string, see below

DATABASE_HOSTNAME=localhost
DATABASE_PORT=5432
DATABASE_USERNAME=postgres
DATABASE_PASSWORD=postgres
DATABASE_NAME=runsmart

ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

STRAVA_CLIENT_ID=
STRAVA_CLIENT_SECRET=
STRAVA_REDIRECT_URI=http://localhost:8000/strava/callback

OPEN_AI_KEY=

# Optional: where the Strava callback sends the browser (default shown)
# FRONTEND_URL=http://localhost:5173
```

Generate a secret key with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

> Never commit API keys, secrets or your `.env` file. The Strava keys come from [strava.com/settings/api](https://www.strava.com/settings/api) (set the Authorization Callback Domain to `localhost`); the OpenAI key is only needed for the AI explanations.

### 4. Run the backend

```bash
python -m venv venv
# Windows:        venv\Scripts\activate
# macOS / Linux:  source venv/bin/activate

pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

The API is now at `http://127.0.0.1:8000` (docs at `/docs`).

### 5. Run the frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** (use `localhost`, not `127.0.0.1`, so the Strava redirect lands on the same address). The frontend finds the API through `VITE_API_URL` in `frontend/.env`.

If you change the backend API, regenerate the frontend types with the backend running:

```bash
npm run gen:api
```

---

## 🧪 Testing

CI runs everything below on every push and pull request (see `.github/workflows/ci.yml`):

| Job | What it checks |
| --- | --- |
| **Backend** | Migrations apply to an empty database, models and migrations are in sync, and the pytest suite passes against a real PostgreSQL |
| **Frontend** | Lint, Vitest unit tests, TypeScript type-check and production build |
| **API contract** | The frontend's generated API types match the backend's current OpenAPI spec |

The backend suite covers sign-up and login, plan creation and validation, ownership rules, the AI explanation cache, and the Strava connect and import flow. **OpenAI and Strava are faked in the tests**, so they need no network or API keys and cost nothing.

### Run the tests locally

The API tests use a real Postgres database and **wipe its tables**, so they only run against a database whose name contains `test` (anything else is refused). Create an empty one first:

```bash
docker compose exec db psql -U postgres -c "CREATE DATABASE runsmart_test;"
```

Then, from `backend/`:

```bash
pip install -r requirements-dev.txt

# macOS / Linux
export TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/runsmart_test
# Windows PowerShell
# $env:TEST_DATABASE_URL="postgresql://postgres:postgres@localhost:5432/runsmart_test"

pytest
```

Without `TEST_DATABASE_URL` the database tests are skipped and only the pure unit tests run. For the frontend, run `npm test` in `frontend/`.

---

## ⚠️ Strava note

A new Strava API application starts in a restricted mode where only the developer's own account can connect, so the live Strava flow is shown in the demo. Everything else, including plan generation from manually entered data, works for any account.

---

## 🔮 Future development

- Heart-rate-based adjustment of the fitness score, and shorter long runs in recovery weeks (both currently inactive)
- More advanced fitness scoring and training metrics
- Adaptive plan adjustments as the runner trains
- Expanded Strava analytics
- Richer AI coaching
- Deployment

---

## 💡 Motivation

Run Smart began as a backend project combining an interest in endurance training with API design, data modelling and third-party integrations. The frontend, tests and CI were added to make it a complete, shippable product.

> **Your goal. Your pace. Your schedule. Your plan.**

---

## 👨‍💻 Author

**David**, [github.com/DavidDC0de](https://github.com/DavidDC0de)

⭐ If you find the project interesting, consider starring the repository!
