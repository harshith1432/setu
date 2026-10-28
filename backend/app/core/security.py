from datetime import datetime, timedelta, timezone
from typing import Optional, Any
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import HTTPException, status, Security, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings

import bcrypt

# Workaround for passlib compatibility with bcrypt >= 4.0.0
if not hasattr(bcrypt, "__about__"):
    class BcryptAbout:
        __version__ = getattr(bcrypt, "__version__", "4.0.0")
    bcrypt.__about__ = BcryptAbout()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security_scheme = HTTPBearer()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    import uuid
    to_encode = data.copy()
    to_encode.setdefault("jti", uuid.uuid4().hex)
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_token(token: str) -> dict:
    """
    SEC-01, SEC-02 & SEC-15: Cryptographic token verification.
    Supports:
    1. Centralized OIDC / Keycloak asymmetric tokens (RS256 / JWKS) with realm role mapping.
    2. Strictly validates HMAC-SHA256 signature against settings.SECRET_KEY.
    Rejects forged tokens, expired tokens, and unverified development bypass strings.
    """
    if not token or not isinstance(token, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or empty authorization token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 1. Check for Centralized OIDC / Keycloak asymmetric tokens
    try:
        from app.core.oidc_auth import oidc_verifier
        unverified_hdr = jwt.get_unverified_header(token)
        if unverified_hdr.get("alg", "").startswith(("RS", "ES")):
            oidc_payload = oidc_verifier.verify_token(token)
            if oidc_payload:
                return oidc_payload
    except HTTPException:
        raise
    except Exception:
        pass

    # 2. Strictly verify HMAC signature with server SECRET_KEY
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"verify_exp": True, "verify_signature": True}
        )
        if not payload or not isinstance(payload, dict):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Malformed token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )
        # SEC-11: Token Revocation / Blacklist Check (ASVS V3.4 / OWASP A07)
        try:
            from app.services.db_service import is_token_revoked
            import hashlib
            tok_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
            jti = payload.get("jti")
            if is_token_revoked(jti, tok_hash):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication token has been revoked or invalidated. Please re-authenticate.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            # SEC-SESS: Authoritative Server-Side Tab Session Validation
            session_id = payload.get("session_id")
            if session_id:
                from app.services.db_service import is_session_valid
                if not is_session_valid(session_id):
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Session has been revoked or expired. Please re-authenticate.",
                        headers={"WWW-Authenticate": "Bearer"},
                    )
        except HTTPException:
            raise
        except Exception:
            pass

        return payload
    except JWTError:
        # Invalid signature or expired token
        try:
            from app.services.siem_service import SIEMForwarder
            SIEMForwarder().emit_event(
                event_type="AUTH_FAILURE",
                severity="HIGH",
                actor="anonymous",
                action="INVALID_TOKEN_SIGNATURE",
                status="DENIED",
                details="Cryptographic JWT signature verification failed or token expired."
            )
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials: invalid or expired token signature",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_user_payload(credentials: HTTPAuthorizationCredentials = Security(security_scheme), request: Request = None) -> dict:
    token = credentials.credentials
    payload = decode_token(token)
    username = payload.get("sub")

    # SEC-MULTI-TAB: Verify X-Session-ID header against token session claim
    if request:
        x_sess_id = request.headers.get("x-session-id")
        tok_sess_id = payload.get("session_id")
        if x_sess_id and tok_sess_id and x_sess_id != tok_sess_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session mismatch: X-Session-ID header does not match active tab session context.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if tok_sess_id:
            try:
                from app.services.db_service import update_session_activity
                update_session_activity(tok_sess_id)
            except Exception:
                pass
    user_id = payload.get("user_id")

    if username and username != "admin":
        from app.services.db_service import get_user_by_username
        user = get_user_by_username(username)
        if not user or not user.get("is_active", 1):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account has been suspended or deactivated",
            )
        # Check employee status if user_id or username exists
        try:
            from app.services.org_employee_db import get_user_access_context
            target_uid = user.get("id") or user_id
            if target_uid:
                ctx = get_user_access_context(target_uid)
                if not ctx.get("is_active", True):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Account has been suspended or deactivated",
                    )
                # Enrich JWT payload with authoritative context
                payload["access_scope"] = ctx.get("access_scope", "GLOBAL")
                payload["assigned_resources"] = ctx.get("assigned_resources", {"sheds": [], "devices": []})
                payload["permissions"] = ctx.get("permissions", [])
                payload["role"] = ctx.get("role", payload.get("role", "farmer"))
                payload["user_id"] = target_uid
        except HTTPException:
            raise
        except Exception:
            pass
    elif username == "admin":
        payload["access_scope"] = "GLOBAL"
        payload["assigned_resources"] = {"sheds": ["shed_01", "shed_02", "shed_03"], "devices": []}
        try:
            from app.services.org_employee_db import ALL_PERMISSION_CODES
            payload["permissions"] = list(ALL_PERMISSION_CODES)
        except Exception:
            payload["permissions"] = []

    return payload

