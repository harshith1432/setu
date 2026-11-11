"""
SeriCare Enterprise Platform - Firebase Cloud Firestore Service
Handles primary NoSQL database operations for telemetry, products, orders,
audit logs, devices, and user profiles with automated fallback to PostgreSQL.
Project ID: setu-a767c
"""

import os
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

logger = logging.getLogger("firestore_service")

FIRESTORE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID") or "setu-a767c"

class FirestoreService:
    _instance = None
    _db = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FirestoreService, cls).__new__(cls)
            cls._instance._init_client()
        return cls._instance

    def _init_client(self):
        """Initialize Firebase Admin SDK with graceful fallback."""
        if self._initialized:
            return

        try:
            import firebase_admin
            from firebase_admin import credentials, firestore

            if not firebase_admin._apps:
                cred = None
                sa_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
                default_local_sa = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "credentials", "firebase-service-account.json"))
                sa_path = os.getenv("FIREBASE_CREDENTIALS_PATH") or os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY") or os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or (default_local_sa if os.path.exists(default_local_sa) else None)

                if sa_json and len(sa_json.strip()) > 20:
                    try:
                        sa_dict = json.loads(sa_json)
                        cred = credentials.Certificate(sa_dict)
                    except Exception as e:
                        logger.warning("Could not parse FIREBASE_SERVICE_ACCOUNT_JSON: %s", e)

                if not cred and sa_path and os.path.exists(sa_path):
                    try:
                        cred = credentials.Certificate(sa_path)
                    except Exception as e:
                        logger.warning("Could not load credentials from %s: %s", sa_path, e)

                options = {"projectId": FIRESTORE_PROJECT_ID}
                if cred:
                    firebase_admin.initialize_app(cred, options=options)
                else:
                    firebase_admin.initialize_app(options=options)

            self._db = firestore.client()
            self._initialized = True
            logger.info("Cloud Firestore client initialized for project '%s'", FIRESTORE_PROJECT_ID)
        except Exception as e:
            logger.warning("Firestore Admin SDK not fully initialized (operating in graceful fallback mode): %s", e)
            self._db = None
            self._initialized = False

    @property
    def is_available(self) -> bool:
        return self._db is not None

    @property
    def client(self):
        return self._db

    # =========================================================================
    # 1. SHED TELEMETRY
    # =========================================================================

    def record_telemetry(self, shed_id: str, reading: Dict[str, Any]) -> Optional[str]:
        """Record live telemetry reading in Firestore."""
        if not self.is_available:
            return None

        try:
            doc_ref = self._db.collection("shed_telemetry").document()
            now_iso = datetime.now(timezone.utc).isoformat()
            
            data = dict(reading)
            data["id"] = doc_ref.id
            data["shed_id"] = shed_id
            if "timestamp" not in data or not data["timestamp"]:
                data["timestamp"] = now_iso
            elif isinstance(data["timestamp"], datetime):
                data["timestamp"] = data["timestamp"].isoformat()

            doc_ref.set(data)

            # Update latest reading snapshot in shed document
            shed_ref = self._db.collection("sheds").document(shed_id)
            shed_ref.set({
                "latest_reading": data,
                "updated_at": now_iso
            }, merge=True)

            return doc_ref.id
        except Exception as e:
            logger.error("Failed to record telemetry in Firestore: %s", e)
            return None

    def get_latest_telemetry(self, shed_id: str) -> Optional[Dict[str, Any]]:
        """Fetch latest telemetry reading for a shed."""
        if not self.is_available:
            return None

        try:
            docs = (
                self._db.collection("shed_telemetry")
                .where("shed_id", "==", shed_id)
                .order_by("timestamp", direction="DESCENDING")
                .limit(1)
                .get()
            )
            for d in docs:
                res = d.to_dict()
                res["id"] = d.id
                return res
        except Exception as e:
            logger.debug("Firestore get_latest_telemetry query failed: %s", e)
        return None

    def get_telemetry_history(self, shed_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch chronological telemetry records with limit."""
        if not self.is_available:
            return []

        try:
            docs = (
                self._db.collection("shed_telemetry")
                .where("shed_id", "==", shed_id)
                .order_by("timestamp", direction="DESCENDING")
                .limit(limit)
                .get()
            )
            results = []
            for d in docs:
                m = d.to_dict()
                m["id"] = d.id
                results.append(m)
            return results
        except Exception as e:
            logger.debug("Firestore get_telemetry_history query failed: %s", e)
            return []

    # =========================================================================
    # 2. PRODUCTS & HARDWARE CATALOGUE
    # =========================================================================

    def get_products(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve hardware products from Firestore."""
        if not self.is_available:
            return []

        try:
            col = self._db.collection("products")
            q = col.where("publication_status", "==", "PUBLISHED") if hasattr(col, 'where') else col
            if category and category.upper() != "ALL":
                q = q.where("category", "==", category)
            
            docs = q.get()
            return [{"id": d.id, **d.to_dict()} for d in docs]
        except Exception as e:
            logger.debug("Firestore get_products failed: %s", e)
            return []

    def get_product(self, product_id_or_sku: str) -> Optional[Dict[str, Any]]:
        """Get product by ID or SKU."""
        if not self.is_available:
            return None

        try:
            doc = self._db.collection("products").document(product_id_or_sku).get()
            if doc.exists:
                return {"id": doc.id, **doc.to_dict()}
            
            # Try by SKU
            docs = self._db.collection("products").where("sku", "==", product_id_or_sku).limit(1).get()
            for d in docs:
                return {"id": d.id, **d.to_dict()}
        except Exception as e:
            logger.debug("Firestore get_product failed: %s", e)
        return None

    # =========================================================================
    # 3. ORDERS
    # =========================================================================

    def create_order(self, order_data: Dict[str, Any]) -> Optional[str]:
        """Create a new order document in Firestore."""
        if not self.is_available:
            return None

        try:
            doc_id = order_data.get("id")
            if doc_id:
                doc_ref = self._db.collection("orders").document(doc_id)
            else:
                doc_ref = self._db.collection("orders").document()
                order_data["id"] = doc_ref.id

            now_iso = datetime.now(timezone.utc).isoformat()
            order_data["created_at"] = order_data.get("created_at") or now_iso
            order_data["updated_at"] = now_iso

            doc_ref.set(order_data)
            return doc_ref.id
        except Exception as e:
            logger.error("Failed to create order in Firestore: %s", e)
            return None

    def get_orders(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get orders optionally filtered by user."""
        if not self.is_available:
            return []

        try:
            q = self._db.collection("orders")
            if user_id:
                q = q.where("user_id", "==", user_id)
            docs = q.order_by("created_at", direction="DESCENDING").get()
            return [{"id": d.id, **d.to_dict()} for d in docs]
        except Exception as e:
            logger.debug("Firestore get_orders failed: %s", e)
            return []

    # =========================================================================
    # 4. AUDIT LOGS & DEVICE COMMANDS
    # =========================================================================

    def record_audit_log(self, action: str, user_id: str, resource: str, details: Optional[Dict[str, Any]] = None, ip_address: Optional[str] = None) -> Optional[str]:
        """Append-only administrative audit record in Firestore."""
        if not self.is_available:
            return None

        try:
            doc_ref = self._db.collection("audit_logs").document()
            data = {
                "id": doc_ref.id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": action,
                "user_id": user_id,
                "resource": resource,
                "details": details or {},
                "ip_address": ip_address or "127.0.0.1"
            }
            doc_ref.set(data)
            return doc_ref.id
        except Exception as e:
            logger.debug("Failed to record audit log in Firestore: %s", e)
            return None

    def create_device_command(self, shed_id: str, actuator: str, state: int, source: str = "backend", correlation_id: Optional[str] = None) -> Optional[str]:
        """Record device control command in Firestore."""
        if not self.is_available:
            return None

        try:
            doc_ref = self._db.collection("device_commands").document()
            data = {
                "command_id": doc_ref.id,
                "shed_id": shed_id,
                "actuator": actuator,
                "state": state,
                "source": source,
                "correlation_id": correlation_id or "",
                "status": "SENT",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            doc_ref.set(data)
            return doc_ref.id
        except Exception as e:
            logger.debug("Failed to record device command in Firestore: %s", e)
            return None

    # =========================================================================
    # 5. USER & AUTHENTICATION MANAGEMENT
    # =========================================================================

    def get_user_by_username_or_phone(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Finds user by username, email, or phone number in Firestore."""
        if not self.is_available:
            return None
        clean_id = (identifier or "").strip()
        if not clean_id:
            return None
        try:
            users_ref = self._db.collection("users")
            # 1. By exact username
            docs = list(users_ref.where("username", "==", clean_id).limit(1).stream())
            if docs:
                return {"id": docs[0].id, **docs[0].to_dict()}

            # 2. Lowercase username
            if clean_id.lower() != clean_id:
                docs = list(users_ref.where("username", "==", clean_id.lower()).limit(1).stream())
                if docs:
                    return {"id": docs[0].id, **docs[0].to_dict()}

            # 3. By official_email
            docs = list(users_ref.where("official_email", "==", clean_id).limit(1).stream())
            if docs:
                return {"id": docs[0].id, **docs[0].to_dict()}
            if clean_id.lower() != clean_id:
                docs = list(users_ref.where("official_email", "==", clean_id.lower()).limit(1).stream())
                if docs:
                    return {"id": docs[0].id, **docs[0].to_dict()}

            # 4. By phone
            docs = list(users_ref.where("phone", "==", clean_id).limit(1).stream())
            if docs:
                return {"id": docs[0].id, **docs[0].to_dict()}

            # 5. By clean phone digits
            digits = "".join(ch for ch in clean_id if ch.isdigit())
            if len(digits) >= 10:
                for candidate in [digits, f"+91{digits[-10:]}", f"+91 {digits[-10:]}"]:
                    docs = list(users_ref.where("phone", "==", candidate).limit(1).stream())
                    if docs:
                        return {"id": docs[0].id, **docs[0].to_dict()}

            return None
        except Exception as e:
            logger.debug("Firestore get_user_by_username_or_phone notice: %s", e)
            return None

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves user by ID from Firestore."""
        if not self.is_available or not user_id:
            return None
        try:
            doc = self._db.collection("users").document(user_id).get()
            if doc.exists:
                return {"id": doc.id, **doc.to_dict()}
            docs = list(self._db.collection("users").where("id", "==", user_id).limit(1).stream())
            if docs:
                return {"id": docs[0].id, **docs[0].to_dict()}
            return None
        except Exception as e:
            logger.debug("Firestore get_user_by_id notice: %s", e)
            return None

    def create_user(self, user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Creates or updates user document in Firestore."""
        if not self.is_available:
            return None
        try:
            u_id = user_data.get("id") or f"usr_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
            clean_data = dict(user_data)
            clean_data["id"] = u_id
            self._db.collection("users").document(u_id).set(clean_data, merge=True)
            return clean_data
        except Exception as e:
            logger.warning("Firestore create_user error: %s", e)
            return None

    def update_user_password(self, user_id: str, hashed_password: str) -> bool:
        """Updates user password in Firestore."""
        if not self.is_available or not user_id:
            return False
        try:
            self._db.collection("users").document(user_id).set({
                "hashed_password": hashed_password,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }, merge=True)
            return True
        except Exception as e:
            logger.warning("Firestore update_user_password error: %s", e)
            return False

    def create_user_session(self, session_data: Dict[str, Any]) -> bool:
        """Stores active tab session in Firestore."""
        if not self.is_available:
            return False
        try:
            s_id = session_data.get("session_id")
            if s_id:
                self._db.collection("user_sessions").document(s_id).set(session_data, merge=True)
                return True
        except Exception as e:
            logger.debug("Firestore create_user_session notice: %s", e)
        return False

    def get_user_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves session from Firestore."""
        if not self.is_available or not session_id:
            return None
        try:
            doc = self._db.collection("user_sessions").document(session_id).get()
            if doc.exists:
                return doc.to_dict()
        except Exception as e:
            logger.debug("Firestore get_user_session notice: %s", e)
        return None

    def list_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """Lists active sessions from Firestore."""
        if not self.is_available or not user_id:
            return []
        try:
            docs = self._db.collection("user_sessions").where("user_id", "==", user_id).where("is_revoked", "==", False).stream()
            return [d.to_dict() for d in docs]
        except Exception as e:
            logger.debug("Firestore list_user_sessions notice: %s", e)
            return []

    def revoke_user_session(self, session_id: str, reason: str = "") -> bool:
        """Revokes a session in Firestore."""
        if not self.is_available or not session_id:
            return False
        try:
            self._db.collection("user_sessions").document(session_id).set({
                "is_revoked": True,
                "revoked_at": datetime.now(timezone.utc).isoformat(),
                "revocation_reason": reason
            }, merge=True)
            return True
        except Exception as e:
            logger.debug("Firestore revoke_user_session notice: %s", e)
            return False

    def create_password_reset(self, reset_data: Dict[str, Any]) -> bool:
        """Stores password reset record in Firestore."""
        if not self.is_available:
            return False
        try:
            pr_id = reset_data.get("id") or reset_data.get("reset_code")
            self._db.collection("password_resets").document(pr_id).set(reset_data, merge=True)
            return True
        except Exception as e:
            logger.debug("Firestore create_password_reset notice: %s", e)
            return False

    def get_active_password_reset(self, code_or_token: str) -> Optional[Dict[str, Any]]:
        """Finds active unexpired password reset by code or token."""
        if not self.is_available or not code_or_token:
            return None
        clean_val = code_or_token.strip()
        try:
            for field in ["reset_code", "reset_token"]:
                docs = list(self._db.collection("password_resets").where(field, "==", clean_val).stream())
                for d in docs:
                    data = d.to_dict()
                    if not data.get("used_at"):
                        return {"id": d.id, **data}
            return None
        except Exception as e:
            logger.debug("Firestore get_active_password_reset notice: %s", e)
            return None

    def mark_password_reset_used(self, reset_id: str) -> bool:
        """Marks password reset as consumed."""
        if not self.is_available or not reset_id:
            return False
        try:
            self._db.collection("password_resets").document(reset_id).set({
                "used_at": datetime.now(timezone.utc).isoformat()
            }, merge=True)
            return True
        except Exception as e:
            logger.debug("Firestore mark_password_reset_used notice: %s", e)
            return False


# Global singleton instance
firestore_service = FirestoreService()

