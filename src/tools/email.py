"""
Gmail Email Service for JARVIS - Phase 7

Provides email integration using Gmail API (FREE for personal use).

Features:
- Read recent emails
- Search emails by sender, subject, date
- Send emails
- Reply to emails
- Summarize email threads

Setup:
1. Go to Google Cloud Console (https://console.cloud.google.com/)
2. Enable Gmail API
3. Create OAuth 2.0 credentials (Desktop app)
4. Download credentials.json to config/google_credentials.json
5. Run JARVIS - it will prompt for authorization on first use

API Documentation: https://developers.google.com/gmail/api/reference/rest
"""

from __future__ import annotations

import asyncio
import base64
import pickle
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Any, Dict, List, Optional
import html

from loguru import logger

# Google API imports (optional)
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False
    logger.debug("Google API libraries not installed")


# OAuth scopes for Gmail API
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify',
]


@dataclass
class EmailMessage:
    """Represents an email message."""
    id: str
    thread_id: str
    subject: str
    sender: str
    sender_email: str
    recipients: List[str]
    date: datetime
    snippet: str
    body: str = ""
    is_read: bool = True
    labels: List[str] = field(default_factory=list)
    
    @classmethod
    def from_gmail_message(cls, msg: Dict[str, Any]) -> "EmailMessage":
        """Create EmailMessage from Gmail API response."""
        headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
        
        # Parse sender
        sender_full = headers.get("from", "Unknown")
        if "<" in sender_full:
            sender_name = sender_full.split("<")[0].strip().strip('"')
            sender_email = sender_full.split("<")[1].rstrip(">")
        else:
            sender_name = sender_full
            sender_email = sender_full
        
        # Parse recipients
        recipients = []
        to_header = headers.get("to", "")
        if to_header:
            recipients = [r.strip() for r in to_header.split(",")]
        
        # Parse date
        date_str = headers.get("date", "")
        try:
            # Try common date formats
            for fmt in [
                "%a, %d %b %Y %H:%M:%S %z",
                "%d %b %Y %H:%M:%S %z",
                "%a, %d %b %Y %H:%M:%S",
            ]:
                try:
                    date = datetime.strptime(date_str.split(" (")[0].strip(), fmt)
                    break
                except ValueError:
                    continue
            else:
                date = datetime.now()
        except Exception:
            date = datetime.now()
        
        # Get body
        body = ""
        payload = msg.get("payload", {})
        
        if "body" in payload and payload["body"].get("data"):
            body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="ignore")
        elif "parts" in payload:
            for part in payload["parts"]:
                if part.get("mimeType") == "text/plain":
                    if part.get("body", {}).get("data"):
                        body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="ignore")
                        break
                elif part.get("mimeType") == "text/html":
                    if part.get("body", {}).get("data"):
                        html_body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="ignore")
                        # Simple HTML to text conversion
                        body = html.unescape(html_body)
                        # Remove HTML tags (basic)
                        import re
                        body = re.sub(r'<[^>]+>', '', body)
        
        # Check if read
        labels = msg.get("labelIds", [])
        is_read = "UNREAD" not in labels
        
        return cls(
            id=msg.get("id", ""),
            thread_id=msg.get("threadId", ""),
            subject=headers.get("subject", "(No Subject)"),
            sender=sender_name,
            sender_email=sender_email,
            recipients=recipients,
            date=date,
            snippet=msg.get("snippet", ""),
            body=body,
            is_read=is_read,
            labels=labels,
        )
    
    def format_display(self, include_body: bool = False) -> str:
        """Format email for display."""
        read_indicator = "📧" if self.is_read else "📬"
        lines = [
            f"{read_indicator} **{self.subject}**",
            f"   From: {self.sender} <{self.sender_email}>",
            f"   Date: {self.date.strftime('%B %d, %Y at %I:%M %p')}",
        ]
        
        if include_body:
            # Truncate body for display
            body_preview = self.body[:500] if len(self.body) > 500 else self.body
            lines.append(f"\n{body_preview}")
            if len(self.body) > 500:
                lines.append("...[truncated]")
        else:
            lines.append(f"   {self.snippet[:100]}...")
        
        return "\n".join(lines)


