import os
import json
import time
import logging
import urllib.request
from typing import Dict, Any, Optional, List
from jose import jwt, jwk, JWTError
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

class OIDCVerifier:
    """
    Centralized OpenID Connect (OIDC) & Keycloak Authentication Verifier.
    Supports:
    - JWKS Public Key Retrieval and in-memory TTL caching.
    - Issuer (iss) and Audience (aud) claim enforcement.
    - Keycloak Realm & Resource Access Role Extraction (`realm_access.roles`).
    - Standard role normalization into SeriCare RBAC roles.
    """

    def __init__(self, jwks_uri: Optional[str] = None, issuer: Optional[str] = None, audience: Optional[str] = None):
        self.jwks_uri = jwks_uri or os.getenv("OIDC_JWKS_URI")
        self.issuer = issuer or os.getenv("OIDC_ISSUER")
        self.audience = audience or os.getenv("OIDC_AUDIENCE", "sericare-platform")
        self._jwks_cache: Optional[Dict[str, Any]] = None
        self._jwks_cache_time = 0
        self.cache_ttl = 3600  # 1 hour JWKS cache

    def is_enabled(self) -> bool:
        """Returns True if OIDC issuer or JWKS endpoint is configured."""
        return bool(self.jwks_uri or self.issuer)

    def _get_jwks(self) -> Dict[str, Any]:
        """Fetches and caches the JSON Web Key Set (JWKS) from the OIDC identity provider."""
        now = time.time()
        if self._jwks_cache and (now - self._jwks_cache_time) < self.cache_ttl:
            return self._jwks_cache

        uri = self.jwks_uri
        if not uri and self.issuer:
            uri = f"{self.issuer.rstrip('/')}/protocol/openid-connect/certs"

        if not uri:
            return {"keys": []}

        try:
            req = urllib.request.Request(uri, headers={"User-Agent": "SeriCare-Security/1.0"})
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    self._jwks_cache = json.loads(response.read().decode())
                    self._jwks_cache_time = now
                    logger.info("Successfully refreshed OIDC JWKS from %s", uri)
                    return self._jwks_cache
        except Exception as e:
            logger.warning("Could not fetch remote JWKS from %s: %s", uri, e)
            if self._jwks_cache:
                return self._jwks_cache

        return {"keys": []}

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Validates an OIDC JWT using the provider's JWKS.
        Returns the parsed and normalized claims dictionary, or raises HTTPException on invalid tokens.
        """
        try:
            unverified_headers = jwt.get_unverified_header(token)
        except JWTError:
            return None

        kid = unverified_headers.get("kid")
        alg = unverified_headers.get("alg", "RS256")

        # If it's an HMAC token (HS256), let internal security.py handle it
        if alg.startswith("HS"):
            return None

        jwks_data = self._get_jwks()
        keys = jwks_data.get("keys", [])

        # Find matching key by kid
        matching_key = None
        for k in keys:
            if not kid or k.get("kid") == kid:
                matching_key = k
                break

        if not matching_key:
            logger.warning("No matching key found in JWKS for kid: %s", kid)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: Key ID (kid) not found in identity provider JWKS"
            )

        try:
            # Construct public key object
            public_key = jwk.construct(matching_key)
            
            # Verify and decode
            verify_options = {
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
                "verify_aud": bool(self.audience),
                "verify_iss": bool(self.issuer),
            }

            payload = jwt.decode(
                token,
                public_key.to_pem().decode(),
                algorithms=[alg],
                audience=self.audience if self.audience else None,
                issuer=self.issuer if self.issuer else None,
                options=verify_options
            )

            # Map Keycloak claims to internal SeriCare format
            normalized = self._normalize_oidc_claims(payload)
            return normalized

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="OIDC Token has expired"
            )
        except JWTError as e:
            logger.warning("OIDC token verification failed: %s", e)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"OIDC Token verification failed: {str(e)}"
            )

    def _normalize_oidc_claims(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Maps Keycloak / OIDC standard attributes into SeriCare authentication format."""
        # Keycloak roles are located in realm_access.roles
        realm_roles = payload.get("realm_access", {}).get("roles", [])
        
        # Determine internal role priority
        role = "USER"
        upper_roles = [r.upper() for r in realm_roles]
        if "SUPERADMIN" in upper_roles or "ADMIN" in upper_roles:
            role = "ADMIN"
        elif "MANAGER" in upper_roles:
            role = "MANAGER"
        elif "FARMER" in upper_roles:
            role = "FARMER"
        elif "TECHNICIAN" in upper_roles:
            role = "TECHNICIAN"

        # Email / Subject
        sub = payload.get("sub")
        email = payload.get("email") or payload.get("preferred_username") or sub

        return {
            "sub": sub,
            "email": email,
            "role": role,
            "raw_roles": realm_roles,
            "organization_id": payload.get("organization_id") or payload.get("tenant_id") or "org_default",
            "name": payload.get("name") or payload.get("preferred_username") or "",
            "auth_provider": "KEYCLOAK_OIDC"
        }

oidc_verifier = OIDCVerifier()
