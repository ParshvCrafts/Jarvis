"""
JARVIS WhatsApp Automation

Provides:
- Send WhatsApp messages via WhatsApp Web URL
- Make WhatsApp voice/video calls
- Integration with contacts system
"""

from __future__ import annotations

import re
import urllib.parse
import webbrowser
from dataclasses import dataclass
from typing import Optional, Tuple

from loguru import logger

from .contacts import ContactsManager


@dataclass
class WhatsAppResult:
    """Result of a WhatsApp operation."""
    success: bool
    message: str
    url: Optional[str] = None


class WhatsAppService:
    """
    WhatsApp automation service.
    
    Uses WhatsApp Web URLs for messaging:
    - https://wa.me/{phone}?text={message}
    - https://web.whatsapp.com/send?phone={phone}&text={message}
    """
    
    WHATSAPP_WEB_URL = "https://web.whatsapp.com/send"
    WHATSAPP_DIRECT_URL = "https://wa.me"
    
    def __init__(
        self,
        contacts_manager: ContactsManager,
        auto_send: bool = False,
        use_web_whatsapp: bool = True,
        default_country_code: str = "+1",
    ):
        """
        Initialize WhatsApp service.
        
        Args:
            contacts_manager: Contacts manager for resolving names
            auto_send: If True, attempt to auto-send (requires Playwright)
            use_web_whatsapp: If True, use web.whatsapp.com, else use wa.me
            default_country_code: Default country code for phone numbers
        """
        self.contacts = contacts_manager
        self.auto_send = auto_send
        self.use_web_whatsapp = use_web_whatsapp
        self.default_country_code = default_country_code
    
    def _normalize_phone(self, phone: str) -> str:
        """
        Normalize phone number for WhatsApp URL.
        
        WhatsApp requires numbers without + or spaces.
        
        Args:
            phone: Phone number with country code
            
        Returns:
            Normalized phone number (digits only)
        """
        # Remove all non-digit characters
        digits = re.sub(r'\D', '', phone)
        return digits
    
    def _build_message_url(self, phone: str, message: Optional[str] = None) -> str:
        """
        Build WhatsApp message URL.
        
        Args:
            phone: Phone number (with country code)
            message: Optional message to pre-fill
            
        Returns:
            WhatsApp URL
        """
        normalized_phone = self._normalize_phone(phone)
        
        if self.use_web_whatsapp:
            url = f"{self.WHATSAPP_WEB_URL}?phone={normalized_phone}"
            if message:
                encoded_message = urllib.parse.quote(message)
                url += f"&text={encoded_message}"
        else:
            url = f"{self.WHATSAPP_DIRECT_URL}/{normalized_phone}"
            if message:
                encoded_message = urllib.parse.quote(message)
                url += f"?text={encoded_message}"
        
        return url
    
    def send_message(
        self,
        contact_name: str,
        message: str,
    ) -> WhatsAppResult:
        """
        Send a WhatsApp message to a contact.
        
        Opens WhatsApp Web with the message pre-filled.
        User needs to click send (unless auto_send is enabled).
        
        Args:
            contact_name: Name or nickname of contact
            message: Message to send
            
        Returns:
            WhatsAppResult with success status
        """
        # Resolve contact to phone number
        contact, resolve_msg = self.contacts.resolve_contact(contact_name)
        
        if not contact:
            return WhatsAppResult(
                success=False,
                message=resolve_msg,
            )
        
        phone = contact.whatsapp or contact.phone
        if not phone:
            return WhatsAppResult(
                success=False,
                message=f"{contact.name} doesn't have a WhatsApp number saved",
            )
        
        # Build URL
        url = self._build_message_url(phone, message)
        
        try:
            # Open in browser
            webbrowser.open(url)
            
            # Log contact interaction for recent contacts
            self.contacts.log_contact_interaction(contact, "message")
            
            logger.info(f"Opened WhatsApp for {contact_name}: {message[:50]}...")
            
            return WhatsAppResult(
                success=True,
                message=f"Opening WhatsApp to send message to {contact_name}. Please click send.",
                url=url,
            )
            
        except Exception as e:
            logger.error(f"Failed to open WhatsApp: {e}")
            return WhatsAppResult(
                success=False,
                message=f"Failed to open WhatsApp: {e}",
            )
    
    def send_message_to_number(
        self,
        phone: str,
        message: str,
    ) -> WhatsAppResult:
        """
        Send a WhatsApp message to a phone number directly.
        
        Args:
            phone: Phone number with country code
            message: Message to send
            
        Returns:
            WhatsAppResult with success status
        """
        # Ensure country code
        if not phone.startswith('+'):
            phone = self.default_country_code + phone
        
        url = self._build_message_url(phone, message)
        
        try:
            webbrowser.open(url)
            
            logger.info(f"Opened WhatsApp for {phone}: {message[:50]}...")
            
            return WhatsAppResult(
                success=True,
                message=f"Opening WhatsApp to send message to {phone}. Please click send.",
                url=url,
            )
            
        except Exception as e:
            logger.error(f"Failed to open WhatsApp: {e}")
            return WhatsAppResult(
                success=False,
                message=f"Failed to open WhatsApp: {e}",
            )
    
    def open_chat(self, contact_name: str, log_action: str = "chat") -> WhatsAppResult:
        """
        Open WhatsApp chat with a contact (no message).
        
        Args:
            contact_name: Name or nickname of contact
            log_action: Action type for logging (chat, call, video_call)
            
        Returns:
            WhatsAppResult with success status
        """
        contact, resolve_msg = self.contacts.resolve_contact(contact_name)
        
        if not contact:
            return WhatsAppResult(
                success=False,
                message=resolve_msg,
            )
        
        phone = contact.whatsapp or contact.phone
        if not phone:
            return WhatsAppResult(
                success=False,
                message=f"{contact.name} doesn't have a WhatsApp number saved",
            )
        
        url = self._build_message_url(phone)
        
        try:
            webbrowser.open(url)
            
            # Log contact interaction
            self.contacts.log_contact_interaction(contact, log_action)
            
            logger.info(f"Opened WhatsApp chat with {contact_name}")
            
            return WhatsAppResult(
                success=True,
                message=f"Opening WhatsApp chat with {contact_name}",
                url=url,
            )
            
        except Exception as e:
            logger.error(f"Failed to open WhatsApp: {e}")
            return WhatsAppResult(
                success=False,
                message=f"Failed to open WhatsApp: {e}",
            )
    
    def make_call(
        self,
        contact_name: str,
        video: bool = False,
    ) -> WhatsAppResult:
        """
        Initiate a WhatsApp call.
        
        Note: WhatsApp Web doesn't support direct call initiation via URL.
        This opens the chat and instructs user to click call button.
        
        Args:
            contact_name: Name or nickname of contact
            video: If True, suggest video call
            
        Returns:
            WhatsAppResult with instructions
        """
        call_type = "video_call" if video else "call"
        result = self.open_chat(contact_name, log_action=call_type)
        
        if not result.success:
            return result
        
        call_type_display = "video" if video else "voice"
        
        return WhatsAppResult(
            success=True,
            message=f"Opening WhatsApp chat with {contact_name}. Click the {call_type_display} call button to start the call.",
            url=result.url,
        )