class EmailService:
    """
    Gmail service for JARVIS.
    
    Provides email management capabilities using the Gmail API.
    Free for personal use with OAuth 2.0 authentication.
    """
    
    def __init__(
        self,
        credentials_file: str = "config/google_credentials.json",
        token_file: str = "config/gmail_token.pickle",
        max_results: int = 10,
        require_confirmation: bool = True,
    ):
        """
        Initialize email service.
        
        Args:
            credentials_file: Path to Google OAuth credentials JSON
            token_file: Path to store OAuth token
            max_results: Default max results for queries
            require_confirmation: Require confirmation before sending
        """
        self.credentials_file = Path(credentials_file)
        self.token_file = Path(token_file)
        self.max_results = max_results
        self.require_confirmation = require_confirmation
        self._service = None
        self._user_email = None
        
        # Pending emails awaiting confirmation
        self._pending_sends: Dict[str, Dict[str, Any]] = {}
    
    def _get_credentials(self) -> Optional[Credentials]:
        """Get or refresh OAuth credentials."""
        if not GOOGLE_API_AVAILABLE:
            logger.error("Google API libraries not installed")
            return None
        
        creds = None
        
        # Load existing token
        if self.token_file.exists():
            try:
                with open(self.token_file, "rb") as f:
                    creds = pickle.load(f)
            except Exception as e:
                logger.warning(f"Failed to load token: {e}")
        
        # Refresh or get new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    logger.warning(f"Failed to refresh token: {e}")
                    creds = None
            
            if not creds:
                if not self.credentials_file.exists():
                    logger.error(f"Credentials file not found: {self.credentials_file}")
                    return None
                
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(self.credentials_file), SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                except Exception as e:
                    logger.error(f"Failed to get credentials: {e}")
                    return None
            
            # Save token
            try:
                self.token_file.parent.mkdir(parents=True, exist_ok=True)
                with open(self.token_file, "wb") as f:
                    pickle.dump(creds, f)
            except Exception as e:
                logger.warning(f"Failed to save token: {e}")
        
        return creds
    
    def _get_service(self):
        """Get or create Gmail API service."""
        if self._service is None:
            creds = self._get_credentials()
            if creds is None:
                return None
            
            try:
                self._service = build("gmail", "v1", credentials=creds)
            except Exception as e:
                logger.error(f"Failed to build Gmail service: {e}")
                return None
        
        return self._service
    
    def is_available(self) -> bool:
        """Check if email service is available."""
        if not GOOGLE_API_AVAILABLE:
            return False
        return self._get_service() is not None
    
    async def get_user_email(self) -> Optional[str]:
        """Get the authenticated user's email address."""
        if self._user_email:
            return self._user_email
        
        service = self._get_service()
        if service is None:
            return None
        
        try:
            loop = asyncio.get_event_loop()
            profile = await loop.run_in_executor(
                None,
                lambda: service.users().getProfile(userId="me").execute()
            )
            self._user_email = profile.get("emailAddress")
            return self._user_email
        except Exception as e:
            logger.error(f"Failed to get user email: {e}")
            return None
    
    async def list_messages(
        self,
        query: str = "",
        max_results: Optional[int] = None,
        label_ids: Optional[List[str]] = None,
    ) -> List[EmailMessage]:
        """
        List email messages.
        
        Args:
            query: Gmail search query (e.g., "from:john@example.com")
            max_results: Maximum number of messages
            label_ids: Filter by label IDs (e.g., ["INBOX", "UNREAD"])
            
        Returns:
            List of EmailMessage objects
        """
        service = self._get_service()
        if service is None:
            return []
        
        max_results = max_results or self.max_results
        
        try:
            loop = asyncio.get_event_loop()
            
            # List message IDs
            params = {
                "userId": "me",
                "maxResults": max_results,
            }
            if query:
                params["q"] = query
            if label_ids:
                params["labelIds"] = label_ids
            
            results = await loop.run_in_executor(
                None,
                lambda: service.users().messages().list(**params).execute()
            )
            
            messages = []
            for msg_ref in results.get("messages", []):
                # Get full message
                msg = await loop.run_in_executor(
                    None,
                    lambda mid=msg_ref["id"]: service.users().messages().get(
                        userId="me",
                        id=mid,
                        format="full",
                    ).execute()
                )
                messages.append(EmailMessage.from_gmail_message(msg))
            
            return messages
            
        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
            return []
        except Exception as e:
            logger.error(f"Failed to list messages: {e}")
            return []
    
    async def get_unread_messages(self, max_results: int = 10) -> List[EmailMessage]:
        """Get unread messages from inbox."""
        return await self.list_messages(
            query="is:unread",
            max_results=max_results,
            label_ids=["INBOX"],
        )
    
    async def get_inbox(self, max_results: int = 10) -> List[EmailMessage]:
        """Get recent inbox messages."""
        return await self.list_messages(
            max_results=max_results,
            label_ids=["INBOX"],
        )
    
    async def search_messages(
        self,
        sender: Optional[str] = None,
        subject: Optional[str] = None,
        after_date: Optional[datetime] = None,
        before_date: Optional[datetime] = None,
        has_attachment: bool = False,
        max_results: int = 10,
    ) -> List[EmailMessage]:
        """
        Search for emails with various criteria.
        
        Args:
            sender: Filter by sender email or name
            subject: Filter by subject keywords
            after_date: Emails after this date
            before_date: Emails before this date
            has_attachment: Only emails with attachments
            max_results: Maximum results
            
        Returns:
            List of matching EmailMessage objects
        """
        query_parts = []
        
        if sender:
            query_parts.append(f"from:{sender}")
        if subject:
            query_parts.append(f"subject:{subject}")
        if after_date:
            query_parts.append(f"after:{after_date.strftime('%Y/%m/%d')}")
        if before_date:
            query_parts.append(f"before:{before_date.strftime('%Y/%m/%d')}")
        if has_attachment:
            query_parts.append("has:attachment")
        
        query = " ".join(query_parts)
        return await self.list_messages(query=query, max_results=max_results)
    
    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        reply_to_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Send an email.
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body (plain text)
            cc: CC recipients
            bcc: BCC recipients
            reply_to_id: Message ID to reply to
            
        Returns:
            Sent message ID or None on failure
        """
        service = self._get_service()
        if service is None:
            return None
        
        try:
            # Create message
            message = MIMEMultipart()
            message["to"] = to
            message["subject"] = subject
            
            if cc:
                message["cc"] = ", ".join(cc)
            if bcc:
                message["bcc"] = ", ".join(bcc)
            
            # Get sender email
            sender = await self.get_user_email()
            if sender:
                message["from"] = sender
            
            message.attach(MIMEText(body, "plain"))
            
            # Encode message
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
            
            body_data = {"raw": raw}
            
            # If replying, add thread ID
            if reply_to_id:
                # Get original message for thread ID
                loop = asyncio.get_event_loop()
                original = await loop.run_in_executor(
                    None,
                    lambda: service.users().messages().get(
                        userId="me",
                        id=reply_to_id,
                        format="minimal",
                    ).execute()
                )
                body_data["threadId"] = original.get("threadId")
            
            # Send
            loop = asyncio.get_event_loop()
            sent = await loop.run_in_executor(
                None,
                lambda: service.users().messages().send(
                    userId="me",
                    body=body_data,
                ).execute()
            )
            
            logger.info(f"Email sent to {to}: {subject}")
            return sent.get("id")
            
        except HttpError as e:
            logger.error(f"Failed to send email: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return None
    
    async def mark_as_read(self, message_id: str) -> bool:
        """Mark a message as read."""
        service = self._get_service()
        if service is None:
            return False
        
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: service.users().messages().modify(
                    userId="me",
                    id=message_id,
                    body={"removeLabelIds": ["UNREAD"]},
                ).execute()
            )
            return True
        except Exception as e:
            logger.error(f"Failed to mark as read: {e}")
            return False
    
    def prepare_send(
        self,
        to: str,
        subject: str,
        body: str,
    ) -> str:
        """
        Prepare an email for sending (requires confirmation).
        
        Returns a confirmation ID that can be used to confirm or cancel.
        """
        import uuid
        confirm_id = str(uuid.uuid4())[:8]
        
        self._pending_sends[confirm_id] = {
            "to": to,
            "subject": subject,
            "body": body,
            "created": datetime.now(),
        }
        
        return confirm_id
    
    async def confirm_send(self, confirm_id: str) -> Optional[str]:
        """Confirm and send a prepared email."""
        if confirm_id not in self._pending_sends:
            return None
        
        email_data = self._pending_sends.pop(confirm_id)
        return await self.send_email(
            to=email_data["to"],
            subject=email_data["subject"],
            body=email_data["body"],
        )
    
    def cancel_send(self, confirm_id: str) -> bool:
        """Cancel a prepared email."""
        if confirm_id in self._pending_sends:
            del self._pending_sends[confirm_id]
            return True
        return False


# Singleton instance
_email_service: Optional[EmailService] = None


def get_email_service(
    credentials_file: str = "config/google_credentials.json",
) -> EmailService:
    """Get or create email service singleton."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService(credentials_file=credentials_file)
    return _email_service


