"""
Data models for JARVIS Communication Hub Module.

Defines structures for emails, meetings, and LinkedIn content.
"""

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional


class EmailCategory(Enum):
    """Email template category."""
    THANK_YOU = "thank_you"
    FOLLOW_UP = "follow_up"
    NETWORKING = "networking"
    COLD_OUTREACH = "cold_outreach"
    MEETING_REQUEST = "meeting_request"
    INTRODUCTION = "introduction"
    PROFESSIONAL = "professional"


class MeetingType(Enum):
    """Type of meeting."""
    ONE_ON_ONE = "one_on_one"
    GROUP = "group"
    INTERVIEW = "interview"
    OFFICE_HOURS = "office_hours"
    COFFEE_CHAT = "coffee_chat"
    PHONE_CALL = "phone_call"
    VIDEO_CALL = "video_call"


class LinkedInContentType(Enum):
    """Type of LinkedIn content."""
    POST = "post"
    CONNECTION_REQUEST = "connection_request"
    MESSAGE = "message"
    COMMENT = "comment"


@dataclass
class EmailTemplate:
    """An email template."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    category: EmailCategory = EmailCategory.PROFESSIONAL
    
    subject: str = ""
    body: str = ""
    
    # Variables that need to be filled in
    variables: List[str] = field(default_factory=list)
    
    # Metadata
    usage_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,
            "subject": self.subject,
            "body": self.body,
            "variables": self.variables,
        }


@dataclass
class EmailDraft:
    """An email draft."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    to: str = ""
    cc: str = ""
    subject: str = ""
    body: str = ""
    
    # Status
    sent: bool = False
    sent_at: Optional[datetime] = None
    
    # Context
    context: str = ""  # e.g., "Interview follow-up for Google"
    template_used: Optional[str] = None
    
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "to": self.to,
            "subject": self.subject,
            "body": self.body,
            "sent": self.sent,
            "context": self.context,
        }


@dataclass
class TimeSlot:
    """A time slot for meetings."""
    date: date
    start_time: time
    end_time: time
    
    @property
    def duration_minutes(self) -> int:
        start = datetime.combine(self.date, self.start_time)
        end = datetime.combine(self.date, self.end_time)
        return int((end - start).total_seconds() / 60)
    
    def __str__(self) -> str:
        return f"{self.date.strftime('%A, %b %d')} {self.start_time.strftime('%I:%M %p')} - {self.end_time.strftime('%I:%M %p')}"


@dataclass
class Meeting:
    """A meeting."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    title: str = ""
    description: str = ""
    
    meeting_type: MeetingType = MeetingType.ONE_ON_ONE
    
    # Time
    date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    duration_minutes: int = 30
    
    # Participants
    organizer: str = ""
    attendees: List[str] = field(default_factory=list)
    
    # Location
    location: str = ""  # Physical location or video link
    is_virtual: bool = True
    
    # Status
    confirmed: bool = False
    cancelled: bool = False
    
    # Notes
    notes: str = ""
    agenda: List[str] = field(default_factory=list)
    
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "meeting_type": self.meeting_type.value,
            "date": self.date.isoformat() if self.date else None,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "duration_minutes": self.duration_minutes,
            "attendees": self.attendees,
            "location": self.location,
            "confirmed": self.confirmed,
        }


@dataclass
class MeetingPreferences:
    """User's meeting preferences."""
    preferred_times: List[str] = field(default_factory=lambda: ["10:00-12:00", "14:00-16:00"])
    duration_default: int = 30
    buffer_time: int = 15  # Minutes between meetings
    no_meeting_days: List[str] = field(default_factory=list)  # e.g., ["Friday"]
    timezone: str = "America/Los_Angeles"


