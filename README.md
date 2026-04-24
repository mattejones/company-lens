# Company Lens

> Enrich UK Companies House data with verified, LLM-inferred domain intelligence.

Company Lens bridges the gap between a registered company and its real-world web presence. Given a company name or registration number, it queries the Companies House API, uses a two-stage LLM pipeline to infer and rank likely domain names, then verifies each candidate through DNS, WHOIS, HTTPS, SSL, and content signals — producing an auditable, ranked result with full diagnostic data.

The resulting dataset links structured company data to confirmed domains and is designed to compound in value over time: every human-verified lookup is a labelled training example.

---

## Why this exists

Most domain enrichment tools are black boxes. They return a domain with a confidence score and no explanation. Company Lens is different — every candidate has a reasoning field, a signal breakdown, and a full audit trail. You can see *why* the answer is what it is.

The most interesting signal isn't always the LLM's first guess. A redirect chain from `selcobuilders.co.uk → selcobw.com` surfaces the correct domain even when the trading name abbreviation ("BW" for Builders Warehouse) never appears in the registered company name. The verification layer finds answers the inference layer cannot.

---

## How it works

```
CH API → LLM Inference → Verification → LLM Ranking → Persisted Dataset
```

**Stage 1 — Inference**
The Companies House profile is sent to an LLM which generates up to 5 candidate domain names, considering international brand patterns, UK trading name conventions, SIC industry codes, and company type.

**Stage 2 — Verification**
Each candidate is checked in parallel:
- **DNS** — MX record presence (strongest signal), A record resolution, nameserver parking detection
- **HTTPS** — Reachability, redirect following (with HTTP fallback), status codes
- **SSL** — Certificate org field, Subject Alternative Names (often reveals sibling domains)
- **WHOIS** — Registration status, registrar, org field, creation date
- **Content** — Page title, OG tags, meta description scored via fuzzy matching against the company name

