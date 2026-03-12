"""
Firebase JWT verification and seller scope enforcement.
Cloud Endpoints injects X-Seller-Id after verifying the Bearer token.
In development mode, accepts a plain seller_id header for testing.
"""
import os
from fastapi import Header, HTTPException, Query, status

# In production, Cloud Endpoints validates JWT and injects this header.
# In dev, we skip verification and use the query param directly.
DEV_MODE = os.getenv("CP_DEV_MODE", "false").lower() == "true"


async def get_authenticated_seller(
    x_seller_id: str | None = Header(default=None, alias="X-Seller-Id"),
) -> str:
    """
    Extract the authenticated seller_id from the header injected by Cloud Endpoints.
    In dev mode, returns a default test seller.
    """
    if x_seller_id:
        return x_seller_id
    if DEV_MODE:
        return "test-seller-001"
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing authentication. X-Seller-Id header required.",
    )


async def enforce_seller_scope(
    seller_id:    str = Query(..., description="Seller ID to query"),
    auth_seller:  str = Header(default=None, alias="X-Seller-Id"),
) -> str:
    """
    Ensure the seller_id in the query matches the authenticated seller.
    Prevents cross-seller data access.
    """
    if DEV_MODE:
        return seller_id

    if not auth_seller:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated.",
        )

    if auth_seller != seller_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: seller_id does not match authenticated user.",
        )

    return seller_id
