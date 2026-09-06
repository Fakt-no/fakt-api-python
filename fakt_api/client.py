"""Thin Python client for the fakt.no public job-market API.

Wraps ``https://fakt.no/api/v1`` (documented at
https://github.com/Fakt-no/fakt-api). This is only a thin HTTP wrapper around
the public endpoints — it contains no backend logic, scoring or data
processing.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import requests

DEFAULT_BASE_URL = "https://fakt.no/api/v1"

__all__ = [
    "DEFAULT_BASE_URL",
    "FaktAuthError",
    "FaktClient",
    "FaktError",
    "FaktNotFoundError",
    "FaktPermissionError",
    "FaktRateLimitError",
]


class FaktError(Exception):
    """Base exception for fakt API errors."""

    def __init__(
        self,
        message: str,
        *,
        status: Optional[int] = None,
        response: Optional[requests.Response] = None,
    ) -> None:
        self.message = message
        self.status = status
        self.status_code = status
        self.response = response
        super().__init__(message)


class FaktAuthError(FaktError):
    """401 — invalid or missing API key."""


class FaktPermissionError(FaktError):
    """403 — key expired, or endpoint not available on your plan."""


class FaktNotFoundError(FaktError):
    """404 — resource not found."""


class FaktRateLimitError(FaktError):
    """429 — monthly, daily or per-minute quota exceeded."""


class FaktClient:
    """Minimal client for the fakt.no public API.

    Parameters
    ----------
    api_key:
        Optional fakt API key. If omitted the client uses **demo mode**
        (no ``X-API-Key`` header): read-only, ~50 requests/day per IP.
    base_url:
        Override the API base URL. Defaults to ``https://fakt.no/api/v1``.
    timeout:
        Request timeout in seconds (default 30).

    Example
    -------
    >>> client = FaktClient(api_key="YOUR_API_KEY_HERE")
    >>> data = client.jobs(q="sykepleier", county="Oslo", limit=10)
    >>> print(data["count"])
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 30.0,
    ) -> None:
        self.api_key = api_key
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.last_headers: Dict[str, str] = {}

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #
    @staticmethod
    def _clean(params: Dict[str, Any]) -> Dict[str, Any]:
        """Drop ``None`` values so we don't send empty query params."""
        return {k: v for k, v in params.items() if v is not None}

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
    ) -> Any:
        query = self._clean(params or {})
        headers = {"X-API-Key": self.api_key} if self.api_key else {}
        url = f"{self.base_url}{path}"

        resp = self.session.request(
            method,
            url,
            params=query,
            json=json_body,
            headers=headers,
            timeout=self.timeout,
        )
        self.last_headers = {k.lower(): v for k, v in resp.headers.items()}
        self._raise_for_status(resp)
        return self._parse(resp)

    @staticmethod
    def _parse(resp: requests.Response) -> Any:
        """Parse JSON, NDJSON and SSE responses."""
        if resp.status_code == 204 or not resp.content:
            return None
        ctype = resp.headers.get("content-type", "")
        if "ndjson" in ctype or "x-ndjson" in ctype:
            return [line for line in resp.text.splitlines() if line.strip()]
        if "event-stream" in ctype:
            return resp.text
        return resp.json()

    def _raise_for_status(self, resp: requests.Response) -> None:
        if resp.status_code in (200, 201):
            return
        message = self._extract_error(resp)
        status = resp.status_code
        if status == 401:
            raise FaktAuthError(message or "401 Unauthorized — invalid or missing X-API-Key", status=status, response=resp)
        if status == 403:
            raise FaktPermissionError(message or "403 Forbidden — endpoint not available on this plan", status=status, response=resp)
        if status == 404:
            raise FaktNotFoundError(message or "404 Not Found", status=status, response=resp)
        if status == 429:
            raise FaktRateLimitError(message or "429 Too Many Requests — quota exceeded", status=status, response=resp)
        raise FaktError(message or f"{status} {resp.reason}", status=status, response=resp)

    @staticmethod
    def _extract_error(resp: requests.Response) -> Optional[str]:
        try:
            data = resp.json()
        except Exception:
            return (resp.text or "").strip()[:200] or None
        if isinstance(data, dict):
            for key in ("error", "message", "detail", "reason"):
                value = data.get(key)
                if value:
                    return str(value)
        return None

    # ------------------------------------------------------------------ #
    # Rate-limit / quota headers from the last response
    # ------------------------------------------------------------------ #
    @property
    def quota_remaining(self) -> Optional[str]:
        return self.last_headers.get("x-quota-remaining")

    @property
    def quota_limit(self) -> Optional[str]:
        return self.last_headers.get("x-quota-limit")

    @property
    def daily_remaining(self) -> Optional[str]:
        return self.last_headers.get("x-daily-remaining")

    @property
    def rate_limit_remaining(self) -> Optional[str]:
        return self.last_headers.get("x-ratelimit-remaining")

    # ------------------------------------------------------------------ #
    # Jobs
    # ------------------------------------------------------------------ #
    def jobs(self, *, q=None, county=None, category=None, postal=None, radius_km=None, sort=None, limit=None, offset=None, **extra):
        """GET /jobs — search active jobs."""
        params = {
            "q": q, "county": county, "category": category, "postal": postal,
            "radius_km": radius_km, "sort": sort, "limit": limit, "offset": offset,
        }
        params.update(extra)
        return self._request("GET", "/jobs", params=params)

    def job(self, job_id, **extra):
        """GET /jobs/{id} — full enriched job."""
        return self._request("GET", f"/jobs/{job_id}", params=extra or None)

    def similar_jobs(self, job_id, **extra):
        """GET /jobs/{id}/similar — similar jobs."""
        return self._request("GET", f"/jobs/{job_id}/similar", params=extra or None)

    # ------------------------------------------------------------------ #
    # Employers
    # ------------------------------------------------------------------ #
    def employers(self, *, q=None, limit=None, **extra):
        """GET /employers — employer list with aggregates."""
        params = {"q": q, "limit": limit}
        params.update(extra)
        return self._request("GET", "/employers", params=params)

    def employer(self, name, **extra):
        """GET /employers/{name} — employer profile."""
        return self._request("GET", f"/employers/{name}", params=extra or None)

    # ------------------------------------------------------------------ #
    # Recruitment
    # ------------------------------------------------------------------ #
    def recruitment(self, *, sort=None, q=None, limit=None, **extra):
        """GET /recruitment — employer recruitment patterns."""
        params = {"sort": sort, "q": q, "limit": limit}
        params.update(extra)
        return self._request("GET", "/recruitment", params=params)

    def recruitment_audit(self):
        """GET /recruitment/audit — algorithm validation."""
        return self._request("GET", "/recruitment/audit")

    # ------------------------------------------------------------------ #
    # Changes
    # ------------------------------------------------------------------ #
    def events(self, *, after=None, limit=None, **extra):
        """GET /events — change-log events (keyset pagination)."""
        params = {"after": after, "limit": limit}
        params.update(extra)
        return self._request("GET", "/events", params=params)

    def stream(self):
        """GET /stream — SSE live stream of the change log (returns raw text)."""
        return self._request("GET", "/stream")

    # ------------------------------------------------------------------ #
    # Watchlists
    # ------------------------------------------------------------------ #
    def watchlists(self):
        """GET /watchlists — list saved searches."""
        return self._request("GET", "/watchlists")

    def create_watchlist(self, *, name=None, q=None, postal=None, radius_km=None, **extra):
        """POST /watchlists — create a saved search."""
        body = {"name": name, "q": q, "postal": postal, "radius_km": radius_km}
        body.update(extra)
        return self._request("POST", "/watchlists", json_body=body)

    def watchlist(self, watchlist_id, **extra):
        """GET /watchlists/{id} — new jobs since last check."""
        return self._request("GET", f"/watchlists/{watchlist_id}", params=extra or None)

    def delete_watchlist(self, watchlist_id, **extra):
        """DELETE /watchlists/{id} — delete a saved search."""
        return self._request("DELETE", f"/watchlists/{watchlist_id}", params=extra or None)

    # ------------------------------------------------------------------ #
    # Market
    # ------------------------------------------------------------------ #
    def market(self):
        """GET /market — market KPIs."""
        return self._request("GET", "/market")

    def market_salary(self, *, category=None, occupation=None, county=None, source=None, limit=None, **extra):
        """GET /market/salary — salary breakdown (Pro plan or higher)."""
        params = {"category": category, "occupation": occupation, "county": county, "source": source, "limit": limit}
        params.update(extra)
        return self._request("GET", "/market/salary", params=params)

    def market_history(self, *, days=None, **extra):
        """GET /market/history — daily market history."""
        params = {"days": days}
        params.update(extra)
        return self._request("GET", "/market/history", params=params)

    def market_timetofill(self, *, category=None, county=None, **extra):
        """GET /market/timetofill — time-to-fill statistics."""
        params = {"category": category, "county": county}
        params.update(extra)
        return self._request("GET", "/market/timetofill", params=params)

    # ------------------------------------------------------------------ #
    # Collector / exports
    # ------------------------------------------------------------------ #
    def usage(self):
        """GET /usage — traffic telemetry and quota status."""
        return self._request("GET", "/usage")

    def export_jobs(self, *, limit=None, offset=None, **extra):
        """GET /export/jobs — bulk NDJSON export of jobs (plan-gated)."""
        params = {"limit": limit, "offset": offset}
        params.update(extra)
        return self._request("GET", "/export/jobs", params=params)

    def export_employers(self, *, limit=None, offset=None, **extra):
        """GET /export/employers — bulk NDJSON export of employers."""
        params = {"limit": limit, "offset": offset}
        params.update(extra)
        return self._request("GET", "/export/employers", params=params)

    def export_events(self, *, limit=None, offset=None, **extra):
        """GET /export/events — bulk NDJSON export of the change log."""
        params = {"limit": limit, "offset": offset}
        params.update(extra)
        return self._request("GET", "/export/events", params=params)
