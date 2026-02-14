"""
User Management Router.
Handles CRUD operations for users, including validation and audits.
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from dependencies import GlobalStateManager, get_global_state
from auth_dependencies import require_admin, require_user_or_admin, get_current_user
from auth_models import UserAuthCredentials, UserResponse

router = APIRouter(prefix="/api/internal/users", tags=["User Management"])

# --- Models ---
# We'll use Pydantic models for requests/responses to ensure validation
from pydantic import BaseModel, Field, EmailStr

class UserCreateRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=30, pattern=r"^[a-zA-Z0-9_-]+$")
    password: str = Field(..., min_length=8)
    role: str = Field(..., pattern="^(admin|user)$")
    first_name: str = Field(default="Unknown")
    last_name: str = Field(default="User")
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    gov_id: Optional[str] = None
    country_value: str = "US"
    language: str = "en"

class UserUpdateRequest(BaseModel):
    # All fields optional for PATCH/PUT (we handle partials manually if needed, 
    # but for PUT usually all are required. Pydantic makes them required by default 
    # unless Optional. Let's start with a flexible model for both or separate them.)
    # For now, let's allow partial updates as the logic in service handles it.
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    gov_id: Optional[str] = None
    country_value: Optional[str] = None
    language: Optional[str] = None
    role: Optional[str] = None # Admin only
    
class PasswordResetRequest(BaseModel):
    password: str = Field(..., min_length=8)

# --- Routes ---

@router.get("", response_model=List[UserResponse])
async def list_users(
    session: object = Depends(require_admin),
    state: GlobalStateManager = Depends(get_global_state)
):
    """
    List all users (Admin only).
    """
    users = []
    # Project to hide password_hash by default? 
    # The response_model might expose it if we use UserAuthCredentials directly...
    # UserAuthCredentials *has* password_hash. We should probably exclude it or use a different model.
    # For now, let's trust the response_model mapping or explicitly exclude.
    # Actually, UserAuthCredentials includes password_hash. We should NOT return that.
    # Let's return raw dicts and let FastAPI filter? No, we need a safe model.
    
    cursor = state.credentials_collection.find({})
    async for doc in cursor:
        doc.pop("_id", None)
        doc.pop("password_hash", None) # Security: Remove hash
        users.append(doc)
    return users

@router.get("/{user_id}", dependencies=[Depends(require_user_or_admin("user_id"))])
async def get_user(
    user_id: str,
    state: GlobalStateManager = Depends(get_global_state)
):
    """
    Get specific user details (Admin or Self).
    """
    user = await state.auth_service.get_credentials(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Return as dict to exclude hash easily, or convert
    user_dict = user.model_dump()
    user_dict.pop("password_hash", None)
    return user_dict

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_user(
    request: Request,
    user_data: UserCreateRequest,
    session: dict = Depends(require_admin),
    state: GlobalStateManager = Depends(get_global_state)
):
    """
    Create a new user (Admin only).
    """
    # 1. Validate
    # Logic moved to service, but we check specific unique constraints here?
    # Service handles uniqueness.
    
    success, message = await state.auth_service.create_credentials(
        user_id=user_data.user_id,
        password=user_data.password,
        role=user_data.role,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        phone_number=user_data.phone_number or "",
        email=user_data.email or "",
        gov_id=user_data.gov_id or "",
        country_value=user_data.country_value,
        language=user_data.language
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
        
    # 2. Audit Log
    if state.audit_logs_collection is not None:
        from gateway.audit_logger import AuditLogger
        logger = AuditLogger(state.audit_logs_collection)
        # Session is an object (UserAuthCredentials or Session), so use attribute access
        current_user = getattr(session, "user_id", "unknown")
        await logger.log_event(
            event_type="user_created",
            user_id=current_user, # Who performed action
            details={"created_user_id": user_data.user_id, "role": user_data.role}
        )
        
    return {"status": "success", "user_id": user_data.user_id}

@router.put("/{user_id}")
async def update_user_full(
    request: Request,
    user_id: str,
    user_data: UserUpdateRequest,
    session: dict = Depends(require_admin), # STRICT SECURITY: Admin Only
    state: GlobalStateManager = Depends(get_global_state)
):
    """
    Update user details (Admin Only).
    Full update / Replace.
    """
    # 1. Fetch existing
    existing = await state.auth_service.get_credentials(user_id)
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")
        
    # 2. Last Admin Protection
    if existing.role == "admin" and user_data.role == "user":
        # Check if this is the last admin
        admin_count = await state.credentials_collection.count_documents({"role": "admin"})
        if admin_count <= 1:
            raise HTTPException(status_code=400, detail="Cannot demote the last administrator.")

    # 3. Update
    update_data = user_data.model_dump(exclude_unset=True)
    
    # Prevent changing user_id
    if "user_id" in update_data: del update_data["user_id"]
    
    result = await state.credentials_collection.update_one(
        {"user_id": user_id},
        {"$set": update_data}
    )
    
    # 4. Session Invalidation (If role changed)
    if "role" in update_data and update_data["role"] != existing.role:
        await state.session_manager.invalidate_all_sessions(user_id, reason="Role Changed")

    # 5. Audit
    if state.audit_logs_collection is not None:
        from gateway.audit_logger import AuditLogger
        logger = AuditLogger(state.audit_logs_collection)
        current_user = getattr(session, "user_id", "unknown")
        await logger.log_event(
            event_type="user_updated_full",
            user_id=current_user,
            details={"target_user": user_id, "updates": list(update_data.keys())}
        )
        
    return {"status": "success"}

@router.patch("/{user_id}")
async def update_user_partial(
    request: Request,
    user_id: str,
    user_data: UserUpdateRequest,
    session: dict = Depends(require_user_or_admin("user_id")), # Admin or Self
    state: GlobalStateManager = Depends(get_global_state)
):
    """
    Partial update user details.
    Restricted fields for non-admins (NO ROLE CHANGE).
    """
    # 1. Fetch existing
    existing = await state.auth_service.get_credentials(user_id)
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")
    
    # 2. Prepare Update Data
    update_data = user_data.model_dump(exclude_unset=True)
    
    # 3. Security: Role Sanitization
    current_role = getattr(session, "role", "user")
    if current_role != "admin":
        if "role" in update_data:
            # Silently strip or error? Strip is safer/easier for FE potentially sending stale data.
            # But let's be explicit if they try to hack.
            if update_data["role"] != existing.role:
                 # If they try to change it to something else
                 logging.warning(f"SECURITY: User {user_id} tried to change role to {update_data['role']}")
            
            # Remove dangerous fields
            update_data.pop("role", None)
            # Potentially other fields? (e.g. governance flags if any)
            
    # 4. Last Admin Protection (If Admin is demoting self/others via PATCH)
    if "role" in update_data and existing.role == "admin" and update_data["role"] == "user":
        admin_count = await state.credentials_collection.count_documents({"role": "admin"})
        if admin_count <= 1:
            raise HTTPException(status_code=400, detail="Cannot demote the last administrator.")

    if not update_data:
        return {"status": "success", "message": "No changes detected"}

    # 5. Update
    result = await state.credentials_collection.update_one(
        {"user_id": user_id},
        {"$set": update_data}
    )
    
    # 6. Session Invalidation
    if "role" in update_data and update_data["role"] != existing.role:
        await state.session_manager.invalidate_all_sessions(user_id, reason="Role Changed")
        
    # 7. Audit
    if state.audit_logs_collection is not None:
        from gateway.audit_logger import AuditLogger
        logger = AuditLogger(state.audit_logs_collection)
        current_user = getattr(session, "user_id", "unknown")
        await logger.log_event(
            event_type="user_updated",
            user_id=current_user,
            details={"target_user": user_id, "updates": list(update_data.keys()), "type": "partial"}
        )

    return {"status": "success"}

@router.delete("/{user_id}")
async def delete_user(
    request: Request,
    user_id: str,
    session: dict = Depends(require_admin),
    state: GlobalStateManager = Depends(get_global_state)
):
    """
    Delete a user (Admin only).
    """
    # 1. Fetch existing
    existing = await state.auth_service.get_credentials(user_id)
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")

    # 2. Last Admin Protection
    if existing.role == "admin":
        admin_count = await state.credentials_collection.count_documents({"role": "admin"})
        if admin_count <= 1:
            raise HTTPException(status_code=400, detail="Cannot delete the last administrator.")
            
    # 3. Prevent Self-Deletion? (Optional, but safer)
    current_user = getattr(session, "user_id", None)
    if user_id == current_user:
        raise HTTPException(status_code=400, detail="Cannot delete your own account.")

    # 4. Invalidate Sessions
    await state.session_manager.invalidate_all_sessions(user_id, reason="User Deleted")

    # 5. Delete Credentials
    await state.auth_service.delete_credentials(user_id)
    
    # 6. Delete Bots? (Optional, based on requirement. Owner cleanup.)
    # Plan says: "Refactor bot deletion...". 
    # Usually we might want to keep bots or reassign. For now, let's leave bots orphan or delete?
    # "Recursive delete" in plan implies deleting bots too?
    # Let's Just remove ownership for now, or if they own bots, maybe warn?
    # Logic: Remove ownership from bots is handled by delete_bot (bot->owner), 
    # but here we delete owner. We should probably unset owner of bots.
    # The system doesn't rigidly enforce "Bot MUST have owner".
    
    # 7. Audit
    if state.audit_logs_collection is not None:
        from gateway.audit_logger import AuditLogger
        logger = AuditLogger(state.audit_logs_collection)
        await logger.log_event(
            event_type="user_deleted",
            user_id=current_user or "unknown",
            details={"target_user": user_id}
        )

    return {"status": "success"}

@router.put("/{user_id}/password")
async def reset_password(
    request: Request,
    user_id: str,
    body: PasswordResetRequest,
    session: dict = Depends(require_admin),
    state: GlobalStateManager = Depends(get_global_state)
):
    """
    Reset user password (Admin only).
    """
    success, message = await state.auth_service.update_password(user_id, body.password)
    if not success:
        raise HTTPException(status_code=400, detail=message)
        
    # Invalidate Sessions
    await state.session_manager.invalidate_all_sessions(user_id, reason="Password Reset")
    
    # Audit
    if state.audit_logs_collection is not None:
        from gateway.audit_logger import AuditLogger
        logger = AuditLogger(state.audit_logs_collection)
        current_user = getattr(session, "user_id", "unknown")
        await logger.log_event(
            event_type="password_reset",
            user_id=current_user,
            details={"target_user": user_id}
        )
        
    return {"status": "success"}

# --- Validation Endpoints ---

@router.get("/validate/user_id")
async def validate_user_id(
    value: str,
    state: GlobalStateManager = Depends(get_global_state)
):
    """
    Check if user_id is available.
    """
    existing = await state.credentials_collection.find_one({"user_id": value})
    return {"available": existing is None}

@router.get("/validate/email")
async def validate_email(
    value: str,
    state: GlobalStateManager = Depends(get_global_state)
):
    """
    Check if email is available.
    """
    existing = await state.credentials_collection.find_one({"email": value})
    return {"available": existing is None}
