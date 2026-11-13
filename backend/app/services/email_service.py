import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
import json
import urllib.request
import urllib.error
from typing import Optional
from app.core.config import settings

logger = logging.getLogger("email_service")

def ensure_firebase_user_exists(email: str, display_name: Optional[str] = None) -> bool:
    """
    Verifies that the user exists in Firebase Authentication, creating the identity if absent.
    """
    clean_email = (email or "").strip().lower()
    if not clean_email or "@" not in clean_email:
        return False
    try:
        import firebase_admin
        from firebase_admin import auth
        from app.services.firestore_service import firestore_service
        _ = firestore_service.is_available

        try:
            auth.get_user_by_email(clean_email)
            return True
        except auth.UserNotFoundError:
            auth.create_user(
                email=clean_email,
                display_name=display_name or clean_email.split("@")[0]
            )
            logger.info("Provisioned user %s in Firebase Auth directory.", clean_email)
            return True
    except Exception as e:
        logger.warning("ensure_firebase_user_exists notice for %s: %s", clean_email, e)
        return False

def send_firebase_password_reset_email(to_email: str, continue_url: Optional[str] = None, display_name: Optional[str] = None) -> bool:
    """
    Sends the official password reset email to an existing user via the Firebase
    Authentication email server (Project: setu-a767c).
    Email server console: https://console.firebase.google.com/project/setu-a767c/authentication/emails
    """
    clean_email = (to_email or "").strip().lower()
    if not clean_email or "@" not in clean_email:
        logger.warning("Invalid recipient email for Firebase password reset: '%s'", to_email)
        return False

    api_key = settings.FIREBASE_WEB_API_KEY
    if not api_key:
        logger.warning("FIREBASE_WEB_API_KEY is not configured.")
        return False

    # Ensure user exists in Firebase Auth before dispatching
    ensure_firebase_user_exists(clean_email, display_name=display_name)

    url = f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={api_key}"
    target_continue_url = continue_url or "https://setu-adminweb.vercel.app/login?mode=resetPassword"
    payload = {
        "requestType": "PASSWORD_RESET",
        "email": clean_email,
        "continueUrl": target_continue_url
    }

    try:
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                logger.info("Firebase Auth password reset email sent successfully to %s", clean_email)
                return True
            logger.warning("Firebase sendOobCode unexpected status %s for %s", resp.status, clean_email)
            return False
    except urllib.error.HTTPError as he:
        body = he.read().decode("utf-8", errors="ignore")
        logger.warning("Firebase sendOobCode HTTP %s for %s: %s", he.code, clean_email, body)
        return False
    except Exception as e:
        logger.warning("Firebase sendOobCode error for %s: %s", clean_email, e)
        return False

def send_firebase_welcome_email(
    to_email: str,
    full_name: str,
    role_code: str = "technician",
    continue_url: Optional[str] = None
) -> bool:
    """
    Sends the official Welcome & Account Activation email to newly added users / employees
    via the Firebase Authentication email server (Project: setu-a767c).
    When the recipient clicks the link in their inbox, they arrive on the platform, reset/set their password,
    and are immediately authenticated into their dashboard.
    """
    clean_email = (to_email or "").strip().lower()
    if not clean_email or "@" not in clean_email:
        logger.warning("Invalid recipient email for welcome email: '%s'", to_email)
        return False

    api_key = settings.FIREBASE_WEB_API_KEY
    if not api_key:
        logger.warning("FIREBASE_WEB_API_KEY is not configured.")
        return False

    # Ensure user exists in Firebase Auth before dispatching
    ensure_firebase_user_exists(clean_email, display_name=full_name)

    target_continue_url = continue_url or "https://setu-adminweb.vercel.app/login?mode=resetPassword"
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={api_key}"
    payload = {
        "requestType": "PASSWORD_RESET",
        "email": clean_email,
        "continueUrl": target_continue_url
    }

    try:
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                logger.info("Firebase Auth Welcome / Password Reset email dispatched to %s", clean_email)
                return True
            logger.warning("Firebase sendOobCode unexpected status %s for %s", resp.status, clean_email)
            return False
    except Exception as e:
        logger.warning("Firebase sendOobCode welcome email notice for %s: %s", clean_email, e)
        return False

def verify_and_apply_firebase_password_reset(oob_code: str, new_password: str) -> Optional[str]:
    """
    Applies the new password in Firebase Authentication using the verified oobCode
    from the password reset email. Returns the confirmed user email on success, or None.
    """
    clean_code = (oob_code or "").strip()
    if not clean_code or len(new_password) < 6:
        return None

    api_key = settings.FIREBASE_WEB_API_KEY
    if not api_key:
        return None

    url = f"https://identitytoolkit.googleapis.com/v1/accounts:resetPassword?key={api_key}"
    payload = {
        "oobCode": clean_code,
        "newPassword": new_password
    }

    try:
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                resp_data = json.loads(resp.read().decode("utf-8"))
                confirmed_email = resp_data.get("email")
                logger.info("Firebase password reset successful for %s", confirmed_email)
                return confirmed_email
            return None
    except Exception as e:
        logger.warning("Firebase resetPassword error for code: %s", e)
        return None

