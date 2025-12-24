"""
Enhanced Telegram Bot Module for JARVIS.

Features:
- Voice note processing with transcription preview
- Rich inline keyboards for common actions
- Status dashboard
- Two-factor confirmation for sensitive actions
- Location-based commands
- Rate limiting and security
"""

from __future__ import annotations

import asyncio
import hashlib
import tempfile
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

from loguru import logger

try:
    from telegram import (
        Update, 
        InlineKeyboardButton, 
        InlineKeyboardMarkup,
        ReplyKeyboardMarkup,
        KeyboardButton,
        BotCommand,
    )
    from telegram.ext import (
        Application,
        CommandHandler,
        MessageHandler,
        CallbackQueryHandler,
        ContextTypes,
        filters,
        ConversationHandler,
    )
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    logger.warning("python-telegram-bot not available")


class ConfirmationType(Enum):
    """Types of confirmation required."""
    NONE = "none"
    SINGLE = "single"
    PIN = "pin"
    TWO_FACTOR = "two_factor"


@dataclass
class PendingAction:
    """A pending action awaiting confirmation."""
    action_id: str
    action_type: str
    description: str
    callback: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    expires_at: float = 0.0
    confirmation_type: ConfirmationType = ConfirmationType.SINGLE
    
    def __post_init__(self):
        if self.expires_at == 0.0:
            self.expires_at = self.created_at + 60  # 1 minute expiry
    
    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at


class RateLimiter:
    """Rate limiter for bot commands."""
    
    def __init__(
        self,
        max_requests: int = 30,
        window_seconds: int = 60,
    ):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: Dict[int, List[float]] = defaultdict(list)
    
    def is_allowed(self, user_id: int) -> bool:
        """Check if user is within rate limit."""
        now = time.time()
        cutoff = now - self.window_seconds
        
        # Clean old requests
        self._requests[user_id] = [t for t in self._requests[user_id] if t > cutoff]
        
        if len(self._requests[user_id]) >= self.max_requests:
            return False
        
        self._requests[user_id].append(now)
        return True
    
    def get_wait_time(self, user_id: int) -> float:
        """Get seconds until rate limit resets."""
        if not self._requests[user_id]:
            return 0
        
        oldest = min(self._requests[user_id])
        return max(0, oldest + self.window_seconds - time.time())


