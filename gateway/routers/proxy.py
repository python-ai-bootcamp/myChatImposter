"""
Request proxying from gateway to backend.
"""

import logging
import httpx
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import Response, JSONResponse
from gateway.dependencies import gateway_state


router = APIRouter(tags=["Proxy"])


async def _forward_request(
    method: str,
    url: str,
    params: dict,
    headers: dict,
    body: bytes,
) -> Response:
    """Helper to forward request to backend."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            backend_response = await client.request(
                method=method,
                url=url,
                params=params,
                headers=headers,
                content=body,
            )

            # Log response
            logging.debug(
                f"GATEWAY: Backend response {backend_response.status_code} for {url}"
            )

            return Response(
                content=backend_response.content,
                status_code=backend_response.status_code,
                headers=dict(backend_response.headers),
            )

        except httpx.TimeoutException:
            logging.error(f"GATEWAY: Backend timeout for {url}")
            return Response(
                content=b'{"detail": "Backend request timeout"}',
                status_code=504,
                media_type="application/json",
            )

        except httpx.RequestError as e:
            logging.error(f"GATEWAY: Backend request error for {url}: {e}")
            return Response(
                content=b'{"detail": "Backend request failed"}',
                status_code=502,
                media_type="application/json",
            )


@router.get("/api/external/bots")
async def list_bots_proxy(request: Request):
    """
    Interceptor for listing bots.
    
    Logic:
    - User Role: Inject 'bot_ids' from session ownership list.
    - Admin Role: Pass as is.
    """
    session = getattr(request.state, "session", None)
    if not session:
        # Should be caught by middleware, but safe fallback
        raise HTTPException(status_code=401, detail="Authentication required")

    backend_url = f"{gateway_state.backend_url}/api/internal/bots"
    params = dict(request.query_params)
    headers = dict(request.headers)
    headers.pop("host", None)

    # Role-based filtering
    if session.role == "user":
        owned_ids = getattr(session, "owned_bots", [])
        
        # If user owns nothing, short-circuit
        if not owned_ids:
            return JSONResponse(content=[], status_code=200)
            
        # Inject bot_ids list
        params["bot_ids"] = owned_ids

    return await _forward_request(
        method="GET",
        url=backend_url,
        params=params,
        headers=headers,
        body=b"",
    )


@router.get("/api/external/bots/status")
async def list_bots_status_proxy(request: Request):
    """
    Interceptor for listing bots status.
    
    Logic:
    - User Role: Inject 'bot_ids' from session ownership list.
    - Admin Role: Pass as is.
    """
    session = getattr(request.state, "session", None)
    if not session:
        raise HTTPException(status_code=401, detail="Authentication required")

    backend_url = f"{gateway_state.backend_url}/api/internal/bots/status"
    params = dict(request.query_params)
    headers = dict(request.headers)
    headers.pop("host", None)

    # Role-based filtering
    if session.role == "user":
        owned_ids = getattr(session, "owned_bots", [])
        
        # If user owns nothing, short-circuit
        if not owned_ids:
            # Return empty structure matching BotStatusList
            return JSONResponse(content={"configurations": [], "count": 0}, status_code=200)
            
        params["bot_ids"] = owned_ids

    return await _forward_request(
        method="GET",
        url=backend_url,
        params=params,
        headers=headers,
        body=b"",
    )


@router.api_route(
    "/api/external/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
)
async def proxy_to_backend(path: str, request: Request):
    """
    Generic proxy for all other requests.
    Includes Interceptor for PUT Creation (Ownership Claim).
    """
    # Transform path: /api/external/* → /api/internal/*
    
    # Determine target URL based on path prefix
    # Determine target URL based on path prefix
    if (path == "resources" or path.startswith("resources/") or 
        path == "users" or path.startswith("users/") or 
        path == "ui" or path.startswith("ui/") or
        path == "bots" or path.startswith("bots/")):
        # Map /api/external/resources -> /api/internal/resources
        # Map /api/external/users -> /api/internal/users
        # Map /api/external/ui -> /api/internal/ui
        # Map /api/external/bots -> /api/internal/bots
        backend_url = f"{gateway_state.backend_url}/api/internal/{path}"
    else:
        # Default to bots for backward compatibility (naked bot IDs)
        # Map /api/external/{bot_id}/... -> /api/internal/bots/{bot_id}/...
        backend_url = f"{gateway_state.backend_url}/api/internal/bots/{path}"

    # Get query parameters
    query_params = dict(request.query_params)

    # Get headers (exclude host header)
    headers = dict(request.headers)
    headers.pop("host", None)

    # Inject X-User-Id and X-User-Role from session if available
    session = getattr(request.state, "session", None)
    if session:
        headers["X-User-Id"] = session.user_id
        headers["X-User-Role"] = session.role

    # Get request body
    try:
        body = await request.body()
    except Exception as e:
        logging.error(f"GATEWAY: Error reading request body: {e}")
        body = b""

    # Log request
    logging.debug(
        f"GATEWAY: Proxying {request.method} {backend_url} (from {request.url.path})"
    )

    # Interceptor: Security Check (IDOR Prevention)
    # Ensure users can only access their own bots
    target_bot_id = None
    parts = path.strip("/").split("/")
    
    # Identify bot_id from path
    if len(parts) >= 2 and parts[0] == "bots":
        target_bot_id = parts[1]
    elif len(parts) >= 3 and parts[0] == "ui" and parts[1] == "bots":
        target_bot_id = parts[2]

    # Perform Check
    if target_bot_id:
        # Whitelist public resources that might look like bot IDs
        if target_bot_id in ["schema", "defaults"]:
            pass
        else:
            session = getattr(request.state, "session", None)
            if session and session.role == "user":
                owned_ids = getattr(session, "owned_bots", [])
                
                # 1. Block access to unowned bots (unless it's a creation request)
                # PUT is blocked by PermissionValidator for users. 
                # POST is for actions, PATCH is for Create/Update.
                if request.method != "POST" and request.method != "PATCH" and target_bot_id not in owned_ids:
                    logging.warning(f"GATEWAY: IDOR attempt by {session.user_id} on {target_bot_id}")
                    return JSONResponse(status_code=403, content={"detail": "Access denied."})
                
                # Special Case for POST (Actions on unowned bots) - Block unless whitelisted?
                # Actually, POST to /actions/link usually requires ownership.
                if request.method == "POST" and target_bot_id not in owned_ids:
                     logging.warning(f"GATEWAY: Unauthorized action attempt by {session.user_id} on {target_bot_id}")
                     return JSONResponse(status_code=403, content={"detail": "Access denied."})

                # 2. Bot Limit Check (for PATCH creation)
                # If PATCH and not owned, assume Creation attempt.
                if request.method == "PATCH" and target_bot_id not in owned_ids:
                       limit = getattr(session, "max_user_configuration_limit", 5)
                       if len(owned_ids) >= limit:
                            logging.warning(f"GATEWAY: User {session.user_id} reached limit ({limit}) trying to create {target_bot_id}")
                            return JSONResponse(
                                status_code=403, 
                                content={"detail": f"You have reached your limit of {limit} concurrent bots."}
                            )

    # Forward request
    response = await _forward_request(
        method=request.method,
        url=backend_url,
        params=query_params,
        headers=headers,
        body=body,
    )

    # Interceptor: PATCH Creation (Ownership Claim)
    # Check if successful PATCH to a bot resource
    if request.method == "PATCH" and response.status_code in [200, 201]:
        target_bot_id = None
        parts = path.strip("/").split("/")
        
        # Case 1: Legacy /bots/{bot_id}
        if len(parts) == 2 and parts[0] == "bots":
            target_bot_id = parts[1]
        # Case 2: UI /ui/bots/{bot_id}
        elif len(parts) == 3 and parts[0] == "ui" and parts[1] == "bots":
            target_bot_id = parts[2]
            
        if target_bot_id:
            session = getattr(request.state, "session", None)
            
            if session:
                # Check if we need to claim it
                owned_ids = getattr(session, "owned_bots", [])
                
                if target_bot_id not in owned_ids:
                    logging.info(f"GATEWAY: Claiming new bot {target_bot_id} for user {session.user_id} (Role: {session.role})")
                    try:
                        # Update Persistence
                        await request.app.state.auth_service.add_owned_configuration(
                            session.user_id, target_bot_id
                        )
                        # Update Cache
                        await request.app.state.session_manager.add_owned_configuration(
                            session.session_id, target_bot_id
                        )
                    except Exception as e:
                        logging.error(f"GATEWAY: Failed to claim ownership: {e}")

    # Interceptor: DELETE (Ownership Removal)
    # Check if successful DELETE to a bot resource
    if request.method == "DELETE" and response.status_code == 200:
        target_bot_id = None
        parts = path.strip("/").split("/")
        
        # Case 1: Legacy /bots/{bot_id}
        if len(parts) == 2 and parts[0] == "bots":
            target_bot_id = parts[1]
        # Case 2: UI /ui/bots/{bot_id}
        elif len(parts) == 3 and parts[0] == "ui" and parts[1] == "bots":
            target_bot_id = parts[2]
            
        if target_bot_id:
            session = getattr(request.state, "session", None)
            
            if session:
                owned_ids = getattr(session, "owned_bots", [])
                
                if target_bot_id in owned_ids:
                    logging.info(f"GATEWAY: Removing {target_bot_id} from user {session.user_id}'s ownership")
                    try:
                        # Update Persistence (credentials collection)
                        await request.app.state.auth_service.remove_owned_configuration(
                            session.user_id, target_bot_id
                        )
                        # Update Cache (session)
                        await request.app.state.session_manager.remove_owned_configuration(
                            session.session_id, target_bot_id
                        )
                    except Exception as e:
                        logging.error(f"GATEWAY: Failed to remove ownership: {e}")

    return response
