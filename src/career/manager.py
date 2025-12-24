"""
Career Manager for JARVIS.

Orchestrates all career and advanced intelligence features:
- Interview Prep Mode
- Resume/Experience Tracker
- Job Application Tracker
- Expense Tracker
- Notion Integration
- Networking Tracker
- Voice Journal
- Learning Path Generator
"""

import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from loguru import logger

from .interview import InterviewPrep, QuestionType, Difficulty
from .resume import ResumeTracker, ExperienceType
from .applications import ApplicationTracker, ApplicationStatus
from .expense import ExpenseTracker, ExpenseCategory
from .notion import NotionIntegration
from .networking import NetworkingTracker, ContactType
from .voice_journal import VoiceJournal
from .learning_path import LearningPathGenerator


class CareerManager:
    """
    Orchestrates all career and advanced intelligence features.
    
    Features:
    - Interview practice with question bank
    - Resume and experience tracking
    - Job application management
    - Expense and budget tracking
    - Notion workspace integration
    - Professional networking
    - Voice journaling
    - Learning path generation
    """
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        data_dir: str = "data",
    ):
        self.config = config or {}
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self._init_interview()
        self._init_resume()
        self._init_applications()
        self._init_expense()
        self._init_notion()
        self._init_networking()
        self._init_journal()
        self._init_learning_path()
        
        logger.info("Career Manager initialized")
    
    def _init_interview(self):
        """Initialize interview prep."""
        config = self.config.get("interview_prep", {})
        self.interview = InterviewPrep(
            data_dir=str(self.data_dir),
            default_difficulty=config.get("default_difficulty", "medium"),
        )
    
    def _init_resume(self):
        """Initialize resume tracker."""
        config = self.config.get("resume", {})
        self.resume = ResumeTracker(
            data_dir=str(self.data_dir),
            name=config.get("name", ""),
            university=config.get("university", "UC Berkeley"),
            major=config.get("major", "Data Science"),
            graduation=config.get("graduation", "2028"),
        )
    
    def _init_applications(self):
        """Initialize application tracker."""
        config = self.config.get("applications", {})
        self.applications = ApplicationTracker(
            data_dir=str(self.data_dir),
            reminder_days=config.get("reminder_days", 3),
        )
    
    def _init_expense(self):
        """Initialize expense tracker."""
        config = self.config.get("finance", {}).get("expense_tracker", {})
        self.expense = ExpenseTracker(
            data_dir=str(self.data_dir),
            currency=config.get("currency", "USD"),
            monthly_budget=config.get("monthly_budget", 1000),
            budget_threshold=config.get("budget_threshold", 80),
        )
    
    def _init_notion(self):
        """Initialize Notion integration."""
        config = self.config.get("notion", {})
        self.notion = NotionIntegration(
            data_dir=str(self.data_dir),
            integration_type=config.get("integration_type", "url"),
            api_key=config.get("api_key"),
        )
    
    def _init_networking(self):
        """Initialize networking tracker."""
        config = self.config.get("networking", {})
        self.networking = NetworkingTracker(
            data_dir=str(self.data_dir),
            follow_up_days=config.get("follow_up_days", 14),
        )
    
    def _init_journal(self):
        """Initialize voice journal."""
        self.journal = VoiceJournal(data_dir=str(self.data_dir))
    
    def _init_learning_path(self):
        """Initialize learning path generator."""
        self.learning = LearningPathGenerator(data_dir=str(self.data_dir))
    
    # =========================================================================
    # Command Handling
    # =========================================================================
    
    async def handle_command(self, text: str) -> Optional[str]:
        """Route and handle career-related commands."""
        text_lower = text.lower().strip()
        
        # Interview commands
        if self._is_interview_command(text_lower):
            return self._handle_interview(text_lower, text)
        
        # Resume commands
        if self._is_resume_command(text_lower):
            return self._handle_resume(text_lower, text)
        
        # Application commands
        if self._is_application_command(text_lower):
            return self._handle_application(text_lower, text)
        
        # Expense commands
        if self._is_expense_command(text_lower):
            return self._handle_expense(text_lower, text)
        
        # Notion commands
        if self._is_notion_command(text_lower):
            return self._handle_notion(text_lower, text)
        
        # Networking commands
        if self._is_networking_command(text_lower):
            return self._handle_networking(text_lower, text)
        
        # Journal commands
        if self._is_journal_command(text_lower):
            return self._handle_journal(text_lower, text)
        
        # Learning path commands
        if self._is_learning_command(text_lower):
            return self._handle_learning(text_lower, text)
        
        return None
    
    # =========================================================================
    # Command Detection
    # =========================================================================
    
    def _is_interview_command(self, text: str) -> bool:
        patterns = [
            "interview", "coding question", "ml question", "behavioral question",
            "system design question", "give me a hint", "show solution",
            "rate my answer", "interview stats", "mock interview",
            "practice question", "leetcode",
        ]
        return any(p in text for p in patterns)
    
    def _is_resume_command(self, text: str) -> bool:
        patterns = [
            "add experience", "show experience", "my experience", "add skill",
            "my skills", "update gpa", "resume", "generate bullet",
            "add certification", "add project", "what's on my resume",
        ]
        return any(p in text for p in patterns)
    
    def _is_application_command(self, text: str) -> bool:
        patterns = [
            "add application", "applied to", "application status", "update application",
            "my applications", "pending application", "application stats",
            "applications due", "job application", "internship application",
        ]
        return any(p in text for p in patterns)
    
    def _is_expense_command(self, text: str) -> bool:
        patterns = [
            "log expense", "spent", "expense", "budget", "how much did i spend",
            "spending", "add income", "set budget", "budget status",
            "weekly spending", "monthly spending",
        ]
        return any(p in text for p in patterns)
    
    def _is_notion_command(self, text: str) -> bool:
        patterns = [
            "open notion", "notion page", "save notion", "my notion",
            "notion pages", "search notion",
        ]
        return any(p in text for p in patterns)
    
    def _is_networking_command(self, text: str) -> bool:
        # Professional networking - distinct from communication contacts
        patterns = [
            "add networking contact", "my network", "professional contact",
            "follow up with", "who should i contact", "networking", "met someone",
            "add note for contact", "network stats", "linkedin contact",
        ]
        # Exclude communication contact patterns (handled by communication module)
        exclude_patterns = ["whatsapp", "phone number", "call", "message"]
        if any(p in text for p in exclude_patterns):
            return False
        return any(p in text for p in patterns)
    
    def _is_journal_command(self, text: str) -> bool:
        # Voice journal - distinct from learning journal in productivity module
        patterns = [
            "voice journal", "diary", "today's journal", "journal entry",
            "how am i feeling", "mood", "journal stats", "search journal",
            "grateful for", "reflect on", "daily reflection",
        ]
        # Exclude learning journal patterns (handled by productivity module)
        exclude_patterns = ["learning journal", "what did i learn", "log learning", "til:"]
        if any(p in text for p in exclude_patterns):
            return False
        return any(p in text for p in patterns)
    
    def _is_learning_command(self, text: str) -> bool:
        patterns = [
            "learning path", "what should i learn", "create path",
            "my learning", "completed", "next in", "add to path",
            "learning progress", "skill roadmap",
        ]
        return any(p in text for p in patterns)
    
    # =========================================================================
    # Command Handlers
    # =========================================================================
    
    def _handle_interview(self, text: str, original: str) -> str:
        """Handle interview prep commands."""
        # Get coding question
        if "coding question" in text or "leetcode" in text:
            difficulty = None
            if "easy" in text:
                difficulty = "easy"
            elif "hard" in text:
                difficulty = "hard"
            elif "medium" in text:
                difficulty = "medium"
            return self.interview.get_coding_question(difficulty)
        
        # Get ML question
        if "ml question" in text or "machine learning question" in text:
            return self.interview.get_ml_question()
        
        # Get behavioral question
        if "behavioral question" in text:
            return self.interview.get_behavioral_question()
        
        # Get system design question
        if "system design" in text:
            return self.interview.get_system_design_question()
        
        # Get hint
        if "hint" in text:
            return self.interview.get_hint()
        
        # Show solution
        if "solution" in text or "answer" in text:
            return self.interview.get_solution()
        
        # Rate answer
        rate_match = re.search(r"rate.*?(\d)", text)
        if rate_match:
            rating = int(rate_match.group(1))
            return self.interview.rate_answer(rating)
        
        # Interview stats
        if "stats" in text or "statistics" in text:
            return self.interview.get_stats()
        
        # Start mock interview
        if "mock interview" in text or "start interview" in text:
            qtype = "coding"
            if "ml" in text:
                qtype = "ml"
            elif "behavioral" in text:
                qtype = "behavioral"
            return self.interview.start_mock_interview(qtype)
        
        # Default: random question
        if "interview practice" in text or "practice question" in text:
            return self.interview.get_coding_question()
        
        return self.interview.get_stats()
    
    def _handle_resume(self, text: str, original: str) -> str:
        """Handle resume/experience commands."""
        # Add experience
        exp_match = re.search(r"add\s+(?:experience|project)[:\s]+(.+)", text, re.IGNORECASE)
        if exp_match:
            description = exp_match.group(1).strip()
            
            # Detect type
            exp_type = "project"
            if any(w in text for w in ["internship", "work", "job"]):
                exp_type = "work"
            elif any(w in text for w in ["club", "leadership", "president", "officer"]):
                exp_type = "leadership"
            elif any(w in text for w in ["award", "certification", "certificate"]):
                exp_type = "achievement"
            
            # Extract title (first part before "using" or end)
            title_match = re.match(r"([^,]+?)(?:\s+using|\s+with|\s*,|$)", description)
            title = title_match.group(1).strip() if title_match else description[:50]
            
            # Extract skills
            skills = []
            skills_match = re.search(r"using\s+(.+?)(?:\s*,\s*improved|\s*$)", description, re.IGNORECASE)
            if skills_match:
                skills = [s.strip() for s in skills_match.group(1).split(",")]
            
            # Extract impact
            impact = ""
            impact_match = re.search(r"(improved|increased|reduced|achieved).+", description, re.IGNORECASE)
            if impact_match:
                impact = impact_match.group(0)
            
            exp = self.resume.add_experience(
                title=title,
                exp_type=exp_type,
                description=description,
                skills=skills,
                impact=impact,
            )
            
            return f"✅ Added to your resume!\n\n**{exp.title}** ({exp.type.value})\n{description}\n\nWould you like me to generate a resume bullet for this?"
        
        # Add skill
        skill_match = re.search(r"add\s+skill[:\s]+(.+?)(?:\s*,\s*(beginner|intermediate|advanced|expert))?$", text, re.IGNORECASE)
        if skill_match:
            skill_name = skill_match.group(1).strip()
            level = skill_match.group(2) or "intermediate"
            self.resume.add_skill(skill_name, level=level)
            return f"✅ Added skill: {skill_name} ({level})"
        
        # Update GPA
        gpa_match = re.search(r"(?:update|set)\s+(?:my\s+)?gpa\s+(?:to\s+)?(\d+\.?\d*)", text)
        if gpa_match:
            gpa = float(gpa_match.group(1))
            return self.resume.update_gpa(gpa)
        
        # Show experiences
        if "show experience" in text or "my experience" in text:
            experiences = self.resume.get_experiences()
            return self.resume.format_experiences(experiences)
        
        # Show skills
        if "my skills" in text or "show skills" in text:
            skills = self.resume.get_skills()
            return self.resume.format_skills(skills)
        
        # Resume summary
        if "resume" in text or "what's on my resume" in text:
            return self.resume.get_resume_summary()
        
        # Generate bullet
        if "generate bullet" in text:
            experiences = self.resume.get_experiences(limit=1)
            if experiences:
                bullet = self.resume.generate_bullet(experiences[0].id)
                return f"📝 **Resume Bullet:**\n\n• {bullet}"
            return "No experiences to generate bullets from."
        
        return self.resume.get_resume_summary()
    
    def _handle_application(self, text: str, original: str) -> str:
        """Handle job application commands."""
        # Add application
        add_match = re.search(r"(?:add\s+application|applied\s+to)[:\s]+(.+)", text, re.IGNORECASE)
        if add_match:
            details = add_match.group(1).strip()
            
            # Parse company and position
            company = details
            position = "Software Engineering Intern"
            
            # Try to extract position
            pos_match = re.search(r"(.+?)\s+(?:for|as)\s+(.+)", details)
            if pos_match:
                company = pos_match.group(1).strip()
                position = pos_match.group(2).strip()
            
            app = self.applications.add_application(
                company=company,
                position=position,
            )
            
            return f"✅ Added application!\n\n**{app.company}** - {app.position}\nStatus: {app.status.value.replace('_', ' ').title()}"
        
        # Update application status
        update_match = re.search(r"update\s+(.+?)\s+(?:application)?[:\s]+(.+)", text, re.IGNORECASE)
        if update_match:
            company = update_match.group(1).strip()
            new_status = update_match.group(2).strip()
            
            # Map common phrases to statuses
            status_map = {
                "got phone screen": "phone_screen",
                "phone screen": "phone_screen",
                "got interview": "technical",
                "technical interview": "technical",
                "onsite": "onsite",
                "got offer": "offer",
                "offer": "offer",
                "rejected": "rejected",
                "withdrew": "withdrawn",
            }
            
            status = status_map.get(new_status.lower(), new_status)
            return self.applications.update_status(company, status)
        
        # Show applications
        if "my applications" in text or "show applications" in text:
            apps = self.applications.get_applications()
            return self.applications.format_applications(apps)
        
        # Pending applications
        if "pending" in text:
            apps = self.applications.get_pending_applications()
            return self.applications.format_applications(apps)
        
        # Applications due
        if "due" in text:
            apps = self.applications.get_upcoming_deadlines()
            if apps:
                return self.applications.format_applications(apps)
            return "No upcoming application deadlines."
        
        # Application stats
        if "stats" in text:
            return self.applications.get_stats()
        
        return self.applications.get_stats()
    
    def _handle_expense(self, text: str, original: str) -> str:
        """Handle expense tracking commands."""
        # Log expense
        expense_match = re.search(r"(?:log\s+expense|spent)[:\s]*\$?(\d+\.?\d*)\s*(?:on\s+)?(.+)?", text, re.IGNORECASE)
        if expense_match:
            amount = float(expense_match.group(1))
            description = expense_match.group(2).strip() if expense_match.group(2) else ""
            return self.expense.log_expense(amount, description)
        
        # Add income
        income_match = re.search(r"(?:add\s+income|earned)[:\s]*\$?(\d+\.?\d*)\s*(?:from\s+)?(.+)?", text, re.IGNORECASE)
        if income_match:
            amount = float(income_match.group(1))
            description = income_match.group(2).strip() if income_match.group(2) else ""
            return self.expense.log_income(amount, description)
        
        # Set budget
        budget_match = re.search(r"set\s+(.+?)\s+budget\s+(?:to\s+)?\$?(\d+)", text, re.IGNORECASE)
        if budget_match:
            category = budget_match.group(1).strip()
            limit = float(budget_match.group(2))
            return self.expense.set_budget(category, limit)
        
        # Budget status
        if "budget status" in text or "budget" in text:
            return self.expense.get_budget_status()
        
        # Weekly spending
        if "week" in text:
            return self.expense.get_weekly_summary()
        
        # How much spent
        if "how much" in text and "spend" in text:
            if "week" in text:
                return self.expense.get_weekly_summary()
            return self.expense.get_budget_status()
        
        # Spending by category
        if "category" in text or "breakdown" in text:
            spending = self.expense.get_spending_by_category()
            lines = ["💰 **Spending by Category (30 days)**\n"]
            for cat, amount in sorted(spending.items(), key=lambda x: x[1], reverse=True):
                lines.append(f"  • {cat.title()}: ${amount:.2f}")
            return "\n".join(lines)
        
        # Compare to last month
        if "compare" in text or "last month" in text:
            return self.expense.compare_to_last_month()
        
        return self.expense.get_budget_status()
    
    def _handle_notion(self, text: str, original: str) -> str:
        """Handle Notion commands."""
        # Open Notion
        if text == "open notion" or "open notion" in text and "page" not in text:
            return self.notion.open_notion()
        
        # Open specific page
        open_match = re.search(r"open\s+(?:my\s+)?(.+?)\s+(?:in\s+)?notion", text, re.IGNORECASE)
        if open_match:
            page_name = open_match.group(1).strip()
            return self.notion.open_page(page_name)
        
        # Save page
        save_match = re.search(r"save\s+notion\s+page[:\s]+(.+?)\s+(?:at|url)[:\s]+(.+)", text, re.IGNORECASE)
        if save_match:
            name = save_match.group(1).strip()
            url = save_match.group(2).strip()
            return self.notion.save_page(name, url)
        
        # List pages
        if "notion pages" in text or "my notion" in text or "show notion" in text:
            return self.notion.list_pages()
        
        # Search (if API available)
        search_match = re.search(r"search\s+notion\s+(?:for\s+)?(.+)", text, re.IGNORECASE)
        if search_match:
            query = search_match.group(1).strip()
            return self.notion.search_notion(query)
        
        return self.notion.list_pages()
    
    def _handle_networking(self, text: str, original: str) -> str:
        """Handle networking commands."""
        # Add contact
        contact_match = re.search(r"(?:add\s+contact|met)[:\s]+(.+)", text, re.IGNORECASE)
        if contact_match:
            details = contact_match.group(1).strip()
            
            # Parse details
            name = details
            company = ""
            role = ""
            how_met = ""
            contact_type = "other"
            
            # Try to extract structured info
            # "Met Sarah at career fair, Google recruiter"
            parts = re.split(r",\s*", details)
            if len(parts) >= 1:
                name_part = parts[0]
                # Extract "at [event]"
                at_match = re.search(r"(.+?)\s+at\s+(.+)", name_part)
                if at_match:
                    name = at_match.group(1).strip()
                    how_met = at_match.group(2).strip()
                else:
                    name = name_part.strip()
            
            if len(parts) >= 2:
                # Could be "Google recruiter" or "recruiter at Google"
                company_role = parts[1].strip()
                role_match = re.search(r"(.+?)\s+(?:at|from)\s+(.+)", company_role)
                if role_match:
                    role = role_match.group(1).strip()
                    company = role_match.group(2).strip()
                else:
                    # Check if it's "Company Role" format
                    words = company_role.split()
                    if len(words) >= 2:
                        company = words[0]
                        role = " ".join(words[1:])
                    else:
                        company = company_role
                
                # Detect contact type
                role_lower = role.lower()
                if "recruiter" in role_lower:
                    contact_type = "recruiter"
                elif "professor" in role_lower or "prof" in role_lower:
                    contact_type = "professor"
                elif "ta" in role_lower:
                    contact_type = "ta"
            
            contact = self.networking.add_contact(
                name=name,
                company=company,
                role=role,
                contact_type=contact_type,
                how_met=how_met,
            )
            
            return f"✅ Added contact!\n\n**{contact.name}**\n{contact.role}{' @ ' if contact.role and contact.company else ''}{contact.company}\nMet: {contact.how_met or 'Not specified'}"
        
        # Add note
        note_match = re.search(r"add\s+note\s+(?:for|to)\s+(.+?)[:\s]+(.+)", text, re.IGNORECASE)
        if note_match:
            contact_name = note_match.group(1).strip()
            note = note_match.group(2).strip()
            return self.networking.add_note(contact_name, note)
        
        # Set follow-up reminder
        reminder_match = re.search(r"(?:set\s+)?reminder\s+(?:to\s+)?(?:email|contact|follow up with)\s+(.+?)(?:\s+(?:in|next)\s+(\d+)\s+(?:day|week))?", text, re.IGNORECASE)
        if reminder_match:
            contact_name = reminder_match.group(1).strip()
            days = 7
            if reminder_match.group(2):
                days = int(reminder_match.group(2))
                if "week" in text:
                    days *= 7
            return self.networking.set_follow_up(contact_name, days)
        
        # Who to follow up with
        if "follow up" in text or "who should i" in text:
            contacts = self.networking.get_follow_ups()
            return self.networking.format_follow_ups(contacts)
        
        # Show network
        if "my network" in text or "show contacts" in text:
            contacts = self.networking.get_contacts()
            return self.networking.format_contacts(contacts)
        
        # Network stats
        if "stats" in text:
            return self.networking.get_stats()
        
        return self.networking.get_stats()
    
    def _handle_journal(self, text: str, original: str) -> str:
        """Handle voice journal commands."""
        # Add journal entry
        entry_match = re.search(r"journal[:\s]+(.+)", text, re.IGNORECASE)
        if entry_match:
            content = entry_match.group(1).strip()
            entry = self.journal.add_entry(content)
            
            mood_str = f" Mood: {entry.mood.value}" if entry.mood else ""
            return f"📔 Journal entry saved!{mood_str}"
        
        # Grateful for
        grateful_match = re.search(r"(?:i'm\s+)?grateful\s+(?:for\s+)?(.+)", text, re.IGNORECASE)
        if grateful_match:
            content = f"Grateful for: {grateful_match.group(1).strip()}"
            entry = self.journal.add_entry(content, mood="good")
            return "📔 Gratitude logged! 🙏"
        
        # Today's journal
        if "today's journal" in text or "today journal" in text:
            entries = self.journal.get_today_entries()
            if entries:
                return self.journal.format_entries(entries)
            prompt = self.journal.get_daily_prompt()
            return f"No entries today yet.\n\n💭 **Daily Prompt:** {prompt}"
        
        # Journal entries this week
        if "week" in text:
            entries = self.journal.get_recent_entries(7)
            return self.journal.format_entries(entries)
        
        # Search journal
        search_match = re.search(r"search\s+journal\s+(?:for\s+)?(.+)", text, re.IGNORECASE)
        if search_match:
            query = search_match.group(1).strip()
            entries = self.journal.search_entries(query)
            return self.journal.format_entries(entries)
        
        # Mood summary
        if "mood" in text:
            return self.journal.get_mood_summary()
        
        # Journal stats
        if "stats" in text:
            return self.journal.get_stats()
        
        # Daily prompt
        if "prompt" in text or "reflect" in text:
            prompt = self.journal.get_daily_prompt()
            return f"💭 **Daily Prompt:**\n\n{prompt}"
        
        # Default: show recent + prompt
        entries = self.journal.get_today_entries()
        if entries:
            return self.journal.format_entries(entries)
        
        prompt = self.journal.get_daily_prompt()
        streak = self.journal.get_streak()
        return f"📔 **Voice Journal**\n\n🔥 Current streak: {streak} days\n\n💭 **Today's Prompt:** {prompt}\n\nSay 'journal: [your thoughts]' to add an entry."
    
    def _handle_learning(self, text: str, original: str) -> str:
        """Handle learning path commands."""
        # Create learning path
        create_match = re.search(r"(?:create|start)\s+(?:learning\s+)?path\s+(?:for\s+)?(.+)", text, re.IGNORECASE)
        if create_match:
            topic = create_match.group(1).strip()
            
            # Check if it matches a template
            templates = self.learning.get_available_templates()
            template_match = None
            for t in templates:
                if t.replace("_", " ") in topic.lower() or topic.lower() in t.replace("_", " "):
                    template_match = t
                    break
            
            if template_match:
                path = self.learning.create_path(topic, template=template_match)
                return f"✅ Created learning path!\n\n{self.learning.format_path(path)}"
            else:
                path = self.learning.create_path(topic, goal=f"Learn {topic}")
                return f"✅ Created custom learning path: {topic}\n\nAdd items with 'add to {topic} path: [item name]'"
        
        # Complete item
        complete_match = re.search(r"(?:i\s+)?completed?\s+(.+?)(?:\s+in\s+(.+)\s+path)?", text, re.IGNORECASE)
        if complete_match and "path" in text:
            item_name = complete_match.group(1).strip()
            path_name = complete_match.group(2).strip() if complete_match.group(2) else None
            
            if not path_name:
                # Try to find active path
                paths = self.learning.get_all_paths()
                if paths:
                    path_name = paths[0].name
            
            if path_name:
                return self.learning.complete_item(path_name, item_name)
            return "Please specify which learning path."
        
        # What's next
        next_match = re.search(r"(?:what's\s+)?next\s+(?:in\s+)?(?:my\s+)?(.+?)(?:\s+path)?$", text, re.IGNORECASE)
        if next_match or "what should i learn" in text:
            if next_match:
                path_name = next_match.group(1).strip()
            else:
                paths = self.learning.get_all_paths()
                if paths:
                    path_name = paths[0].name
                else:
                    return "No learning paths yet. Create one with 'create learning path for [topic]'"
            
            return self.learning.get_next_item(path_name)
        
        # Add item to path
        add_match = re.search(r"add\s+(?:to\s+)?(.+?)\s+path[:\s]+(.+)", text, re.IGNORECASE)
        if add_match:
            path_name = add_match.group(1).strip()
            item_name = add_match.group(2).strip()
            return self.learning.add_item(path_name, item_name)
        
        # Learning progress / list paths
        if "progress" in text or "my learning" in text or "learning path" in text:
            return self.learning.list_paths()
        
        return self.learning.list_paths()
    
    # =========================================================================
    # Briefing Integration
    # =========================================================================
    
    def get_career_briefing(self) -> str:
        """Get career-related items for daily briefing."""
        lines = []
        
        # Upcoming application deadlines
        deadlines = self.applications.get_upcoming_deadlines(days=7)
        if deadlines:
            lines.append("💼 **Application Deadlines:**")
            for app in deadlines[:3]:
                days_left = (app.deadline - date.today()).days
                lines.append(f"  • {app.company}: {days_left} days")
        
        # Follow-up reminders
        follow_ups = self.networking.get_follow_ups()
        if follow_ups:
            lines.append("\n🤝 **Follow Up With:**")
            for contact in follow_ups[:3]:
                lines.append(f"  • {contact.name} ({contact.company})")
        
        # Budget status
        monthly_spent = self.expense.get_monthly_spending()
        budget = self.expense.monthly_budget
        remaining = budget - monthly_spent
        if remaining < budget * 0.2:
            lines.append(f"\n💰 **Budget Alert:** ${remaining:.0f} remaining this month")
        
        # Journal streak
        streak = self.journal.get_streak()
        if streak > 0:
            lines.append(f"\n📔 Journal streak: {streak} days 🔥")
        
        return "\n".join(lines) if lines else ""
    
    def get_daily_interview_question(self) -> str:
        """Get a daily interview question for briefing."""
        q = self.interview.get_random_question()
        if q:
            return f"📝 **Daily Interview Question:**\n\n{q.title} ({q.difficulty.value})\n\nSay 'interview practice' to start!"
        return ""
