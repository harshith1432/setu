"""
Employee & User Management Router for SeriCare / Setu Enterprise.
Supports employee onboarding, reporting structures, resource-level scoping, and account suspension.
"""

from fastapi import APIRouter, HTTPException, Depends, Query, status, Request
from typing import List, Dict, Any, Optional

from app.core.security import (
    get_current_user_payload,
    require_roles,
    require_permission,
)
from app.models.schemas import EmployeeCreate, EmployeeUpdate, EmployeeStatusUpdate
from app.services.org_employee_db import (
    list_employees,
    get_employee_detail,
    create_employee_with_invitation,
    update_employee,
    update_employee_status,
    resend_employee_invitation,
    revoke_employee_invitation,
    delete_employee_record
)

router = APIRouter(prefix="/employees", tags=["Employee Management"])


@router.get("", response_model=Dict[str, Any])
def get_employees_directory(
    dept_id: Optional[str] = Query(None, description="Filter by department"),
    role: Optional[str] = Query(None, description="Filter by role code"),
    status: Optional[str] = Query(None, description="Filter by employment status (ACTIVE, SUSPENDED, PENDING_ACTIVATION)"),
    search: Optional[str] = Query(None, description="Search by name, email, employee ID or username"),
    sort_by: str = Query("created_at", description="Field to sort by (created_at, employee_id, full_name, status)"),
    sort_desc: bool = Query(True, description="Sort descending"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(require_permission("users:read"))
):
    """
    Search, filter, sort and paginate employee records across the organization.
    Never exposes password hashes, token secrets, or sensitive credentials.
    """
    total, emps = list_employees(
        dept_id=dept_id,
        role=role,
        status=status,
        search=search,
        sort_by=sort_by,
        sort_desc=sort_desc,
        limit=limit,
        offset=offset
    )
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "employees": emps
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def invite_employee(
    payload: EmployeeCreate,
    request: Request,
    current_user: dict = Depends(require_permission("users:invite"))
):
    """
    Onboards a new employee:
    1. Validates organizational boundary and unique identities.
    2. Enforces role delegation permissions (privilege escalation prevention).
    3. Validates absence of circular reporting hierarchies.
    4. Transactionally generates single-use, time-limited activation invitation.
    5. Returns onboarding link and delivery status.
    """
    data = payload.model_dump(exclude_unset=True)
    caller_role = current_user.get("role")
    actor_is_superadmin = (caller_role in ["superadmin", "admin"])



    if data.get("role_code") == "farmer":
        raise HTTPException(
            status_code=400,
            detail="Farmers register directly through the public landing portal and cannot be onboarded as corporate employees."
        )

    base_url = str(request.base_url).rstrip("/")
    actor_perms = current_user.get("permissions") or []

    try:
        result = create_employee_with_invitation(
            data=data,
            actor=current_user.get("sub", "admin"),
            actor_perms=actor_perms,
            actor_is_superadmin=actor_is_superadmin,
            base_url=base_url
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to onboard employee: {str(e)}")


@router.get("/{employee_id}")
def get_employee(
    employee_id: str,
    current_user: dict = Depends(require_permission("users:read"))
):
    """
    Retrieves full employee record, reporting manager, direct subordinates, and resource assignments.
    """
    emp = get_employee_detail(employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail=f"Employee '{employee_id}' not found.")
    return emp


@router.put("/{employee_id}")
@router.patch("/{employee_id}")
def update_employee_record(
    employee_id: str,
    payload: EmployeeUpdate,
    current_user: dict = Depends(require_permission("users:write"))
):
    """
    Updates employee details, department, designation, reporting manager, role, and resource scopes.
    Validates that changes do not introduce circular reporting loops.
    """
    emp = get_employee_detail(employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail=f"Employee '{employee_id}' not found.")

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided for update.")

    actor_is_superadmin = (current_user.get("role") in ["superadmin", "admin"])
    try:
        updated = update_employee(
            employee_id=emp["id"],
            updates=updates,
            actor=current_user.get("sub", "admin"),
            actor_is_superadmin=actor_is_superadmin
        )
        return updated
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{employee_id}/status")
def change_employee_status(
    employee_id: str,
    payload: EmployeeStatusUpdate,
    current_user: dict = Depends(require_permission("users:suspend"))
):
    """
    Activates or suspends an employee account.
    Suspension immediately invalidates existing JWT sessions and prevents further API access.
    """
    emp = get_employee_detail(employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail=f"Employee '{employee_id}' not found.")

    try:
        return update_employee_status(
            employee_id=emp["id"],
            new_status=payload.status,
            actor=current_user.get("sub", "admin")
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{employee_id}/resend-invitation")
def resend_invitation(
    employee_id: str,
    request: Request,
    current_user: dict = Depends(require_permission("users:invite"))
):
    """
    Invalidates any previous pending invitation and issues a fresh, time-limited activation token.
    """
    emp = get_employee_detail(employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail=f"Employee '{employee_id}' not found.")

    base_url = str(request.base_url).rstrip("/")
    try:
        return resend_employee_invitation(
            employee_id=emp["id"],
            actor=current_user.get("sub", "admin"),
            base_url=base_url
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{employee_id}/revoke-invitation")
def revoke_invitation(
    employee_id: str,
    current_user: dict = Depends(require_permission("users:invite"))
):
    """
    Revokes any active onboarding invitation, blocking activation attempts.
    """
    emp = get_employee_detail(employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail=f"Employee '{employee_id}' not found.")

    success = revoke_employee_invitation(employee_id=emp["id"], actor=current_user.get("sub", "admin"))
    return {"status": "success", "message": "Pending invitation revoked successfully."}



@router.delete("/{employee_id}")
def delete_employee(
    employee_id: str,
    current_user: dict = Depends(require_permission("users:write"))
):
    """
    Permanently deletes an employee record, associated invitations, and user credentials.
    Root platform administrator accounts are strictly protected.
    """
    try:
        actor = current_user.get("username", "admin")
        success = delete_employee_record(employee_id, actor=actor)
        if not success:
            raise HTTPException(status_code=404, detail=f"Employee '{employee_id}' not found.")
        return {
            "status": "success",
            "message": f"Employee '{employee_id}' successfully deleted."
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete employee: {str(e)}")
