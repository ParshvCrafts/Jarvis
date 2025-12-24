"""
Test script for Phase 3 Career & Advanced Intelligence Features.
Run with: python tests/test_career.py
"""

import asyncio
import sys
sys.path.insert(0, '.')

from src.career import (
    CareerManager,
    InterviewPrep,
    ResumeTracker,
    ApplicationTracker,
    ExpenseTracker,
    NotionIntegration,
    NetworkingTracker,
    VoiceJournal,
    LearningPathGenerator,
)


async def test_career_features():
    """Test all career features."""
    print("=" * 60)
    print("Phase 3: Career & Advanced Intelligence - Tests")
    print("=" * 60)
    
    # Test 1: Interview Prep
    print("\n[Test 1] Interview Prep Mode")
    interview = InterviewPrep(data_dir='data/test')
    
    # Get coding question
    q = interview.get_coding_question("easy")
    print(f"  ✓ Coding question: {q[:50]}...")
    
    # Get ML question
    q = interview.get_ml_question()
    print(f"  ✓ ML question: {q[:50]}...")
    
    # Get hint
    hint = interview.get_hint()
    print(f"  ✓ Hint: {hint[:50]}...")
    
    # Get stats
    stats = interview.get_stats()
    print(f"  ✓ Stats available")
    
    # Test 2: Resume Tracker
    print("\n[Test 2] Resume/Experience Tracker")
    resume = ResumeTracker(data_dir='data/test', name="Test User", university="UC Berkeley")
    
    # Add experience
    exp = resume.add_experience(
        title="Sentiment Analysis Project",
        exp_type="project",
        description="Built a sentiment analysis model using PyTorch",
        skills=["Python", "PyTorch", "NLP"],
        impact="Achieved 92% accuracy"
    )
    print(f"  ✓ Added experience: {exp.title}")
    
    # Add skill
    skill = resume.add_skill("Python", category="programming", level="advanced")
    print(f"  ✓ Added skill: {skill.name}")
    
    # Get summary
    summary = resume.get_resume_summary()
    print(f"  ✓ Resume summary available")
    
    # Test 3: Application Tracker
    print("\n[Test 3] Job Application Tracker")
    apps = ApplicationTracker(data_dir='data/test')
    
    # Add application
    app = apps.add_application(
        company="Google",
        position="STEP Intern",
        status="applied"
    )
    print(f"  ✓ Added application: {app.company} - {app.position}")
    
    # Update status
    result = apps.update_status("Google", "phone_screen")
    print(f"  ✓ Updated status: {result[:40]}...")
    
    # Get stats
    stats = apps.get_stats()
    print(f"  ✓ Application stats available")
    
    # Test 4: Expense Tracker
    print("\n[Test 4] Expense Tracker")
    expense = ExpenseTracker(data_dir='data/test', monthly_budget=1000)
    
    # Log expense
    result = expense.log_expense(15.50, "lunch at Chipotle")
    print(f"  ✓ Logged expense: {result[:40]}...")
    
    # Log income
    result = expense.log_income(500, "tutoring")
    print(f"  ✓ Logged income: {result[:40]}...")
    
    # Budget status
    status = expense.get_budget_status()
    print(f"  ✓ Budget status available")
    
    # Test 5: Notion Integration
    print("\n[Test 5] Notion Integration")
    notion = NotionIntegration(data_dir='data/test')
    
    # Save page
    result = notion.save_page("Class Notes", "https://notion.so/class-notes")
    print(f"  ✓ Saved page: {result}")
    
    # List pages
    pages = notion.list_pages()
    print(f"  ✓ Pages listed")
    
    # Test 6: Networking Tracker
    print("\n[Test 6] Networking Tracker")
    network = NetworkingTracker(data_dir='data/test')
    
    # Add contact
    contact = network.add_contact(
        name="Sarah Smith",
        company="Google",
        role="Recruiter",
        contact_type="recruiter",
        how_met="Career Fair"
    )
    print(f"  ✓ Added contact: {contact.name}")
    
    # Log interaction
    result = network.log_interaction("Sarah", "meeting", "Discussed ML interview tips")
    print(f"  ✓ Logged interaction: {result[:40]}...")
    
    # Get follow-ups
    follow_ups = network.get_follow_ups()
    print(f"  ✓ Follow-ups: {len(follow_ups)} contacts")
    
    # Test 7: Voice Journal
    print("\n[Test 7] Voice Journal")
    journal = VoiceJournal(data_dir='data/test')
    
    # Add entry
    entry = journal.add_entry("Today I learned about transformers and attention mechanisms. Feeling good about my progress!")
    print(f"  ✓ Added journal entry, mood: {entry.mood}")
    
    # Get prompt
    prompt = journal.get_daily_prompt()
    print(f"  ✓ Daily prompt: {prompt[:40]}...")
    
    # Get stats
    stats = journal.get_stats()
    print(f"  ✓ Journal stats available")
    
    # Test 8: Learning Path Generator
    print("\n[Test 8] Learning Path Generator")
    learning = LearningPathGenerator(data_dir='data/test')
    
    # Create path from template
    path = learning.create_path("ML Fundamentals", template="machine_learning")
    print(f"  ✓ Created path: {path.name} with {len(path.items)} items")
    
    # Get next item
    next_item = learning.get_next_item("ML Fundamentals")
    print(f"  ✓ Next item available")
    
    # List paths
    paths = learning.list_paths()
    print(f"  ✓ Paths listed")
    
    # Test 9: Career Manager Integration
    print("\n[Test 9] Career Manager (Command Routing)")
    manager = CareerManager(config={}, data_dir='data/test')
    
    # Test command detection
    test_commands = [
        ("give me a coding question", "interview"),
        ("add experience: Built ML model", "resume"),
        ("applied to Meta", "application"),
        ("spent $20 on lunch", "expense"),
        ("open notion", "notion"),
        ("add contact: Met John at hackathon", "networking"),
        ("journal: Today was productive", "journal"),
        ("create learning path for NLP", "learning"),
    ]
    
    passed = 0
    for cmd, expected_type in test_commands:
        # Check if command is detected
        is_interview = manager._is_interview_command(cmd)
        is_resume = manager._is_resume_command(cmd)
        is_app = manager._is_application_command(cmd)
        is_expense = manager._is_expense_command(cmd)
        is_notion = manager._is_notion_command(cmd)
        is_network = manager._is_networking_command(cmd)
        is_journal = manager._is_journal_command(cmd)
        is_learning = manager._is_learning_command(cmd)
        
        detected = {
            "interview": is_interview,
            "resume": is_resume,
            "application": is_app,
            "expense": is_expense,
            "notion": is_notion,
            "networking": is_network,
            "journal": is_journal,
            "learning": is_learning,
        }
        
        if detected.get(expected_type):
            passed += 1
            print(f"  ✓ '{cmd[:30]}...' -> {expected_type}")
        else:
            print(f"  ✗ '{cmd[:30]}...' -> expected {expected_type}")
    
    print(f"  Result: {passed}/{len(test_commands)} commands detected correctly")
    
    # Test 10: Command Handling
    print("\n[Test 10] Command Handling")
    
    # Test interview command
    result = await manager.handle_command("give me a coding question")
    print(f"  ✓ Interview: {result[:50] if result else 'None'}...")
    
    # Test expense command
    result = await manager.handle_command("budget status")
    print(f"  ✓ Expense: {result[:50] if result else 'None'}...")
    
    # Test journal command
    result = await manager.handle_command("journal: Testing the journal feature")
    print(f"  ✓ Journal: {result[:50] if result else 'None'}...")
    
    print("\n" + "=" * 60)
    print("✅ Phase 3 Career Features Tests Complete!")
    print("=" * 60)
    
    # Voice commands summary
    print("\n📢 New Voice Commands Available:")
    print("""
    Interview Prep:
      - "Give me a coding question" / "ML question" / "Behavioral question"
      - "I need a hint" / "Show solution"
      - "Interview stats" / "Mock interview"
    
    Resume/Experience:
      - "Add experience: [description]"
      - "Add skill: Python, advanced"
      - "Show my experiences" / "My skills"
      - "Update my GPA to 3.8"
    
    Job Applications:
      - "Applied to Google for STEP program"
      - "Update Google application: got phone screen"
      - "My applications" / "Application stats"
      - "Applications due this week"
    
    Expense Tracker:
      - "Spent $15 on lunch"
      - "Add income: $500 from tutoring"
      - "Budget status" / "Weekly spending"
      - "Set food budget to $300"
    
    Notion:
      - "Open Notion"
      - "Open my class notes in Notion"
      - "Save Notion page: CS 61A at [url]"
    
    Networking:
      - "Add contact: Met Sarah at career fair, Google recruiter"
      - "Who should I follow up with?"
      - "Add note for Sarah: Discussed ML tips"
      - "Network stats"
    
    Voice Journal:
      - "Journal: Today I learned about..."
      - "Today's journal" / "Journal this week"
      - "Mood summary" / "Journal stats"
    
    Learning Paths:
      - "Create learning path for deep learning"
      - "What should I learn next?"
      - "I completed PyTorch basics"
      - "My learning progress"
    """)


if __name__ == "__main__":
    asyncio.run(test_career_features())