# =============================================================================
# Tool Functions for Agent Integration
# =============================================================================

async def read_emails(
    filter_type: str = "inbox",
    count: int = 5,
    sender: Optional[str] = None,
) -> str:
    """
    Read emails from inbox.
    
    Args:
        filter_type: "inbox", "unread", or "all"
        count: Number of emails to retrieve
        sender: Optional sender filter
        
    Returns:
        Formatted list of emails
    """
    try:
        service = get_email_service()
        if not service.is_available():
            return "Email service not available. Please configure Gmail credentials."
        
        if sender:
            messages = await service.search_messages(sender=sender, max_results=count)
            header = f"Emails from {sender}"
        elif filter_type == "unread":
            messages = await service.get_unread_messages(max_results=count)
            header = "Unread Emails"
        else:
            messages = await service.get_inbox(max_results=count)
            header = "Recent Emails"
        
        if not messages:
            return f"**{header}**\n\nNo emails found."
        
        lines = [f"**{header}** ({len(messages)} messages)\n"]
        for msg in messages:
            lines.append(msg.format_display())
            lines.append("")
        
        return "\n".join(lines)
        
    except Exception as e:
        logger.error(f"Failed to read emails: {e}")
        return f"Failed to read emails: {e}"


async def search_emails(
    query: str,
    count: int = 5,
) -> str:
    """
    Search emails by keyword, sender, or subject.
    
    Args:
        query: Search query (sender name, subject keywords, etc.)
        count: Maximum results
        
    Returns:
        Formatted search results
    """
    try:
        service = get_email_service()
        if not service.is_available():
            return "Email service not available. Please configure Gmail credentials."
        
        # Determine search type
        if "@" in query:
            messages = await service.search_messages(sender=query, max_results=count)
        else:
            messages = await service.list_messages(query=query, max_results=count)
        
        if not messages:
            return f"No emails found matching '{query}'."
        
        lines = [f"**Search Results for '{query}'** ({len(messages)} found)\n"]
        for msg in messages:
            lines.append(msg.format_display())
            lines.append("")
        
        return "\n".join(lines)
        
    except Exception as e:
        logger.error(f"Failed to search emails: {e}")
        return f"Failed to search emails: {e}"