@dataclass
class LinkedInContent:
    """LinkedIn content (post, message, etc.)."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    content_type: LinkedInContentType = LinkedInContentType.POST
    content: str = ""
    
    # For messages/connection requests
    recipient: str = ""
    recipient_title: str = ""
    recipient_company: str = ""
    
    # Status
    posted: bool = False
    posted_at: Optional[datetime] = None
    
    # Engagement (for posts)
    likes: int = 0
    comments: int = 0
    
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content_type": self.content_type.value,
            "content": self.content,
            "recipient": self.recipient,
            "posted": self.posted,
        }


@dataclass
class ContactInfo:
    """Contact information for communication."""
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None
    notes: str = ""
    last_contacted: Optional[datetime] = None


# Pre-built email templates
EMAIL_TEMPLATES = {
    "interview_thank_you": EmailTemplate(
        name="Interview Thank You",
        category=EmailCategory.THANK_YOU,
        subject="Thank You - {position} Interview",
        body="""Dear {interviewer_name},

Thank you for taking the time to speak with me today about the {position} position. I enjoyed learning about {topic_discussed} and how the team approaches {challenge_mentioned}.

Our conversation reinforced my enthusiasm for the role. My experience with {relevant_skill} aligns well with the team's focus on {area_discussed}.

Please don't hesitate to reach out if you need any additional information.

Best regards,
{your_name}""",
        variables=["interviewer_name", "position", "topic_discussed", "challenge_mentioned", "relevant_skill", "area_discussed", "your_name"],
    ),
    
    "follow_up": EmailTemplate(
        name="Application Follow-Up",
        category=EmailCategory.FOLLOW_UP,
        subject="Following Up - {position} Application",
        body="""Dear {recipient_name},

I hope this email finds you well. I wanted to follow up on my application for the {position} position submitted on {application_date}.

I remain very enthusiastic about the opportunity to contribute to {company}. My experience with {relevant_skill} aligns well with the role's requirements.

I would welcome the opportunity to discuss how my background could benefit the team.

Thank you for your consideration.

Best regards,
{your_name}""",
        variables=["recipient_name", "position", "application_date", "company", "relevant_skill", "your_name"],
    ),
    
    "networking_cold": EmailTemplate(
        name="Cold Networking Email",
        category=EmailCategory.COLD_OUTREACH,
        subject="{university} Student Interested in Your Work",
        body="""Dear {recipient_name},

I'm a {year} {major} student at {university}, and I recently {how_you_found_them}. Your work on {their_work} was fascinating.

I'm currently working on {your_project} and would love to learn more about {specific_aspect}. Would you have 15 minutes for a brief conversation?

Thank you for your time.

Best,
{your_name}""",
        variables=["recipient_name", "year", "major", "university", "how_you_found_them", "their_work", "your_project", "specific_aspect", "your_name"],
    ),
    
    "meeting_request": EmailTemplate(
        name="Meeting Request",
        category=EmailCategory.MEETING_REQUEST,
        subject="Meeting Request - {topic}",
        body="""Dear {recipient_name},

I hope this email finds you well. I would like to schedule a meeting to discuss {topic}.

Would you be available {suggested_times}? The meeting should take approximately {duration} minutes.

Please let me know what works best for your schedule.

Thank you,
{your_name}""",
        variables=["recipient_name", "topic", "suggested_times", "duration", "your_name"],
    ),
}

# LinkedIn templates
LINKEDIN_TEMPLATES = {
    "connection_recruiter": """Hi {name},

I noticed you're a recruiter at {company} focused on {focus_area}. I'm a {major} student at {university} passionate about {interest}, and I'd love to connect and learn more about opportunities at {company}.

Thank you!
{your_name}""",

    "connection_professional": """Hi {name},

I came across your profile and was impressed by your work at {company}. As a {major} student interested in {interest}, I'd love to connect and learn from your experience.

Best,
{your_name}""",

    "post_project": """Excited to share my latest project: {project_name}! 🚀

{project_description}

Key learnings:
• {learning_1}
• {learning_2}
• {learning_3}

Check it out: {project_link}

#DataScience #MachineLearning #Python""",

    "post_insight": """Interesting trend in {topic}: {insight}

What I've observed:
• {observation_1}
• {observation_2}

What do you think? I'd love to hear your perspectives.

#{hashtag_1} #{hashtag_2}""",
}
