"""Resend email service for Truth Mirror authentication and verification."""

from __future__ import annotations

import html
import logging
import os
from typing import Any, Dict

import resend

logger = logging.getLogger(__name__)


def _build_verification_html(code: str) -> str:
    """Generate responsive HTML body for the verification email with #06B6D4 branding."""
    escaped_code = html.escape(code.strip())
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Your Truth Mirror Verification Code</title>
</head>
<body style="margin: 0; padding: 0; background-color: #0f172a; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #f8fafc;">
  <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color: #0f172a; padding: 40px 20px;">
    <tr>
      <td align="center">
        <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 520px; background-color: #1e293b; border: 1px solid #334155; border-radius: 12px; overflow: hidden; padding: 32px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
          <tr>
            <td align="center" style="padding-bottom: 24px;">
              <h1 style="margin: 0; font-size: 26px; font-weight: 700; color: #06B6D4; letter-spacing: -0.5px;">Truth Mirror</h1>
              <p style="margin: 6px 0 0 0; font-size: 14px; color: #94a3b8;">Multi-Source Narrative &amp; Truth Intelligence</p>
            </td>
          </tr>
          <tr>
            <td style="padding-bottom: 24px; border-top: 1px solid #334155; padding-top: 24px;">
              <p style="margin: 0 0 16px 0; font-size: 16px; line-height: 24px; color: #e2e8f0;">Hello,</p>
              <p style="margin: 0 0 24px 0; font-size: 15px; line-height: 22px; color: #cbd5e1;">Use the following verification code to verify your email address and activate your Truth Mirror account:</p>
              <div style="background-color: #0f172a; border: 2px solid #06B6D4; border-radius: 8px; padding: 20px; text-align: center; margin-bottom: 24px;">
                <span style="font-family: 'Courier New', Courier, monospace; font-size: 36px; font-weight: 700; letter-spacing: 8px; color: #06B6D4; display: inline-block;">{escaped_code}</span>
              </div>
              <p style="margin: 0; font-size: 13px; line-height: 20px; color: #94a3b8;">This code will expire in 15 minutes. If you did not request this code, you can safely ignore this email.</p>
            </td>
          </tr>
          <tr>
            <td align="center" style="border-top: 1px solid #334155; padding-top: 20px;">
              <p style="margin: 0; font-size: 12px; color: #64748b;">&copy; Truth Mirror. All rights reserved.</p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def send_verification_email(to_email: str, code: str) -> None:
    """Send a verification email with the 6-digit code via Resend.

    Args:
        to_email: Recipient email address.
        code: 6-digit verification code.

    Raises:
        RuntimeError: If RESEND_API_KEY is not set in environment.
        Exception: If Resend API call fails.
    """
    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        logger.error("RESEND_API_KEY is not set")
        raise RuntimeError("RESEND_API_KEY is not set")

    from_email = os.environ.get("RESEND_FROM", "noreply@truth-mirror.net")

    resend.api_key = api_key
    html_content = _build_verification_html(code)

    params: resend.Emails.SendParams = {
        "from": from_email,
        "to": [to_email.strip()],
        "subject": "Your Truth Mirror Verification Code",
        "html": html_content,
    }

    try:
        response = resend.Emails.send(params)
        logger.info("Verification email sent successfully to %s: %s", to_email, response)
    except Exception as exc:
        logger.error("Failed to send verification email to %s: %s", to_email, exc)
        raise
