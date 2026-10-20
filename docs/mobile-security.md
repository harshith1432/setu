# Mobile Application Security Specification
**Framework**: Flutter 3.x / Dart (Android & iOS)  
**Security Standard**: OWASP Mobile Application Security Verification Standard (MASVS v2.0)  

---

## 1. Compliance Checklist (OWASP MASVS)

| MASVS Domain | Requirement | Implementation in SeriCare Mobile |
|---|---|---|
| **MASVS-STORAGE** | System credential storage | Tokens stored in hardware-backed storage via `flutter_secure_storage` (Android Keystore / iOS Keychain). |
| **MASVS-CRYPTO** | Cryptographic strength | TLS 1.3 enforced for all backend communications; no weak ciphers or custom crypto. |
| **MASVS-AUTH** | User session management | Automatic session verification via `/auth/me`; explicit logout clears secure storage and in-memory tokens. |
| **MASVS-NETWORK** | Network communication security | HTTPS enforced for all REST API, SSE, and WebSocket connections (`https://` and `wss://`). |
| **MASVS-PLATFORM** | Platform interaction | Deep links, location permissions, and background sync follow principle of least privilege. |
| **MASVS-CODE** | Code hardening & secrets | Zero hardcoded backend secrets, admin passwords, or private keys in the mobile binary. |

---

## 2. Hardening Measures Implemented

1. **Elimination of Insecure Token Fallbacks**:
   Removed legacy `'firebase_${user.uid}'` fallback string generation. If authentic token generation fails, the application prompts the user to re-authenticate cleanly.
2. **Encrypted Local Storage**:
   JWT access tokens and user profile records are persisted using hardware AES-256 encryption backed by the Android KeyStore or iOS Keychain.
3. **Safe Offline Operation**:
   Local sensor caching in SQLite / SharedPreferences stores only non-sensitive microclimate telemetry logs without persisting authentication credentials in plaintext.
4. **ProGuard / R8 Obfuscation**:
   Release builds apply R8 shrinking, name obfuscation, and debug interface stripping in `mobile/android/app/build.gradle.kts`.
