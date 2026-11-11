import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
from typing import Optional
from app.core.config import settings

logger = logging.getLogger("email_service")

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
