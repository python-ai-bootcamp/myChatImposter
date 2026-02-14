"""
Authentication dependencies for FastAPI routes.
"""
from typing import Optional, Tuple
from fastapi import Request, HTTPException, Depends, status
from dependencies import GlobalStateManager, get_global_state
import logging

async def get_current_user(
    request: Request, 
    state: GlobalStateManager = Depends(get_global_state)
) -> object:
    """
    Extracts user session from request state (Gateway) OR headers (Backend).
    Returns object with user info or raises 401.
    """
    # 1. Check if session is already attached (Gateway Middleware)
    session = getattr(request.state, "session", None)
    if session:
        return session
        
    # 2. Check for attributes passed from Gateway (Backend mode)
    user_id = request.headers.get("X-User-Id")
    if user_id:
        # Trust the Gateway's authentication
        # We need to fetch the user's role and details to populate the session-like object
        # Using auth_service to fetch credentials
        if not state.auth_service:
             # Should not happen if initialized correctly
             logging.error("Auth Service not initialized in backend.")
             raise HTTPException(status_code=500, detail="Internal Auth Error")
             
        user = await state.auth_service.get_credentials(user_id)
        if user:
            # UserAuthCredentials has .role, .user_id, .owned_bots
            # It matches the interface needed by require_admin and others
            return user
            
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated"
    )

async def require_admin(
    session: dict = Depends(get_current_user)
) -> dict:
    """
    Dependency that ensures the user is an administrator.
    """
    # Session object from middleware is likely an object, not a dict, 
    # but let's handle attribute access safely
    role = getattr(session, "role", None)
    logging.info(f"AUTH_DEBUG: require_admin check. User: {getattr(session, 'user_id', 'unknown')}, Role: {role}")
    if role != "admin":
        logging.warning(f"AUTH_DEBUG: Access denied for {getattr(session, 'user_id', 'unknown')}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administration privileges required"
        )
    return session

def require_user_or_admin(user_id_param_name: str = "id"):
    """
    Factory for a dependency that checks if the requestor is Admin OR the specific user.
    """
    async def _check_access(
        request: Request,
        session: dict = Depends(get_current_user)
    ):
        # get target user_id from path params
        target_user_id = request.path_params.get(user_id_param_name)
        
        current_role = getattr(session, "role", None)
        current_user_id = getattr(session, "user_id", None)
        
        if current_role == "admin":
            return session
            
        if current_user_id == target_user_id:
            return session
            
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    return _check_access
