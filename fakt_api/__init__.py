"""fakt-api: a thin Python client for the fakt.no public job-market API."""

from .client import (
    DEFAULT_BASE_URL,
    FaktAuthError,
    FaktClient,
    FaktError,
    FaktNotFoundError,
    FaktPermissionError,
    FaktRateLimitError,
)

__version__ = "0.1.0"

__all__ = [
    "DEFAULT_BASE_URL",
    "FaktAuthError",
    "FaktClient",
    "FaktError",
    "FaktNotFoundError",
    "FaktPermissionError",
    "FaktRateLimitError",
    "__version__",
]
