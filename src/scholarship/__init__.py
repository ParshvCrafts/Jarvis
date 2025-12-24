"""
JARVIS Scholarship Automation Module.

A comprehensive scholarship discovery, essay generation, and application
management system with RAG-powered personalization using past winning essays.

Components:
- models.py: Data models for scholarships, essays, profiles
- supabase_client.py: Supabase connection and vector operations
- embeddings.py: Embedding generation (local + cloud options)
- rag.py: RAG retrieval system for past essays
- local_rag.py: ChromaDB local fallback for RAG
- discovery.py: Scholarship search and eligibility matching
- prompts.py: Advanced prompt templates
- generator.py: Essay generation workflow
- tracker.py: Application tracking
- docs_output.py: Google Docs formatted output
- importer.py: Tools to import past essays
- setup.py: Database setup and verification
- manager.py: Main manager class with voice commands
"""

from loguru import logger

# Module availability flags
SCHOLARSHIP_AVAILABLE = True
SUPABASE_AVAILABLE = False
EMBEDDINGS_AVAILABLE = False
CHROMADB_AVAILABLE = False

# Try importing components
try:
    from .models import (
        EligibilityProfile,
        Scholarship,
        ScholarshipQuestion,
        PastEssay,
        EssayOutcome,
        ApplicationStatus,
        Application,
    )
except ImportError as e:
    logger.warning(f"Scholarship models not available: {e}")
    SCHOLARSHIP_AVAILABLE = False
    EligibilityProfile = None
    Scholarship = None
    ScholarshipQuestion = None
    PastEssay = None
    EssayOutcome = None
    ApplicationStatus = None
    Application = None

try:
    from .supabase_client import SupabaseClient
    SUPABASE_AVAILABLE = True
except ImportError as e:
    logger.debug(f"Supabase client not available: {e}")
    SupabaseClient = None

try:
    from .embeddings import EmbeddingGenerator
    EMBEDDINGS_AVAILABLE = True
except ImportError as e:
    logger.debug(f"Embeddings not available: {e}")
    EmbeddingGenerator = None

try:
    from .rag import ScholarshipRAG
except ImportError as e:
    logger.debug(f"RAG not available: {e}")
    ScholarshipRAG = None

try:
    from .discovery import ScholarshipDiscovery
except ImportError as e:
    logger.debug(f"Discovery not available: {e}")
    ScholarshipDiscovery = None

try:
    from .prompts import PromptTemplates
except ImportError as e:
    logger.debug(f"Prompts not available: {e}")
    PromptTemplates = None

try:
    from .generator import EssayGenerator
except ImportError as e:
    logger.debug(f"Generator not available: {e}")
    EssayGenerator = None

try:
    from .tracker import ApplicationTracker
except ImportError as e:
    logger.debug(f"Tracker not available: {e}")
    ApplicationTracker = None

try:
    from .importer import EssayImporter
except ImportError as e:
    logger.debug(f"Importer not available: {e}")
    EssayImporter = None

try:
    from .manager import ScholarshipManager, ScholarshipConfig
except ImportError as e:
    logger.debug(f"Manager not available: {e}")
    ScholarshipManager = None
    ScholarshipConfig = None

try:
    from .docs_output import ScholarshipDocsOutput
except ImportError as e:
    logger.debug(f"Docs output not available: {e}")
    ScholarshipDocsOutput = None

try:
    from .local_rag import LocalRAGStore, CHROMADB_AVAILABLE as _CHROMADB
    CHROMADB_AVAILABLE = _CHROMADB
except ImportError as e:
    logger.debug(f"Local RAG not available: {e}")
    LocalRAGStore = None

try:
    from .setup import ScholarshipDatabaseSetup, setup_scholarship_database, get_database_mode
except ImportError as e:
    logger.debug(f"Setup not available: {e}")
    ScholarshipDatabaseSetup = None
    setup_scholarship_database = None
    get_database_mode = None

__all__ = [
    # Flags
    "SCHOLARSHIP_AVAILABLE",
    "SUPABASE_AVAILABLE",
    "EMBEDDINGS_AVAILABLE",
    "CHROMADB_AVAILABLE",
    # Models
    "EligibilityProfile",
    "Scholarship",
    "ScholarshipQuestion",
    "PastEssay",
    "EssayOutcome",
    "ApplicationStatus",
    "Application",
    # Components
    "SupabaseClient",
    "EmbeddingGenerator",
    "ScholarshipRAG",
    "ScholarshipDiscovery",
    "PromptTemplates",
    "EssayGenerator",
    "ApplicationTracker",
    "EssayImporter",
    "ScholarshipManager",
    "ScholarshipConfig",
    "ScholarshipDocsOutput",
    # Local RAG
    "LocalRAGStore",
    # Setup
    "ScholarshipDatabaseSetup",
    "setup_scholarship_database",
    "get_database_mode",
]
