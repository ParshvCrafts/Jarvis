"""
JARVIS - Main Application Module

The central orchestrator that brings together all JARVIS components:
- Authentication (face, voice, liveness)
- Voice pipeline (wake word, STT, TTS)
- LLM with tiered fallback
- Agent system with specialized sub-agents
- Memory systems
- System control
- IoT integration
- Telegram bot
"""

from __future__ import annotations

import asyncio
import signal
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from loguru import logger

from .core.config import config, env, ensure_directories, PROJECT_ROOT, DATA_DIR
from .core.logger import setup_logging
from .core.llm import create_llm_manager, LLMManager, Message
from .core.llm_router import IntelligentLLMRouter, create_intelligent_router, TaskType

from .auth import AuthenticationManager
from .voice.pipeline import VoicePipeline, VoiceCommand, PipelineState
from .memory.conversation import ConversationMemory
from .memory.vector_store import VectorMemory
from .memory.episodic import EpisodicMemory
from .agents.supervisor import SupervisorAgent
from .agents.specialized import create_all_agents
from .system.controller import SystemController


class Jarvis:
    """
    Main JARVIS application class.
    
    Orchestrates all components and provides the main interaction loop.
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize JARVIS.
        
        Args:
            config_path: Optional path to configuration file.
        """
        # Load configuration
        self._config = config()
        self._env = env()
        
        # Ensure directories exist
        ensure_directories()
        
        # Setup logging
        setup_logging(self._config)
        
        logger.info("=" * 60)
        logger.info("Initializing JARVIS...")
        logger.info("=" * 60)
        
        # Initialize components (lazy loaded)
        self._llm_manager: Optional[LLMManager] = None
        self._auth_manager: Optional[AuthenticationManager] = None
        self._voice_pipeline: Optional[VoicePipeline] = None
        self._supervisor: Optional[SupervisorAgent] = None
        self._conversation_memory: Optional[ConversationMemory] = None
        self._vector_memory: Optional[VectorMemory] = None
        self._episodic_memory: Optional[EpisodicMemory] = None
        self._system_controller: Optional[SystemController] = None
        self._iot_controller = None
        self._telegram_bot = None
        
        # State
        self._running = False
        self._authenticated = False
    
    # =========================================================================
    # Component Initialization
    # =========================================================================
    
    def _init_llm(self) -> IntelligentLLMRouter:
        """Initialize intelligent LLM router with task-based routing."""
        if self._llm_manager is None:
            logger.info("Initializing intelligent LLM router...")
            
            # Use the new intelligent router with all providers
            self._llm_manager = create_intelligent_router(
                groq_api_key=self._env.groq_api_key,
                gemini_api_key=self._env.gemini_api_key,
                mistral_api_key=self._env.mistral_api_key,
                openrouter_api_key=self._env.openrouter_api_key,
                anthropic_api_key=self._env.anthropic_api_key,
                ollama_base_url=self._env.ollama_base_url,
                cache_dir=DATA_DIR / "llm_cache",
            )
            
            status = self._llm_manager.get_status()
            available = [name for name, info in status["providers"].items() if info["available"]]
            logger.info(f"Available LLM providers: {available}")
        
        return self._llm_manager
    
    def _init_auth(self) -> AuthenticationManager:
        """Initialize authentication manager."""
        if self._auth_manager is None:
            logger.info("Initializing authentication manager...")
            
            auth_config = self._config.auth
            
            self._auth_manager = AuthenticationManager(
                data_dir=DATA_DIR,
                face_config={
                    "tolerance": auth_config.face_recognition.tolerance,
                    "model": auth_config.face_recognition.model,
                    "num_jitters": auth_config.face_recognition.num_jitters,
                },
                voice_config={
                    "similarity_threshold": auth_config.voice_verification.similarity_threshold,
                    "min_audio_duration": auth_config.voice_verification.min_audio_duration,
                },
                liveness_config={
                    "ear_threshold": auth_config.liveness_detection.ear_threshold,
                    "consec_frames": auth_config.liveness_detection.consec_frames,
                    "head_movement_enabled": auth_config.liveness_detection.head_movement_enabled,
                    "timeout": auth_config.liveness_detection.timeout,
                },
                session_config={
                    "session_timeout": auth_config.session_timeout,
                    "max_failed_attempts": auth_config.max_failed_attempts,
                    "lockout_duration": auth_config.lockout_duration,
                    "jwt_secret": self._env.jwt_secret,
                    "authorization_levels": {
                        "low": auth_config.authorization_levels.low,
                        "medium": auth_config.authorization_levels.medium,
                        "high": auth_config.authorization_levels.high,
                    },
                },
            )
            
            status = self._auth_manager.get_enrollment_status()
            logger.info(f"Auth status: {status}")
        
        return self._auth_manager
    
    def _init_voice(self) -> VoicePipeline:
        """Initialize voice pipeline."""
        if self._voice_pipeline is None:
            logger.info("Initializing voice pipeline...")
            
            voice_config = self._config.voice
            
            self._voice_pipeline = VoicePipeline(
                wake_word_config={
                    "phrase": voice_config.wake_word.phrase,
                    "threshold": voice_config.wake_word.threshold,
                    "model_path": voice_config.wake_word.model_path or None,
                },
                stt_config={
                    "model": voice_config.speech_to_text.model,
                    "device": voice_config.speech_to_text.device,
                    "compute_type": voice_config.speech_to_text.compute_type,
                    "language": voice_config.speech_to_text.language,
                    "silence_duration": voice_config.voice_activity_detection.silence_duration,
                },
                tts_config={
                    "engine": voice_config.text_to_speech.engine,
                    "voice": voice_config.text_to_speech.voice,
                    "rate": voice_config.text_to_speech.rate,
                    "volume": voice_config.text_to_speech.volume,
                },
                audio_config={
                    "sample_rate": voice_config.audio.sample_rate,
                    "channels": voice_config.audio.channels,
                    "chunk_size": voice_config.audio.chunk_size,
                    "input_device": voice_config.audio.input_device,
                    "output_device": voice_config.audio.output_device,
                },
            )
            
            # Set callbacks
            self._voice_pipeline.set_callbacks(
                on_wake_word=self._on_wake_word,
                on_command=self._on_voice_command,
                on_state_change=self._on_pipeline_state_change,
                on_error=self._on_pipeline_error,
            )
        
        return self._voice_pipeline
    
    def _init_memory(self) -> None:
        """Initialize memory systems."""
        logger.info("Initializing memory systems...")
        
        memory_config = self._config.memory
        
        # Conversation memory
        self._conversation_memory = ConversationMemory(
            max_messages=memory_config.conversation.max_messages,
            window_size=memory_config.conversation.window_size,
            llm_manager=self._init_llm(),
        )
        
        # Vector memory
        self._vector_memory = VectorMemory(
            persist_directory=DATA_DIR / "chroma_db",
            collection_name=memory_config.vector_store.collection_name,
            embedding_model=memory_config.vector_store.embedding_model,
            max_results=memory_config.vector_store.max_results,
        )
        
        # Episodic memory
        self._episodic_memory = EpisodicMemory(
            db_path=DATA_DIR / memory_config.episodic.db_path,
        )
        
        logger.info("Memory systems initialized")
    
    def _init_agents(self) -> SupervisorAgent:
        """Initialize agent system."""
        if self._supervisor is None:
            logger.info("Initializing agent system...")
            
            llm = self._init_llm()
            
            # Create specialized agents
            agents = create_all_agents(llm)
            
            # Create supervisor
            self._supervisor = SupervisorAgent(
                llm_manager=llm,
                agents=agents,
                max_iterations=self._config.agents.supervisor.max_iterations or 10,
            )
            
            logger.info(f"Initialized {len(agents)} specialized agents")
        
        return self._supervisor
    
    def _init_system_controller(self) -> SystemController:
        """Initialize system controller."""
        if self._system_controller is None:
            logger.info("Initializing system controller...")
            
            self._system_controller = SystemController(
                allowed_apps=self._config.agents.system.allowed_apps,
                screenshot_dir=DATA_DIR / "screenshots",
            )
            
            status = self._system_controller.get_status()
            logger.info(f"System controller status: {status}")
        
        return self._system_controller
    
    # =========================================================================
    # Callbacks
    # =========================================================================
    
    def _on_wake_word(self) -> None:
        """Handle wake word detection."""
        logger.info("Wake word detected!")
        
        # Play acknowledgment
        if self._voice_pipeline:
            self._voice_pipeline.say("Yes?", blocking=False)
    
    def _on_voice_command(self, command: VoiceCommand) -> str:
        """
        Handle voice command.
        
        Args:
            command: Voice command from user.
            
        Returns:
            Response text.
        """
        logger.info(f"Processing command: {command.text}")
        
        # Check authentication for sensitive commands
        auth = self._init_auth()
        authorized, message = auth.check_command_authorization(command.text.lower())
        
        if not authorized and not self._authenticated:
            return "Please authenticate first. Say 'authenticate me' to begin."
        
        # Add to conversation memory
        if self._conversation_memory:
            self._conversation_memory.add_message("user", command.text)
        
        # Log command
        if self._episodic_memory:
            self._episodic_memory.log_command(command.text)
        
        # Process with agent system
        try:
            response = self._process_command(command.text)
            
            # Add response to memory
            if self._conversation_memory:
                self._conversation_memory.add_message("assistant", response)
            
            return response
        
        except Exception as e:
            logger.error(f"Command processing error: {e}")
            return f"I encountered an error: {e}"
    
    def _on_pipeline_state_change(self, state: PipelineState) -> None:
        """Handle voice pipeline state changes."""
        logger.debug(f"Pipeline state: {state.value}")
    
    def _on_pipeline_error(self, error: Exception) -> None:
        """Handle voice pipeline errors."""
        logger.error(f"Pipeline error: {error}")
    
    # =========================================================================
    # Command Processing
    # =========================================================================
    
    def _process_command(self, text: str) -> str:
        """
        Process a command through the agent system.
        
        Args:
            text: Command text.
            
        Returns:
            Response text.
        """
        text_lower = text.lower()
        
        # Handle special commands
        if "authenticate" in text_lower:
            return self._handle_authentication()
        
        if "enroll" in text_lower and "face" in text_lower:
            return self._handle_face_enrollment()
        
        if "enroll" in text_lower and "voice" in text_lower:
            return self._handle_voice_enrollment()
        
        if "logout" in text_lower or "sign out" in text_lower:
            return self._handle_logout()
        
        # Process through supervisor agent
        supervisor = self._init_agents()
        response = supervisor.run_sync(text)
        
        return response
    
    def _handle_authentication(self) -> str:
        """Handle authentication request."""
        auth = self._init_auth()
        
        if not auth.is_enrolled:
            return "No biometrics enrolled. Please enroll your face first by saying 'enroll my face'."
        
        result = auth.authenticate(
            require_face=True,
            require_voice=False,
            require_liveness=True,
        )
        
        if result.success:
            self._authenticated = True
            return f"Authentication successful! {result.message}"
        else:
            return f"Authentication failed. {result.message}"
    
    def _handle_face_enrollment(self) -> str:
        """Handle face enrollment request."""
        auth = self._init_auth()
        success, message = auth.enroll_face_from_camera(num_samples=5)
        return message
    
    def _handle_voice_enrollment(self) -> str:
        """Handle voice enrollment request."""
        auth = self._init_auth()
        success, message = auth.enroll_voice_from_microphone(num_samples=3)
        return message
    
    def _handle_logout(self) -> str:
        """Handle logout request."""
        auth = self._init_auth()
        auth.logout()
        self._authenticated = False
        return "You have been logged out. Goodbye!"
    
    # =========================================================================
    # Public Interface
    # =========================================================================
    
    def chat(self, message: str) -> str:
        """
        Send a text message to JARVIS.
        
        Args:
            message: User message.
            
        Returns:
            JARVIS response.
        """
        command = VoiceCommand(
            text=message,
            confidence=1.0,
            duration=0.0,
            timestamp=0.0,
        )
        return self._on_voice_command(command)
    
    def start_voice(self) -> bool:
        """Start the voice pipeline."""
        pipeline = self._init_voice()
        return pipeline.start()
    
    def stop_voice(self) -> None:
        """Stop the voice pipeline."""
        if self._voice_pipeline:
            self._voice_pipeline.stop()
    
    def say(self, text: str) -> None:
        """Speak text."""
        if self._voice_pipeline:
            self._voice_pipeline.say(text)
        else:
            logger.info(f"JARVIS: {text}")
    
    async def start_telegram(self) -> None:
        """Start the Telegram bot."""
        if not self._config.telegram.enabled:
            logger.info("Telegram bot disabled in configuration")
            return
        
        if not self._env.telegram_bot_token:
            logger.warning("Telegram bot token not configured")
            return
        
        from .telegram.bot import JarvisTelegramBot
        
        self._telegram_bot = JarvisTelegramBot(
            token=self._env.telegram_bot_token,
            allowed_users=self._config.telegram.allowed_users,
            command_handler=self.chat,
        )
        
        await self._telegram_bot.start()
    
    async def stop_telegram(self) -> None:
        """Stop the Telegram bot."""
        if self._telegram_bot:
            await self._telegram_bot.stop()
    
    def run(self) -> None:
        """
        Run JARVIS main loop.
        
        This starts the voice pipeline and runs until interrupted.
        """
        logger.info("Starting JARVIS...")
        
        # Initialize components
        self._init_llm()
        self._init_auth()
        self._init_memory()
        self._init_agents()
        self._init_system_controller()
        
        # Setup signal handlers
        def signal_handler(sig, frame):
            logger.info("Shutdown signal received")
            self._running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Start voice pipeline
        self._running = True
        
        if self.start_voice():
            logger.info("Voice pipeline started")
            self.say("JARVIS online and ready.")
        else:
            logger.warning("Voice pipeline failed to start. Running in text mode.")
        
        # Main loop
        try:
            while self._running:
                asyncio.get_event_loop().run_until_complete(asyncio.sleep(0.1))
        except KeyboardInterrupt:
            pass
        finally:
            self.shutdown()
    
    def run_text_mode(self) -> None:
        """
        Run JARVIS in text-only mode.
        
        Useful for testing without audio hardware.
        """
        logger.info("Starting JARVIS in text mode...")
        
        # Initialize components
        self._init_llm()
        self._init_memory()
        self._init_agents()
        
        print("\n" + "=" * 60)
        print("JARVIS - Text Mode")
        print("Type 'quit' or 'exit' to stop")
        print("=" * 60 + "\n")
        
        while True:
            try:
                user_input = input("You: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ["quit", "exit", "bye"]:
                    print("\nJARVIS: Goodbye!")
                    break
                
                response = self.chat(user_input)
                print(f"\nJARVIS: {response}\n")
            
            except KeyboardInterrupt:
                print("\n\nJARVIS: Goodbye!")
                break
            except Exception as e:
                logger.error(f"Error: {e}")
                print(f"\nJARVIS: I encountered an error: {e}\n")
    
    def shutdown(self) -> None:
        """Shutdown JARVIS gracefully."""
        logger.info("Shutting down JARVIS...")
        
        self._running = False
        
        # Stop voice pipeline
        self.stop_voice()
        
        # Stop Telegram bot
        if self._telegram_bot:
            asyncio.get_event_loop().run_until_complete(self.stop_telegram())
        
        logger.info("JARVIS shutdown complete")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="JARVIS - Advanced Personal AI Assistant")
    parser.add_argument("--text", action="store_true", help="Run in text-only mode")
    parser.add_argument("--config", type=str, help="Path to configuration file")
    
    args = parser.parse_args()
    
    jarvis = Jarvis(config_path=Path(args.config) if args.config else None)
    
    if args.text:
        jarvis.run_text_mode()
    else:
        jarvis.run()


if __name__ == "__main__":
    main()