async def send_email_with_confirmation(
    to: str,
    subject: str,
    body: str,
) -> str:
    """
    Prepare an email for sending (requires confirmation).
    
    Args:
        to: Recipient email address
        subject: Email subject
        body: Email body
        
    Returns:
        Confirmation request with preview
    """
    try:
        service = get_email_service()
        if not service.is_available():
            return "Email service not available. Please configure Gmail credentials."
        
        # Prepare the email
        confirm_id = service.prepare_send(to, subject, body)
        
        preview = f"""📧 **Email Ready to Send**

**To:** {to}
**Subject:** {subject}

**Body:**
{body[:200]}{'...' if len(body) > 200 else ''}

---
To send this email, say "confirm send {confirm_id}" or "yes, send it".
To cancel, say "cancel email" or "don't send"."""
        
        return preview
        
    except Exception as e:
        logger.error(f"Failed to prepare email: {e}")
        return f"Failed to prepare email: {e}"


async def summarize_emails(count: int = 5) -> str:
    """
    Summarize recent unread emails.
    
    Args:
        count: Number of emails to summarize
        
    Returns:
        Summary of unread emails
    """
    try:
        service = get_email_service()
        if not service.is_available():
            return "Email service not available. Please configure Gmail credentials."
        
        messages = await service.get_unread_messages(max_results=count)
        
        if not messages:
            return "📭 No unread emails!"
        
        lines = [f"📬 **You have {len(messages)} unread email(s)**\n"]
        
        # Group by sender
        by_sender: Dict[str, List[EmailMessage]] = {}
        for msg in messages:
            if msg.sender not in by_sender:
                by_sender[msg.sender] = []
            by_sender[msg.sender].append(msg)
        
        for sender, msgs in by_sender.items():
            if len(msgs) == 1:
                lines.append(f"• **{sender}**: {msgs[0].subject}")
            else:
                lines.append(f"• **{sender}**: {len(msgs)} emails")
                for msg in msgs[:3]:
                    lines.append(f"  - {msg.subject}")
        
        return "\n".join(lines)
        
    except Exception as e:
        logger.error(f"Failed to summarize emails: {e}")
        return f"Failed to summarize emails: {e}"


