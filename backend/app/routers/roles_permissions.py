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
from app.models.schemas import CustomRoleCreate, CustomRoleUpdate, RoleDashboardUpdate
from app.services.org_employee_db import (
    list_roles,
    get_role_detail,
    create_custom_role,
    update_custom_role,
    delete_custom_role,
    list_all_permissions,
    get_dashboard_matrix,
    update_role_dashboards,
    get_role_allowed_dashboards
)

router = APIRouter(tags=["Roles & Permissions Management"])


@router.get("/permissions", response_model=List[Dict[str, Any]])
def get_permissions(current_user: dict = Depends(get_current_user_payload)):
    """
    Returns exhaustive list of granular system permissions across all categories:
    Organization, Users, Roles, Farmers & Sheds, IoT Hardware, Operations, Commercial, Analytics, Administration.
    """
    return list_all_permissions()


@router.get("/roles/dashboard-matrix")
def get_dashboard_matrix_endpoint(
    current_user: dict = Depends(get_current_user_payload)
):
    """
    Returns the comprehensive dashboard access matrix:
    - 25 dashboards categorized by operational department
    - 6 operational departments (Customer Operations / Helpdesk, Sales, Ops, etc.)
    - All roles with their allowed_dashboards and employee user count
    """
    role = current_user.get("role")
    org_id = current_user.get("organization_id") if role not in ["superadmin", "admin"] else None
    return get_dashboard_matrix(org_id=org_id)


@router.get("/roles", response_model=List[Dict[str, Any]])
def get_roles_list(
    current_user: dict = Depends(require_permission("roles:read"))
):
    """
    Lists system role templates (10 standardized profiles) and tenant-specific custom roles.
    Respects tenant isolation for multi-tenant accounts.
    """
    role = current_user.get("role")
    org_id = current_user.get("organization_id") if role not in ["superadmin", "admin"] else None
    return list_roles(org_id=org_id)


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


@router.get("/roles/{role_id}/dashboards")
def get_role_dashboards_endpoint(
    role_id: str,
    current_user: dict = Depends(get_current_user_payload)
):
    """
    Retrieves the allowed dashboards list for a specific role.
    """
    role = get_role_detail(role_id)
    if not role:
        dashboards = get_role_allowed_dashboards(role_id)
        return {"role_id": role_id, "allowed_dashboards": dashboards}
    return {
        "role_id": role["id"],
        "role_code": role["code"],
        "name": role["name"],
        "allowed_dashboards": role.get("allowed_dashboards") or []
    }


@router.put("/roles/{role_id}/dashboards")
def update_role_dashboards_endpoint(
    role_id: str,
    payload: RoleDashboardUpdate,
    current_user: dict = Depends(require_permission("roles:write"))
):
    """
    Updates the checkbox dashboard permissions for a particular role.
    Any employee under this role will immediately see only the permitted dashboards in their left sidebar.
    Enforces tenant isolation and logs an immutable security audit event.
    """
    role = current_user.get("role")
    actor_is_superadmin = (role in ["superadmin", "admin"])
    org_id = current_user.get("organization_id")
    try:
        updated = update_role_dashboards(
            role_id=role_id,
            dashboards=payload.allowed_dashboards,
            actor=current_user.get("sub", "admin"),
            actor_is_superadmin=actor_is_superadmin,
            org_id=org_id
        )
        return updated
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


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
