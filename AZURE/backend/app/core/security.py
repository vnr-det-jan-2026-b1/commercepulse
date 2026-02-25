"""Simple API key auth, seller scoping, and rate limiting dependencies."""
import time
from collections import defaultdict, deque
from typing import Deque, Dict

from fastapi import Depends, Header, HTTPException, status

from app.core.config import settings


# ── API Key Auth ─────────────────────────────────────────────────
async def require_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> str:
    """Require X-API-Key header to match configured API key."""
    if not settings.API_KEY:
        # Misconfiguration on server; fail closed.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API key not configured on server",
        )
    if x_api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    return x_api_key


# ── Seller scope enforcement ────────────────────────────────────
async def enforce_seller_scope(
    seller_id: str | None = None,
    x_seller_id: str | None = Header(None, alias="X-Seller-Id"),
) -> str:
    """
    Best-effort multi-tenant safety.

    - If X-Seller-Id header is provided, it MUST match the seller_id
      parameter used in the route (prevents a client from querying a
      different seller's data when the UI is correctly wiring headers).
    - If the header is absent, the call is allowed (for backwards
      compatibility), but you should prefer always sending X-Seller-Id
      from the authenticated context on the frontend.
    """
    if x_seller_id is not None and x_seller_id != seller_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seller scope violation",
        )
    return seller_id


# ── In-memory rate limiting (best-effort) ────────────────────────
_REQUEST_LOGS: Dict[str, Deque[float]] = defaultdict(deque)


def rate_limiter(max_requests: int, window_seconds: int):
    """
    Returns a dependency that enforces a simple sliding-window
    limit per API key. Best-effort only (per-process, not shared
    across multiple replicas).
    """

    async def _limit(x_api_key: str = Depends(require_api_key)) -> None:
        now = time.time()
        q = _REQUEST_LOGS[x_api_key]

        # Drop entries outside the window
        while q and now - q[0] > window_seconds:
            q.popleft()

        if len(q) >= max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Try again later.",
            )

        q.append(now)

    return _limit

