"""
Department & Organizational Hierarchy Router for SeriCare / Setu Enterprise.
Supports department management, team structure, and member lookups.
"""

from fastapi import APIRouter, HTTPException, Depends, Query, status
from typing import List, Dict, Any, Optional

from app.core.security import (
    get_current_user_payload,
    require_roles,
    require_permission,
)
from app.models.schemas import DepartmentCreate, DepartmentUpdate
from app.services.org_employee_db import (
    list_departments,
    get_department,
    create_department,
    update_department,
    delete_department
)

router = APIRouter(prefix="/departments", tags=["Department Management"])


@router.get("", response_model=List[Dict[str, Any]])
def get_departments(
    current_user: dict = Depends(get_current_user_payload)
):
    """
    Returns list of departments with employee headcount and departmental head names.
    Non-superadmin callers are constrained to their own organization.
    """
    return list_departments()


@router.post("", status_code=status.HTTP_201_CREATED)
def add_department(
    payload: DepartmentCreate,
    current_user: dict = Depends(require_permission("users:write"))
):
    """
    Creates a new operational department within the organization.
    """
    data = payload.model_dump(exclude_unset=True)


    try:
        return create_department(data=data, actor=current_user.get("sub", "admin"))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{dept_id}")
def get_department_by_id(
    dept_id: str,
    current_user: dict = Depends(get_current_user_payload)
):
    """
    Returns full department specification and roster of assigned employee members.
    """
    dept = get_department(dept_id)
    if not dept:
        raise HTTPException(status_code=404, detail=f"Department '{dept_id}' not found.")
    return dept


@router.put("/{dept_id}")
@router.patch("/{dept_id}")
def update_department_by_id(
    dept_id: str,
    payload: DepartmentUpdate,
    current_user: dict = Depends(require_permission("users:write"))
):
    """
    Updates department name, description, assigned head, or status.
    """
    dept = get_department(dept_id)
    if not dept:
        raise HTTPException(status_code=404, detail=f"Department '{dept_id}' not found.")

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided for update.")

    try:
        updated = update_department(dept_id=dept_id, updates=updates, actor=current_user.get("sub", "admin"))
        return updated
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{dept_id}")
def remove_department(
    dept_id: str,
    current_user: dict = Depends(require_permission("users:write"))
):
    """
    Deletes department if no employee members remain assigned.
    """
    dept = get_department(dept_id)
    if not dept:
        raise HTTPException(status_code=404, detail=f"Department '{dept_id}' not found.")

    try:
        success = delete_department(dept_id=dept_id, actor=current_user.get("sub", "admin"))
        if not success:
            raise HTTPException(status_code=404, detail="Department not found.")
        return {"status": "success", "message": f"Department '{dept['name']}' deleted successfully."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
