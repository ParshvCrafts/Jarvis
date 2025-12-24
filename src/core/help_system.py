"""
Help system for JARVIS.

Provides contextual help, command documentation, and user guidance.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class HelpCategory(Enum):
    """Categories of help topics."""
    GENERAL = "general"
    VOICE = "voice"
    SYSTEM = "system"
    IOT = "iot"
    CODING = "coding"
    RESEARCH = "research"
    COMMUNICATION = "communication"
    SETTINGS = "settings"


@dataclass
class HelpTopic:
    """A help topic with examples."""
    name: str
    category: HelpCategory
    description: str
    examples: List[str] = field(default_factory=list)
    related: List[str] = field(default_factory=list)
    voice_phrases: List[str] = field(default_factory=list)


class HelpSystem:
    """
    Comprehensive help system for JARVIS.
    
    Provides:
    - Command documentation
    - Example phrases
    - Contextual suggestions
    - Category-based browsing
    """
    
    def __init__(self):
        self._topics: Dict[str, HelpTopic] = {}
        self._load_default_topics()
    
    def _load_default_topics(self) -> None:
        """Load default help topics."""
        topics = [
            # General
            HelpTopic(
                name="getting_started",
                category=HelpCategory.GENERAL,
                description="How to get started with JARVIS",
                examples=[
                    "Say 'Hey Jarvis' to wake me up",
                    "Ask me anything after the wake word",
                    "Say 'goodbye' or 'that's all' to end conversation",
                ],
                voice_phrases=["help", "what can you do", "how do I use you"],
            ),
            HelpTopic(
                name="wake_word",
                category=HelpCategory.VOICE,
                description="How to activate JARVIS with wake word",
                examples=[
                    "'Hey Jarvis' - Default wake word",
                    "Wait for the beep before speaking",
                    "Speak clearly within 10 seconds",
                ],
                related=["conversation_mode", "voice_commands"],
            ),
            HelpTopic(
                name="conversation_mode",
                category=HelpCategory.VOICE,
                description="Multi-turn conversation without repeating wake word",
                examples=[
                    "After wake word, you have 30 seconds to ask follow-up questions",
                    "Say 'that's all' or 'goodbye' to exit conversation mode",
                    "Conversation mode auto-exits after 30 seconds of silence",
                ],
                related=["wake_word"],
            ),
            
            # System Control
            HelpTopic(
                name="open_apps",
                category=HelpCategory.SYSTEM,
                description="Open applications on your computer",
                examples=[
                    "Open Chrome",
                    "Launch Notepad",
                    "Start Visual Studio Code",
                    "Open File Explorer",
                ],
                voice_phrases=["open", "launch", "start", "run"],
            ),
            HelpTopic(
                name="screenshots",
                category=HelpCategory.SYSTEM,
                description="Take screenshots of your screen",
                examples=[
                    "Take a screenshot",
                    "Capture my screen",
                    "Screenshot this",
                ],
                voice_phrases=["screenshot", "capture screen"],
            ),
            HelpTopic(
                name="volume_control",
                category=HelpCategory.SYSTEM,
                description="Control system volume",
                examples=[
                    "Mute the volume",
                    "Set volume to 50%",
                    "Turn up the volume",
                ],
                voice_phrases=["volume", "mute", "unmute"],
            ),
            
            # IoT
            HelpTopic(
                name="lights",
                category=HelpCategory.IOT,
                description="Control smart lights",
                examples=[
                    "Turn on the lights",
                    "Turn off the bedroom light",
                    "Dim the lights to 50%",
                    "Set lights to warm white",
                ],
                voice_phrases=["light", "lights", "lamp", "bulb"],
            ),
            HelpTopic(
                name="door_locks",
                category=HelpCategory.IOT,
                description="Control smart door locks",
                examples=[
                    "Lock the front door",
                    "Unlock the garage",
                    "Is the door locked?",
                ],
                voice_phrases=["lock", "unlock", "door"],
            ),
            HelpTopic(
                name="device_status",
                category=HelpCategory.IOT,
                description="Check status of IoT devices",
                examples=[
                    "What devices are online?",
                    "Is the light on?",
                    "Show device status",
                ],
                voice_phrases=["status", "devices", "online"],
            ),
            
            # Coding
            HelpTopic(
                name="code_generation",
                category=HelpCategory.CODING,
                description="Generate code in various languages",
                examples=[
                    "Write a Python function to sort a list",
                    "Create a JavaScript async function",
                    "Generate a REST API endpoint",
                ],
                voice_phrases=["write code", "create function", "generate"],
            ),
            HelpTopic(
                name="code_explanation",
                category=HelpCategory.CODING,
                description="Explain code and errors",
                examples=[
                    "Explain this error message",
                    "What does this code do?",
                    "Help me debug this function",
                ],
                voice_phrases=["explain", "debug", "what does"],
            ),
            HelpTopic(
                name="git_operations",
                category=HelpCategory.CODING,
                description="Git version control operations",
                examples=[
                    "Git status",
                    "Commit with message 'fix bug'",
                    "Push to origin",
                    "Create a new branch",
                ],
                voice_phrases=["git", "commit", "push", "branch"],
            ),
            
            # Research
            HelpTopic(
                name="web_search",
                category=HelpCategory.RESEARCH,
                description="Search the web for information",
                examples=[
                    "Search for Python tutorials",
                    "Look up the weather",
                    "Find restaurants nearby",
                ],
                voice_phrases=["search", "look up", "find"],
            ),
            HelpTopic(
                name="questions",
                category=HelpCategory.RESEARCH,
                description="Ask questions and get answers",
                examples=[
                    "What is machine learning?",
                    "Who invented the telephone?",
                    "How does photosynthesis work?",
                ],
                voice_phrases=["what is", "who is", "how does", "why"],
            ),
            
            # Communication
            HelpTopic(
                name="reminders",
                category=HelpCategory.COMMUNICATION,
                description="Set reminders and alarms",
                examples=[
                    "Remind me to call mom at 5pm",
                    "Set an alarm for 7am",
                    "What are my reminders?",
                ],
                voice_phrases=["remind", "reminder", "alarm"],
            ),
            
            # Settings
            HelpTopic(
                name="settings",
                category=HelpCategory.SETTINGS,
                description="Configure JARVIS settings",
                examples=[
                    "Change wake word sensitivity",
                    "Set conversation timeout",
                    "Enable/disable audio cues",
                ],
                voice_phrases=["settings", "configure", "change"],
            ),
        ]
        
        for topic in topics:
            self._topics[topic.name] = topic
    
    def get_topic(self, name: str) -> Optional[HelpTopic]:
        """Get a help topic by name."""
        return self._topics.get(name)
    
    def get_topics_by_category(self, category: HelpCategory) -> List[HelpTopic]:
        """Get all topics in a category."""
        return [t for t in self._topics.values() if t.category == category]
    
    def search_topics(self, query: str) -> List[HelpTopic]:
        """Search topics by keyword."""
        query_lower = query.lower()
        results = []
        
        for topic in self._topics.values():
            # Check name
            if query_lower in topic.name.lower():
                results.append(topic)
                continue
            
            # Check description
            if query_lower in topic.description.lower():
                results.append(topic)
                continue
            
            # Check examples
            for example in topic.examples:
                if query_lower in example.lower():
                    results.append(topic)
                    break
            
            # Check voice phrases
            for phrase in topic.voice_phrases:
                if query_lower in phrase.lower():
                    results.append(topic)
                    break
        
        return results
    
    def get_quick_help(self) -> str:
        """Get quick help summary."""
        return """
