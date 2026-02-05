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


@router.get("/api/external/users")
async def list_users_proxy(request: Request):
    """
    Interceptor for listing users.
    
    Logic:
    - User Role: Inject 'user_ids' from session ownership list.
    - Admin Role: Pass as is.
    """
    session = getattr(request.state, "session", None)
    if not session:
        # Should be caught by middleware, but safe fallback
        raise HTTPException(status_code=401, detail="Authentication required")

    backend_url = f"{gateway_state.backend_url}/api/internal/users"
    params = dict(request.query_params)
    headers = dict(request.headers)
    headers.pop("host", None)

    # Role-based filtering
    if session.role == "user":
        owned_ids = getattr(session, "owned_user_configurations", [])
        
        # If user owns nothing, short-circuit
        if not owned_ids:
            return JSONResponse(content=[], status_code=200)
            
        # Inject user_ids list
        # We must handle the fact that httpx expects 'key': 'val' or 'key': ['val1', 'val2']
        # Request.query_params might have multiple values for same key, dict() flattens it if not careful?
        # dict(request.query_params) returns last value if duplicate keys?
        # request.query_params.multi_items() is safer but lets simplify.
        # We are overwriting user_ids anyway.
        params["user_ids"] = owned_ids

    return await _forward_request(
        method="GET",
        url=backend_url,
        params=params,
        headers=headers,
        body=b"",
    )


