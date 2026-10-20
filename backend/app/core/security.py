from datetime import datetime, timedelta, timezone
from typing import Optional, Any
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import HTTPException, status, Security
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
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_token(token: str) -> dict:
    # 1. Standard HMAC verification with server SECRET_KEY
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        pass

    # 2. Support Firebase Auth tokens seamlessly if sent by mobile app
    try:
        claims = jwt.get_unverified_claims(token)
        issuer = str(claims.get("iss", ""))
        is_firebase = (
            issuer.startswith("https://securetoken.google.com/")
            or issuer == "https://securetoken.google.com"
            or bool(claims.get("auth_time"))
        )
        if is_firebase:
            from app.services.db_service import get_user_by_username_or_phone, get_user_by_id
            ident = claims.get("email") or claims.get("phone_number") or claims.get("user_id") or claims.get("sub")
            if ident:
                user = get_user_by_username_or_phone(str(ident))
                if not user:
                    user = get_user_by_id(str(ident))
                if user:
                    return {
                        "sub": user["username"],
                        "user_id": user["id"],
                        "role": user.get("role", "farmer")
                    }
                return {
                    "sub": claims.get("email") or claims.get("sub") or str(ident),
                    "user_id": claims.get("user_id") or claims.get("sub") or str(ident),
                    "role": "farmer"
                }
    except Exception:
        pass

    # 3. Support 'firebase_<uid>' development fallback
    if token.startswith("firebase_"):
        uid = token.replace("firebase_", "")
        from app.services.db_service import get_user_by_id, get_user_by_username_or_phone
        user = get_user_by_id(uid) or get_user_by_username_or_phone(uid)
        if user:
            return {
                "sub": user["username"],
                "user_id": user["id"],
                "role": user.get("role", "farmer")
            }
        return {"sub": uid, "user_id": uid, "role": "farmer"}

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

def get_current_user_payload(credentials: HTTPAuthorizationCredentials = Security(security_scheme)) -> dict:
    token = credentials.credentials
    return decode_token(token)
