"""
Telegram Bot Module for JARVIS.

Provides remote access to JARVIS via Telegram:
- Text commands
- Voice note processing
- Rich responses with buttons
- Location-based triggers
"""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from loguru import logger

try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import (
        Application,
        CommandHandler,
        MessageHandler,
        CallbackQueryHandler,
        ContextTypes,
        filters,
    )
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    logger.warning("python-telegram-bot not available")


class JarvisTelegramBot:
    """
    Telegram bot interface for JARVIS.
    
    Features:
    - Secure access (only responds to authorized users)
    - Text command processing
    - Voice note transcription and processing
    - Rich responses with inline keyboards
    - Location sharing for geofencing
    """
    
    def __init__(
        self,
        token: str,
        allowed_users: List[int],
        command_handler: Optional[Callable[[str], str]] = None,
        voice_transcriber: Optional[Any] = None,
    ):
        """
        Initialize the Telegram bot.
        
        Args:
            token: Telegram bot token from @BotFather.
            allowed_users: List of allowed Telegram user IDs.
            command_handler: Function to process commands (text -> response).
            voice_transcriber: STT instance for voice notes.
        """
        if not TELEGRAM_AVAILABLE:
            raise RuntimeError("python-telegram-bot not installed")
        
        self.token = token
        self.allowed_users = set(allowed_users)
        self.command_handler = command_handler
        self.voice_transcriber = voice_transcriber
        
        self._app: Optional[Application] = None
        self._running = False
    
    def _is_authorized(self, user_id: int) -> bool:
        """Check if user is authorized."""
        return user_id in self.allowed_users
    
    async def _check_auth(self, update: Update) -> bool:
        """Check authorization and send error if not authorized."""
        user_id = update.effective_user.id
        
        if not self._is_authorized(user_id):
            logger.warning(f"Unauthorized access attempt from user {user_id}")
            await update.message.reply_text(
                "⛔ Unauthorized. This bot only responds to its owner."
            )
            return False
        
        return True
    
    async def _start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        if not await self._check_auth(update):
            return
        
        keyboard = [
            [
                InlineKeyboardButton("🏠 Status", callback_data="status"),
                InlineKeyboardButton("💡 Lights", callback_data="lights"),
            ],
            [
                InlineKeyboardButton("🔒 Lock Door", callback_data="lock_door"),
                InlineKeyboardButton("🔓 Unlock Door", callback_data="unlock_door"),
            ],
            [
                InlineKeyboardButton("📍 Share Location", callback_data="location"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "👋 Hello! I'm JARVIS, your personal AI assistant.\n\n"
            "You can:\n"
            "• Send me text commands\n"
            "• Send voice notes\n"
            "• Use the buttons below\n\n"
            "How can I help you?",
            reply_markup=reply_markup,
        )
    
    async def _help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        if not await self._check_auth(update):
            return
        
        help_text = """
🤖 *JARVIS Telegram Bot*

*Commands:*
/start - Show main menu
/help - Show this help
/status - System status
/lights - Control lights
/door - Control door lock

*Features:*
• Send any text message as a command
• Send voice notes for voice commands
• Share location for geofencing

*Examples:*
• "What's the weather?"
• "Turn on the lights"
• "Search for Python tutorials"
• "Open Chrome"
"""
        await update.message.reply_text(help_text, parse_mode="Markdown")
    
    async def _status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /status command."""
        if not await self._check_auth(update):
            return
        
        # Get system status
        status_text = "📊 *System Status*\n\n"
        status_text += "✅ JARVIS Online\n"
        status_text += "✅ Telegram Bot Active\n"
        
        if self.command_handler:
            response = self.command_handler("system status")
            status_text += f"\n{response}"
        
        await update.message.reply_text(status_text, parse_mode="Markdown")
    
    async def _handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle text messages."""
        if not await self._check_auth(update):
            return
        
        text = update.message.text
        logger.info(f"Received text command: {text}")
        
        # Send typing indicator
        await update.message.chat.send_action("typing")
        
        if self.command_handler:
            try:
                response = self.command_handler(text)
                await update.message.reply_text(response)
            except Exception as e:
                logger.error(f"Command handler error: {e}")
                await update.message.reply_text(f"❌ Error processing command: {e}")
        else:
            await update.message.reply_text(
                "Command handler not configured. Please set up JARVIS properly."
            )
    
    async def _handle_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle voice notes."""
        if not await self._check_auth(update):
            return
        
        if not self.voice_transcriber:
            await update.message.reply_text(
                "Voice transcription not available. Please send text commands."
            )
            return
        
        # Download voice note
        voice = update.message.voice
        file = await context.bot.get_file(voice.file_id)
        
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
            await file.download_to_drive(f.name)
            voice_path = Path(f.name)
        
        try:
            # Send typing indicator
            await update.message.chat.send_action("typing")
            
            # Transcribe
            await update.message.reply_text("🎤 Transcribing voice note...")
            
            result = self.voice_transcriber.transcribe_file(voice_path)
            
            if not result.text:
                await update.message.reply_text("❌ Could not transcribe voice note.")
                return
            
            await update.message.reply_text(f"📝 Transcribed: _{result.text}_", parse_mode="Markdown")
            
            # Process command
            if self.command_handler:
                response = self.command_handler(result.text)
                await update.message.reply_text(response)
        
        finally:
            # Clean up temp file
            voice_path.unlink(missing_ok=True)
    
    async def _handle_location(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle location sharing."""
        if not await self._check_auth(update):
            return
        
        location = update.message.location
        
        await update.message.reply_text(
            f"📍 Location received!\n"
            f"Latitude: {location.latitude}\n"
            f"Longitude: {location.longitude}\n\n"
            "Location-based automations can be triggered based on this."
        )
        
        # Here you would integrate with geofencing logic
        logger.info(f"Location update: {location.latitude}, {location.longitude}")
    
    async def _handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle inline keyboard callbacks."""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        if not self._is_authorized(user_id):
            await query.edit_message_text("⛔ Unauthorized")
            return
        
        data = query.data
        
        if data == "status":
            await query.edit_message_text("📊 Fetching status...")
            if self.command_handler:
                response = self.command_handler("system status")
                await query.edit_message_text(f"📊 *Status*\n\n{response}", parse_mode="Markdown")
        
        elif data == "lights":
            keyboard = [
                [
                    InlineKeyboardButton("💡 Turn On", callback_data="lights_on"),
                    InlineKeyboardButton("🌑 Turn Off", callback_data="lights_off"),
                ],
                [InlineKeyboardButton("« Back", callback_data="back")],
            ]
            await query.edit_message_text(
                "💡 *Light Control*\n\nChoose an action:",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown",
            )
        
        elif data == "lights_on":
            if self.command_handler:
                response = self.command_handler("turn on the lights")
                await query.edit_message_text(f"💡 {response}")
            else:
                await query.edit_message_text("💡 Lights turned on!")
        
        elif data == "lights_off":
            if self.command_handler:
                response = self.command_handler("turn off the lights")
                await query.edit_message_text(f"🌑 {response}")
            else:
                await query.edit_message_text("🌑 Lights turned off!")
        
        elif data == "lock_door":
            if self.command_handler:
                response = self.command_handler("lock the door")
                await query.edit_message_text(f"🔒 {response}")
            else:
                await query.edit_message_text("🔒 Door locked!")
        
        elif data == "unlock_door":
            await query.edit_message_text(
                "⚠️ *Door Unlock Request*\n\n"
                "This action requires additional authentication.\n"
                "Please use voice command or face recognition.",
                parse_mode="Markdown",
            )
        
        elif data == "location":
            keyboard = [[InlineKeyboardButton("« Back", callback_data="back")]]
            await query.edit_message_text(
                "📍 *Location Sharing*\n\n"
                "To share your location:\n"
                "1. Tap the 📎 attachment icon\n"
                "2. Select 'Location'\n"
                "3. Share your current location\n\n"
                "This enables location-based automations.",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown",
            )
        
        elif data == "back":
            keyboard = [
                [
                    InlineKeyboardButton("🏠 Status", callback_data="status"),
                    InlineKeyboardButton("💡 Lights", callback_data="lights"),
                ],
                [
                    InlineKeyboardButton("🔒 Lock Door", callback_data="lock_door"),
                    InlineKeyboardButton("🔓 Unlock Door", callback_data="unlock_door"),
                ],
                [
                    InlineKeyboardButton("📍 Share Location", callback_data="location"),
                ],
            ]
            await query.edit_message_text(
                "👋 How can I help you?",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
    
    def build(self) -> Application:
        """Build the Telegram application."""
        self._app = Application.builder().token(self.token).build()
        
        # Add handlers
        self._app.add_handler(CommandHandler("start", self._start_command))
        self._app.add_handler(CommandHandler("help", self._help_command))
        self._app.add_handler(CommandHandler("status", self._status_command))
        
        self._app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_text))
        self._app.add_handler(MessageHandler(filters.VOICE, self._handle_voice))
        self._app.add_handler(MessageHandler(filters.LOCATION, self._handle_location))
        
        self._app.add_handler(CallbackQueryHandler(self._handle_callback))
        
        return self._app
    
    async def start(self) -> None:
        """Start the bot."""
        if self._app is None:
            self.build()
        
        self._running = True
        logger.info("Starting Telegram bot...")
        
        await self._app.initialize()
        await self._app.start()
        await self._app.updater.start_polling()
        
        logger.info("Telegram bot started")
    
    async def stop(self) -> None:
        """Stop the bot."""
        if self._app and self._running:
            self._running = False
            await self._app.updater.stop()
            await self._app.stop()
            await self._app.shutdown()
            logger.info("Telegram bot stopped")
    
    def run(self) -> None:
        """Run the bot (blocking)."""
        if self._app is None:
            self.build()
        
        logger.info("Running Telegram bot...")
        self._app.run_polling()
    
    async def send_message(self, user_id: int, text: str) -> bool:
        """
        Send a message to a user.
        
        Args:
            user_id: Telegram user ID.
            text: Message text.
            
        Returns:
            True if sent successfully.
        """
        if self._app is None:
            return False
        
        try:
            await self._app.bot.send_message(chat_id=user_id, text=text)
            return True
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False
    
    async def send_notification(
        self,
        text: str,
        keyboard: Optional[List[List[InlineKeyboardButton]]] = None,
    ) -> int:
        """
        Send notification to all authorized users.
        
        Args:
            text: Notification text.
            keyboard: Optional inline keyboard.
            
        Returns:
            Number of users notified.
        """
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
                )
                sent += 1
            except Exception as e:
                logger.error(f"Failed to notify user {user_id}: {e}")
        
        return sent


class TelegramNotifier:
    """
    Simple notifier for sending alerts via Telegram.
    """
    
    def __init__(self, token: str, chat_ids: List[int]):
        """
        Initialize notifier.
        
        Args:
            token: Bot token.
            chat_ids: List of chat IDs to notify.
        """
        self.token = token
        self.chat_ids = chat_ids
    
    async def notify(self, message: str) -> int:
        """Send notification to all chat IDs."""
        if not TELEGRAM_AVAILABLE:
            return 0
        
        import httpx
        
        sent = 0
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        
        async with httpx.AsyncClient() as client:
            for chat_id in self.chat_ids:
                try:
                    response = await client.post(
                        url,
                        json={"chat_id": chat_id, "text": message},
                    )
                    if response.status_code == 200:
                        sent += 1
                except Exception as e:
                    logger.error(f"Failed to send notification: {e}")
        
        return sent
    
    def notify_sync(self, message: str) -> int:
        """Send notification synchronously."""
        return asyncio.run(self.notify(message))
