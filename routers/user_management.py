"""
User Management Router.
Handles CRUD operations for users, including validation and audits.
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from dependencies import GlobalStateManager, get_global_state
from auth_dependencies import require_admin, require_user_or_admin, get_current_user
from auth_models import UserAuthCredentials, UserResponse, UserRestrictedResponse, LLMQuota

router = APIRouter(prefix="/api/internal/users", tags=["User Management"])

# --- Models ---
# We'll use Pydantic models for requests/responses to ensure validation
from pydantic import BaseModel, Field, EmailStr

# --- Shared Field Constraints ---
# define these once to ensure consistency between Create and Patch/Update
USER_ID_CONSTRAINTS = {"min_length": 1, "max_length": 30, "pattern": r"^[a-zA-Z0-9_-]+$"}
PASSWORD_CONSTRAINTS = {"min_length": 8}
ROLE_CONSTRAINTS = {"pattern": "^(admin|user)$"}
NAME_CONSTRAINTS = {"min_length": 1}
PHONE_CONSTRAINTS = {"min_length": 10, "pattern": r"^\+\d{10,15}$", "description": "E.164 format (e.g. +1234567890)"}
GOV_ID_CONSTRAINTS = {"min_length": 1, "description": "Government ID"}
COUNTRY_CONSTRAINTS = {"min_length": 2, "pattern": r"^[A-Z]{2}$", "description": "ISO 3166-1 alpha-2 code (e.g. US)"}
LANGUAGE_CONSTRAINTS = {"min_length": 2, "pattern": r"^[a-z]{2}$", "description": "ISO 639-1 code (e.g. en)"}

class UserProfileBase(BaseModel):
    """
    Base profile data shared between creation and strict validation.
    All fields here are REQUIRED and strictly validated.
    """
    first_name: str = Field(..., **NAME_CONSTRAINTS)
    last_name: str = Field(..., **NAME_CONSTRAINTS)
    email: EmailStr = Field(...)
    phone_number: str = Field(..., **PHONE_CONSTRAINTS)
    gov_id: str = Field(..., **GOV_ID_CONSTRAINTS)
    country_value: str = Field(..., **COUNTRY_CONSTRAINTS)
    language: str = Field("en", **LANGUAGE_CONSTRAINTS)

class UserCreateRequest(UserProfileBase):
    user_id: str = Field(..., **USER_ID_CONSTRAINTS)
    password: str = Field(..., **PASSWORD_CONSTRAINTS)
    role: str = Field(..., **ROLE_CONSTRAINTS)
    llm_quota: Optional[LLMQuota] = None
    # Inherits: first_name, last_name, email, phone_number, gov_id, country_value, language

class UserPatchRequest(BaseModel):
    # For PATCH: Partial updates, NO role. Fields are Optional but constrained if present.
    first_name: Optional[str] = Field(None, **NAME_CONSTRAINTS)
    last_name: Optional[str] = Field(None, **NAME_CONSTRAINTS)
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = Field(None, **PHONE_CONSTRAINTS)
    gov_id: Optional[str] = Field(None, **GOV_ID_CONSTRAINTS)
    country_value: Optional[str] = Field(None, **COUNTRY_CONSTRAINTS)
    language: Optional[str] = Field(None, **LANGUAGE_CONSTRAINTS)

class UserAdminUpdateRequest(UserPatchRequest):
    # For PUT (Admin Only): Includes role.
    role: Optional[str] = Field(None, **ROLE_CONSTRAINTS)
    llm_quota: Optional[LLMQuota] = None
    
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
    cursor = state.credentials_collection.find({})
    async for doc in cursor:
        doc.pop("_id", None)
        doc.pop("password_hash", None) # Security: Remove hash
        users.append(doc)
    return users

@router.get("/{user_id}", dependencies=[Depends(require_user_or_admin("user_id"))])
async def get_user(
    request: Request,
    user_id: str,
    state: GlobalStateManager = Depends(get_global_state)
):
    """
    Get specific user details (Admin or Self).
    Returns restricted model for non-admins.
    """
    user = await state.auth_service.get_credentials(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    requester_role = request.headers.get("x-user-role", "user") 
    
    # Convert DB model to dict
    user_dict = user.model_dump()
    user_dict.pop("password_hash", None)
    
    if requester_role == "admin":
        return UserResponse(**user_dict)
    else:
        # User sees restricted view (no role, no limits)
        return UserRestrictedResponse(**user_dict)

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
    # Service handles uniqueness.
    
    success, message = await state.auth_service.create_credentials(
        user_id=user_data.user_id,
        password=user_data.password,
        role=user_data.role,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        phone_number=user_data.phone_number,
        email=user_data.email,
        gov_id=user_data.gov_id,
        country_value=user_data.country_value,
        language=user_data.language,
        llm_quota=user_data.llm_quota
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
        
    # 2. Audit Log
    if state.audit_logs_collection is not None:
        from gateway.audit_logger import AuditLogger
        logger = AuditLogger(state.audit_logs_collection)
        current_user = getattr(session, "user_id", "unknown")
        await logger.log_event(
            event_type="user_created",
            user_id=current_user, 
            details={"created_user_id": user_data.user_id, "role": user_data.role}
        )
        
    return {"status": "success", "user_id": user_data.user_id}

@router.put("/{user_id}")
async def update_user_full(
    request: Request,
    user_id: str,
    user_data: UserAdminUpdateRequest,
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

    # 3. Update via Service
    update_data = user_data.model_dump(exclude_unset=True)
    if "user_id" in update_data: del update_data["user_id"] # Safety
    
    success, message = await state.auth_service.update_credentials(user_id, **update_data)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
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
    user_data: UserPatchRequest,
    session: dict = Depends(require_user_or_admin("user_id")), # Admin or Self
    state: GlobalStateManager = Depends(get_global_state)
):
    """
    Partial update user details.
    Restricted fields for non-admins (NO ROLE CHANGE).
    Uses STRICT validation by merging with existing data.
    """
    # 1. Fetch existing
    existing = await state.auth_service.get_credentials(user_id)
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")
    
    # 2. Prepare Update Data
    update_data = user_data.model_dump(exclude_unset=True)
    
    if not update_data:
         return {"status": "success", "message": "No changes detected"}
    
    # 3. Security: Role Sanitization
    # UserPatchRequest does NOT have 'role', so it won't be in update_data.
            
    # 4. Strict Validation: Merge & Check
    # We construct what the user WOULD look like after the update
    # and validate that against the strict UserProfileBase schema.
    try:
        # Get current state as dict
        failed_defaults = {
            "first_name": "Unknown", "last_name": "User", 
            "email": "temp@example.com", "phone_number": "+0000000000",
            "gov_id": "temp", "country_value": "US", "language": "en"
        }
        
        # We start with existing data. 
        # Note: 'existing' is a UserAuthCredentials model.
        merged_data = existing.model_dump()
        
        # Override with the patch updates
        merged_data.update(update_data)
        
        # Now validate strictly.
        # This ensures that even if we are only updating "phone_number", 
        # the resulting user object MUST still have a valid "first_name", "email", etc.
        # This effectively "autofills" the missing request fields from the DB
        # and sends them to the shared validation.
        UserProfileBase(**merged_data)
        
    except Exception as e:
        # Pydantic validation error or similar
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, 
            detail=f"Validation failed (Merged State): {str(e)}"
        )

    # 5. Last Admin Protection
    if "role" in update_data and existing.role == "admin" and update_data["role"] == "user":
        # Note: role is not in UserPatchRequest, but keeping logic for safety if model changes
        admin_count = await state.credentials_collection.count_documents({"role": "admin"})
        if admin_count <= 1:
            raise HTTPException(status_code=400, detail="Cannot demote the last administrator.")

    # 6. Update via Service
    success, message = await state.auth_service.update_credentials(user_id, **update_data)
    if not success:
         raise HTTPException(status_code=400, detail=message)
    
    # 7. Session Invalidation
    if "role" in update_data and update_data["role"] != existing.role:
        await state.session_manager.invalidate_all_sessions(user_id, reason="Role Changed")
        
    # 8. Audit
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
    if existing:
        return {"valid": False, "error_message": "User ID already exists."}
    return {"valid": True, "error_message": None}

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
