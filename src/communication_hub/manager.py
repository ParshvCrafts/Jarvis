"""
Communication Hub Manager for JARVIS.

Main orchestrator for emails, meetings, and LinkedIn content.
"""

import os
import re
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from .models import (
    EmailTemplate, EmailDraft, EmailCategory,
    Meeting, MeetingType, MeetingPreferences, TimeSlot,
    LinkedInContent, LinkedInContentType, ContactInfo,
    EMAIL_TEMPLATES, LINKEDIN_TEMPLATES
)


@dataclass
class CommunicationConfig:
    """Configuration for communication hub."""
    db_path: str = "data/communication.db"
    
    # User info
    user_name: str = "Parshv"
    user_email: str = ""
    user_university: str = "UC Berkeley"
    user_major: str = "Data Science"
    user_year: str = "Freshman"
    
    # Email settings
    email_signature: str = "Best,\nParshv"
    
    # Meeting settings
    meeting_duration_default: int = 30
    meeting_buffer: int = 15
    
    # LinkedIn
    linkedin_reminder: bool = True


class CommunicationManager:
    """
    Main manager for communication functionality.
    
    Features:
    - Email template generation
    - Meeting scheduling assistance
    - LinkedIn content generation
    - Contact management
    - Email summarization
    """
    
    def __init__(
        self,
        config: Optional[CommunicationConfig] = None,
        llm_router: Optional[Any] = None,
    ):
        self.config = config or CommunicationConfig()
        self.llm_router = llm_router
        
        # Initialize database
        self._init_db()
        
        logger.info("Communication Manager initialized")
    
    def _init_db(self):
        """Initialize SQLite database."""
        Path(self.config.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.config.db_path)
        cursor = conn.cursor()
        
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS email_drafts (
                id TEXT PRIMARY KEY,
                to_address TEXT,
                cc TEXT,
                subject TEXT,
                body TEXT,
                context TEXT,
                template_used TEXT,
                sent INTEGER DEFAULT 0,
                sent_at TEXT,
                created_at TEXT
            );
            
            CREATE TABLE IF NOT EXISTS meetings (
                id TEXT PRIMARY KEY,
                title TEXT,
                description TEXT,
                meeting_type TEXT,
                date TEXT,
                start_time TEXT,
                end_time TEXT,
                duration_minutes INTEGER,
                attendees TEXT,
                location TEXT,
                is_virtual INTEGER,
                confirmed INTEGER DEFAULT 0,
                notes TEXT,
                created_at TEXT
            );
            
            CREATE TABLE IF NOT EXISTS linkedin_content (
                id TEXT PRIMARY KEY,
                content_type TEXT,
                content TEXT,
                recipient TEXT,
                posted INTEGER DEFAULT 0,
                posted_at TEXT,
                created_at TEXT
            );
            
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                email TEXT,
                phone TEXT,
                linkedin TEXT,
                company TEXT,
                title TEXT,
                notes TEXT,
                last_contacted TEXT,
                created_at TEXT
            );
            
            CREATE INDEX IF NOT EXISTS idx_drafts_date ON email_drafts(created_at);
            CREATE INDEX IF NOT EXISTS idx_meetings_date ON meetings(date);
        """)
        
        conn.commit()
        conn.close()
    
    # =========================================================================
    # Email Generation
    # =========================================================================
    
    def generate_thank_you_email(
        self,
        company: str,
        interviewer_name: str = "[Interviewer Name]",
        position: str = "the position",
        topic_discussed: str = "[specific topic]",
    ) -> EmailDraft:
        """Generate a thank you email after an interview."""
        template = EMAIL_TEMPLATES["interview_thank_you"]
        
        body = template.body.format(
            interviewer_name=interviewer_name,
            position=position,
            topic_discussed=topic_discussed,
            challenge_mentioned="[challenge mentioned]",
            relevant_skill="[your relevant skill]",
            area_discussed="[area discussed]",
            your_name=self.config.user_name,
        )
        
        subject = template.subject.format(position=position)
        
        draft = EmailDraft(
            subject=subject,
            body=body,
            context=f"Interview thank you for {company}",
            template_used="interview_thank_you",
        )
        
        self._save_draft(draft)
        return draft
    
    def generate_follow_up_email(
        self,
        company: str,
        position: str = "the position",
        application_date: str = "[date]",
        recipient_name: str = "Hiring Manager",
    ) -> EmailDraft:
        """Generate a follow-up email for an application."""
        template = EMAIL_TEMPLATES["follow_up"]
        
        body = template.body.format(
            recipient_name=recipient_name,
            position=position,
            application_date=application_date,
            company=company,
            relevant_skill="[your relevant skill]",
            your_name=self.config.user_name,
        )
        
        subject = template.subject.format(position=position)
        
        draft = EmailDraft(
            subject=subject,
            body=body,
            context=f"Follow-up for {company} application",
            template_used="follow_up",
        )
        
        self._save_draft(draft)
        return draft
    
    def generate_networking_email(
        self,
        recipient_name: str,
        their_work: str = "[their research/work]",
        specific_aspect: str = "[specific aspect]",
    ) -> EmailDraft:
        """Generate a cold networking email."""
        template = EMAIL_TEMPLATES["networking_cold"]
        
        body = template.body.format(
            recipient_name=recipient_name,
            year=self.config.user_year,
            major=self.config.user_major,
            university=self.config.user_university,
            how_you_found_them="read your paper on [topic]",
            their_work=their_work,
            your_project="[your project]",
            specific_aspect=specific_aspect,
            your_name=self.config.user_name,
        )
        
        subject = template.subject.format(university=self.config.user_university)
        
        draft = EmailDraft(
            subject=subject,
            body=body,
            context=f"Networking email to {recipient_name}",
            template_used="networking_cold",
        )
        
        self._save_draft(draft)
        return draft
    
    def generate_meeting_request_email(
        self,
        recipient_name: str,
        topic: str,
        suggested_times: str = "next week",
    ) -> EmailDraft:
        """Generate a meeting request email."""
        template = EMAIL_TEMPLATES["meeting_request"]
        
        body = template.body.format(
            recipient_name=recipient_name,
            topic=topic,
            suggested_times=suggested_times,
            duration=self.config.meeting_duration_default,
            your_name=self.config.user_name,
        )
        
        subject = template.subject.format(topic=topic)
        
        draft = EmailDraft(
            subject=subject,
            body=body,
            context=f"Meeting request with {recipient_name}",
            template_used="meeting_request",
        )
        
        self._save_draft(draft)
        return draft
    
    def _save_draft(self, draft: EmailDraft):
        """Save email draft to database."""
        conn = sqlite3.connect(self.config.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO email_drafts
            (id, to_address, cc, subject, body, context, template_used, sent, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            draft.id,
            draft.to,
            draft.cc,
            draft.subject,
            draft.body,
            draft.context,
            draft.template_used,
            0,
            datetime.now().isoformat(),
        ))
        
        conn.commit()
        conn.close()
    
    def get_drafts(self, limit: int = 10) -> List[Dict]:
        """Get recent email drafts."""
        conn = sqlite3.connect(self.config.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM email_drafts WHERE sent = 0 ORDER BY created_at DESC LIMIT ?
        """, (limit,))
        
        columns = [desc[0] for desc in cursor.description]
        drafts = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return drafts
    
    # =========================================================================
    # Meeting Scheduling
    # =========================================================================
    
    def get_available_slots(
        self,
        days_ahead: int = 7,
        duration: int = 30,
    ) -> List[TimeSlot]:
        """
        Get available time slots for meetings.
        
        This is a simplified version - in production, would integrate with
        Google Calendar API.
        """
        slots = []
        today = date.today()
        
        # Default available times (would come from calendar in production)
        default_times = [
            (time(10, 0), time(12, 0)),
            (time(14, 0), time(16, 0)),
        ]
        
        for day_offset in range(1, days_ahead + 1):
            check_date = today + timedelta(days=day_offset)
            
            # Skip weekends
            if check_date.weekday() >= 5:
                continue
            
            for start, end in default_times:
                # Create slots within this time range
                current = datetime.combine(check_date, start)
                end_dt = datetime.combine(check_date, end)
                
                while current + timedelta(minutes=duration) <= end_dt:
                    slot = TimeSlot(
                        date=check_date,
                        start_time=current.time(),
                        end_time=(current + timedelta(minutes=duration)).time(),
                    )
                    slots.append(slot)
                    current += timedelta(minutes=duration + self.config.meeting_buffer)
        
        return slots[:10]  # Return first 10 slots
    
    def format_availability(self, days_ahead: int = 7) -> str:
        """Format availability as a readable message."""
        slots = self.get_available_slots(days_ahead)
        
        if not slots:
            return "No available slots found."
        
        # Group by day
        by_day = {}
        for slot in slots:
            day_str = slot.date.strftime("%A, %b %d")
            if day_str not in by_day:
                by_day[day_str] = []
            by_day[day_str].append(f"{slot.start_time.strftime('%I:%M %p')}")
        
        lines = ["📅 **Your Availability:**", ""]
        for day, times in by_day.items():
            lines.append(f"**{day}:** {', '.join(times)}")
        
        return "\n".join(lines)
    
    def create_meeting(
        self,
        title: str,
        attendee: str,
        meeting_date: date,
        start_time: time,
        duration: int = 30,
        meeting_type: str = "one_on_one",
    ) -> Meeting:
        """Create a meeting."""
        type_map = {
            "one_on_one": MeetingType.ONE_ON_ONE,
            "interview": MeetingType.INTERVIEW,
            "coffee": MeetingType.COFFEE_CHAT,
            "office_hours": MeetingType.OFFICE_HOURS,
            "video": MeetingType.VIDEO_CALL,
            "phone": MeetingType.PHONE_CALL,
        }
        
        meeting = Meeting(
            title=title,
            meeting_type=type_map.get(meeting_type, MeetingType.ONE_ON_ONE),
            date=meeting_date,
            start_time=start_time,
            duration_minutes=duration,
            attendees=[attendee],
        )
        
        self._save_meeting(meeting)
        return meeting
    
    def _save_meeting(self, meeting: Meeting):
        """Save meeting to database."""
        conn = sqlite3.connect(self.config.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO meetings
            (id, title, description, meeting_type, date, start_time, duration_minutes,
             attendees, location, is_virtual, confirmed, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            meeting.id,
            meeting.title,
            meeting.description,
            meeting.meeting_type.value,
            meeting.date.isoformat() if meeting.date else None,
            meeting.start_time.isoformat() if meeting.start_time else None,
            meeting.duration_minutes,
            ",".join(meeting.attendees),
            meeting.location,
            1 if meeting.is_virtual else 0,
            1 if meeting.confirmed else 0,
            meeting.notes,
            datetime.now().isoformat(),
        ))
        
        conn.commit()
        conn.close()
    
    def get_upcoming_meetings(self, days: int = 7) -> List[Dict]:
        """Get upcoming meetings."""
        conn = sqlite3.connect(self.config.db_path)
        cursor = conn.cursor()
        
        today = date.today().isoformat()
        future = (date.today() + timedelta(days=days)).isoformat()
        
        cursor.execute("""
            SELECT * FROM meetings 
            WHERE date BETWEEN ? AND ? 
            ORDER BY date, start_time
        """, (today, future))
        
        columns = [desc[0] for desc in cursor.description]
        meetings = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return meetings
    
    # =========================================================================
    # LinkedIn Content
    # =========================================================================
    
    def generate_connection_request(
        self,
        name: str,
        company: str,
        role: str = "recruiter",
        focus_area: str = "new grad roles",
    ) -> LinkedInContent:
        """Generate a LinkedIn connection request message."""
        if role.lower() == "recruiter":
            template = LINKEDIN_TEMPLATES["connection_recruiter"]
        else:
            template = LINKEDIN_TEMPLATES["connection_professional"]
        
        content = template.format(
            name=name,
            company=company,
            focus_area=focus_area,
            major=self.config.user_major,
            university=self.config.user_university,
            interest="AI and machine learning",
            your_name=self.config.user_name,
        )
        
        linkedin_content = LinkedInContent(
            content_type=LinkedInContentType.CONNECTION_REQUEST,
            content=content,
            recipient=name,
            recipient_company=company,
        )
        
        self._save_linkedin_content(linkedin_content)
        return linkedin_content
    
    def generate_post_ideas(self) -> List[str]:
        """Generate LinkedIn post ideas."""
        ideas = [
            "📝 **Project Update**\n"
            "'Excited to share my latest project: [project name]! "
            "Key learnings: [insight]. #DataScience #MachineLearning'",
            
            "💡 **Industry Insight**\n"
            "'Interesting trend in AI: [trend]. "
            "What do you think? #AI #TechTrends'",
            
            "❓ **Ask the Network**\n"
            "'Data scientists: What's your favorite Python library for [task]? "
            "Looking for recommendations! #Python'",
            
            "📚 **Learning Share**\n"
            "'Just completed [course/certification]. "
            "Here are my top 3 takeaways: [insights]. #Learning #Growth'",
            
            "🎯 **Career Milestone**\n"
            "'Excited to announce [achievement]! "
            "Grateful for [acknowledgment]. #CareerGrowth'",
        ]
        
        return ideas
    
    def generate_project_post(
        self,
        project_name: str,
        project_description: str,
        learnings: List[str],
        project_link: str = "",
    ) -> LinkedInContent:
        """Generate a LinkedIn post about a project."""
        template = LINKEDIN_TEMPLATES["post_project"]
        
        content = template.format(
            project_name=project_name,
            project_description=project_description,
            learning_1=learnings[0] if len(learnings) > 0 else "Key learning 1",
            learning_2=learnings[1] if len(learnings) > 1 else "Key learning 2",
            learning_3=learnings[2] if len(learnings) > 2 else "Key learning 3",
            project_link=project_link or "[link]",
        )
        
        linkedin_content = LinkedInContent(
            content_type=LinkedInContentType.POST,
            content=content,
        )
        
        self._save_linkedin_content(linkedin_content)
        return linkedin_content
    
    def _save_linkedin_content(self, content: LinkedInContent):
        """Save LinkedIn content to database."""
        conn = sqlite3.connect(self.config.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO linkedin_content
            (id, content_type, content, recipient, posted, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            content.id,
            content.content_type.value,
            content.content,
            content.recipient,
            0,
            datetime.now().isoformat(),
        ))
        
        conn.commit()
        conn.close()
    
    # =========================================================================
    # Email Summarization
    # =========================================================================
    
    async def summarize_email_thread(self, thread_text: str) -> str:
        """Summarize an email thread using LLM."""
        if not self.llm_router:
            return "LLM not available for summarization."
        
        prompt = f"""Summarize this email thread concisely:

{thread_text}

Provide:
1. Topic (one line)
2. Key points (bullet points)
3. Action items (if any)
4. Deadline (if mentioned)"""

        try:
            response = await self.llm_router.generate(prompt)
            return response
        except Exception as e:
            logger.error(f"Email summarization failed: {e}")
            return "Failed to summarize email thread."
    
    # =========================================================================
    # Voice Command Handler
    # =========================================================================
    
    async def handle_command(self, command: str) -> str:
        """Handle voice commands for communication."""
        command_lower = command.lower()
        
        # Thank you email
        if "thank you" in command_lower and "email" in command_lower:
            company_match = re.search(r'for\s+(\w+)', command_lower)
            company = company_match.group(1).title() if company_match else "Company"
            
            draft = self.generate_thank_you_email(company)
            return self._format_email_draft(draft)
        
        # Follow-up email
        if "follow" in command_lower and "up" in command_lower:
            company_match = re.search(r'(?:for|with)\s+(\w+)', command_lower)
            company = company_match.group(1).title() if company_match else "Company"
            
            draft = self.generate_follow_up_email(company)
            return self._format_email_draft(draft)
        
        # Networking email
        if "networking" in command_lower or "cold email" in command_lower:
            name_match = re.search(r'to\s+([A-Za-z\s]+?)(?:\s+at|\s*$)', command_lower)
            name = name_match.group(1).strip().title() if name_match else "Professor"
            
            draft = self.generate_networking_email(name)
            return self._format_email_draft(draft)
        
        # Meeting request email
        if "meeting" in command_lower and "email" in command_lower:
            name_match = re.search(r'with\s+([A-Za-z\s]+?)(?:\s+about|\s*$)', command_lower)
            name = name_match.group(1).strip().title() if name_match else "Recipient"
            
            topic_match = re.search(r'about\s+(.+)', command_lower)
            topic = topic_match.group(1).strip() if topic_match else "our discussion"
            
            draft = self.generate_meeting_request_email(name, topic)
            return self._format_email_draft(draft)
        
        # Availability
        if "free" in command_lower or "available" in command_lower or "availability" in command_lower:
            return self.format_availability()
        
        # LinkedIn connection
        if "linkedin" in command_lower and ("message" in command_lower or "connection" in command_lower):
            company_match = re.search(r'(?:at|from)\s+(\w+)', command_lower)
            company = company_match.group(1).title() if company_match else "Company"
            
            content = self.generate_connection_request("Name", company)
            return self._format_linkedin_content(content)
        
        # LinkedIn post ideas
        if "linkedin" in command_lower and ("post" in command_lower or "idea" in command_lower):
            ideas = self.generate_post_ideas()
            lines = ["📝 **LinkedIn Post Ideas:**", ""]
            lines.extend(ideas[:3])
            return "\n\n".join(lines)
        
        # Upcoming meetings
        if "upcoming" in command_lower and "meeting" in command_lower:
            meetings = self.get_upcoming_meetings()
            if not meetings:
                return "No upcoming meetings scheduled."
            
            lines = ["📅 **Upcoming Meetings:**", ""]
            for m in meetings[:5]:
                lines.append(f"  • {m['title']} - {m['date']}")
            return "\n".join(lines)
        
        # Drafts
        if "draft" in command_lower:
            drafts = self.get_drafts()
            if not drafts:
                return "No email drafts saved."
            
            lines = ["📧 **Email Drafts:**", ""]
            for d in drafts[:5]:
                lines.append(f"  • {d['subject']} ({d['context']})")
            return "\n".join(lines)
        
        return (
            "Communication commands:\n"
            "  - 'Thank you email for Google interview'\n"
            "  - 'Follow up email for Amazon'\n"
            "  - 'Networking email to Professor Smith'\n"
            "  - 'When am I free this week?'\n"
            "  - 'LinkedIn message for Google recruiter'\n"
            "  - 'LinkedIn post ideas'"
        )
    
    def _format_email_draft(self, draft: EmailDraft) -> str:
        """Format email draft for display."""
        lines = [
            "📧 **Email Draft:**",
            "",
            f"**Subject:** {draft.subject}",
            "",
            "---",
            draft.body,
            "---",
            "",
            f"*Context: {draft.context}*",
            "",
            "💡 Replace [bracketed text] with your specific details.",
        ]
        
        return "\n".join(lines)
    
    def _format_linkedin_content(self, content: LinkedInContent) -> str:
        """Format LinkedIn content for display."""
        lines = [
            f"💼 **LinkedIn {content.content_type.value.replace('_', ' ').title()}:**",
            "",
            "---",
            content.content,
            "---",
            "",
            "💡 Personalize before sending!",
        ]
        
        return "\n".join(lines)
    
    # =========================================================================
    # Status
    # =========================================================================
    
    def get_status(self) -> Dict[str, Any]:
        """Get communication hub status."""
        drafts = len(self.get_drafts(limit=100))
        meetings = len(self.get_upcoming_meetings())
        
        return {
            "drafts_pending": drafts,
            "upcoming_meetings": meetings,
            "templates_available": len(EMAIL_TEMPLATES),
        }
    
    def get_status_summary(self) -> str:
        """Get formatted status summary."""
        status = self.get_status()
        
        lines = [
            "📧 **Communication Hub Status**",
            "",
            f"📝 Pending drafts: {status['drafts_pending']}",
            f"📅 Upcoming meetings: {status['upcoming_meetings']}",
            f"📋 Templates available: {status['templates_available']}",
        ]
        
        return "\n".join(lines)
