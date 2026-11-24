"""One HTTP GET helper with retries, shared by every candidate fetcher.

Transient failures (timeouts, connection resets, HTTP 429 and 5xx) are retried with
growing pauses. A Retry-After header is honoured (capped). Other HTTP errors, such as
403 quota errors from the YouTube API, fail at once: retrying them only burns quota.
"""

from __future__ import annotations

import socket
import time
import urllib.error
import urllib.request

RETRY_STATUS = {429, 500, 502, 503, 504}
DEFAULT_PAUSES = (5, 20, 60)  # seconds before attempts 2, 3 and 4
MAX_RETRY_AFTER = 120
USER_AGENT = "northstar/1.0 (+https://github.com/tarun-bisht/northstar)"

_sleep = time.sleep  # tests replace this


def _retry_after(err: urllib.error.HTTPError) -> float | None:
    try:
        v = float(err.headers.get("Retry-After", ""))
    except (TypeError, ValueError, AttributeError):
        return None
    return min(max(v, 0.0), MAX_RETRY_AFTER)


def get(url: str, *, timeout: int = 30, headers: dict | None = None,
        pauses: tuple[float, ...] = DEFAULT_PAUSES) -> bytes:
    """GET `url` and return the body, retrying transient failures. Raises the last error."""
    h = {"User-Agent": USER_AGENT, **(headers or {})}
    last: Exception | None = None
    for attempt in range(len(pauses) + 1):
        if attempt:
            _sleep(wait)
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code not in RETRY_STATUS:
                raise
            last = e
            wait = _retry_after(e) or pauses[min(attempt, len(pauses) - 1)]
        except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError) as e:
            last = e
            wait = pauses[min(attempt, len(pauses) - 1)]
    assert last is not None
    raise last
