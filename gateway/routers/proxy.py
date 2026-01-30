"""
Request proxying from gateway to backend.
"""

import logging
import httpx
from fastapi import APIRouter, Request
from fastapi.responses import Response
from gateway.dependencies import gateway_state


router = APIRouter(tags=["Proxy"])


@router.api_route(
    "/api/external/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
)
async def proxy_to_backend(path: str, request: Request):
    """
    Proxy requests from /api/external/* to backend /api/internal/*.

    Transformation:
    - /api/external/users/john → /api/internal/users/john
    - /api/external/features/... → /api/internal/features/...

    Forwards:
    - Method (GET, POST, PUT, DELETE, PATCH)
    - Headers
    - Query parameters
    - Request body
    - Session info via request.state (set by middleware)

    Returns backend response with same status, headers, and content.
    """
    # Transform path: /api/external/* → /api/internal/*
    backend_path = f"/api/internal/{path}"

    # Build full backend URL
    backend_url = f"{gateway_state.backend_url}{backend_path}"

    # Get query parameters
    query_params = dict(request.query_params)

    # Get headers (exclude host header to avoid conflicts)
    headers = dict(request.headers)
    headers.pop("host", None)

    # Get request body (if any)
    try:
        body = await request.body()
    except Exception as e:
        logging.error(f"GATEWAY: Error reading request body: {e}")
        body = b""

    # Log request
    logging.debug(
        f"GATEWAY: Proxying {request.method} {backend_url} (from {request.url.path})"
    )

    # Forward request to backend
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            backend_response = await client.request(
                method=request.method,
                url=backend_url,
                params=query_params,
                headers=headers,
                content=body,
            )

            # Log response
            logging.debug(
                f"GATEWAY: Backend response {backend_response.status_code} for {backend_url}"
            )

            # Return backend response
            return Response(
                content=backend_response.content,
                status_code=backend_response.status_code,
                headers=dict(backend_response.headers),
            )

        except httpx.TimeoutException:
            logging.error(f"GATEWAY: Backend timeout for {backend_url}")
            return Response(
                content=b'{"detail": "Backend request timeout"}',
                status_code=504,
                media_type="application/json",
            )

        except httpx.RequestError as e:
            logging.error(f"GATEWAY: Backend request error for {backend_url}: {e}")
            return Response(
                content=b'{"detail": "Backend request failed"}',
                status_code=502,
                media_type="application/json",
            )