Redirect targets outside the candidate set are automatically promoted to new candidates and verified. Cross-candidate redirect signals are applied (if `monzo.co.uk → monzo.com`, this boosts `monzo.com`'s score).

**Stage 3 — Ranking**
A second LLM call receives all verified candidates as structured JSON and re-ranks them using explicit decision rules, detecting squatted/parked domains and identifying the canonical primary domain.

**Scoring**
Each candidate carries two scores:
- `verification_score` — composite of DNS, HTTPS, SSL, content signals
- `final_score` — weighted combination of LLM confidence (40%) and verification score (60%)

---

## Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15, Tailwind CSS |
| API | Python 3.12, FastAPI |
| Queue | Redis, Celery |
| Database | PostgreSQL 16 |
| LLM | OpenAI (gpt-4o, o3, o4-mini) or Ollama (self-hosted) |
| Structured output | `instructor` |
| Infrastructure | Docker Compose |

---

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (includes Docker Compose)
- [Companies House API key](https://developer.company-information.service.gov.uk/) — free registration
- OpenAI API key **or** a running [Ollama](https://ollama.com/) instance

---

## Setup

```bash
git clone https://github.com/your-username/company-lens.git
cd company-lens
cp .env.example .env
```

Edit `.env` with your credentials — see [Configuration](#configuration) below.

```bash
docker compose up --build
```

On first run, initialise the database:

```bash
docker compose exec backend alembic upgrade head
```

The app is now available at:
- **UI** → `http://localhost:3000`
- **API + Swagger** → `http://localhost:8000/docs`

---

## Configuration

All configuration lives in `.env`. Copy `.env.example` to get started.

```bash
# Database
POSTGRES_USER=company_lens
POSTGRES_PASSWORD=changeme          # change this

# Companies House
CH_API_KEY=your_key_here

# LLM — OpenAI (default)
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
LLM_BASE_URL=https://api.openai.com/v1
LLM_REASONING_EFFORT=              # low | medium | high
OPENAI_API_KEY=your_key_here

# LLM — Ollama (self-hosted alternative)
# LLM_PROVIDER=ollama
# LLM_MODEL=qwen3:8b
# LLM_BASE_URL=http://host.docker.internal:11434/v1
# OPENAI_API_KEY=ollama             # required by client, ignored by Ollama
```

### LLM provider notes

**OpenAI standard models** (`gpt-4o`, `gpt-4o-mini`): fastest, best structured output quality. Leave `LLM_REASONING_EFFORT` empty.

**OpenAI reasoning models** (`o3`, `o4-mini`): use `LLM_REASONING_EFFORT=medium` for domain inference. These models use a different API surface internally — the adapter handles this transparently.

**Ollama**: requires a running Ollama instance reachable from Docker. On Windows/Mac, `host.docker.internal` resolves to the host machine. Recommended models: `qwen3:8b` (best reasoning/speed balance on CPU), `qwen3:14b` (better quality, needs ~10GB RAM). CPU inference is significantly slower — expect 3-8 tokens/second.

---

## API

Full interactive documentation is available at `http://localhost:8000/docs`.

### Companies House

```
GET  /companies/search?q={query}          Search by name or registration number
GET  /companies/{company_number}          Fetch full company profile
```

### Pipeline

```
GET  /companies/{company_number}/infer    Trigger full enrichment pipeline (returns job_id)
POST /infer                               Trigger pipeline with pre-fetched CH data
```

Both endpoints return immediately with a `job_id`. The pipeline runs asynchronously.

### Jobs

```
GET  /jobs                                List all jobs with current status
GET  /jobs/{job_id}                       Poll job status — SUCCESS includes lookup_id
```

Job statuses: `PENDING` → `STARTED` → `SUCCESS` | `FAILURE`

### Lookups

```
GET  /lookups                             List all completed lookups
GET  /lookups/{lookup_id}                 Full lookup detail with all candidates
GET  /lookups/{lookup_id}/candidates      Candidates only
PUT  /lookups/{lookup_id}/verify          Set ground truth verified domain
```

The verify endpoint accepts `{"domain": "example.com", "verified_by": "human"}` and records the ground truth in the dataset. Human-verified results take precedence over automated ranking in the `/dataset/companies/{number}/best` endpoint.

### Dataset

```
GET  /dataset/companies                   All enriched companies
GET  /dataset/companies/{company_number}  Company detail with all lookups
GET  /dataset/companies/{company_number}/best   Best confirmed domain
```

---

## Testing

Tests use `pytest` with `pytest-asyncio`. Data API tests use SQLite in-memory — no database dependency required.

```bash
# Run all tests
docker compose exec backend pytest tests/ -v

# Run a specific test file
docker compose exec backend pytest tests/test_verification.py -v
```

The test suite covers:
- CH API client — search and company profile
- Domain inference — structured output, candidate ordering
- Verification — DNS signals, redirect injection, cross-candidate scoring, parking detection, content matching, HTTP fallback
- Inference routes — job dispatch, status polling, 404 on unknown jobs
- Data API — lookups, dataset, ground truth verification
- Routing integrity — catches the double-prefix bug if it reappears during merges

```bash
# Routing integrity test specifically (fast, no mocking)
docker compose exec backend pytest tests/test_routing.py -v
```

---

## Project structure

```
company-lens/
├── backend/
│   ├── api/
│   │   ├── config.py              # Pydantic settings — reads from .env
│   │   ├── main.py                # FastAPI app — NOTE: routers define their own prefixes
│   │   └── routes/
│   │       ├── companies.py       # CH API proxy routes
│   │       ├── inference.py       # Pipeline dispatch
│   │       ├── jobs.py            # Job status polling
│   │       ├── lookups.py         # Lookup detail and verification
│   │       └── dataset.py         # Dataset query endpoints
│   ├── db/
│   │   ├── models/                # SQLAlchemy models
│   │   ├── migrations/            # Alembic migrations
│   │   ├── repository.py          # DB write operations
│   │   └── session.py             # Engine and session factory
│   ├── prompts/                   # Jinja2 prompt templates
│   │   ├── domain_inference_system.j2
│   │   ├── domain_inference_user.j2
│   │   ├── domain_ranking_system.j2
│   │   └── domain_ranking_user.j2
│   ├── services/
│   │   ├── llm/                   # LLM adapter pattern
│   │   │   ├── base.py            # Protocol definition
│   │   │   ├── factory.py         # build_llm_adapter()
│   │   │   ├── openai_adapter.py  # OpenAI + reasoning models
│   │   │   └── ollama_adapter.py  # Ollama via OpenAI-compatible API
│   │   ├── companies_house.py     # CH API client
│   │   ├── domain_inference.py    # Stage 1 LLM
│   │   ├── domain_ranking.py      # Stage 2 LLM
│   │   └── verification.py        # DNS, WHOIS, HTTPS, SSL, content
│   ├── utils/
│   │   ├── content_matching.py    # rapidfuzz scoring, page fetch
│   │   ├── job_registry.py        # Redis job metadata store
│   │   ├── prompts.py             # Jinja2 template loader
│   │   ├── redirect_safety.py     # Redirect validation and safety checks
│   │   └── ssl_info.py            # SSL certificate extraction
│   ├── workers/
│   │   ├── celery_app.py          # Celery configuration
│   │   └── tasks/
│   │       └── pipeline.py        # fetch → infer → verify → rank → persist
│   └── tests/
├── frontend/
│   └── src/
│       ├── app/
│       │   ├── page.tsx           # Company search
│       │   ├── dataset/           # Enriched dataset browser
│       │   └── lookups/           # Job list and lookup detail
│       └── lib/
│           └── api.ts             # Typed API client
└── docker-compose.yml
```

---

## Database schema

The schema preserves full pipeline provenance — every lookup is reproducible.

| Table | Purpose |
|---|---|
| `companies` | Deduplicated CH company records |
| `ch_snapshots` | Immutable CH data at time of lookup — never updated |
| `pipeline_configs` | LLM model, prompt versions, scoring weights at time of lookup |
| `lookups` | One per pipeline run — links company, snapshot, config, and results |
| `inference_results` | Stage 1 raw LLM output, rendered prompts preserved |
| `domain_candidates` | All candidates with full signal data (JSONB) |
| `ranking_summaries` | Stage 2 LLM output — primary domain and summary |

Ground truth is recorded on `lookups.verified_domain_id` with `verified_by` and `verified_at`. Human-verified results take precedence over automated ranking.

---

## Known limitations

- **Bulk processing** — the pipeline is designed for one-off lookups. Bulk dispatch is a planned follow-on.
- **CPU inference speed** — Ollama on CPU is 3-8 tokens/second. A full pipeline run takes 5-10 minutes without GPU acceleration.
- **Trading names** — the CH registered name sometimes differs significantly from the trading name (e.g. "SELCO BUILDERS WAREHOUSE" registered as a holding company). The redirect injection step mitigates this but cannot always close the gap. CH previous names are not yet fetched.
- **WHOIS reliability** — WHOIS data quality varies significantly by registrar. Raw data is preserved for future LLM-based parsing.
- **CH API rate limiting** — no backoff strategy is implemented. At high volume, requests may be throttled.

---

## Adding a new LLM provider

The LLM adapter pattern makes this straightforward:

1. Create `backend/services/llm/your_provider_adapter.py` implementing the `complete()` method
2. Add an `elif` branch in `backend/services/llm/factory.py`
3. Add any new config fields to `api/config.py` and `.env.example`

No service code changes required.

---

## Branching strategy

```
main        — stable releases only, never pushed to directly
develop     — integration branch
feature/*   — individual features, PR into develop
```

Branch protection is configured on `main` — all changes require a pull request.

---

## Project status

Active development. Core pipeline is complete and functional. See [Known limitations](#known-limitations) for current gaps.