def sync_firebase_user_password(email: str, new_password: str) -> bool:
    """
    Updates the password of an existing user in Firebase Authentication using Admin SDK.
    Creates the user if not yet registered in Firebase Auth.
    """
    clean_email = (email or "").strip().lower()
    if not clean_email or "@" not in clean_email or len(new_password) < 6:
        return False

    try:
        import firebase_admin
        from firebase_admin import auth
        from app.services.firestore_service import firestore_service
        _ = firestore_service.is_available

        try:
            fb_user = auth.get_user_by_email(clean_email)
            auth.update_user(fb_user.uid, password=new_password)
            logger.info("Synchronized password in Firebase Auth for %s (uid=%s)", clean_email, fb_user.uid)
            return True
        except auth.UserNotFoundError:
            fb_user = auth.create_user(email=clean_email, password=new_password)
            logger.info("Created user and set password in Firebase Auth for %s (uid=%s)", clean_email, fb_user.uid)
            return True
    except Exception as e:
        logger.warning("Error syncing Firebase user password for %s: %s", clean_email, e)
        return False

def send_password_reset_email(to_email: str, username: str, reset_code: str) -> bool:
    """
    Sends a secure 6-digit verification code to the user's email via SMTP for password recovery.
    """
    clean_email = (to_email or "").strip()
    if not clean_email or "@" not in clean_email:
        logger.warning("Invalid destination email address for password reset: '%s'", to_email)
        return False

    display_name = username or "Valued User"
    subject = f"Your Setu Verification Code: {reset_code}"
    
    html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Setu Verification Code</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      background-color: #f8fafc;
      margin: 0;
      padding: 24px;
      color: #1e293b;
    }}
    .email-container {{
      max-width: 520px;
      margin: 0 auto;
      background: #ffffff;
      border-radius: 12px;
      border: 1px solid #e2e8f0;
      overflow: hidden;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }}
    .email-header {{
      background: #065f46;
      color: #ffffff;
      padding: 24px 32px;
      text-align: center;
    }}
    .email-header h1 {{
      margin: 0;
      font-size: 20px;
      font-weight: 700;
      letter-spacing: 0.02em;
    }}
    .email-header p {{
      margin: 4px 0 0;
      font-size: 13px;
      opacity: 0.9;
    }}
    .email-body {{
      padding: 32px;
    }}
    .otp-card {{
      background: #f0fdf4;
      border: 2px dashed #059669;
      border-radius: 8px;
      padding: 20px;
      text-align: center;
      margin: 24px 0;
    }}
    .otp-code {{
      font-family: 'JetBrains Mono', 'Courier New', monospace;
      font-size: 32px;
      font-weight: 800;
      letter-spacing: 8px;
      color: #065f46;
    }}
    .expiry-badge {{
      font-size: 12px;
      color: #047857;
      margin-top: 8px;
      font-weight: 600;
    }}
    .email-footer {{
      padding: 16px 32px;
      background: #f8fafc;
      border-top: 1px solid #e2e8f0;
      font-size: 12px;
      color: #64748b;
      text-align: center;
      line-height: 1.5;
    }}
  </style>
</head>
<body>
  <div class="email-container">
    <div class="email-header">
      <h1>Setu Sericulture Platform</h1>
      <p>Official Security &amp; Identity Gateway</p>
    </div>
    <div class="email-body">
      <p style="font-size: 15px; margin-top: 0;">Hello <strong>{display_name}</strong>,</p>
      <p style="font-size: 14px; line-height: 1.6; color: #475569;">
        We received a request to recover your password on the Setu Platform. Enter the 6-digit verification code below in your browser to choose your new password:
      </p>
      
      <div class="otp-card">
        <div class="otp-code">{reset_code}</div>
        <div class="expiry-badge">&#x23F1; Active for 15 minutes</div>
      </div>

      <p style="font-size: 13px; color: #64748b; line-height: 1.5;">
        If you did not request this verification code, please ignore this email or notify your system administrator immediately.
      </p>
    </div>
    <div class="email-footer">
      Protected by Setu Enterprise RBAC &middot; ISO 9001:2015 QA Compliant<br>
      Global Sericulture Environment Management Network
    </div>
  </div>
</body>
</html>
"""

    text_content = f"""Hello {display_name},

Your Setu Platform password recovery code is: {reset_code}

This code is active for 15 minutes.
If you did not request this recovery code, you can safely ignore this email.

Setu Enterprise Platform
Official Security & Identity Gateway
"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    from_addr = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>" if settings.SMTP_FROM_NAME else settings.SMTP_FROM_EMAIL
    msg["From"] = from_addr
    msg["To"] = clean_email

    msg.attach(MIMEText(text_content, "plain", "utf-8"))
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    try:
        # Check if custom port or SSL
        if settings.SMTP_SSL or settings.SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=8)
        else:
            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=8)
            if settings.SMTP_TLS:
                server.starttls()

        if settings.SMTP_USER and settings.SMTP_PASSWORD:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)

        server.sendmail(settings.SMTP_FROM_EMAIL or "noreply@setu.ag", [clean_email], msg.as_string())
        server.quit()
        logger.info("Successfully sent password reset email to %s via %s:%s", clean_email, settings.SMTP_HOST, settings.SMTP_PORT)
        return True
    except Exception as e:
        logger.warning("SMTP dispatch notice to %s: %s (Verification code is %s)", clean_email, e, reset_code)
        return False
