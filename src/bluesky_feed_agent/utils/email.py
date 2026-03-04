"""Email utilities for sending Bluesky summaries."""

import base64
import os
from datetime import datetime
from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


def _authorize_gmail(credentials_file: str) -> Credentials:
    """Authorize Gmail access and return user credentials.

    Uses local server flow by default. For remote/WSL environments, set
    GMAIL_OAUTH_FLOW=manual to use copy-link mode (no auto browser open), which
    still uses a valid localhost redirect.
    """
    flow = InstalledAppFlow.from_client_secrets_file(credentials_file, GMAIL_SCOPES)
    oauth_flow = os.getenv("GMAIL_OAUTH_FLOW", "local").strip().lower()

    if oauth_flow == "manual":
        return flow.run_local_server(
            host="127.0.0.1",
            port=0,
            open_browser=False,
            authorization_prompt_message="Open this URL in your browser:\n{url}",
            success_message="Authentication complete. You can close this tab.",
        )

    try:
        return flow.run_local_server(
            host="127.0.0.1",
            port=0,
            open_browser=True,
            success_message="Authentication complete. You can close this tab.",
        )
    except Exception:
        return flow.run_local_server(
            host="127.0.0.1",
            port=0,
            open_browser=False,
            authorization_prompt_message="Automatic browser open failed. Use this URL:\n{url}",
            success_message="Authentication complete. You can close this tab.",
        )


def send_summary_email_oauth(summary: str, user_handle: str = "") -> str:
    """Send summary email using Gmail OAuth.

    Args:
        summary: Generated summary text
        user_handle: Optional handle used in subject line

    Returns:
        Email status: sent or skipped
    """
    if os.getenv("GMAIL_OAUTH_ENABLED", "false").lower() != "true":
        return "skipped: GMAIL_OAUTH_ENABLED is not true"

    to_email = os.getenv("SUMMARY_EMAIL_TO", "")
    if not to_email:
        raise ValueError("SUMMARY_EMAIL_TO is required when GMAIL_OAUTH_ENABLED=true")

    credentials_file = os.getenv("GMAIL_CREDENTIALS_FILE", "credentials.json")
    token_file = os.getenv("GMAIL_TOKEN_FILE", "token.json")

    if not os.path.exists(credentials_file):
        raise FileNotFoundError(
            f"Gmail OAuth credentials file not found: {credentials_file}"
        )

    creds = None
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, GMAIL_SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            creds = _authorize_gmail(credentials_file)

        with open(token_file, "w", encoding="utf-8") as file:
            file.write(creds.to_json())

    service = build("gmail", "v1", credentials=creds)

    subject_target = user_handle if user_handle else "home feed"
    # Append current date in MM/DD/YYYY format to subject
    date_str = datetime.now().strftime("%m/%d/%Y")
    message = MIMEText(summary, "plain", "utf-8")
    message["to"] = to_email
    message["subject"] = f"Bluesky Summary ({subject_target}) - {date_str}"

    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    service.users().messages().send(userId="me", body={"raw": raw_message}).execute()
    return "sent"
