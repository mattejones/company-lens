# Company Lens

A tool for enriching [Companies House](https://www.gov.uk/government/organisations/companies-house) data with verified domain information.

Given a company name or registration number, Company Lens queries the Companies House API, uses an LLM to infer likely domain names, and verifies candidates through DNS, WHOIS, and web scraping — producing a ranked list of probable matches.

The resulting dataset links structured company data to real-world web presence, and is designed to be reusable across other projects.

---

## How it works

1. **Lookup** — search for a company via the Companies House API
2. **Infer** — an LLM generates candidate domain names based on company metadata
3. **Verify** — candidates are checked against DNS, WHOIS, and scraped for content signals
4. **Rank** — results are scored and stored for reuse

---

## Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js, Tailwind CSS, shadcn/ui |
| API | Python, FastAPI |
| Queue | Redis, Celery |
| Database | PostgreSQL |
| Infrastructure | Docker Compose |

---

## Getting started

### Prerequisites

- [Docker](https://www.docker.com/) and Docker Compose

### Setup

```bash
git clone https://github.com/mattejones/company-lens.git
cd company-lens
cp .env.example .env
# Fill in your API keys in .env
docker compose up
```

The app will be available at `http://localhost:3000`.

---

## Project status

Early development. Core pipeline is not yet complete.
