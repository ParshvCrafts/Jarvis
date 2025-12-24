#!/usr/bin/env python3
"""
JARVIS Runner Script

Entry point for running JARVIS with all enhanced features.

Usage:
    python run.py              # Full voice mode
    python run.py --text       # Text-only mode
    python run.py --check-config  # Validate configuration
    python run.py --setup      # Run first-time setup
    python run.py --setup -i   # Interactive setup with prompts
    python run.py --status     # Show system status
    python run.py --add-key groq  # Add API key interactively
    python run.py --legacy     # Use legacy (non-enhanced) modules
    python run.py --add-contacts  # Interactive contact setup
    python run.py --add-contact "Name" "Phone"  # Quick add contact
    
Scholarship Commands:
    python run.py --setup-scholarship      # Setup Supabase database tables
    python run.py --import-essays FOLDER   # Import essays from folder
    python run.py --scholarship-status     # Show scholarship module status
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

def run_contact_setup():
    """Interactive contact setup wizard."""
    from src.communication import ContactsManager
    
    print("\n" + "=" * 50)
    print("       JARVIS Contact Setup Wizard")
    print("=" * 50)
    print("\nAdd your contacts one by one.")
    print("Type 'done' when finished, 'list' to see contacts.\n")
    
    db_path = Path(__file__).parent / "data" / "contacts.db"
    manager = ContactsManager(db_path)
    
    added_count = 0
    
    while True:
        print(f"\n--- Contact {added_count + 1} ---")
        
        # Get name
        name = input("Name (or 'done'/'list'): ").strip()
        
        if name.lower() == 'done':
            break
        
        if name.lower() == 'list':
            contacts = manager.list_contacts()
            if contacts:
                print(f"\nYou have {len(contacts)} contacts:")
                for c in contacts:
                    fav = "⭐" if c.favorite else ""
                    print(f"  • {c.name} - {c.phone} {fav}")
            else:
                print("\nNo contacts yet.")
            continue
        
        if not name:
            print("Name is required.")
            continue
        
        # Get phone
        phone = input("Phone (with country code, e.g., +91 9825779760): ").strip()
        if not phone:
            print("Phone is required.")
            continue
        
        # Get optional fields
        email = input("Email (optional, press Enter to skip): ").strip() or None
        nickname = input("Nickname (optional, e.g., 'Sister'): ").strip() or None
        
        # Category
        category_input = input("Category [family/friend/work] (default: family): ").strip().lower()
        category = category_input if category_input in ['family', 'friend', 'work'] else 'family'
        
        # Favorite
        fav_input = input("Add to favorites? [y/N]: ").strip().lower()
        favorite = fav_input in ['y', 'yes']
        
        # Add contact
        success, msg = manager.add_contact(
            name=name,
            phone=phone,
            email=email,
            nickname=nickname,
            category=category,
            favorite=favorite,
        )
        
        if success:
            print(f"\n✅ Added {name} to contacts!")
            if not phone.startswith("+"):
                print(f"   (Using default country code {manager.default_country_code})")
            added_count += 1
        else:
            print(f"\n❌ {msg}")
    
    # Summary
    print("\n" + "=" * 50)
    if added_count > 0:
        print(f"✅ Added {added_count} contact(s) successfully!")
        
        # Show favorites
        favorites = manager.get_favorites()
        if favorites:
            print(f"\n⭐ Favorites: {', '.join(c.name for c in favorites)}")
    else:
        print("No contacts added.")
    
    total = manager.get_contact_count()
    print(f"\nTotal contacts: {total}")
    print("\nTip: Say 'List my contacts' in JARVIS to see them.")
    print("=" * 50 + "\n")

def get_enhanced_scholarship_status(manager) -> str:
    """Get comprehensive scholarship status with dependency checks."""
    lines = ["🎓 **Scholarship Module Status**", "=" * 40, ""]
    
    # Check installed dependencies
    lines.append("**Dependencies:**")
    deps = [
        ("supabase", "supabase"),
        ("chromadb", "chromadb"),
        ("sentence_transformers", "sentence-transformers"),
        ("tavily", "tavily-python"),
        ("docx", "python-docx"),
        ("PyPDF2", "PyPDF2"),
        ("cohere", "cohere"),
    ]
    
    all_installed = True
    for import_name, pkg_name in deps:
        try:
            __import__(import_name)
            lines.append(f"  ✅ {pkg_name}")
        except ImportError:
            lines.append(f"  ❌ {pkg_name}")
            all_installed = False
    
    # Get manager status
    status = manager.get_status()
    
    lines.extend([
        "",
        "**Database:**",
    ])
    
    if status['rag_mode'] == 'cloud':
        lines.append("  ✅ Supabase: Connected")
    else:
        if status.get('supabase_available'):
            lines.append("  ⚠️ Supabase: Configured (not connected)")
        else:
            lines.append("  ❌ Supabase: Not configured")
    
    if status['chromadb_available']:
        lines.append("  ✅ ChromaDB: Active (Local Mode)")
    else:
        lines.append("  ⚠️ ChromaDB: Not available")
    
    lines.extend([
        f"  📚 Essays Indexed: {status['rag_essays']}",
        f"  📝 Statement Sections: {status['rag_statements']}",
        f"  👤 Profile Sections: {status['rag_profiles']}",
        "",
        "**APIs:**",
        f"  {'✅' if status['tavily_available'] else '❌'} Tavily API",
        f"  {'✅' if status['serper_available'] else '❌'} Serper API",
        "",
        "**Eligibility Profile:**",
        f"  Name: {status['profile']}",
    ])
    
    # Get profile details if available
    if hasattr(manager, 'profile'):
        p = manager.profile
        lines.extend([
            f"  University: {getattr(p, 'university', 'Not set')}",
            f"  Major: {getattr(p, 'major', 'Not set')}",
            f"  Year: {getattr(p, 'year', 'Not set')}",
        ])
    
    lines.extend([
        "",
        "**Applications:**",
        f"  📊 Total: {status['applications']}",
        f"  ⏳ Pending: {status['pending_count']}",
        f"  📤 Submitted: {status['submitted_count']}",
        f"  🏆 Won: {status['won_count']} (${status['won_amount']:,.0f})",
        "",
    ])
    
    # Ready status
    if all_installed and (status['tavily_available'] or status['serper_available']):
        lines.append("**Ready to use:** ✅")
        lines.extend([
            "",
            "**Next steps:**",
            "  1. Import essays: python run.py --import-essays FOLDER",
            "  2. Setup database: python run.py --setup-scholarship",
            "  3. Find scholarships: 'Find scholarships for me'",
        ])
    else:
        lines.append("**Ready to use:** ⚠️ Partial")
        lines.extend([
            "",
            "**To enable full functionality:**",
        ])
        if not all_installed:
            lines.append("  pip install -r requirements-scholarship.txt")
        if not status['tavily_available'] and not status['serper_available']:
            lines.append("  Add TAVILY_API_KEY or SERPER_API_KEY to .env")
    
    return "\n".join(lines)

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="JARVIS - Advanced Personal AI Assistant")
    parser.add_argument("--text", action="store_true", help="Run in text-only mode")
    parser.add_argument("--check-config", action="store_true", help="Validate configuration and exit")
    parser.add_argument("--config", type=str, help="Path to configuration file")
    parser.add_argument("--legacy", action="store_true", help="Use legacy (non-enhanced) modules")
    parser.add_argument("--setup", action="store_true", help="Run first-time setup wizard")
    parser.add_argument("--status", action="store_true", help="Show system status")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive setup mode")
    parser.add_argument("--add-key", type=str, metavar="NAME", help="Add API key (e.g., --add-key groq)")
    parser.add_argument("--add-contacts", action="store_true", help="Interactive contact setup wizard")
    parser.add_argument("--add-contact", nargs=2, metavar=("NAME", "PHONE"), help="Quick add a contact")
    parser.add_argument("--email", type=str, help="Email for --add-contact")
    parser.add_argument("--category", type=str, default="family", help="Category for --add-contact")
    parser.add_argument("--setup-scholarship", action="store_true", help="Setup scholarship database")
    parser.add_argument("--import-essays", type=str, metavar="FOLDER", help="Import essays from folder")
    parser.add_argument("--scholarship-status", action="store_true", help="Show scholarship module status")
    parser.add_argument("--install-scholarship-deps", action="store_true", help="Install scholarship module dependencies")
    
    # Internship module arguments
    parser.add_argument("--internship-status", action="store_true", help="Show internship module status")
    parser.add_argument("--find-internships", type=str, nargs="?", const="", metavar="QUERY", help="Search for internships")
    parser.add_argument("--install-internship-deps", action="store_true", help="Install internship module dependencies")
    parser.add_argument("--import-resume", type=str, metavar="FOLDER", help="Import resume/projects from folder")
    parser.add_argument("--diagnose-apis", action="store_true", help="Diagnose internship job search APIs")
    parser.add_argument("--internship-dashboard", action="store_true", help="Show application analytics dashboard")
    parser.add_argument("--import-github", type=str, nargs="?", const="", metavar="USERNAME", help="Import projects from GitHub")
    
    # Phase 4 module arguments
    parser.add_argument("--travel-status", action="store_true", help="Show travel module status")
    parser.add_argument("--health-status", action="store_true", help="Show health module status")
    parser.add_argument("--news", type=str, nargs="?", const="tech", metavar="TOPIC", help="Get news (tech, ai, datascience)")
    parser.add_argument("--communication-status", action="store_true", help="Show communication hub status")
    
    args = parser.parse_args()
    
    # Quick add contact
    if args.add_contact:
        from src.communication import ContactsManager
        from pathlib import Path
        
        name, phone = args.add_contact
        db_path = Path(__file__).parent / "data" / "contacts.db"
        manager = ContactsManager(db_path)
        
        success, msg = manager.add_contact(
            name=name,
            phone=phone,
            email=args.email,
            category=args.category,
        )
        
        if success:
            print(f"✅ {msg}")
            # Show note about country code if no + in phone
            if not phone.startswith("+"):
                print(f"   Note: Using default country code {manager.default_country_code}")
                print(f"   Change in config/settings.yaml if needed.")
        else:
            print(f"❌ {msg}")
        return
    
    # Interactive contact setup
    if args.add_contacts:
        run_contact_setup()
        return
    
    # Add API key
    if args.add_key:
        from src.core.setup_wizard import add_api_key
        import getpass
        
        key_name = args.add_key.upper()
        if not key_name.endswith("_API_KEY"):
            key_name = f"{key_name}_API_KEY"
        
        print(f"Adding {key_name}...")
        key_value = getpass.getpass(f"Enter value for {key_name}: ")
        
        if key_value:
            if add_api_key(key_name, key_value):
                print(f"✓ {key_name} saved to .env")
            else:
                print(f"✗ Failed to save {key_name}")
        else:
            print("No key entered, skipping.")
        return
    
    # Setup wizard
    if args.setup:
        from src.core.setup_wizard import run_first_time_setup
        run_first_time_setup(interactive=args.interactive)
        return
    
    # Status check
    if args.status:
        from src.core.setup_wizard import print_status
        print_status()
        return
    
    # Scholarship database setup
    if args.setup_scholarship:
        import asyncio
        import os
        from dotenv import load_dotenv
        load_dotenv()
        
        from src.scholarship import setup_scholarship_database, SCHOLARSHIP_AVAILABLE
        
        if not SCHOLARSHIP_AVAILABLE:
            print("❌ Scholarship module not available")
            return
        
        print("\n🎓 Setting up Scholarship Database...")
        result = asyncio.run(setup_scholarship_database(
            supabase_url=os.getenv("SUPABASE_URL"),
            supabase_key=os.getenv("SUPABASE_KEY"),
        ))
        print(result)
        return
    
    # Import essays
    if args.import_essays:
        import asyncio
        import os
        from dotenv import load_dotenv
        load_dotenv()
        
        from src.scholarship import ScholarshipManager, ScholarshipConfig, SCHOLARSHIP_AVAILABLE
        
        if not SCHOLARSHIP_AVAILABLE:
            print("❌ Scholarship module not available")
            return
        
        folder = args.import_essays
        print(f"\n📥 Importing essays from: {folder}")
        
        config = ScholarshipConfig(
            supabase_url=os.getenv("SUPABASE_URL"),
            supabase_key=os.getenv("SUPABASE_KEY"),
        )
        manager = ScholarshipManager(config=config)
        
        imported, failed = asyncio.run(manager.import_essays_folder(folder))
        print(f"\n✅ Imported: {imported}")
        print(f"❌ Failed: {failed}")
        return
    
    # Scholarship status
    if args.scholarship_status:
        from dotenv import load_dotenv
        import os
        load_dotenv()
        
        from src.scholarship import ScholarshipManager, ScholarshipConfig, SCHOLARSHIP_AVAILABLE
        
        if not SCHOLARSHIP_AVAILABLE:
            print("❌ Scholarship module not available")
            return
        
        # Load config from environment
        config = ScholarshipConfig(
            supabase_url=os.getenv("SUPABASE_URL"),
            supabase_key=os.getenv("SUPABASE_KEY"),
            tavily_api_key=os.getenv("TAVILY_API_KEY"),
            serper_api_key=os.getenv("SERPER_API_KEY"),
        )
        manager = ScholarshipManager(config=config)
        print(get_enhanced_scholarship_status(manager))
        return
    
    # Install scholarship dependencies
    if args.install_scholarship_deps:
        import subprocess
        import sys
        
        print("\n🎓 Installing Scholarship Module Dependencies...")
        print("=" * 50)
        
        deps = [
            ("supabase", "supabase"),
            ("chromadb", "chromadb"),
            ("sentence-transformers", "sentence_transformers"),
            ("tavily-python", "tavily"),
            ("python-docx", "docx"),
            ("PyPDF2", "PyPDF2"),
            ("cohere", "cohere"),
        ]
        
        installed = []
        failed = []
        
        for pkg_name, import_name in deps:
            print(f"\n📦 Installing {pkg_name}...")
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", pkg_name],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    print(f"   ✅ {pkg_name} installed")
                    installed.append(pkg_name)
                else:
                    print(f"   ❌ {pkg_name} failed: {result.stderr[:100]}")
                    failed.append(pkg_name)
            except Exception as e:
                print(f"   ❌ {pkg_name} error: {e}")
                failed.append(pkg_name)
        
        print("\n" + "=" * 50)
        print(f"✅ Installed: {len(installed)}/{len(deps)}")
        if failed:
            print(f"❌ Failed: {', '.join(failed)}")
        
        print("\nNext steps:")
        print("  1. Run: python run.py --scholarship-status")
        print("  2. Run: python run.py --setup-scholarship")
        return
    
    # Internship module status
    if args.internship_status:
        from dotenv import load_dotenv
        import os
        load_dotenv()
        
        try:
            from src.internship import InternshipManager, InternshipConfig, INTERNSHIP_AVAILABLE
            
            if not INTERNSHIP_AVAILABLE:
                print("❌ Internship module not available")
                return
            
            config = InternshipConfig(
                tavily_api_key=os.getenv("TAVILY_API_KEY"),
                serper_api_key=os.getenv("SERPER_API_KEY"),
            )
            manager = InternshipManager(config=config)
            print(manager.get_status_summary())
        except ImportError as e:
            print(f"❌ Internship module import error: {e}")
        return
    
    # Find internships
    if args.find_internships is not None:
        import asyncio
        from dotenv import load_dotenv
        import os
        load_dotenv()
        
        try:
            from src.internship import InternshipManager, InternshipConfig, INTERNSHIP_AVAILABLE
            
            if not INTERNSHIP_AVAILABLE:
                print("❌ Internship module not available")
                return
            
            config = InternshipConfig(
                tavily_api_key=os.getenv("TAVILY_API_KEY"),
                serper_api_key=os.getenv("SERPER_API_KEY"),
            )
            manager = InternshipManager(config=config)
            
            query = args.find_internships or "data science intern"
            print(f"\n🔍 Searching for: {query}")
            print("=" * 50)
            
            listings = asyncio.run(manager.search_internships(query=query))
            print(manager.get_search_summary(listings))
        except ImportError as e:
            print(f"❌ Internship module import error: {e}")
        return
    
    # Install internship dependencies
    if args.install_internship_deps:
        import subprocess
        import sys
        
        print("\n💼 Installing Internship Module Dependencies...")
        print("=" * 50)
        
        deps = [
            ("httpx", "httpx"),
            ("sentence-transformers", "sentence_transformers"),
            ("chromadb", "chromadb"),
            ("tavily-python", "tavily"),
            ("python-docx", "docx"),
            ("reportlab", "reportlab"),
        ]
        
        installed = []
        failed = []
        
        for pkg_name, import_name in deps:
            print(f"\n📦 Installing {pkg_name}...")
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", pkg_name],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    print(f"   ✅ {pkg_name} installed")
                    installed.append(pkg_name)
                else:
                    print(f"   ❌ {pkg_name} failed: {result.stderr[:100]}")
                    failed.append(pkg_name)
            except Exception as e:
                print(f"   ❌ {pkg_name} error: {e}")
                failed.append(pkg_name)
        
        print("\n" + "=" * 50)
        print(f"✅ Installed: {len(installed)}/{len(deps)}")
        if failed:
            print(f"❌ Failed: {', '.join(failed)}")
        
        print("\nNext steps:")
        print("  1. Run: python run.py --internship-status")
        print("  2. Run: python run.py --find-internships")
        return
    
    # Import resume data
    if args.import_resume:
        from dotenv import load_dotenv
        import os
        load_dotenv()
        
        folder_path = args.import_resume
        
        print(f"\n📄 Importing resume data from: {folder_path}")
        print("=" * 50)
        
        try:
            from src.internship import InternshipManager, InternshipConfig, INTERNSHIP_AVAILABLE
            from src.internship.importer import import_resume_data, get_import_status_message
            
            if not INTERNSHIP_AVAILABLE:
                print("❌ Internship module not available")
                return
            
            # Initialize manager to get RAG
            config = InternshipConfig()
            manager = InternshipManager(config=config)
            
            # Import data
            result = import_resume_data(folder_path, manager.resume_rag)
            
            # Print results
            print(get_import_status_message(result))
            
            print("\n" + "=" * 50)
            print("\n✅ Import complete! Your data is now stored in the RAG system.")
            print("\nNext steps:")
            print("  1. Run: python run.py --internship-status")
            print("  2. Run: python run.py --find-internships")
            print("  3. Say: 'Customize resume for Google'")
            
        except ImportError as e:
            print(f"❌ Import error: {e}")
        except Exception as e:
            print(f"❌ Error: {e}")
        return
    
    # Diagnose APIs
    if args.diagnose_apis:
        import asyncio
        from dotenv import load_dotenv
        load_dotenv()
        
        try:
            from src.internship.diagnostics import diagnose_internship_apis
            
            print("\n🔍 Diagnosing Internship APIs...")
            print("=" * 50)
            
            report = asyncio.run(diagnose_internship_apis())
            print(report)
            
        except ImportError as e:
            print(f"❌ Import error: {e}")
        return
    
    # Internship dashboard
    if args.internship_dashboard:
        from dotenv import load_dotenv
        load_dotenv()
        
        try:
            from src.internship import InternshipManager, InternshipConfig, INTERNSHIP_AVAILABLE
            
            if not INTERNSHIP_AVAILABLE:
                print("❌ Internship module not available")
                return
            
            config = InternshipConfig()
            manager = InternshipManager(config=config)
            
            print(manager.get_dashboard())
            
            # Also save HTML dashboard
            html_path = manager.save_dashboard_html()
            print(f"\n📊 HTML Dashboard saved to: {html_path}")
            
        except ImportError as e:
            print(f"❌ Import error: {e}")
        return
    
    # Import from GitHub
    if args.import_github is not None:
        import asyncio
        from dotenv import load_dotenv
        load_dotenv()
        
        try:
            from src.internship import InternshipManager, InternshipConfig, INTERNSHIP_AVAILABLE
            from src.internship.github_import import get_github_import_summary
            
            if not INTERNSHIP_AVAILABLE:
                print("❌ Internship module not available")
                return
            
            config = InternshipConfig()
            manager = InternshipManager(config=config)
            
            username = args.import_github if args.import_github else None
            print(f"\n📁 Importing projects from GitHub{' for ' + username if username else ''}...")
            print("=" * 50)
            
            result = asyncio.run(manager.import_from_github(username=username))
            print(get_github_import_summary(result))
            
        except ImportError as e:
            print(f"❌ Import error: {e}")
        return
    
    # Phase 4: Travel status
    if args.travel_status:
        try:
            from src.travel import TravelManager, TRAVEL_AVAILABLE
            if TRAVEL_AVAILABLE:
                manager = TravelManager()
                print(manager.get_status_summary())
            else:
                print("❌ Travel module not available")
        except ImportError as e:
            print(f"❌ {e}")
        return
    
    # Phase 4: Health status
    if args.health_status:
        try:
            from src.health import HealthManager, HEALTH_AVAILABLE
            if HEALTH_AVAILABLE:
                manager = HealthManager()
                print(manager.get_status_summary())
            else:
                print("❌ Health module not available")
        except ImportError as e:
            print(f"❌ {e}")
        return
    
    # Phase 4: News
    if args.news is not None:
        import asyncio
        try:
            from src.news import NewsManager, NEWS_AVAILABLE
            if NEWS_AVAILABLE:
                manager = NewsManager()
                topic = args.news or "tech"
                if topic == "ai":
                    articles = asyncio.run(manager.get_ai_news(5))
                else:
                    articles = asyncio.run(manager.get_tech_news(5))
                print(f"📰 **{topic.title()} News:**\n")
                for i, a in enumerate(articles[:5], 1):
                    print(f"{i}. {a.title}")
            else:
                print("❌ News module not available")
        except ImportError as e:
            print(f"❌ {e}")
        return
    
    # Phase 4: Communication status
    if args.communication_status:
        try:
            from src.communication_hub import CommunicationManager, COMMUNICATION_AVAILABLE
            if COMMUNICATION_AVAILABLE:
                manager = CommunicationManager()
                print(manager.get_status_summary())
            else:
                print("❌ Communication module not available")
        except ImportError as e:
            print(f"❌ {e}")
        return
    
    if args.legacy:
        # Use original jarvis.py
        from src.jarvis import main as legacy_main
        legacy_main()
    else:
        # Use unified jarvis with all enhanced features
        from src.jarvis_unified import main as unified_main, check_config
        
        if args.check_config:
            check_config()
        else:
            # Re-parse in unified module
            unified_main()

if __name__ == "__main__":
    main()