# Email tool definitions for agent system
EMAIL_TOOLS = [
    {
        "name": "read_emails",
        "description": "Read recent emails from inbox. Use this when the user asks to check their email or read messages.",
        "parameters": {
            "type": "object",
            "properties": {
                "filter_type": {
                    "type": "string",
                    "description": "'inbox' for all recent, 'unread' for unread only",
                    "enum": ["inbox", "unread"],
                    "default": "inbox"
                },
                "count": {
                    "type": "integer",
                    "description": "Number of emails to retrieve (default 5)",
                    "default": 5
                },
                "sender": {
                    "type": "string",
                    "description": "Filter by sender email or name (optional)"
                }
            },
            "required": []
        },
        "function": read_emails,
    },
    {
        "name": "search_emails",
        "description": "Search emails by keyword, sender, or subject. Use this when the user asks to find specific emails.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query - sender email, name, or keywords"
                },
                "count": {
                    "type": "integer",
                    "description": "Maximum results (default 5)",
                    "default": 5
                }
            },
            "required": ["query"]
        },
        "function": search_emails,
    },
    {
        "name": "send_email",
        "description": "Compose and send an email. Will ask for confirmation before sending.",
        "parameters": {
            "type": "object",
            "properties": {
                "to": {
                    "type": "string",
                    "description": "Recipient email address"
                },
                "subject": {
                    "type": "string",
                    "description": "Email subject line"
                },
                "body": {
                    "type": "string",
                    "description": "Email body content"
                }
            },
            "required": ["to", "subject", "body"]
        },
        "function": send_email_with_confirmation,
    },
    {
        "name": "summarize_emails",
        "description": "Get a quick summary of unread emails. Use this when the user asks for an email overview.",
        "parameters": {
            "type": "object",
            "properties": {
                "count": {
                    "type": "integer",
                    "description": "Number of emails to summarize (default 5)",
                    "default": 5
                }
            },
            "required": []
        },
        "function": summarize_emails,
    },
]