class WhatsAppCommandParser:
    """
    Parse natural language commands for WhatsApp actions.
    """
    
    # Patterns for extracting contact and message
    MESSAGE_PATTERNS = [
        # "Send WhatsApp message to Papa saying I'll be late"
        r"(?:send\s+)?whatsapp\s+(?:message\s+)?to\s+(.+?)\s+(?:saying|that|message)\s+(.+)",
        # "WhatsApp Mom that I reached safely"
        r"whatsapp\s+(.+?)\s+(?:saying|that)\s+(.+)",
        # "Message John on WhatsApp saying hello"
        r"message\s+(.+?)\s+on\s+whatsapp\s+(?:saying|that)\s+(.+)",
        # "Send message to Papa on WhatsApp I'll be late"
        r"send\s+(?:a\s+)?message\s+to\s+(.+?)\s+on\s+whatsapp\s+(.+)",
        # "Text Papa on WhatsApp hello"
        r"text\s+(.+?)\s+on\s+whatsapp\s+(.+)",
    ]
    
    CALL_PATTERNS = [
        # "Call Papa on WhatsApp"
        r"(?:make\s+a\s+)?(?:voice\s+)?call\s+(?:to\s+)?(.+?)\s+on\s+whatsapp",
        # "WhatsApp call Papa"
        r"whatsapp\s+(?:voice\s+)?call\s+(?:to\s+)?(.+)",
        # "Call Papa via WhatsApp"
        r"call\s+(.+?)\s+(?:via|through|using)\s+whatsapp",
    ]
    
    VIDEO_CALL_PATTERNS = [
        # "Video call Papa on WhatsApp"
        r"video\s+call\s+(?:to\s+)?(.+?)\s+on\s+whatsapp",
        # "WhatsApp video call Papa"
        r"whatsapp\s+video\s+call\s+(?:to\s+)?(.+)",
        # "Video call Papa via WhatsApp"
        r"video\s+call\s+(.+?)\s+(?:via|through|using)\s+whatsapp",
    ]
    
    @classmethod
    def parse_message_command(cls, text: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Parse a WhatsApp message command.
        
        Args:
            text: Command text
            
        Returns:
            Tuple of (contact_name, message) or (None, None) if not matched
        """
        text_lower = text.lower()
        
        for pattern in cls.MESSAGE_PATTERNS:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                contact = match.group(1).strip()
                message = match.group(2).strip()
                
                # Get original case message from input
                # Find where message starts in original text
                msg_start = text_lower.find(message)
                if msg_start >= 0:
                    message = text[msg_start:msg_start + len(message)]
                
                return contact, message
        
        return None, None
    
    @classmethod
    def parse_call_command(cls, text: str) -> Tuple[Optional[str], bool]:
        """
        Parse a WhatsApp call command.
        
        Args:
            text: Command text
            
        Returns:
            Tuple of (contact_name, is_video) or (None, False) if not matched
        """
        text_lower = text.lower()
        
        # Check video call patterns first
        for pattern in cls.VIDEO_CALL_PATTERNS:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                contact = match.group(1).strip()
                return contact, True
        
        # Then check voice call patterns
        for pattern in cls.CALL_PATTERNS:
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if match:
                contact = match.group(1).strip()
                return contact, False
        
        return None, False
    
    @classmethod
    def is_whatsapp_command(cls, text: str) -> bool:
        """Check if text is a WhatsApp-related command."""
        text_lower = text.lower()
        return "whatsapp" in text_lower or "wa " in text_lower


class CommunicationRouter:
    """
    Routes communication commands to appropriate services.
    """
    
    def __init__(
        self,
        contacts_manager: ContactsManager,
        whatsapp_service: WhatsAppService,
        confirm_before_send: bool = True,
    ):
        """
        Initialize communication router.
        
        Args:
            contacts_manager: Contacts manager
            whatsapp_service: WhatsApp service
            confirm_before_send: If True, require confirmation before sending
        """
        self.contacts = contacts_manager
        self.whatsapp = whatsapp_service
        self.confirm_before_send = confirm_before_send
        
        # Pending actions awaiting confirmation
        self._pending_action: Optional[dict] = None
    
    def handle_command(self, text: str) -> Tuple[str, bool]:
        """
        Handle a communication command.
        
        Args:
            text: Command text
            
        Returns:
            Tuple of (response_message, needs_confirmation)
        """
        text_lower = text.lower()
        
        # Check for confirmation of pending action
        if self._pending_action:
            if text_lower in ["yes", "yeah", "yep", "sure", "send it", "go ahead", "confirm"]:
                return self._execute_pending_action()
            elif text_lower in ["no", "nope", "cancel", "nevermind", "don't"]:
                self._pending_action = None
                return "Cancelled.", False
        
        # Parse WhatsApp message command
        contact, message = WhatsAppCommandParser.parse_message_command(text)
        if contact and message:
            if self.confirm_before_send:
                self._pending_action = {
                    "type": "whatsapp_message",
                    "contact": contact,
                    "message": message,
                }
                return f"I'll send '{message}' to {contact} on WhatsApp. Should I send it?", True
            else:
                result = self.whatsapp.send_message(contact, message)
                return result.message, False
        
        # Parse WhatsApp call command
        contact, is_video = WhatsAppCommandParser.parse_call_command(text)
        if contact:
            result = self.whatsapp.make_call(contact, video=is_video)
            return result.message, False
        
        # Contact management commands
        if "add contact" in text_lower:
            return self._handle_add_contact(text), False
        
        if "delete contact" in text_lower or "remove contact" in text_lower:
            return self._handle_delete_contact(text), False
        
        if "list contacts" in text_lower or "my contacts" in text_lower:
            return self._handle_list_contacts(), False
        
        # Contact count/status
        if "how many contacts" in text_lower or "contact count" in text_lower:
            return self._handle_contact_count(), False
        
        # Recent contacts
        if "recent contact" in text_lower or "recently contacted" in text_lower:
            return self._handle_recent_contacts(), False
        
        # Favorite contacts
        if "favorite contact" in text_lower or "favourite contact" in text_lower:
            return self._handle_favorite_contacts(), False
        
        if "add" in text_lower and "favorite" in text_lower:
            return self._handle_add_favorite(text), False
        
        if "remove" in text_lower and "favorite" in text_lower:
            return self._handle_remove_favorite(text), False
        
        if "what's" in text_lower and "number" in text_lower:
            return self._handle_get_number(text), False
        
        return "", False
    
    def _execute_pending_action(self) -> Tuple[str, bool]:
        """Execute the pending action."""
        if not self._pending_action:
            return "No pending action.", False
        
        action = self._pending_action
        self._pending_action = None
        
        if action["type"] == "whatsapp_message":
            result = self.whatsapp.send_message(action["contact"], action["message"])
            return result.message, False
        
        return "Unknown action.", False
    
    def _handle_add_contact(self, text: str) -> str:
        """Handle add contact command."""
        # Parse: "add contact John phone 1234567890"
        # or: "add contact John 1234567890"
        
        patterns = [
            r"add\s+contact\s+(.+?)\s+(?:phone|number)\s+(\+?[\d\s-]+)",
            r"add\s+contact\s+(.+?)\s+(\+?[\d\s-]+)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                phone = match.group(2).strip()
                
                success, msg = self.contacts.add_contact(name=name, phone=phone)
                return msg
        
        return "Please specify: add contact [name] phone [number]"
    
    def _handle_delete_contact(self, text: str) -> str:
        """Handle delete contact command."""
        match = re.search(r"(?:delete|remove)\s+contact\s+(.+)", text, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            success, msg = self.contacts.delete_contact(name)
            return msg
        
        return "Please specify: delete contact [name]"
    
    def _handle_list_contacts(self) -> str:
        """Handle list contacts command."""
        contacts = self.contacts.list_contacts()
        
        if not contacts:
            return "You don't have any contacts saved yet."
        
        count = len(contacts)
        names = [c.name for c in contacts[:10]]
        
        if count <= 10:
            return f"You have {count} contacts: {', '.join(names)}"
        else:
            return f"You have {count} contacts. First 10: {', '.join(names)}"
    
    def _handle_get_number(self, text: str) -> str:
        """Handle get phone number command."""
        # "What's Papa's number?"
        match = re.search(r"what(?:'s|s| is)\s+(.+?)(?:'s|s)?\s+(?:phone\s+)?number", text, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            phone, msg = self.contacts.get_phone_number(name)
            return msg
        
        return "Please specify: what's [name]'s number?"
    
    def _handle_contact_count(self) -> str:
        """Handle contact count/status command."""
        total = self.contacts.get_contact_count()
        
        if total == 0:
            return "You don't have any contacts yet. Say 'Add contact [name] phone [number]' to add one."
        
        # Get category breakdown
        all_contacts = self.contacts.list_contacts()
        categories = {}
        for c in all_contacts:
            cat = c.category or "other"
            categories[cat] = categories.get(cat, 0) + 1
        
        # Get favorites count
        favorites = self.contacts.get_favorites()
        fav_count = len(favorites)
        
        # Build response
        cat_parts = [f"{count} {cat}" for cat, count in categories.items()]
        response = f"You have {total} contacts"
        
        if cat_parts:
            response += f": {', '.join(cat_parts)}"
        
        if fav_count > 0:
            response += f". {fav_count} marked as favorites."
        else:
            response += "."
        
        return response
    
    def _handle_recent_contacts(self) -> str:
        """Handle recent contacts command."""
        recent = self.contacts.get_recent_contacts(limit=5)
        
        if not recent:
            return "You haven't contacted anyone recently."
        
        names = [c.name for c in recent]
        return f"Your recent contacts are: {', '.join(names)}. Who would you like to contact?"
    
    def _handle_favorite_contacts(self) -> str:
        """Handle favorite contacts command."""
        favorites = self.contacts.get_favorites(limit=10)
        
        if not favorites:
            return "You don't have any favorite contacts yet. Say 'add [name] to favorites' to add one."
        
        names = [c.name for c in favorites]
        return f"Your favorite contacts are: {', '.join(names)}"
    
    def _handle_add_favorite(self, text: str) -> str:
        """Handle add to favorites command."""
        # "Add Papa to favorites"
        match = re.search(r"add\s+(.+?)\s+to\s+favou?rites?", text, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            success, msg = self.contacts.set_favorite(name, True)
            return msg
        
        return "Please specify: add [name] to favorites"
    
    def _handle_remove_favorite(self, text: str) -> str:
        """Handle remove from favorites command."""
        # "Remove Papa from favorites"
        match = re.search(r"remove\s+(.+?)\s+from\s+favou?rites?", text, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            success, msg = self.contacts.set_favorite(name, False)
            return msg
        
        return "Please specify: remove [name] from favorites"
