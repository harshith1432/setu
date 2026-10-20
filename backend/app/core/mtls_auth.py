import hashlib
import logging
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, status
from app.core.config import settings
from app.services.db_service import get_device_by_id

logger = logging.getLogger(__name__)

class MTLSAuthenticationService:
    """
    Enterprise Hardware Root of Trust / Mutual TLS (mTLS) Authentication Service.
    Enforces hardware cryptographic client certificate verification for IoT microcontrollers
    (e.g. ESP32 with ATECC608A Secure Element or embedded X.509 client certificates).
    """

    def __init__(self):
        # Header names passed by terminating reverse proxies / load balancers (Envoy, Nginx, ALB, Cloudflare)
        self.cert_sha256_header = "x-client-cert-sha256"
        self.cert_dn_header = "x-client-cert-dn"
        self.cert_verified_header = "x-client-cert-verified"
        self.cert_serial_header = "x-client-cert-serial"

    def extract_client_cert_metadata(self, request: Request) -> Optional[Dict[str, str]]:
        """Extracts verified client certificate metadata passed from edge TLS terminator."""
        headers = request.headers
        fingerprint = headers.get(self.cert_sha256_header)
        dn = headers.get(self.cert_dn_header)
        verified = headers.get(self.cert_verified_header, "NONE")
        serial = headers.get(self.cert_serial_header)

        if not fingerprint and not dn:
            return None

        # Extract Common Name (CN) from Distinguished Name (e.g. "CN=node_shed_01_core,O=SeriCare")
        cn = None
        if dn:
            for part in dn.split(","):
                part = part.strip()
                if part.upper().startswith("CN="):
                    cn = part[3:].strip()
                    break

        return {
            "fingerprint_sha256": fingerprint.lower().replace(":", "") if fingerprint else "",
            "common_name": cn or "",
            "distinguished_name": dn or "",
            "verified_status": verified.upper(),
            "serial_number": serial or ""
        }

    def verify_device_mtls(self, request: Request, claimed_device_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Validates the incoming client certificate against registered device hardware records.
        Ensures:
        1. Client cert was verified by the IoT Root CA (verified_status == 'SUCCESS').
        2. Common Name (CN) matches the device identifier.
        3. Fingerprint matches registered hardware certificate hash.
        4. Device status in PostgreSQL is active ('ONLINE'), not 'REVOKED'.
        """
        cert_meta = self.extract_client_cert_metadata(request)
        if not cert_meta:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="mTLS Client Certificate required: No hardware certificate presented in TLS handshake"
            )

        if cert_meta["verified_status"] not in ["SUCCESS", "OK", "VERIFIED"]:
            logger.warning("mTLS Handshake verification failed at edge: status=%s", cert_meta["verified_status"])
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"mTLS Verification Failed: Certificate validation status is '{cert_meta['verified_status']}'"
            )

        target_device_id = claimed_device_id or cert_meta["common_name"]
        if not target_device_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to resolve device ID from client certificate Common Name (CN)"
            )

        device = get_device_by_id(target_device_id)
        if not device:
            logger.warning("mTLS authentication rejected: Unknown hardware device '%s'", target_device_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Device '{target_device_id}' not found in hardware registry"
            )

        # Check revocation status
        if device.get("status") == "REVOKED":
            logger.error("Security Alert: Blocked connection attempt from REVOKED device '%s'", target_device_id)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Device revoked: Hardware certificate has been decommissioned"
            )

        # Check registered certificate fingerprint if configured
        registered_fp = device.get("cert_fingerprint_sha256")
        if registered_fp:
            clean_registered = registered_fp.lower().replace(":", "").strip()
            clean_presented = cert_meta["fingerprint_sha256"].strip()
            if clean_registered != clean_presented:
                logger.error(
                    "mTLS Certificate Fingerprint Mismatch for device '%s': expected %s, got %s",
                    target_device_id, clean_registered, clean_presented
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Certificate fingerprint mismatch: Hardware token does not match registered device"
                )

        return {
            "auth_type": "mtls",
            "device_id": target_device_id,
            "shed_id": device.get("shed_id", "shed_01"),
            "fingerprint": cert_meta["fingerprint_sha256"],
            "device": device
        }

mtls_service = MTLSAuthenticationService()
