# fakt-api-python

A thin, typed **Python client for the [fakt.no](https://fakt.no) public job-market API** — jobs, employers, salary, recruitment patterns, market insights and bulk exports.

> fakt continuously observes the official **NAV Arbeidsplassen** feed for job postings and builds historical value over time. Data is combined with **SSB** (salary / income) and the **Brønnøysundregistrene** (company registry).

This package is only a thin HTTP wrapper around the public endpoints — it contains **no backend logic, scoring algorithms or data processing**.

- **API documentation:** [github.com/Fakt-no/fakt-api](https://github.com/Fakt-no/fakt-api)
- **Base URL:** `https://fakt.no/api/v1`
- **OpenAPI 3.0:** [`openapi.yaml`](https://github.com/Fakt-no/fakt-api/blob/main/openapi.yaml)

---

## Install

```bash
pip install fakt-api
```

## Quick start

```python
from fakt_api import FaktClient

# Demo mode (no key) — read-only, ~50 requests/day per IP
client = FaktClient()

# ...or with your API key
client = FaktClient(api_key="YOUR_API_KEY_HERE")

# Search jobs
data = client.jobs(q="sykepleier", county="Oslo", limit=10)
for job in data["items"]:
    print(job["title"], "—", job.get("location"), "—", job.get("category"))
```

---

## Authentication

Pass an optional `api_key` to the constructor. If you omit it, the client uses the API's **demo tier** (no `X-API-Key` header), which is read-only and limited to **50 requests/day per IP**. Create a key from [fakt.no/dashboard](https://fakt.no/dashboard) — keys are shown once at issue time (stored hashed).

The client sends the key automatically as the `X-API-Key` header on every request.

---

## Methods

All methods map 1:1 to the endpoints in [`openapi.yaml`](https://github.com/Fakt-no/fakt-api/blob/main/openapi.yaml) — nothing is invented.

| Method | Endpoint | Notes |
| --- | --- | --- |
| `client.jobs(...)` | `GET /jobs` | `q`, `county`, `category`, `postal`, `radius_km`, `sort`, `limit`, `offset` |
| `client.job(id)` | `GET /jobs/{id}` | |
| `client.similar_jobs(id)` | `GET /jobs/{id}/similar` | |
| `client.employers(...)` | `GET /employers` | `q`, `limit` |
| `client.employer(name)` | `GET /employers/{name}` | |
| `client.recruitment(...)` | `GET /recruitment` | `sort`, `q`, `limit` |
| `client.recruitment_audit()` | `GET /recruitment/audit` | |
| `client.events(...)` | `GET /events` | `after`, `limit` |
| `client.stream()` | `GET /stream` | returns raw SSE text |
| `client.watchlists()` | `GET /watchlists` | |
| `client.create_watchlist(...)` | `POST /watchlists` | `name`, `q`, `postal`, `radius_km` |
| `client.watchlist(id)` | `GET /watchlists/{id}` | |
| `client.delete_watchlist(id)` | `DELETE /watchlists/{id}` | |
| `client.market()` | `GET /market` | |
| `client.market_salary(...)` | `GET /market/salary` | Pro plan+ — `category`, `occupation`, `county`, `source`, `limit` |
| `client.market_history(...)` | `GET /market/history` | `days` |
| `client.market_timetofill(...)` | `GET /market/timetofill` | `category`, `county` |
| `client.usage()` | `GET /usage` | quota & traffic telemetry |
| `client.export_jobs(...)` | `GET /export/jobs` | NDJSON, plan-gated |
| `client.export_employers(...)` | `GET /export/employers` | NDJSON |
| `client.export_events(...)` | `GET /export/events` | NDJSON |

---

## Rate limits & quota

Every response's limit headers are stored on the client, so you can inspect usage after a call:

```python
data = client.jobs(limit=5)
print("quota remaining:", client.quota_remaining)     # X-Quota-Remaining
print("daily remaining:", client.daily_remaining)     # X-Daily-Remaining
print("rate-limit remaining:", client.rate_limit_remaining)  # X-RateLimit-Remaining
```

**Plan limits** (from the [main API README](https://github.com/Fakt-no/fakt-api)):

| Plan | /min | /day | /month |
| --- | --- | --- | --- |
| Demo (no key) | 10 | 50 (per IP) | ~1,500 |
| Free | 10 | 50 | 1,500 |
| Pro | 60 | 1,000 | 30,000 |
| Business | 300 | 10,000 | 300,000 |
| Enterprise | 1,000 | 100,000 | 3,000,000 |

---

## Errors

The client raises specific exceptions with the API's own error message included:

| Exception | HTTP | Meaning |
| --- | --- | --- |
| `FaktAuthError` | 401 | Invalid / missing API key |
| `FaktPermissionError` | 403 | Key expired or endpoint not on your plan |
| `FaktNotFoundError` | 404 | Resource not found |
| `FaktRateLimitError` | 429 | Quota exceeded |
| `FaktError` | other | Base error, includes status + body |

```python
from fakt_api import FaktClient

client = FaktClient(api_key="YOUR_API_KEY_HERE")
try:
    client.market_salary(category="Sykepleier")
except FaktPermissionError as e:
    print("Need a higher plan:", e)   # "This endpoint requires an API key (Pro plan or higher)..."
```

`FaktError.status` also gives you the HTTP status code.

---

## License

MIT — see [`LICENSE`](./LICENSE).
