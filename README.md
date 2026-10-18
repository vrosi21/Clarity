# Clarity

A full-stack Kanban task tracker with an embedded reinforcement-learning engine that assigns each
ticket to the best-suited team member, based on workload, skill profile and past performance.

**Authors:** Kemal Sivro (20015), Volodymyr Rodin (20188)
**Faculty of Electrical Engineering, University of Sarajevo** (Formal Models course)

## At a glance

| | |
|---|---|
| **Result** | Over 500 simulated sprints (~17.9k assignments) against a greedy baseline: makespan **-9.5%**, blocking rate **-43%**, load variance **-63%** |
| **RL agent** | Q-network written from scratch in NumPy (12-64-32-1, Adam, experience replay, target network) with Boltzmann exploration |
| **Skill matching** | Sentence-transformer cosine similarity replaces one-hot skill encoding, cutting the state from 17 to 12 dimensions |
| **Formal models** | Ticket lifecycle as a 6-state DFA with an enforced safety property; deadlock freedom checked by BFS over the LTS product state space; assignment specified as an MDP |
| **Architecture** | Route → Service → Repository → Model layering; new regressors and policies plug in as one subclass of an abstract base class |
| **Stack** | Python 3.13, FastAPI, PostgreSQL 16, SQLAlchemy, Alembic, NumPy, scikit-learn, sentence-transformers, LangChain + Groq, React 19, TypeScript, Vite, Docker |

Quick start: `cp .env.example .env`, then `docker compose up --build` and open <http://localhost:5173>.
Full setup below.

## What it does

As a product, Clarity lets teams create projects, move tickets through workflow stages, and have
work routed automatically. As a coursework project it shows formal modelling through working
code: the ticket lifecycle is a finite state machine with an enforced safety property, the
concurrent system is a labelled transition system checked by BFS reachability, and the
assignment algorithm is a Markov decision process.

---

## Table of contents

