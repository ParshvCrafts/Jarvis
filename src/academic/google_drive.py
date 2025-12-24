"""
Google Drive Integration for JARVIS.

Provides quick access to academic documents:
- Search documents by name
- Open document URLs
- List recent documents
- Access shared course materials
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import webbrowser

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
    logger.debug("Google API libraries not installed. Install with: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")


# OAuth scopes for Drive API (read-only for safety)
SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/drive.metadata.readonly',
]


@dataclass
class DriveFile:
    """Represents a Google Drive file."""
    id: str
    name: str
    mime_type: str
    web_view_link: Optional[str] = None
    modified_time: Optional[datetime] = None
    size: Optional[int] = None
    owners: List[str] = field(default_factory=list)
    shared: bool = False
    starred: bool = False
    
    @property
    def is_folder(self) -> bool:
        return self.mime_type == "application/vnd.google-apps.folder"
    
    @property
    def is_document(self) -> bool:
        return self.mime_type == "application/vnd.google-apps.document"
    
    @property
    def is_spreadsheet(self) -> bool:
        return self.mime_type == "application/vnd.google-apps.spreadsheet"
    
    @property
    def is_presentation(self) -> bool:
        return self.mime_type == "application/vnd.google-apps.presentation"
    
    @property
    def file_type(self) -> str:
        """Get human-readable file type."""
        type_map = {
            "application/vnd.google-apps.document": "Google Doc",
            "application/vnd.google-apps.spreadsheet": "Google Sheet",
            "application/vnd.google-apps.presentation": "Google Slides",
            "application/vnd.google-apps.folder": "Folder",
            "application/pdf": "PDF",
            "text/plain": "Text",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "Word Doc",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "Excel",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation": "PowerPoint",
        }
        return type_map.get(self.mime_type, "File")
    
    def __str__(self) -> str:
        return f"{self.name} ({self.file_type})"


class GoogleDriveClient:
    """
    Google Drive API client for academic document access.
    
    Usage:
        client = GoogleDriveClient()
        files = await client.search("Data 8 notes")
        client.open_file(files[0])
    """
    
    def __init__(
        self,
        credentials_path: Optional[str] = None,
        token_path: Optional[str] = None,
    ):
        """
        Initialize Google Drive client.
        
        Args:
            credentials_path: Path to OAuth credentials JSON
            token_path: Path to store/load token
        """
        self.credentials_path = Path(credentials_path or "config/google_credentials.json")
        self.token_path = Path(token_path or "data/drive_token.pickle")
        
        self._service = None
        self._credentials = None
    
    @property
    def is_available(self) -> bool:
        """Check if Google API libraries are available."""
        return GOOGLE_API_AVAILABLE
    
    @property
    def is_configured(self) -> bool:
        """Check if credentials are configured."""
        return self.credentials_path.exists()
    
    def _get_credentials(self) -> Optional[Credentials]:
        """Get or refresh OAuth credentials."""
        if not GOOGLE_API_AVAILABLE:
            logger.warning("Google API libraries not installed")
            return None
        
        if not self.credentials_path.exists():
            logger.warning(f"Credentials file not found: {self.credentials_path}")
            return None
        
        creds = None
        
        # Load existing token
        if self.token_path.exists():
            import pickle
            with open(self.token_path, 'rb') as token:
                creds = pickle.load(token)
        
        # Refresh or get new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    logger.error(f"Failed to refresh credentials: {e}")
                    creds = None
            
            if not creds:
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(self.credentials_path), SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                except Exception as e:
                    logger.error(f"Failed to get credentials: {e}")
                    return None
            
            # Save token
            self.token_path.parent.mkdir(parents=True, exist_ok=True)
            import pickle
            with open(self.token_path, 'wb') as token:
                pickle.dump(creds, token)
        
        return creds
    
    def _get_service(self):
        """Get or create Drive API service."""
        if self._service is None:
            creds = self._get_credentials()
            if creds:
                self._service = build('drive', 'v3', credentials=creds)
        return self._service
    
    async def search(
        self,
        query: str,
        max_results: int = 10,
        file_type: Optional[str] = None,
    ) -> List[DriveFile]:
        """
        Search for files by name.
        
        Args:
            query: Search query (file name)
            max_results: Maximum results to return
            file_type: Optional filter (document, spreadsheet, presentation)
            
        Returns:
            List of matching files
        """
        service = self._get_service()
        if not service:
            return []
        
        try:
            # Build search query
            search_query = f"name contains '{query}' and trashed = false"
            
            if file_type:
                type_map = {
                    "document": "application/vnd.google-apps.document",
                    "doc": "application/vnd.google-apps.document",
                    "spreadsheet": "application/vnd.google-apps.spreadsheet",
                    "sheet": "application/vnd.google-apps.spreadsheet",
                    "presentation": "application/vnd.google-apps.presentation",
                    "slides": "application/vnd.google-apps.presentation",
                }
                if file_type.lower() in type_map:
                    search_query += f" and mimeType = '{type_map[file_type.lower()]}'"
            
            results = service.files().list(
                q=search_query,
                pageSize=max_results,
                fields="files(id, name, mimeType, webViewLink, modifiedTime, size, owners, shared, starred)",
                orderBy="modifiedTime desc",
            ).execute()
            
            files = []
            for item in results.get('files', []):
                files.append(self._parse_file(item))
            
            return files
            
        except HttpError as e:
            logger.error(f"Drive API error: {e}")
            return []
        except Exception as e:
            logger.error(f"Drive search error: {e}")
            return []
    
    async def get_recent(self, max_results: int = 10) -> List[DriveFile]:
        """
        Get recently modified files.
        
        Args:
            max_results: Maximum results to return
            
        Returns:
            List of recent files
        """
        service = self._get_service()
        if not service:
            return []
        
        try:
            results = service.files().list(
                q="trashed = false",
                pageSize=max_results,
                fields="files(id, name, mimeType, webViewLink, modifiedTime, size, owners, shared, starred)",
                orderBy="modifiedTime desc",
            ).execute()
            
            files = []
            for item in results.get('files', []):
                files.append(self._parse_file(item))
            
            return files
            
        except HttpError as e:
            logger.error(f"Drive API error: {e}")
            return []
        except Exception as e:
            logger.error(f"Drive recent files error: {e}")
            return []
    
    async def get_starred(self) -> List[DriveFile]:
        """Get starred files."""
        service = self._get_service()
        if not service:
            return []
        
        try:
            results = service.files().list(
                q="starred = true and trashed = false",
                pageSize=20,
                fields="files(id, name, mimeType, webViewLink, modifiedTime, size, owners, shared, starred)",
                orderBy="modifiedTime desc",
            ).execute()
            
            files = []
            for item in results.get('files', []):
                files.append(self._parse_file(item))
            
            return files
            
        except Exception as e:
            logger.error(f"Drive starred files error: {e}")
            return []
    
    def open_file(self, file: DriveFile) -> bool:
        """
        Open a file in the browser.
        
        Args:
            file: DriveFile to open
            
        Returns:
            True if opened successfully
        """
        if file.web_view_link:
            webbrowser.open(file.web_view_link)
            return True
        return False
    
    def open_by_id(self, file_id: str) -> bool:
        """Open a file by its ID."""
        url = f"https://drive.google.com/file/d/{file_id}/view"
        webbrowser.open(url)
        return True
    
    def _parse_file(self, item: Dict[str, Any]) -> DriveFile:
        """Parse API response into DriveFile."""
        modified_time = None
        if 'modifiedTime' in item:
            try:
                modified_time = datetime.fromisoformat(item['modifiedTime'].replace('Z', '+00:00'))
            except Exception:
                pass
        
        owners = []
        if 'owners' in item:
            owners = [o.get('displayName', o.get('emailAddress', '')) for o in item['owners']]
        
        return DriveFile(
            id=item['id'],
            name=item['name'],
            mime_type=item.get('mimeType', ''),
            web_view_link=item.get('webViewLink'),
            modified_time=modified_time,
            size=int(item['size']) if 'size' in item else None,
            owners=owners,
            shared=item.get('shared', False),
            starred=item.get('starred', False),
        )
    
    def format_files(self, files: List[DriveFile], max_display: int = 5) -> str:
        """Format files for display."""
        if not files:
            return "No files found."
        
        lines = []
        for f in files[:max_display]:
            lines.append(f"• {f.name} ({f.file_type})")
        
        if len(files) > max_display:
            lines.append(f"  ... and {len(files) - max_display} more")
        
        return "\n".join(lines)
