"""
SeriCare Enterprise Platform - Firebase Cloud Firestore Service
Handles primary NoSQL database operations for telemetry, products, orders,
audit logs, devices, and user profiles with automated fallback to PostgreSQL.
Project ID: setu-a767c
"""

import os
import json
import logging
import warnings
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple

warnings.filterwarnings("ignore", category=UserWarning, module=".*firestore.*")

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
                sa_b64 = os.getenv("FIREBASE_SERVICE_ACCOUNT_B64")
                default_local_sa = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "credentials", "firebase-service-account.json"))
                render_secret_sa = "/etc/secrets/firebase-service-account.json"
                root_secret_sa = os.path.abspath("firebase-service-account.json")
                sa_path = (
                    os.getenv("FIREBASE_CREDENTIALS_PATH")
                    or os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY")
                    or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
                    or (render_secret_sa if os.path.exists(render_secret_sa) else None)
                    or (root_secret_sa if os.path.exists(root_secret_sa) else None)
                    or (default_local_sa if os.path.exists(default_local_sa) else None)
                )

                # 1. Base64 encoded Service Account JSON (ideal for Render single-line env var)
                if sa_b64 and len(sa_b64.strip()) > 20:
                    try:
                        import base64
                        decoded = base64.b64decode(sa_b64.strip()).decode("utf-8")
                        sa_dict = json.loads(decoded)
                        cred = credentials.Certificate(sa_dict)
                        logger.info("Loaded Firebase credentials from FIREBASE_SERVICE_ACCOUNT_B64")
                    except Exception as e:
                        logger.warning("Could not parse FIREBASE_SERVICE_ACCOUNT_B64: %s", e)

                # 2. Raw JSON string Service Account
                if not cred and sa_json and len(sa_json.strip()) > 20:
                    try:
                        sa_dict = json.loads(sa_json)
                        cred = credentials.Certificate(sa_dict)
                        logger.info("Loaded Firebase credentials from FIREBASE_SERVICE_ACCOUNT_JSON")
                    except Exception as e:
                        logger.warning("Could not parse FIREBASE_SERVICE_ACCOUNT_JSON: %s", e)

                # 3. File path on disk
                if not cred and sa_path and os.path.exists(sa_path):
                    try:
                        cred = credentials.Certificate(sa_path)
                        logger.info("Loaded Firebase credentials from disk: %s", sa_path)
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

    @staticmethod
    def _normalize_user_doc(data: Dict[str, Any], doc_id: str = "") -> Dict[str, Any]:
        """Ensures all standard user keys are present with safe fallbacks."""
        if not isinstance(data, dict):
            return {}
        res = dict(data)
        if not res.get("id"):
            res["id"] = doc_id or res.get("user_id") or ""
        res.setdefault("username", doc_id or "user")
        res.setdefault("full_name", res.get("username", "User"))
        res.setdefault("phone", "")
        res.setdefault("preferred_language", "en")
        res.setdefault("role", "farmer")
        res.setdefault("farm_name", "Green Valley Sericulture Farm")
        res.setdefault("region", "Local Rearing Shed")
        res.setdefault("batch_id", "SERI-2026-M04")
        res.setdefault("dfl_capacity", "200 DFL")
        res.setdefault("breed", "Double Hybrid (FC1 x FC2)")
        act_val = res.get("is_active")
        if act_val is None:
            res["is_active"] = True
        else:
            res["is_active"] = False if (act_val is False or act_val == 0 or str(act_val).lower() == "false") else True
        res.setdefault("access_scope", "GLOBAL")
        res.setdefault("whatsapp_verified", False)
        return res

    def get_user_by_username_or_phone(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Finds user by username, email, or phone number in Firestore."""
        if not self.is_available:
            return None
        clean_id = (identifier or "").strip()
        if not clean_id:
            return None
        try:
            users_ref = self._db.collection("users")

            # 0. Direct document ID lookup
            try:
                doc = users_ref.document(clean_id).get()
                if doc.exists:
                    d_data = doc.to_dict()
                    if d_data and d_data.get("hashed_password"):
                        return self._normalize_user_doc(d_data, doc.id)
            except Exception:
                pass

            # 1. By exact username
            docs = list(users_ref.where("username", "==", clean_id).limit(1).stream())
            if docs:
                return self._normalize_user_doc(docs[0].to_dict(), docs[0].id)

            # 2. Lowercase username
            if clean_id.lower() != clean_id:
                docs = list(users_ref.where("username", "==", clean_id.lower()).limit(1).stream())
                if docs:
                    return self._normalize_user_doc(docs[0].to_dict(), docs[0].id)

            # 3. By official_email or email
            docs = list(users_ref.where("official_email", "==", clean_id).limit(1).stream())
            if docs:
                return self._normalize_user_doc(docs[0].to_dict(), docs[0].id)
            if clean_id.lower() != clean_id:
                docs = list(users_ref.where("official_email", "==", clean_id.lower()).limit(1).stream())
                if docs:
                    return self._normalize_user_doc(docs[0].to_dict(), docs[0].id)

            docs = list(users_ref.where("email", "==", clean_id).limit(1).stream())
            if docs:
                return self._normalize_user_doc(docs[0].to_dict(), docs[0].id)
            if clean_id.lower() != clean_id:
                docs = list(users_ref.where("email", "==", clean_id.lower()).limit(1).stream())
                if docs:
                    return self._normalize_user_doc(docs[0].to_dict(), docs[0].id)

            # 4. By phone
            docs = list(users_ref.where("phone", "==", clean_id).limit(1).stream())
            if docs:
                return self._normalize_user_doc(docs[0].to_dict(), docs[0].id)

            # 5. By clean phone digits
            digits = "".join(ch for ch in clean_id if ch.isdigit())
            if len(digits) >= 10:
                for candidate in [digits, f"+91{digits[-10:]}", f"+91 {digits[-10:]}"]:
                    docs = list(users_ref.where("phone", "==", candidate).limit(1).stream())
                    if docs:
                        return self._normalize_user_doc(docs[0].to_dict(), docs[0].id)

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
                return self._normalize_user_doc(doc.to_dict(), doc.id)
            docs = list(self._db.collection("users").where("id", "==", user_id).limit(1).stream())
            if docs:
                return self._normalize_user_doc(docs[0].to_dict(), docs[0].id)
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

    def update_user_password(self, user_id: str, hashed_password: str, must_change_password: bool = False) -> bool:
        """Updates user password and must_change_password flag in Firestore."""
        if not self.is_available or not user_id:
            return False
        try:
            self._db.collection("users").document(user_id).set({
                "hashed_password": hashed_password,
                "must_change_password": bool(must_change_password),
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

    def update_user_profile(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """Updates user profile attributes in Firestore."""
        if not self.is_available or not user_id:
            return False
        try:
            clean_updates = dict(updates)
            clean_updates["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._db.collection("users").document(user_id).set(clean_updates, merge=True)
            return True
        except Exception as e:
            logger.warning("Firestore update_user_profile error: %s", e)
            return False

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Retrieves user document by exact username from Firestore."""
        return self.get_user_by_username_or_phone(username)

    def get_all_users(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Lists users from Firestore."""
        if not self.is_available:
            return []
        try:
            docs = self._db.collection("users").limit(limit).stream()
            return [{"id": d.id, **d.to_dict()} for d in docs]
        except Exception as e:
            logger.debug("Firestore get_all_users error: %s", e)
            return []

    def get_users_by_role(self, role: str) -> List[Dict[str, Any]]:
        """Queries users matching a specific role in Firestore."""
        if not self.is_available:
            return []
        try:
            docs = self._db.collection("users").where("role", "==", role).stream()
            return [{"id": d.id, **d.to_dict()} for d in docs]
        except Exception as e:
            logger.debug("Firestore get_users_by_role notice: %s", e)
            return []

    # =========================================================================
    # 6. SHEDS & FARM REARING MANAGEMENT
    # =========================================================================

    def create_shed(self, shed_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Creates or registers a rearing shed in Firestore."""
        if not self.is_available:
            return None
        try:
            s_id = shed_data.get("id") or shed_data.get("shed_id")
            if not s_id:
                s_id = f"shed_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
            data = dict(shed_data)
            data["id"] = s_id
            data["shed_id"] = s_id
            now_iso = datetime.now(timezone.utc).isoformat()
            data["created_at"] = data.get("created_at") or now_iso
            data["updated_at"] = now_iso
            self._db.collection("sheds").document(s_id).set(data, merge=True)
            return data
        except Exception as e:
            logger.warning("Firestore create_shed error: %s", e)
            return None

    def get_shed_by_id(self, shed_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a shed document by ID from Firestore."""
        if not self.is_available or not shed_id:
            return None
        try:
            doc = self._db.collection("sheds").document(shed_id).get()
            if doc.exists:
                return {"id": doc.id, **doc.to_dict()}
            docs = list(self._db.collection("sheds").where("shed_id", "==", shed_id).limit(1).stream())
            if docs:
                return {"id": docs[0].id, **docs[0].to_dict()}
        except Exception as e:
            logger.debug("Firestore get_shed_by_id error: %s", e)
        return None

    def get_sheds_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Retrieves sheds owned by a user from Firestore."""
        if not self.is_available or not user_id:
            return []
        try:
            docs = self._db.collection("sheds").where("user_id", "==", user_id).stream()
            return [{"id": d.id, **d.to_dict()} for d in docs]
        except Exception as e:
            logger.debug("Firestore get_sheds_by_user error: %s", e)
            return []

    def update_shed_settings(self, shed_id: str, settings_data: Dict[str, Any]) -> bool:
        """Updates custom setpoints and parameters for a shed in Firestore."""
        if not self.is_available or not shed_id:
            return False
        try:
            self._db.collection("sheds").document(shed_id).set({
                "settings": settings_data,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }, merge=True)
            return True
        except Exception as e:
            logger.warning("Firestore update_shed_settings error: %s", e)
            return False

    def save_product(self, product_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Creates or updates a product in Firestore."""
        if not self.is_available:
            return None
        try:
            p_id = product_data.get("id") or product_data.get("sku") or f"prod_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
            data = dict(product_data)
            data["id"] = p_id
            now_iso = datetime.now(timezone.utc).isoformat()
            data["created_at"] = data.get("created_at") or now_iso
            data["updated_at"] = now_iso
            self._db.collection("products").document(p_id).set(data, merge=True)
            return data
        except Exception as e:
            logger.warning("Firestore save_product error: %s", e)
            return None

    def delete_product(self, product_id: str) -> bool:
        """Deletes a product from Firestore."""
        if not self.is_available or not product_id:
            return False
        try:
            self._db.collection("products").document(product_id).delete()
            return True
        except Exception as e:
            logger.warning("Firestore delete_product error: %s", e)
            return False

    # =========================================================================
    # 7. DEVICES & HARDWARE NODES
    # =========================================================================

    def get_all_devices(self) -> List[Dict[str, Any]]:
        """Retrieves all IoT nodes from Firestore."""
        if not self.is_available:
            return []
        try:
            docs = self._db.collection("devices").stream()
            return [{"id": d.id, **d.to_dict()} for d in docs]
        except Exception as e:
            logger.debug("Firestore get_all_devices error: %s", e)
            return []

    def get_device(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves specific IoT device by ID."""
        if not self.is_available or not device_id:
            return None
        try:
            doc = self._db.collection("devices").document(device_id).get()
            if doc.exists:
                return {"id": doc.id, **doc.to_dict()}
            docs = list(self._db.collection("devices").where("device_id", "==", device_id).limit(1).stream())
            if docs:
                return {"id": docs[0].id, **docs[0].to_dict()}
        except Exception as e:
            logger.debug("Firestore get_device error: %s", e)
        return None

    def save_device(self, device_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Registers or updates IoT device in Firestore."""
        if not self.is_available:
            return None
        try:
            d_id = device_data.get("id") or device_data.get("device_id") or f"dev_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
            data = dict(device_data)
            data["id"] = d_id
            data["device_id"] = d_id
            now_iso = datetime.now(timezone.utc).isoformat()
            data.setdefault("created_at", now_iso)
            data["updated_at"] = now_iso
            self._db.collection("devices").document(d_id).set(data, merge=True)
            return data
        except Exception as e:
            logger.warning("Firestore save_device error: %s", e)
            return None

    def update_device_heartbeat(self, device_id: str, seq: Optional[int] = None) -> bool:
        """Updates device last_seen_at timestamp and ONLINE status."""
        if not self.is_available or not device_id:
            return False
        try:
            updates = {
                "status": "ONLINE",
                "last_seen_at": datetime.now(timezone.utc).isoformat()
            }
            if seq is not None:
                updates["last_sequence"] = seq
            self._db.collection("devices").document(device_id).set(updates, merge=True)
            return True
        except Exception as e:
            logger.debug("Firestore update_device_heartbeat notice: %s", e)
            return False

    # =========================================================================
    # 8. SHEDS, SUBSCRIPTIONS, TICKETS, ALERTS, INSTALLATIONS
    # =========================================================================

    def get_all_sheds(self) -> List[Dict[str, Any]]:
        """Retrieves sheds from Firestore, augmenting with active farmers' sheds."""
        if not self.is_available:
            return []
        try:
            sheds_dict = {}
            # 1. Direct sheds collection
            for d in self._db.collection("sheds").stream():
                data = d.to_dict()
                s_id = data.get("shed_id") or data.get("id") or d.id
                sheds_dict[s_id] = {"id": d.id, "shed_id": s_id, **data}

            # 2. Derive sheds from registered farmers
            farmers = self.get_users_by_role("farmer")
            for f in farmers:
                s_id = f.get("shed_id")
                if s_id and s_id not in sheds_dict:
                    farm_name = f.get("farm_name") or "Rearing Shed"
                    farmer_name = f.get("full_name") or f.get("username") or "Farmer"
                    sheds_dict[s_id] = {
                        "id": s_id,
                        "shed_id": s_id,
                        "farm_name": farm_name,
                        "farmer_name": farmer_name,
                        "farmer_id": f.get("id"),
                        "region": f.get("region") or "Karnataka",
                        "display_name": f"{farm_name} ({farmer_name})",
                        "is_active": bool(f.get("is_active", True))
                    }
            return list(sheds_dict.values())
        except Exception as e:
            logger.debug("Firestore get_all_sheds error: %s", e)
            return []

    def get_all_subscriptions(self) -> List[Dict[str, Any]]:
        """Retrieves all active subscriptions from Firestore."""
        if not self.is_available:
            return []
        try:
            docs = self._db.collection("subscriptions").stream()
            return [{"id": d.id, **d.to_dict()} for d in docs]
        except Exception as e:
            logger.debug("Firestore get_all_subscriptions error: %s", e)
            return []

    def save_subscription(self, sub_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Saves subscription record in Firestore."""
        if not self.is_available:
            return None
        try:
            s_id = sub_data.get("id") or f"sub_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
            data = dict(sub_data)
            data["id"] = s_id
            self._db.collection("subscriptions").document(s_id).set(data, merge=True)
            return data
        except Exception as e:
            logger.warning("Firestore save_subscription error: %s", e)
            return None

    def get_all_support_tickets(self) -> List[Dict[str, Any]]:
        """Retrieves support tickets from Firestore."""
        if not self.is_available:
            return []
        try:
            docs = self._db.collection("support_tickets").order_by("created_at", direction="DESCENDING").stream()
            return [{"id": d.id, **d.to_dict()} for d in docs]
        except Exception:
            try:
                docs = self._db.collection("support_tickets").stream()
                return [{"id": d.id, **d.to_dict()} for d in docs]
            except Exception as e:
                logger.debug("Firestore get_all_support_tickets error: %s", e)
                return []

    def save_support_ticket(self, ticket_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Saves support ticket in Firestore."""
        if not self.is_available:
            return None
        try:
            t_id = ticket_data.get("id") or f"tkt_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
            data = dict(ticket_data)
            data["id"] = t_id
            data.setdefault("created_at", datetime.now(timezone.utc).isoformat())
            self._db.collection("support_tickets").document(t_id).set(data, merge=True)
            return data
        except Exception as e:
            logger.warning("Firestore save_support_ticket error: %s", e)
            return None

    def get_all_alerts(self) -> List[Dict[str, Any]]:
        """Retrieves active alerts from Firestore."""
        if not self.is_available:
            return []
        try:
            docs = self._db.collection("alerts").stream()
            return [{"id": d.id, **d.to_dict()} for d in docs]
        except Exception as e:
            logger.debug("Firestore get_all_alerts error: %s", e)
            return []

    def save_alert(self, alert_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Saves alert document in Firestore."""
        if not self.is_available:
            return None
        try:
            a_id = alert_data.get("id") or f"alt_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
            data = dict(alert_data)
            data["id"] = a_id
            data.setdefault("created_at", datetime.now(timezone.utc).isoformat())
            self._db.collection("alerts").document(a_id).set(data, merge=True)
            return data
        except Exception as e:
            logger.warning("Firestore save_alert error: %s", e)
            return None

    def get_all_installations(self) -> List[Dict[str, Any]]:
        """Retrieves installation jobs from Firestore."""
        if not self.is_available:
            return []
        try:
            docs = self._db.collection("installation_jobs").stream()
            return [{"id": d.id, **d.to_dict()} for d in docs]
        except Exception as e:
            logger.debug("Firestore get_all_installations error: %s", e)
            return []

    def save_installation(self, job_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Saves installation job document in Firestore."""
        if not self.is_available:
            return None
        try:
            j_id = job_data.get("id") or f"job_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
            data = dict(job_data)
            data["id"] = j_id
            data.setdefault("created_at", datetime.now(timezone.utc).isoformat())
            self._db.collection("installation_jobs").document(j_id).set(data, merge=True)
            return data
        except Exception as e:
            logger.warning("Firestore save_installation error: %s", e)
            return None

    # =========================================================================
    # 9. REAL-TIME AUTHORITATIVE KPI COMPUTATION
    # =========================================================================

    def compute_overview_kpis(self) -> Dict[str, Any]:
        """
        Computes 100% authoritative platform KPIs directly from Cloud Firestore collections.
        Used as authoritative source on cloud workers where PostgreSQL is unreachable.
        """
        now_dt = datetime.now(timezone.utc)
        now_iso = now_dt.isoformat()

        if not self.is_available:
            return {
                "total_users": 0, "total_farmers": 0, "active_farmers": 0,
                "total_sheds": 0, "total_devices": 0, "online_devices": 0, "offline_devices": 0,
                "active_subscriptions": 0, "mrr_inr": 0.0, "pending_orders": 0, "total_revenue_inr": 0.0,
                "open_tickets": 0, "critical_tickets": 0, "active_alerts": 0, "critical_alerts": 0,
                "pending_installations": 0, "last_updated": now_iso
            }

        try:
            # 1. Users & Farmers
            all_users = list(self._db.collection("users").stream())
            total_users = len(all_users)
            farmers = []
            for u in all_users:
                ud = u.to_dict()
                if ud.get("role") == "farmer":
                    farmers.append(ud)
            total_farmers = len(farmers)
            active_farmers = sum(1 for f in farmers if f.get("is_active", True))

            # 2. Unique monitored sheds
            shed_ids = set()
            for s in self._db.collection("sheds").stream():
                sd = s.to_dict()
                sid = sd.get("shed_id") or sd.get("id") or s.id
                if sid:
                    shed_ids.add(sid)
            for f in farmers:
                sid = f.get("shed_id")
                if sid:
                    shed_ids.add(sid)
            total_sheds = len(shed_ids)

            # 3. Devices
            devices = [d.to_dict() for d in self._db.collection("devices").stream()]
            total_devices = len(devices)
            online_devices = 0
            cutoff = (now_dt - timedelta(seconds=300)).isoformat()
            for dev in devices:
                status = dev.get("status")
                last_seen = dev.get("last_seen_at") or ""
                if status == "ONLINE" or (last_seen and last_seen > cutoff):
                    online_devices += 1
            offline_devices = max(0, total_devices - online_devices)

            # 4. Subscriptions & MRR
            subscriptions = [s.to_dict() for s in self._db.collection("subscriptions").stream()]
            active_subs = [s for s in subscriptions if s.get("status") == "ACTIVE"]
            active_subscriptions = len(active_subs)
            mrr_minor = sum(s.get("monthly_price_minor_units", 0) for s in active_subs)
            mrr_inr = round(mrr_minor / 100.0, 2)

            # 5. Orders & Revenue
            orders = [o.to_dict() for o in self._db.collection("orders").stream()]
            pending_orders = sum(1 for o in orders if o.get("status") in ("PENDING", "PAYMENT_PENDING", "PROCESSING"))
            total_rev_minor = sum(o.get("total_price_minor_units", o.get("total_amount", 0) * 100) for o in orders if o.get("status") in ("PAID", "DELIVERED", "COMPLETED"))
            total_revenue_inr = round(total_rev_minor / 100.0, 2)

            # 6. Support Tickets
            tickets = [t.to_dict() for t in self._db.collection("support_tickets").stream()]
            open_tickets = sum(1 for t in tickets if t.get("status") in ("OPEN", "ASSIGNED", "IN_PROGRESS", "ESCALATED"))
            critical_tickets = sum(1 for t in tickets if t.get("priority") == "CRITICAL" and t.get("status") != "CLOSED")

            # 7. Alerts
            alerts = [a.to_dict() for a in self._db.collection("alerts").stream()]
            active_alerts_list = [a for a in alerts if a.get("status") == "ACTIVE"]
            active_alerts = len(active_alerts_list)
            critical_alerts = sum(1 for a in active_alerts_list if a.get("severity") == "CRITICAL")

            # 8. Installations
            jobs = [j.to_dict() for j in self._db.collection("installation_jobs").stream()]
            pending_jobs = sum(1 for j in jobs if j.get("status") in ("REQUESTED", "SCHEDULED", "ASSIGNED", "IN_PROGRESS"))

            return {
                "total_users": total_users,
                "total_farmers": total_farmers,
                "active_farmers": active_farmers,
                "total_sheds": total_sheds,
                "total_devices": total_devices,
                "online_devices": online_devices,
                "offline_devices": offline_devices,
                "active_subscriptions": active_subscriptions,
                "mrr_inr": mrr_inr,
                "pending_orders": pending_orders,
                "total_revenue_inr": total_revenue_inr,
                "open_tickets": open_tickets,
                "critical_tickets": critical_tickets,
                "active_alerts": active_alerts,
                "critical_alerts": critical_alerts,
                "pending_installations": pending_jobs,
                "last_updated": now_iso
            }
        except Exception as e:
            logger.error("Error computing Firestore overview KPIs: %s", e)
            return {
                "total_users": 0, "total_farmers": 0, "active_farmers": 0,
                "total_sheds": 0, "total_devices": 0, "online_devices": 0, "offline_devices": 0,
                "active_subscriptions": 0, "mrr_inr": 0.0, "pending_orders": 0, "total_revenue_inr": 0.0,
                "open_tickets": 0, "critical_tickets": 0, "active_alerts": 0, "critical_alerts": 0,
                "pending_installations": 0, "last_updated": now_iso
            }

    # =========================================================================
    # 10. EMPLOYEE DIRECTORY & INVITATIONS
    # =========================================================================

    def create_employee(self, emp_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Saves an employee profile document into Cloud Firestore."""
        if not self.is_available:
            return None
        try:
            emp_id = emp_data.get("id") or f"emp_{emp_data.get('employee_id', 'new')}"
            data_to_store = dict(emp_data)
            if "created_at" not in data_to_store:
                data_to_store["created_at"] = datetime.now(timezone.utc).isoformat()
            data_to_store["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._db.collection("employees").document(emp_id).set(data_to_store, merge=True)
            logger.info("Created employee %s (%s) in Cloud Firestore", emp_id, emp_data.get("official_email"))
            return data_to_store
        except Exception as e:
            logger.error("Error creating employee in Cloud Firestore: %s", e)
            return None

    def get_employee(self, employee_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves an employee record by id, employee_id code, or official_email."""
        if not self.is_available:
            return None
        try:
            doc = self._db.collection("employees").document(employee_id).get()
            if doc.exists:
                d = doc.to_dict()
                d["id"] = doc.id
                return d

            # Query by employee_id or official_email
            for field in ["employee_id", "official_email", "user_id"]:
                docs = list(self._db.collection("employees").where(field, "==", employee_id).limit(1).stream())
                if docs:
                    d = docs[0].to_dict()
                    d["id"] = docs[0].id
                    return d
            return None
        except Exception as e:
            logger.warning("Error fetching employee %s from Firestore: %s", employee_id, e)
            return None

    def list_employees(self, limit: int = 50, offset: int = 0) -> Tuple[int, List[Dict[str, Any]]]:
        """Lists all employees from Cloud Firestore with pagination support."""
        if not self.is_available:
            return 0, []
        try:
            all_emps = []
            for doc in self._db.collection("employees").stream():
                d = doc.to_dict()
                d["id"] = doc.id
                all_emps.append(d)
            # Sort by created_at desc
            all_emps.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)
            total = len(all_emps)
            return total, all_emps[offset:offset + limit]
        except Exception as e:
            logger.warning("Error listing employees from Firestore: %s", e)
            return 0, []

    def update_employee(self, employee_id: str, updates: Dict[str, Any]) -> bool:
        """Updates employee fields in Cloud Firestore."""
        if not self.is_available:
            return False
        try:
            emp = self.get_employee(employee_id)
            if not emp:
                return False
            actual_id = emp.get("id") or employee_id
            updates_copy = dict(updates)
            updates_copy["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._db.collection("employees").document(actual_id).update(updates_copy)
            return True
        except Exception as e:
            logger.warning("Error updating employee %s in Firestore: %s", employee_id, e)
            return False

    def delete_employee(self, employee_id: str) -> bool:
        """Removes an employee document from Cloud Firestore."""
        if not self.is_available:
            return False
        try:
            emp = self.get_employee(employee_id)
            if not emp:
                return False
            actual_id = emp.get("id") or employee_id
            self._db.collection("employees").document(actual_id).delete()
            return True
        except Exception as e:
            logger.warning("Error deleting employee %s from Firestore: %s", employee_id, e)
            return False

    def create_employee_invitation(self, inv_data: Dict[str, Any]) -> bool:
        """Persists single-use employee invitation token in Cloud Firestore."""
        if not self.is_available:
            return False
        try:
            inv_id = inv_data.get("id") or f"inv_{inv_data.get('token', 'tok')[:10]}"
            self._db.collection("employee_invitations").document(inv_id).set(inv_data, merge=True)
            return True
        except Exception as e:
            logger.warning("Error saving employee invitation in Firestore: %s", e)
            return False

    def get_employee_invitation(self, token: str) -> Optional[Dict[str, Any]]:
        """Finds active employee invitation token in Cloud Firestore."""
        if not self.is_available:
            return None
        try:
            docs = list(self._db.collection("employee_invitations").where("token", "==", token).limit(1).stream())
            if docs:
                d = docs[0].to_dict()
                d["id"] = docs[0].id
                return d
            return None
        except Exception as e:
            logger.warning("Error querying employee invitation in Firestore: %s", e)
            return None


# Global singleton instance
firestore_service = FirestoreService()