**JARVIS Quick Help**

🎤 **Voice Commands:**
- Say "Hey Jarvis" to wake me up
- Speak your command after the beep
- Say "goodbye" to end conversation

🖥️ **System Control:**
- "Open [app name]" - Launch applications
- "Take a screenshot" - Capture screen
- "Volume up/down/mute" - Control audio

💡 **Smart Home:**
- "Turn on/off the lights"
- "Lock/unlock the door"
- "What devices are online?"

💻 **Coding:**
- "Write a function to..."
- "Explain this code"
- "Git status/commit/push"

🔍 **Research:**
- "Search for..."
- "What is...?"
- "Tell me about..."

Say "help [topic]" for more details on any topic.
"""
    
    def get_detailed_help(self, topic_name: str) -> str:
        """Get detailed help for a topic."""
        topic = self.get_topic(topic_name)
        
        if not topic:
            # Try searching
            results = self.search_topics(topic_name)
            if results:
                topic = results[0]
            else:
                return f"No help found for '{topic_name}'. Try 'help' for available topics."
        
        lines = [
            f"**{topic.name.replace('_', ' ').title()}**",
            "",
            topic.description,
            "",
            "**Examples:**",
        ]
        
        for example in topic.examples:
            lines.append(f"  • {example}")
        
        if topic.voice_phrases:
            lines.append("")
            lines.append(f"**Voice triggers:** {', '.join(topic.voice_phrases)}")
        
        if topic.related:
            lines.append("")
            lines.append(f"**Related:** {', '.join(topic.related)}")
        
        return "\n".join(lines)
    
    def get_category_help(self, category: HelpCategory) -> str:
        """Get help for all topics in a category."""
        topics = self.get_topics_by_category(category)
        
        if not topics:
            return f"No topics found in category '{category.value}'."
        
        lines = [
            f"**{category.value.title()} Commands**",
            "",
        ]
        
        for topic in topics:
            lines.append(f"• **{topic.name.replace('_', ' ').title()}**: {topic.description}")
            if topic.examples:
                lines.append(f"  Example: \"{topic.examples[0]}\"")
        
        return "\n".join(lines)
    
    def suggest_command(self, partial: str) -> List[str]:
        """Suggest commands based on partial input."""
        suggestions = []
        partial_lower = partial.lower()
        
        for topic in self._topics.values():
            for phrase in topic.voice_phrases:
                if phrase.startswith(partial_lower):
                    suggestions.extend(topic.examples[:2])
                    break
        
        return suggestions[:5]


# Global instance
_help_system: Optional[HelpSystem] = None


def get_help_system() -> HelpSystem:
    """Get the global help system instance."""
    global _help_system
    if _help_system is None:
        _help_system = HelpSystem()
    return _help_system


def get_help(topic: Optional[str] = None) -> str:
    """Get help text."""
    system = get_help_system()
    
    if topic is None:
        return system.get_quick_help()
    
    # Check if it's a category
    try:
        category = HelpCategory(topic.lower())
        return system.get_category_help(category)
    except ValueError:
        pass
    
    return system.get_detailed_help(topic)