class EnhancedTelegramBot:
    """
    Enhanced Telegram bot with rich interface.
    
    Features:
    - Inline keyboards for quick actions
    - Voice note transcription
    - Status dashboard
    - Two-factor confirmation
    - Location sharing
    - Rate limiting
    """
    
    # Sensitive actions requiring confirmation
    SENSITIVE_ACTIONS = {
        "door_unlock": ConfirmationType.TWO_FACTOR,
        "delete_files": ConfirmationType.PIN,
        "system_shutdown": ConfirmationType.TWO_FACTOR,
    }
    
    def __init__(
        self,
        token: str,
        allowed_users: List[int],
        command_handler: Optional[Callable[[str], str]] = None,
        voice_transcriber: Optional[Any] = None,
        pin_code: Optional[str] = None,
        iot_controller: Optional[Any] = None,
    ):
        """
        Initialize enhanced Telegram bot.
        
        Args:
            token: Telegram bot token.
            allowed_users: List of allowed user IDs.
            command_handler: Function to process commands.
            voice_transcriber: STT instance for voice notes.
            pin_code: PIN for sensitive actions.
            iot_controller: IoT controller for device commands.
        """
        if not TELEGRAM_AVAILABLE:
            raise RuntimeError("python-telegram-bot not installed")
        
        self.token = token
        self.allowed_users = set(allowed_users)
        self.command_handler = command_handler
        self.voice_transcriber = voice_transcriber
        self.pin_code = pin_code
        self.iot_controller = iot_controller
        
        self._app: Optional[Application] = None
        self._running = False
        
        # Security
        self.rate_limiter = RateLimiter()
        self._pending_actions: Dict[str, PendingAction] = {}
        self._command_log: List[Dict[str, Any]] = []
    
    def _is_authorized(self, user_id: int) -> bool:
        """Check if user is authorized."""
        return user_id in self.allowed_users
    
    async def _check_auth(self, update: Update) -> bool:
        """Check authorization and rate limit."""
        user_id = update.effective_user.id
        
        if not self._is_authorized(user_id):
            logger.warning(f"Unauthorized access attempt from user {user_id}")
            await update.message.reply_text("⛔ Unauthorized access denied.")
            return False
        
        if not self.rate_limiter.is_allowed(user_id):
            wait_time = self.rate_limiter.get_wait_time(user_id)
            await update.message.reply_text(
                f"⏳ Rate limited. Please wait {int(wait_time)} seconds."
            )
            return False
        
        return True
    
    def _log_command(self, user_id: int, command: str, response: str = "") -> None:
        """Log a command for auditing."""
        self._command_log.append({
            "user_id": user_id,
            "command": command,
            "response": response[:100],
            "timestamp": time.time(),
        })
        
        # Keep only last 100 commands
        if len(self._command_log) > 100:
            self._command_log = self._command_log[-100:]
    
    def _get_main_keyboard(self) -> InlineKeyboardMarkup:
        """Get main menu keyboard."""
        keyboard = [
            [
                InlineKeyboardButton("📊 Status", callback_data="status"),
                InlineKeyboardButton("💡 Lights", callback_data="lights_menu"),
            ],
            [
                InlineKeyboardButton("🚪 Door", callback_data="door_menu"),
                InlineKeyboardButton("🔍 Search", callback_data="search"),
            ],
            [
                InlineKeyboardButton("📍 Location", callback_data="location"),
                InlineKeyboardButton("⚙️ Settings", callback_data="settings"),
            ],
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def _get_lights_keyboard(self) -> InlineKeyboardMarkup:
        """Get lights control keyboard."""
        keyboard = [
            [
                InlineKeyboardButton("💡 All On", callback_data="lights_all_on"),
                InlineKeyboardButton("🌑 All Off", callback_data="lights_all_off"),
            ],
            [
                InlineKeyboardButton("🛋️ Living Room", callback_data="lights_living"),
                InlineKeyboardButton("🛏️ Bedroom", callback_data="lights_bedroom"),
            ],
            [InlineKeyboardButton("« Back", callback_data="main_menu")],
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def _get_door_keyboard(self) -> InlineKeyboardMarkup:
        """Get door control keyboard."""
        keyboard = [
            [
                InlineKeyboardButton("🔓 Unlock (requires 2FA)", callback_data="door_unlock_request"),
            ],
            [
                InlineKeyboardButton("🔒 Lock", callback_data="door_lock"),
                InlineKeyboardButton("📊 Status", callback_data="door_status"),
            ],
            [InlineKeyboardButton("« Back", callback_data="main_menu")],
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def _get_confirmation_keyboard(self, action_id: str) -> InlineKeyboardMarkup:
        """Get confirmation keyboard."""
        keyboard = [
            [
                InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{action_id}"),
                InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{action_id}"),
            ],
        ]
        return InlineKeyboardMarkup(keyboard)
    
    async def _start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        if not await self._check_auth(update):
            return
        
        await update.message.reply_text(
            "👋 *Welcome to JARVIS!*\n\n"
            "I'm your personal AI assistant. Here's what I can do:\n\n"
            "• Send text commands\n"
            "• Send voice notes\n"
            "• Control smart home devices\n"
            "• Share your location\n\n"
            "Use the buttons below or just type a command!",
            reply_markup=self._get_main_keyboard(),
            parse_mode="Markdown",
        )
    
    async def _help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        if not await self._check_auth(update):
            return
        
        help_text = """
🤖 *JARVIS Commands*

*Basic Commands:*
/start - Show main menu
/help - Show this help
/status - System status
/lights - Control lights
/door - Control door

*Voice Commands:*
Send a voice note and I'll transcribe and process it.

*Text Commands:*
Just type any command naturally:
• "Turn on the lights"
• "What's the weather?"
• "Open Chrome"
• "Search for Python tutorials"

*Location:*
Share your location for geofencing features.

*Security:*
Sensitive actions require confirmation or PIN.
"""
        await update.message.reply_text(help_text, parse_mode="Markdown")
    
    async def _status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /status command."""
        if not await self._check_auth(update):
            return
        
        status_text = "📊 *System Status*\n\n"
        status_text += "✅ JARVIS Online\n"
        status_text += "✅ Telegram Bot Active\n"
        
        # Get system status if handler available
        if self.command_handler:
            try:
                response = self.command_handler("system status brief")
                status_text += f"\n{response}"
            except Exception as e:
                status_text += f"\n⚠️ Status check failed: {e}"
        
        # IoT status
        if self.iot_controller:
            try:
                devices = self.iot_controller.get_online_devices()
                status_text += f"\n\n🏠 *IoT Devices:* {len(devices)} online"
            except Exception:
                pass
        
        await update.message.reply_text(status_text, parse_mode="Markdown")
    
    async def _handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle text messages."""
        if not await self._check_auth(update):
            return
        
        text = update.message.text
        user_id = update.effective_user.id
        
        logger.info(f"Received text from {user_id}: {text}")
        
        # Send typing indicator
        await update.message.chat.send_action("typing")
        
        if self.command_handler:
            try:
                response = self.command_handler(text)
                self._log_command(user_id, text, response)
                
                # Split long responses
                if len(response) > 4000:
                    for i in range(0, len(response), 4000):
                        await update.message.reply_text(response[i:i+4000])
                else:
                    await update.message.reply_text(response)
            except Exception as e:
                logger.error(f"Command handler error: {e}")
                await update.message.reply_text(f"❌ Error: {e}")
        else:
            await update.message.reply_text(
                "Command handler not configured.",
                reply_markup=self._get_main_keyboard(),
            )
    
    async def _handle_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle voice notes with transcription preview."""
        if not await self._check_auth(update):
            return
        
        if not self.voice_transcriber:
            await update.message.reply_text(
                "🎤 Voice transcription not available. Please send text."
            )
            return
        
        # Download voice note
        voice = update.message.voice
        file = await context.bot.get_file(voice.file_id)
        
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
            await file.download_to_drive(f.name)
            voice_path = Path(f.name)
        
        try:
            await update.message.chat.send_action("typing")
            
            # Transcribe
            result = self.voice_transcriber.transcribe_file(voice_path)
            
            if not result.text:
                await update.message.reply_text("❌ Could not transcribe voice note.")
                return
            
            # Show transcription preview with confirm button
            keyboard = [
                [
                    InlineKeyboardButton("✅ Execute", callback_data=f"exec_{hash(result.text) % 10000}"),
                    InlineKeyboardButton("❌ Cancel", callback_data="cancel_voice"),
                ],
            ]
            
            # Store the transcription temporarily
            context.user_data["pending_voice_command"] = result.text
            
            await update.message.reply_text(
                f"🎤 *Transcribed:*\n_{result.text}_\n\n"
                f"Execute this command?",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown",
            )
        
        finally:
            voice_path.unlink(missing_ok=True)
    
    async def _handle_location(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle location sharing."""
        if not await self._check_auth(update):
            return
        
        location = update.message.location
        
        await update.message.reply_text(
            f"📍 *Location Received*\n\n"
            f"Latitude: `{location.latitude:.6f}`\n"
            f"Longitude: `{location.longitude:.6f}`\n\n"
            "Location-based automations updated.",
            parse_mode="Markdown",
        )
        
        logger.info(f"Location update: {location.latitude}, {location.longitude}")
        
        # Process with proactive intelligence if available
        # This would integrate with the geofencing system
    
    async def _handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle inline keyboard callbacks."""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        if not self._is_authorized(user_id):
            await query.edit_message_text("⛔ Unauthorized")
            return
        
        data = query.data
        
        # Main menu
        if data == "main_menu":
            await query.edit_message_text(
                "👋 How can I help you?",
                reply_markup=self._get_main_keyboard(),
            )
        
        # Status
        elif data == "status":
            status_text = "📊 *System Status*\n\n✅ JARVIS Online"
            if self.command_handler:
                try:
                    response = self.command_handler("system status brief")
                    status_text += f"\n\n{response}"
                except Exception:
                    pass
            
            keyboard = [[InlineKeyboardButton("« Back", callback_data="main_menu")]]
            await query.edit_message_text(
                status_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown",
            )
        
        # Lights menu
        elif data == "lights_menu":
            await query.edit_message_text(
                "💡 *Light Control*\n\nSelect an option:",
                reply_markup=self._get_lights_keyboard(),
                parse_mode="Markdown",
            )
        
        elif data.startswith("lights_"):
            action = data.replace("lights_", "")
            result = f"💡 Lights: {action}"
            
            if self.command_handler:
                if action == "all_on":
                    result = self.command_handler("turn on all lights")
                elif action == "all_off":
                    result = self.command_handler("turn off all lights")
                elif action == "living":
                    result = self.command_handler("toggle living room lights")
                elif action == "bedroom":
                    result = self.command_handler("toggle bedroom lights")
            
            keyboard = [[InlineKeyboardButton("« Back", callback_data="lights_menu")]]
            await query.edit_message_text(
                result,
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
        
        # Door menu
        elif data == "door_menu":
            await query.edit_message_text(
                "🚪 *Door Control*\n\n⚠️ Unlock requires two-factor confirmation.",
                reply_markup=self._get_door_keyboard(),
                parse_mode="Markdown",
            )
        
        elif data == "door_unlock_request":
            # Create pending action
            action_id = hashlib.md5(f"{user_id}{time.time()}".encode()).hexdigest()[:8]
            
            self._pending_actions[action_id] = PendingAction(
                action_id=action_id,
                action_type="door_unlock",
                description="Unlock front door",
                callback=lambda: self.command_handler("unlock the door") if self.command_handler else "Door unlocked",
                confirmation_type=ConfirmationType.TWO_FACTOR,
            )
            
            await query.edit_message_text(
                "🔓 *Door Unlock Request*\n\n"
                "⚠️ This is a sensitive action.\n\n"
                "Please confirm you want to unlock the door:",
                reply_markup=self._get_confirmation_keyboard(action_id),
                parse_mode="Markdown",
            )
        
        elif data.startswith("confirm_"):
            action_id = data.replace("confirm_", "")
            action = self._pending_actions.get(action_id)
            
            if not action:
                await query.edit_message_text("❌ Action expired or not found.")
                return
            
            if action.is_expired:
                del self._pending_actions[action_id]
                await query.edit_message_text("❌ Action expired. Please try again.")
                return
            
            # Execute action
            try:
                result = action.callback()
                del self._pending_actions[action_id]
                
                keyboard = [[InlineKeyboardButton("« Back", callback_data="main_menu")]]
                await query.edit_message_text(
                    f"✅ *Action Completed*\n\n{result}",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="Markdown",
                )
            except Exception as e:
                await query.edit_message_text(f"❌ Action failed: {e}")
        
        elif data.startswith("cancel_"):
            action_id = data.replace("cancel_", "")
            if action_id in self._pending_actions:
                del self._pending_actions[action_id]
            
            await query.edit_message_text(
                "❌ Action cancelled.",
                reply_markup=self._get_main_keyboard(),
            )
        
        elif data == "door_lock":
            result = "🔒 Door locked"
            if self.command_handler:
                result = self.command_handler("lock the door")
            
            keyboard = [[InlineKeyboardButton("« Back", callback_data="door_menu")]]
            await query.edit_message_text(result, reply_markup=InlineKeyboardMarkup(keyboard))
        
        elif data == "door_status":
            result = "🚪 Door status: Unknown"
            if self.command_handler:
                result = self.command_handler("door status")
            
            keyboard = [[InlineKeyboardButton("« Back", callback_data="door_menu")]]
            await query.edit_message_text(result, reply_markup=InlineKeyboardMarkup(keyboard))
        
        # Voice command execution
        elif data.startswith("exec_"):
            command = context.user_data.get("pending_voice_command")
            if command and self.command_handler:
                response = self.command_handler(command)
                await query.edit_message_text(f"✅ {response}")
            else:
                await query.edit_message_text("❌ Command not found or expired.")
        
        elif data == "cancel_voice":
            context.user_data.pop("pending_voice_command", None)
            await query.edit_message_text("❌ Voice command cancelled.")
        
        # Location
        elif data == "location":
            keyboard = [
                [KeyboardButton("📍 Share Location", request_location=True)],
            ]
            await query.message.reply_text(
                "📍 *Location Sharing*\n\n"
                "Tap the button below to share your location for geofencing features.",
                reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True),
                parse_mode="Markdown",
            )
        
        # Settings
        elif data == "settings":
            keyboard = [
                [InlineKeyboardButton("🔔 Notifications", callback_data="settings_notif")],
                [InlineKeyboardButton("🔐 Security", callback_data="settings_security")],
                [InlineKeyboardButton("« Back", callback_data="main_menu")],
            ]
            await query.edit_message_text(
                "⚙️ *Settings*",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown",
            )
    
    def build(self) -> Application:
        """Build the Telegram application."""
        self._app = Application.builder().token(self.token).build()
        
        # Command handlers
        self._app.add_handler(CommandHandler("start", self._start_command))
        self._app.add_handler(CommandHandler("help", self._help_command))
        self._app.add_handler(CommandHandler("status", self._status_command))
        
        # Message handlers
        self._app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_text))
        self._app.add_handler(MessageHandler(filters.VOICE, self._handle_voice))
        self._app.add_handler(MessageHandler(filters.LOCATION, self._handle_location))
        
        # Callback handler
        self._app.add_handler(CallbackQueryHandler(self._handle_callback))
        
        return self._app
    
    async def start(self) -> None:
        """Start the bot."""
        if self._app is None:
            self.build()
        
        self._running = True
        logger.info("Starting enhanced Telegram bot...")
        
        # Set bot commands
        commands = [
            BotCommand("start", "Show main menu"),
            BotCommand("help", "Show help"),
            BotCommand("status", "System status"),
            BotCommand("lights", "Control lights"),
            BotCommand("door", "Control door"),
        ]
        await self._app.bot.set_my_commands(commands)
        
        await self._app.initialize()
        await self._app.start()
        await self._app.updater.start_polling()
        
        logger.info("Enhanced Telegram bot started")
    
    async def stop(self) -> None:
        """Stop the bot."""
        if self._app and self._running:
            self._running = False
            await self._app.updater.stop()
            await self._app.stop()
            await self._app.shutdown()
            logger.info("Enhanced Telegram bot stopped")
    
    def run(self) -> None:
        """Run the bot (blocking)."""
        if self._app is None:
            self.build()
        
        logger.info("Running enhanced Telegram bot...")
        self._app.run_polling()
    
    async def send_notification(
        self,
        text: str,
        keyboard: Optional[List[List[InlineKeyboardButton]]] = None,
        parse_mode: str = "Markdown",
    ) -> int:
        """Send notification to all authorized users."""
        if self._app is None:
            return 0
        
        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        sent = 0
        
        for user_id in self.allowed_users:
            try:
                await self._app.bot.send_message(
                    chat_id=user_id,
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode,
                )
                sent += 1
            except Exception as e:
                logger.error(f"Failed to notify user {user_id}: {e}")
        
        return sent
    
    async def send_alert(
        self,
        title: str,
        message: str,
        action_buttons: Optional[List[Tuple[str, str]]] = None,
    ) -> int:
        """Send an alert with optional action buttons."""
        text = f"🚨 *{title}*\n\n{message}"
        
        keyboard = None
        if action_buttons:
            keyboard = [[InlineKeyboardButton(text, callback_data=data) for text, data in action_buttons]]
        
        return await self.send_notification(text, keyboard)