@router.get("/api/external/users/status")
async def list_users_status_proxy(request: Request):
    """
    Interceptor for listing users status.
    
    Logic:
    - User Role: Inject 'user_ids' from session ownership list.
    - Admin Role: Pass as is.
    """
    session = getattr(request.state, "session", None)
    if not session:
        raise HTTPException(status_code=401, detail="Authentication required")

    backend_url = f"{gateway_state.backend_url}/api/internal/users/status"
    params = dict(request.query_params)
    headers = dict(request.headers)
    headers.pop("host", None)

    # Role-based filtering
    if session.role == "user":
        owned_ids = getattr(session, "owned_user_configurations", [])
        
        # If user owns nothing, short-circuit
        if not owned_ids:
            # Return empty structure matching UserStatusList
            return JSONResponse(content={"configurations": [], "count": 0}, status_code=200)
            
        params["user_ids"] = owned_ids

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
    # FILE LOGGING DEBUG
    with open("gateway_debug.txt", "a") as f:
        f.write(f"ENTRY: Path={path} | Method={request.method}\n")

    # Transform path: /api/external/* → /api/internal/*
    backend_path = f"/api/internal/{path}"
    backend_url = f"{gateway_state.backend_url}{backend_path}"

    # Get query parameters
    query_params = dict(request.query_params)

    # Get headers (exclude host header)
    headers = dict(request.headers)
    headers.pop("host", None)

    # Inject X-User-Id from session if available
    session = getattr(request.state, "session", None)
    if session:
        headers["X-User-Id"] = session.user_id

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

    # Interceptor: Pre-check for User Limit (PUT Creation)
    if request.method == "PUT":
        target_user_id = None
        parts = path.strip("/").split("/")
        # Valid Paths: /users/{id} or /ui/users/{id}
        if len(parts) == 2 and parts[0] == "users":
            target_user_id = parts[1]
        elif len(parts) == 3 and parts[0] == "ui" and parts[1] == "users":
            target_user_id = parts[2]
            
        if target_user_id:
             session = getattr(request.state, "session", None)
             if session and session.role == "user":
                  owned_ids = getattr(session, "owned_user_configurations", [])
                  
                  # FILE LOGGING DEBUG (Fixed Path)
                  with open("gateway/gateway_debug.txt", "a") as f:
                      f.write(f"CHECK: {session.user_id} | Target: {target_user_id} | Owned: {len(owned_ids)} {owned_ids}\n")
                  
                  # Force log to console
                  logging.info(f"GATEWAY_LIMIT_CHECK: User={session.user_id}, Target={target_user_id}, Count={len(owned_ids)}")

                  # Allow updates to existing owned users, Reject creation if limit reached
                  limit = getattr(session, "max_user_configuration_limit", 5)
                  if target_user_id not in owned_ids and len(owned_ids) >= limit:
                       with open("gateway/gateway_debug.txt", "a") as f:
                           f.write(f"BLOCK: {session.user_id} reached limit {limit}.\n")
                           
                       logging.warning(f"GATEWAY: User {session.user_id} reached limit ({limit}) trying to create {target_user_id}")
                       return JSONResponse(
                           status_code=403, 
                           content={"detail": f"You have reached your limit of {limit} concurrent users."}
                       )



    # Forward request
    response = await _forward_request(
        method=request.method,
        url=backend_url,
        params=query_params,
        headers=headers,
        body=body,
    )

    # Interceptor: PUT Creation (Ownership Claim)
    # Check if successful PUT to a user resource (either legacy or UI)
    if request.method == "PUT":
        logging.info(f"GATEWAY_DEBUG: Checking PUT for ownership. Path={path}, Status={response.status_code}")
        
    if request.method == "PUT" and response.status_code == 200:
        target_user_id = None
        parts = path.strip("/").split("/")
        logging.info(f"GATEWAY_DEBUG: Parts={parts}")
        
        # Case 1: Legacy /users/{user_id}
        if len(parts) == 2 and parts[0] == "users":
            target_user_id = parts[1]
        # Case 2: UI /ui/users/{user_id}
        elif len(parts) == 3 and parts[0] == "ui" and parts[1] == "users":
            target_user_id = parts[2]
            
        if target_user_id:
            session = getattr(request.state, "session", None)
            
            if session:
                logging.info(f"GATEWAY_DEBUG: Session User={session.user_id}, Role={session.role}, Owned={getattr(session, 'owned_user_configurations', [])}")
            else:
                logging.info("GATEWAY_DEBUG: No Session found in request state.")

            if session:
                # Check if we need to claim it
                owned_ids = getattr(session, "owned_user_configurations", [])
                
                if target_user_id not in owned_ids:
                    logging.info(f"GATEWAY: Claiming new bot {target_user_id} for user {session.user_id} (Role: {session.role})")
                    try:
                        # Update Persistence
                        await request.app.state.auth_service.add_owned_configuration(
                            session.user_id, target_user_id
                        )
                        # Update Cache
                        await request.app.state.session_manager.add_owned_configuration(
                            session.session_id, target_user_id
                        )
                    except Exception as e:
                        logging.error(f"GATEWAY: Failed to claim ownership: {e}")

    # Interceptor: DELETE (Ownership Removal)
    # Check if successful DELETE to a user resource
    if request.method == "DELETE" and response.status_code == 200:
        target_user_id = None
        parts = path.strip("/").split("/")
        
        # Case 1: Legacy /users/{user_id}
        if len(parts) == 2 and parts[0] == "users":
            target_user_id = parts[1]
        # Case 2: UI /ui/users/{user_id}
        elif len(parts) == 3 and parts[0] == "ui" and parts[1] == "users":
            target_user_id = parts[2]
            
        if target_user_id:
            session = getattr(request.state, "session", None)
            
            if session:
                owned_ids = getattr(session, "owned_user_configurations", [])
                
                if target_user_id in owned_ids:
                    logging.info(f"GATEWAY: Removing {target_user_id} from user {session.user_id}'s ownership")
                    try:
                        # Update Persistence (credentials collection)
                        await request.app.state.auth_service.remove_owned_configuration(
                            session.user_id, target_user_id
                        )
                        # Update Cache (session)
                        await request.app.state.session_manager.remove_owned_configuration(
                            session.session_id, target_user_id
                        )
                    except Exception as e:
                        logging.error(f"GATEWAY: Failed to remove ownership: {e}")

    return response