def require_roles(allowed_roles: list):
    """
    Role-Based Access Control (RBAC) dependency factory.
    Enforces authorization based on user role in the verified JWT payload.
    """
    def role_checker(payload: dict = Depends(get_current_user_payload)):
        role = payload.get("role", "farmer")
        if ("superadmin" in allowed_roles or "admin" in allowed_roles) and role in ["admin", "superadmin"]:
            return payload
        if role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied for role '{role}'. Required: {allowed_roles}"
            )
        return payload
    return role_checker

def require_permission(perm_code: str):
    """
    Fine-grained permission dependency factory with deny-by-default enforcement.
    Platform Super Admin has universal access.
    """
    def permission_checker(payload: dict = Depends(get_current_user_payload)):
        role = payload.get("role", "farmer")
        if role in ["superadmin", "admin"]:
            return payload
        user_perms = payload.get("permissions") or []
        if perm_code not in user_perms:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: permission '{perm_code}' required for this action."
            )
        return payload
    return permission_checker

def require_any_permission(perm_codes: list):
    """Requires at least one of the specified permissions."""
    def permission_checker(payload: dict = Depends(get_current_user_payload)):
        role = payload.get("role", "farmer")
        if role in ["superadmin", "admin"]:
            return payload
        user_perms = payload.get("permissions") or []
        if not any(p in user_perms for p in perm_codes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: at least one of {perm_codes} required."
            )
        return payload
    return permission_checker

def enforce_organization_isolation(user_payload: dict, target_org_id: Optional[str]):
    """
    Blocks cross-organization data tampering.
    Platform Super Admins are exempt.
    """
    role = user_payload.get("role")
    if role in ["superadmin", "admin"]:
        return
    user_org = user_payload.get("organization_id", "default_org")
    if target_org_id and target_org_id != user_org:
        try:
            from app.services.siem_service import SIEMForwarder
            SIEMForwarder().emit_event(
                event_type="CROSS_TENANT_TAMPER_ATTEMPT",
                severity="CRITICAL",
                actor=user_payload.get("sub", "unknown"),
                action="CROSS_ORGANIZATION_ACCESS",
                status="DENIED",
                details=f"User from org '{user_org}' attempted to access target org '{target_org_id}'",
                target_resource=target_org_id
            )
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cross-organization access violation: you cannot access or modify records of another company."
        )

def enforce_resource_isolation(user_payload: dict, shed_id: Optional[str] = None):
    """
    Enforces resource-level access scope (e.g. ASSIGNED_ONLY).
    """
    role = user_payload.get("role")
    if role in ["superadmin", "admin"]:
        return
    scope = user_payload.get("access_scope", "GLOBAL")
    if scope == "ASSIGNED_ONLY" and shed_id:
        assigned = user_payload.get("assigned_resources") or {}
        assigned_sheds = assigned.get("sheds") or []
        if shed_id not in assigned_sheds:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Resource access restricted: you are not authorized to view or manage shed '{shed_id}'."
            )


