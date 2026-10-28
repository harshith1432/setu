"""
Roles & Permissions Management Router for SeriCare / Setu Enterprise.
Enforces system role immutability, permission categories, and privilege escalation prevention.
"""

from fastapi import APIRouter, HTTPException, Depends, Query, status
from typing import List, Dict, Any, Optional

from app.core.security import (
    get_current_user_payload,
    require_roles,
    require_permission,
)
from app.models.schemas import CustomRoleCreate, CustomRoleUpdate
from app.services.org_employee_db import (
    list_roles,
    get_role_detail,
    create_custom_role,
    update_custom_role,
    delete_custom_role,
    list_all_permissions
)

router = APIRouter(tags=["Roles & Permissions Management"])


@router.get("/permissions", response_model=List[Dict[str, Any]])
def get_permissions(current_user: dict = Depends(get_current_user_payload)):
    """
    Returns exhaustive list of granular system permissions across all categories:
    Organization, Users, Roles, Farmers & Sheds, IoT Hardware, Operations, Commercial, Analytics, Administration.
    """
    return list_all_permissions()


@router.get("/roles", response_model=List[Dict[str, Any]])
def get_roles_list(
    current_user: dict = Depends(require_permission("roles:read"))
):
    """
    Lists system role templates (10 standardized profiles) and tenant-specific custom roles.
    """
    return list_roles()


@router.post("/roles", status_code=status.HTTP_201_CREATED)
def add_custom_role(
    payload: CustomRoleCreate,
    current_user: dict = Depends(require_permission("roles:write"))
):
    """
    Creates a new custom role with a selected subset of permissions.
    Prevents privilege escalation: administrators cannot delegate permissions they do not hold.
    """
    data = payload.model_dump(exclude_unset=True)
    role = current_user.get("role")
    actor_is_superadmin = (role in ["superadmin", "admin"])



    creator_perms = current_user.get("permissions") or []

    try:
        created = create_custom_role(
            data=data,
            creator_perms=creator_perms,
            actor=current_user.get("sub", "admin"),
            actor_is_superadmin=actor_is_superadmin
        )
        return created
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/roles/{role_id}")
def get_role_by_id(
    role_id: str,
    current_user: dict = Depends(require_permission("roles:read"))
):
    """
    Retrieves full details of a specific role, its permissions, and system protection flag.
    """
    role = get_role_detail(role_id)
    if not role:
        raise HTTPException(status_code=404, detail=f"Role '{role_id}' not found.")
    

        
    return role


@router.put("/roles/{role_id}")
@router.patch("/roles/{role_id}")
def update_role_by_id(
    role_id: str,
    payload: CustomRoleUpdate,
    current_user: dict = Depends(require_permission("roles:write"))
):
    """
    Updates custom role name, description, status, or permissions.
    Rejects modification of protected system role templates.
    """
    role = get_role_detail(role_id)
    if not role:
        raise HTTPException(status_code=404, detail=f"Role '{role_id}' not found.")



    actor_is_superadmin = (current_user.get("role") in ["superadmin", "admin"])
    creator_perms = current_user.get("permissions") or []

    try:
        updated = update_custom_role(
            role_id=role_id,
            updates=payload.model_dump(exclude_unset=True),
            creator_perms=creator_perms,
            actor=current_user.get("sub", "admin"),
            actor_is_superadmin=actor_is_superadmin
        )
        return updated
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/roles/{role_id}")
def remove_custom_role(
    role_id: str,
    current_user: dict = Depends(require_permission("roles:write"))
):
    """
    Deletes custom role if not currently assigned to active employees.
    System role templates are protected against deletion.
    """
    role = get_role_detail(role_id)
    if not role:
        raise HTTPException(status_code=404, detail=f"Role '{role_id}' not found.")



    try:
        success = delete_custom_role(role_id=role_id, actor=current_user.get("sub", "admin"))
        if not success:
            raise HTTPException(status_code=404, detail="Role not found.")
        return {"status": "success", "message": f"Custom role '{role['name']}' deleted successfully."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
