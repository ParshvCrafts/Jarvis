"""
Google Docs Integration for JARVIS Research Module.

Handles:
- Document creation
- Content formatting
- Text insertion with styles
- Document sharing
"""

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

# Google API imports
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False
    logger.warning("Google API libraries not installed. Run: pip install google-api-python-client google-auth-oauthlib")


class HeadingLevel(Enum):
    """Document heading levels."""
    TITLE = "TITLE"
    HEADING_1 = "HEADING_1"
    HEADING_2 = "HEADING_2"
    HEADING_3 = "HEADING_3"
    NORMAL = "NORMAL_TEXT"


@dataclass
class DocumentStyle:
    """Document formatting settings."""
    font_family: str = "Times New Roman"
    font_size: int = 12
    line_spacing: float = 2.0  # Double-spaced
    margin_top: float = 1.0  # inches
    margin_bottom: float = 1.0
    margin_left: float = 1.0
    margin_right: float = 1.0
    first_line_indent: float = 0.5  # inches for paragraphs


@dataclass
class InsertRequest:
    """Request to insert content."""
    text: str
    heading_level: HeadingLevel = HeadingLevel.NORMAL
    bold: bool = False
    italic: bool = False
    start_index: Optional[int] = None


class GoogleDocsClient:
    """
    Google Docs API client for creating and formatting documents.
    
    Uses OAuth2 for authentication with existing Google credentials.
    """
    
    SCOPES = [
        "https://www.googleapis.com/auth/documents",
        "https://www.googleapis.com/auth/drive.file",
    ]
    
    def __init__(
        self,
        credentials_path: str = "config/google_credentials.json",
        token_path: str = "config/google_token.json",
    ):
        """
        Initialize Google Docs client.
        
        Args:
            credentials_path: Path to OAuth credentials JSON
            token_path: Path to store/load token
        """
        self.credentials_path = Path(credentials_path)
        self.token_path = Path(token_path)
        self._creds: Optional[Credentials] = None
        self._docs_service = None
        self._drive_service = None
        self._current_doc_id: Optional[str] = None
        self._current_index: int = 1  # Track insertion point
    
    @property
    def is_available(self) -> bool:
        """Check if Google API is available."""
        return GOOGLE_API_AVAILABLE
    
    def authenticate(self) -> bool:
        """
        Authenticate with Google APIs.
        
        Returns:
            True if authentication successful
        """
        if not GOOGLE_API_AVAILABLE:
            logger.error("Google API libraries not installed")
            return False
        
        try:
            # Check for existing token
            if self.token_path.exists():
                self._creds = Credentials.from_authorized_user_file(
                    str(self.token_path), self.SCOPES
                )
            
            # Refresh or get new credentials
            if not self._creds or not self._creds.valid:
                if self._creds and self._creds.expired and self._creds.refresh_token:
                    self._creds.refresh(Request())
                else:
                    if not self.credentials_path.exists():
                        logger.error(f"Credentials file not found: {self.credentials_path}")
                        logger.info("Download OAuth credentials from Google Cloud Console")
                        return False
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(self.credentials_path), self.SCOPES
                    )
                    self._creds = flow.run_local_server(port=0)
                
                # Save token for future use
                self.token_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.token_path, "w") as token:
                    token.write(self._creds.to_json())
            
            # Build services
            self._docs_service = build("docs", "v1", credentials=self._creds)
            self._drive_service = build("drive", "v3", credentials=self._creds)
            
            logger.info("Google Docs authentication successful")
            return True
            
        except Exception as e:
            logger.error(f"Google authentication failed: {e}")
            return False
    
    def create_document(self, title: str) -> Optional[str]:
        """
        Create a new Google Doc.
        
        Args:
            title: Document title
            
        Returns:
            Document ID or None if failed
        """
        if not self._docs_service:
            if not self.authenticate():
                return None
        
        try:
            doc = self._docs_service.documents().create(body={"title": title}).execute()
            self._current_doc_id = doc.get("documentId")
            self._current_index = 1
            
            logger.info(f"Created document: {title} (ID: {self._current_doc_id})")
            return self._current_doc_id
            
        except HttpError as e:
            logger.error(f"Failed to create document: {e}")
            return None
    
    def get_document_url(self, doc_id: Optional[str] = None) -> str:
        """Get the URL for a document."""
        doc_id = doc_id or self._current_doc_id
        if doc_id:
            return f"https://docs.google.com/document/d/{doc_id}/edit"
        return ""
    
    def insert_text(
        self,
        text: str,
        heading_level: HeadingLevel = HeadingLevel.NORMAL,
        bold: bool = False,
        italic: bool = False,
    ) -> bool:
        """
        Insert text at current position.
        
        Args:
            text: Text to insert
            heading_level: Heading style to apply
            bold: Make text bold
            italic: Make text italic
            
        Returns:
            True if successful
        """
        if not self._current_doc_id:
            logger.error("No document open")
            return False
        
        try:
            requests = []
            
            # Insert text
            requests.append({
                "insertText": {
                    "location": {"index": self._current_index},
                    "text": text,
                }
            })
            
            # Calculate range for formatting
            start_index = self._current_index
            end_index = start_index + len(text)
            
            # Apply paragraph style (heading)
            if heading_level != HeadingLevel.NORMAL:
                requests.append({
                    "updateParagraphStyle": {
                        "range": {
                            "startIndex": start_index,
                            "endIndex": end_index,
                        },
                        "paragraphStyle": {
                            "namedStyleType": heading_level.value,
                        },
                        "fields": "namedStyleType",
                    }
                })
            
            # Apply text formatting
            text_style = {}
            if bold:
                text_style["bold"] = True
            if italic:
                text_style["italic"] = True
            
            if text_style:
                requests.append({
                    "updateTextStyle": {
                        "range": {
                            "startIndex": start_index,
                            "endIndex": end_index,
                        },
                        "textStyle": text_style,
                        "fields": ",".join(text_style.keys()),
                    }
                })
            
            # Execute requests
            self._docs_service.documents().batchUpdate(
                documentId=self._current_doc_id,
                body={"requests": requests}
            ).execute()
            
            # Update index
            self._current_index = end_index
            
            return True
            
        except HttpError as e:
            logger.error(f"Failed to insert text: {e}")
            return False
    
    def insert_paragraph(
        self,
        text: str,
        heading_level: HeadingLevel = HeadingLevel.NORMAL,
    ) -> bool:
        """
        Insert a paragraph with newline.
        
        Args:
            text: Paragraph text
            heading_level: Heading style
            
        Returns:
            True if successful
        """
        # Add newline if not present
        if not text.endswith("\n"):
            text += "\n"
        
        return self.insert_text(text, heading_level)
    
    def insert_heading(self, text: str, level: int = 1) -> bool:
        """
        Insert a heading.
        
        Args:
            text: Heading text
            level: Heading level (1-3)
            
        Returns:
            True if successful
        """
        heading_map = {
            1: HeadingLevel.HEADING_1,
            2: HeadingLevel.HEADING_2,
            3: HeadingLevel.HEADING_3,
        }
        heading_level = heading_map.get(level, HeadingLevel.HEADING_1)
        
        return self.insert_paragraph(text, heading_level)
    
    def insert_title(self, text: str) -> bool:
        """Insert document title."""
        return self.insert_paragraph(text, HeadingLevel.TITLE)
    
    def insert_page_break(self) -> bool:
        """Insert a page break."""
        if not self._current_doc_id:
            return False
        
        try:
            requests = [{
                "insertPageBreak": {
                    "location": {"index": self._current_index},
                }
            }]
            
            self._docs_service.documents().batchUpdate(
                documentId=self._current_doc_id,
                body={"requests": requests}
            ).execute()
            
            self._current_index += 1
            return True
            
        except HttpError as e:
            logger.error(f"Failed to insert page break: {e}")
            return False
    
    def apply_document_style(self, style: DocumentStyle) -> bool:
        """
        Apply document-wide formatting.
        
        Args:
            style: Document style settings
            
        Returns:
            True if successful
        """
        if not self._current_doc_id:
            return False
        
        try:
            # Convert inches to points (72 points per inch)
            def inches_to_points(inches: float) -> int:
                return int(inches * 72)
            
            requests = [{
                "updateDocumentStyle": {
                    "documentStyle": {
                        "marginTop": {"magnitude": inches_to_points(style.margin_top), "unit": "PT"},
                        "marginBottom": {"magnitude": inches_to_points(style.margin_bottom), "unit": "PT"},
                        "marginLeft": {"magnitude": inches_to_points(style.margin_left), "unit": "PT"},
                        "marginRight": {"magnitude": inches_to_points(style.margin_right), "unit": "PT"},
                    },
                    "fields": "marginTop,marginBottom,marginLeft,marginRight",
                }
            }]
            
            self._docs_service.documents().batchUpdate(
                documentId=self._current_doc_id,
                body={"requests": requests}
            ).execute()
            
            return True
            
        except HttpError as e:
            logger.error(f"Failed to apply document style: {e}")
            return False
    
    def set_sharing(
        self,
        doc_id: Optional[str] = None,
        anyone_can_view: bool = True,
    ) -> Optional[str]:
        """
        Set document sharing permissions.
        
        Args:
            doc_id: Document ID (uses current if not specified)
            anyone_can_view: Allow anyone with link to view
            
        Returns:
            Shareable link or None
        """
        doc_id = doc_id or self._current_doc_id
        if not doc_id or not self._drive_service:
            return None
        
        try:
            if anyone_can_view:
                # Create permission for anyone with link
                self._drive_service.permissions().create(
                    fileId=doc_id,
                    body={
                        "type": "anyone",
                        "role": "reader",
                    },
                    fields="id",
                ).execute()
            
            return self.get_document_url(doc_id)
            
        except HttpError as e:
            logger.error(f"Failed to set sharing: {e}")
            return self.get_document_url(doc_id)
    
    def write_research_paper(
        self,
        title: str,
        sections: List[Tuple[str, str, int]],  # (heading, content, level)
        style: Optional[DocumentStyle] = None,
    ) -> Optional[str]:
        """
        Write a complete research paper.
        
        Args:
            title: Paper title
            sections: List of (heading, content, level) tuples
            style: Document style (default: academic style)
            
        Returns:
            Document URL or None
        """
        # Create document
        doc_id = self.create_document(title)
        if not doc_id:
            return None
        
        # Apply style
        if style:
            self.apply_document_style(style)
        else:
            self.apply_document_style(DocumentStyle())
        
        # Insert title
        self.insert_title(title)
        self.insert_paragraph("")  # Blank line after title
        
        # Insert sections
        for heading, content, level in sections:
            if heading:
                self.insert_heading(heading, level)
            if content:
                # Split content into paragraphs
                paragraphs = content.split("\n\n")
                for para in paragraphs:
                    if para.strip():
                        self.insert_paragraph(para.strip())
                        self.insert_paragraph("")  # Blank line between paragraphs
        
        # Get shareable link
        url = self.set_sharing(doc_id, anyone_can_view=True)
        
        logger.info(f"Research paper created: {url}")
        return url
    
    def append_section(
        self,
        heading: str,
        content: str,
        level: int = 2,
    ) -> bool:
        """
        Append a section to current document.
        
        Args:
            heading: Section heading
            content: Section content
            level: Heading level
            
        Returns:
            True if successful
        """
        if not self._current_doc_id:
            return False
        
        # Insert heading
        if heading:
            self.insert_heading(heading, level)
        
        # Insert content paragraphs
        paragraphs = content.split("\n\n")
        for para in paragraphs:
            if para.strip():
                self.insert_paragraph(para.strip())
                self.insert_paragraph("")
        
        return True
    
    def close(self):
        """Close the client (cleanup)."""
        self._current_doc_id = None
        self._current_index = 1