1. [Prerequisites](#1-prerequisites)
2. [Environment configuration](#2-environment-configuration)
3. [Getting a Groq API key](#3-getting-a-groq-api-key)
4. [Running with Docker (recommended)](#4-running-with-docker-recommended)
5. [Running locally without Docker](#5-running-locally-without-docker)
6. [Database migrations](#6-database-migrations)
7. [Tests](#7-tests)
8. [Machine-learning pipeline](#8-machine-learning-pipeline)
9. [Project structure](#9-project-structure)
10. [Formal models components](#10-formal-models-components)
11. [Troubleshooting](#11-troubleshooting)

---

## 1. Prerequisites

| Requirement | Version | Needed for |
|---|---|---|
| Docker + Docker Compose | any recent | Recommended path, runs everything |
| Python | 3.13 | Local backend, notebooks |
| Node.js | 20+ | Local frontend |
| PostgreSQL | 16 | Only if running without Docker |

Docker is the easiest route: it starts the database, backend, and frontend together, and you do
not need Python or Node installed locally.

---

## 2. Environment configuration

The repository ships with `.env.example`. **A real `.env` is not included**, so you must create one.

```bash
cp .env.example .env          # macOS / Linux
copy .env.example .env        # Windows
```

Then open `.env` and fill in the values:

```ini
POSTGRES_DB=clarity
POSTGRES_USER=clarity_user
POSTGRES_PASSWORD=<choose a password>
DATABASE_URL=postgresql://clarity_user:<same password>@db:5432/clarity
SECRET_KEY=<a long random string>

GROQ_API_KEY=<your key, see section 3>
GROQ_MODEL=openai/gpt-oss-120b
```

Notes:

- `DATABASE_URL` must use the host `db` when running under Docker (that is the service name in
  `docker-compose.yml`). If you run the backend directly on your machine, change it to `localhost`.
- `SECRET_KEY` signs JWTs. Any long random string works. Generate one with:
  `python -c "import secrets; print(secrets.token_urlsafe(48))"`
- `.env` is listed in `.gitignore` and must never be committed.

---

## 3. Getting a Groq API key

Clarity uses **Groq** (via LangChain) as its LLM layer for the smart-suggestion features:
category suggestions, story-point estimation, and tag extraction on the create-ticket form.

1. Go to <https://console.groq.com> and sign up. The free tier is sufficient.
2. Open **API Keys** and create a new key.
3. Copy the key into `GROQ_API_KEY` in your `.env`.

**The application runs fine without a key.** The LLM client is lazily constructed and only
instantiated when a suggestion endpoint is first hit; if the key is missing, the suggestion
endpoints degrade gracefully and return empty results rather than failing. Everything else (the
board, the FSM, the LTS verifier, and the RL assignment engine) works normally, because the RL
engine uses local NumPy and scikit-learn models rather than the LLM.

Model choice for `GROQ_MODEL`:

| Model | Trade-off |
|---|---|
| `openai/gpt-oss-120b` | Default. Fast, cheap, supports tools and structured output |
| `openai/gpt-oss-20b` | Faster and cheaper, slightly less accurate |
| `qwen/qwen3.8-27b` | Alternative if the GPT-OSS models are rate-limited |

Groq retires models regularly: a `model_not_found` 404 usually means the id was decommissioned,
not that your key is bad. List the ids your key can currently reach with:

```bash
curl -s https://api.groq.com/openai/v1/models -H "Authorization: Bearer $GROQ_API_KEY"
```

---

## 4. Running with Docker (recommended)

From the repository root, with `.env` in place:

```bash
docker compose up --build
```

This starts three containers:

| Service | URL | Notes |
|---|---|---|
| `db` | `localhost:5432` | PostgreSQL 16, data persisted in the `pgdata` volume |
| `backend` | <http://localhost:8000> | FastAPI. Interactive docs at `/docs` |
| `frontend` | <http://localhost:5173> | React + Vite dev server |

Health check: <http://localhost:8000/api/v1/health>

To stop, press `Ctrl+C`. To also delete the database volume and start clean:

```bash
docker compose down -v
```

---

## 5. Running locally without Docker

You will need PostgreSQL 16 running locally with a database matching your `.env`. Remember to
change the `DATABASE_URL` host from `db` to `localhost`.

**Backend:**

```bash
cd backend
python -m venv .venv

# activate
source .venv/bin/activate      # macOS / Linux
.venv\Scripts\activate         # Windows

pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

The backend serves on <http://localhost:8000>.

**Frontend** (in a second terminal):

```bash
cd frontend
npm install
npm run dev
```

The frontend serves on <http://localhost:5173> and proxies `/api` to the backend.

On Windows there are also convenience scripts (`scripts/dev-backend.ps1`,
`scripts/dev-frontend.ps1`) and an `mprocs.yaml` for running the database, backend, and frontend
in one terminal via [mprocs](https://github.com/pvolok/mprocs).

---

## 6. Database migrations

Schema is managed with Alembic. Under Docker, migrations run automatically on backend start
(see `backend/entrypoint.sh`). To run them manually:

```bash
cd backend
alembic upgrade head            # apply all migrations
alembic revision --autogenerate -m "description"   # create a new migration
alembic downgrade -1            # roll back one
```

---

## 7. Tests

```bash
cd backend
pytest
```

The suite covers authentication, project bootstrapping, ticket CRUD, the assignment service,
the permission registry, and, most relevant to the coursework, the FSM transition rules
(`test_fsm.py`, `test_tickets_fsm.py`) and the LTS reachability checker (`test_lts.py`).

---

## 8. Machine-learning pipeline

Because Clarity has no historical assignment data at deployment time, the regressor and RL agent
are pre-trained on synthetic data from a calibrated simulator.

**Trained model artefacts are not included in this repository.** They are large binaries
(hundreds of megabytes) and are regenerated by running the notebooks in order. The application
runs without them: assignment falls back to the non-RL policies until artefacts exist.

Run the notebooks from the `notebooks/` folder in this order:

| Notebook | Purpose |
|---|---|
| `00_nlp_embeddings.ipynb` | Builds sentence-transformer category embeddings |
| `01_data_generation.ipynb` | Runs the simulator; produces the synthetic dataset |
| `02_validation.ipynb` | Sanity checks, external calibration, sensitivity analysis |
| `03_regressor_training.ipynb` | Trains and compares four efficiency regressors |
| `04_rl_training.ipynb` | Trains the Q-network and compares assignment policies |

The notebooks are orchestration only: all logic lives in importable modules under
`backend/app/ml/`, so it is version-controlled and testable rather than buried in cells.

`02_validation.ipynb` downloads the public SiP effort-estimation dataset on first run for external
calibration. If you have no network access it falls back to a literature-derived reference
distribution, and the rest of the notebook still runs.

---

## 9. Project structure

```
Clarity/
├── backend/
│   ├── alembic/              # database migrations
│   ├── app/
│   │   ├── api/v1/routers/   # HTTP routes (thin)
│   │   ├── services/         # business logic
│   │   ├── repositories/     # database access
│   │   ├── models/           # SQLAlchemy ORM
│   │   ├── schemas/          # Pydantic request/response contracts
│   │   ├── core/             # config, database, FSM, LTS, permissions
│   │   └── ml/
│   │       ├── base/         # abstract base classes (extension points)
│   │       ├── agent/        # Q-network, replay buffer, trainer
│   │       ├── policies/     # random, round-robin, greedy, RL
│   │       ├── regressors/   # kNN, decision tree, linear, random forest
│   │       ├── recommenders/ # category, complexity, worker scoring
│   │       ├── simulation/   # synthetic data generator
│   │       └── langchain/    # Groq LLM suggestion layer
│   └── tests/
├── frontend/src/
│   ├── features/             # auth, projects, board, tickets, admin
│   ├── components/           # shared UI
│   ├── api/                  # API client + React Query hooks
│   └── types/
├── notebooks/                # ML pipeline (see section 8)
├── infra/docker/             # Dockerfiles
└── docker-compose.yml
```

The backend follows a strict layered flow, **Route → Service → Repository → Model**, and no
layer is skipped. The `app/ml/` and `app/core/` modules follow SOLID; adding a new regressor or
assignment policy means writing one subclass of the relevant abstract base class, with no changes
to existing code.

---

## 10. Formal models components

The parts most relevant to the coursework:

| Component | Location | What it does |
|---|---|---|
| Task FSM | `backend/app/core/fsm.py` | Six-state DFA over the ticket lifecycle. Validates every transition and raises `InvalidTransitionError` on any move that would violate the safety property |
| System LTS | `backend/app/core/lts.py` | Builds the product state space of N workers and M tickets, runs BFS reachability, checks safety and deadlock freedom |
| MDP / RL engine | `backend/app/ml/` | Assignment formalised as an MDP and solved with a NumPy Q-network using Boltzmann exploration |

The enforced safety property: **a ticket can never reach a FINAL stage without first passing
through a NORMAL stage**. In practice, nothing reaches DONE without going through IN_REVIEW.
This is checked at runtime on every transition by the FSM, and verified statically over the
reachable state space by the LTS checker.

The accompanying paper (`Clarity_IEEE.docx`) documents the formal specifications, the simulation
design, and the policy-comparison results.

---

## 11. Troubleshooting

**`docker compose up` fails with database connection errors.**
The backend waits for the database health check, but on a slow first start the database may still
be initialising. Run `docker compose up` again; the volume persists so the second start is faster.

**Suggestion features return nothing.**
This is expected without a `GROQ_API_KEY`. See section 3. The rest of the application is unaffected.

**`alembic upgrade head` fails with "target database is not up to date".**
Your local database is out of sync with the migration history. For a development database the
quickest fix is `docker compose down -v` followed by `docker compose up --build`, which recreates
the volume from scratch.

**Assignments are not being made automatically.**
The RL policy needs trained artefacts, which are not shipped with the repository. Run the
notebooks in section 8, or use a non-RL assignment policy in the meantime.

**Port already in use.**
Ports 5432, 8000, and 5173 must be free. Stop whatever is using them, or change the port mappings
in `docker-compose.yml`.