class MockGoogleDocsClient:
    """
    Mock Google Docs client for testing without API access.
    
    Generates markdown output instead of actual Google Docs.
    """
    
    def __init__(self):
        self._content: List[str] = []
        self._title: str = ""
        self._doc_id: str = ""
    
    @property
    def is_available(self) -> bool:
        return True
    
    def authenticate(self) -> bool:
        return True
    
    def create_document(self, title: str) -> str:
        self._title = title
        self._doc_id = f"mock_{hash(title)}"
        self._content = [f"# {title}\n"]
        return self._doc_id
    
    def get_document_url(self, doc_id: Optional[str] = None) -> str:
        return f"[Mock Document: {self._title}]"
    
    def insert_text(self, text: str, heading_level=HeadingLevel.NORMAL, bold=False, italic=False) -> bool:
        if bold:
            text = f"**{text}**"
        if italic:
            text = f"*{text}*"
        self._content.append(text)
        return True
    
    def insert_paragraph(self, text: str, heading_level=HeadingLevel.NORMAL) -> bool:
        prefix = ""
        if heading_level == HeadingLevel.HEADING_1:
            prefix = "## "
        elif heading_level == HeadingLevel.HEADING_2:
            prefix = "### "
        elif heading_level == HeadingLevel.HEADING_3:
            prefix = "#### "
        
        self._content.append(f"{prefix}{text}\n")
        return True
    
    def insert_heading(self, text: str, level: int = 1) -> bool:
        prefix = "#" * (level + 1) + " "
        self._content.append(f"{prefix}{text}\n")
        return True
    
    def insert_title(self, text: str) -> bool:
        self._content.append(f"# {text}\n")
        return True
    
    def insert_page_break(self) -> bool:
        self._content.append("\n---\n")
        return True
    
    def apply_document_style(self, style: DocumentStyle) -> bool:
        return True
    
    def set_sharing(self, doc_id=None, anyone_can_view=True) -> str:
        return self.get_document_url()
    
    def write_research_paper(self, title: str, sections: List[Tuple[str, str, int]], style=None) -> str:
        self.create_document(title)
        for heading, content, level in sections:
            if heading:
                self.insert_heading(heading, level)
            if content:
                self.insert_paragraph(content)
        return self.get_document_url()
    
    def append_section(self, heading: str, content: str, level: int = 2) -> bool:
        if heading:
            self.insert_heading(heading, level)
        self.insert_paragraph(content)
        return True
    
    def get_markdown(self) -> str:
        """Get document as markdown."""
        return "\n".join(self._content)
    
    def close(self):
        pass
