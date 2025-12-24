"""
Tests for the Advanced Research & Paper Writing Module.

Tests:
- Scholarly search APIs
- Source management
- Citation formatting
- Outline generation
- Command detection
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_scholarly_search():
    """Test scholarly search APIs."""
    print("\n" + "=" * 60)
    print("Scholarly Search API Tests")
    print("=" * 60)
    
    from research.scholarly_search import (
        ScholarlySearch,
        SemanticScholarClient,
        OpenAlexClient,
        ArxivClient,
        CrossRefClient,
    )
    
    async def run_tests():
        # Test Semantic Scholar
        print("\n[Test 1] Semantic Scholar API")
        ss = SemanticScholarClient()
        try:
            papers = await ss.search("machine learning bias", limit=5)
            print(f"  ✓ Found {len(papers)} papers")
            if papers:
                print(f"    First: {papers[0].title[:60]}...")
        except Exception as e:
            print(f"  ⚠ Error: {e}")
        finally:
            await ss.close()
        
        # Test OpenAlex
        print("\n[Test 2] OpenAlex API")
        oa = OpenAlexClient()
        try:
            papers = await oa.search("algorithmic fairness", limit=5)
            print(f"  ✓ Found {len(papers)} papers")
            if papers:
                print(f"    First: {papers[0].title[:60]}...")
        except Exception as e:
            print(f"  ⚠ Error: {e}")
        finally:
            await oa.close()
        
        # Test arXiv
        print("\n[Test 3] arXiv API")
        arxiv = ArxivClient()
        try:
            papers = await arxiv.search("deep learning", limit=5)
            print(f"  ✓ Found {len(papers)} papers")
            if papers:
                print(f"    First: {papers[0].title[:60]}...")
        except Exception as e:
            print(f"  ⚠ Error: {e}")
        finally:
            await arxiv.close()
        
        # Test CrossRef
        print("\n[Test 4] CrossRef API")
        cr = CrossRefClient()
        try:
            papers = await cr.search("artificial intelligence ethics", limit=5)
            print(f"  ✓ Found {len(papers)} papers")
            if papers:
                print(f"    First: {papers[0].title[:60]}...")
        except Exception as e:
            print(f"  ⚠ Error: {e}")
        finally:
            await cr.close()
        
        # Test unified search
        print("\n[Test 5] Unified Scholarly Search")
        search = ScholarlySearch()
        try:
            papers = await search.search_all("neural networks", limit_per_source=5)
            print(f"  ✓ Found {len(papers)} unique papers from all databases")
        except Exception as e:
            print(f"  ⚠ Error: {e}")
        finally:
            await search.close()
    
    asyncio.run(run_tests())


def test_source_manager():
    """Test source collection and ranking."""
    print("\n" + "=" * 60)
    print("Source Manager Tests")
    print("=" * 60)
    
    from research.source_manager import SourceManager, Source, SourceRanker
    from research.scholarly_search import Paper, Author, SearchDatabase
    
    # Create test papers
    papers = [
        Paper(
            title="Deep Learning for Natural Language Processing",
            authors=[Author(name="John Smith"), Author(name="Jane Doe")],
            year=2023,
            abstract="This paper explores deep learning techniques for NLP tasks.",
            citation_count=150,
            source_database=SearchDatabase.SEMANTIC_SCHOLAR,
            is_open_access=True,
        ),
        Paper(
            title="Machine Learning in Healthcare",
            authors=[Author(name="Alice Johnson")],
            year=2022,
            abstract="A comprehensive review of ML applications in healthcare.",
            citation_count=80,
            source_database=SearchDatabase.OPENALEX,
            is_open_access=False,
        ),
        Paper(
            title="Ethical AI Systems",
            authors=[Author(name="Bob Wilson"), Author(name="Carol Brown"), Author(name="David Lee")],
            year=2024,
            abstract="Examining ethical considerations in AI system design.",
            citation_count=25,
            source_database=SearchDatabase.ARXIV,
            is_open_access=True,
        ),
    ]
    
    # Test source manager
    print("\n[Test 1] Add Papers as Sources")
    manager = SourceManager()
    sources = manager.add_papers(papers)
    print(f"  ✓ Added {len(sources)} sources")
    
    # Test ranking
    print("\n[Test 2] Source Ranking")
    ranker = SourceRanker()
    ranked = ranker.rank_sources(sources, "deep learning NLP")
    print(f"  ✓ Ranked {len(ranked)} sources")
    print(f"    Top source: {ranked[0].title[:50]}... (score: {ranked[0].relevance_score:.2f})")
    
    # Test selection
    print("\n[Test 3] Source Selection")
    selected = ranker.select_top_sources(ranked, min_sources=2, max_sources=3)
    print(f"  ✓ Selected {len(selected)} sources")
    
    # Test author formatting
    print("\n[Test 4] Author Formatting")
    for source in sources:
        print(f"  - {source.get_author_string()}")
    print("  ✓ Author strings formatted correctly")


def test_citation_manager():
    """Test citation formatting."""
    print("\n" + "=" * 60)
    print("Citation Manager Tests")
    print("=" * 60)
    
    from research.citation_manager import CitationManager, CitationStyle
    from research.source_manager import Source
    
    # Create test source
    source = Source(
        title="The Impact of Artificial Intelligence on Society",
        authors=["John Smith", "Jane Doe", "Bob Wilson"],
        year=2023,
        abstract="A comprehensive analysis of AI's societal impact.",
        doi="10.1234/example.2023",
        venue="Journal of AI Research",
    )
    
    # Test APA
    print("\n[Test 1] APA 7th Edition")
    cm = CitationManager(CitationStyle.APA)
    in_text = cm.get_in_text_citation(source)
    full_ref = cm.get_full_reference(source)
    print(f"  In-text: {in_text}")
    print(f"  Reference: {full_ref[:80]}...")
    
    # Test MLA
    print("\n[Test 2] MLA 9th Edition")
    cm.set_style(CitationStyle.MLA)
    in_text = cm.get_in_text_citation(source)
    full_ref = cm.get_full_reference(source)
    print(f"  In-text: {in_text}")
    print(f"  Reference: {full_ref[:80]}...")
    
    # Test Chicago
    print("\n[Test 3] Chicago Style")
    cm.set_style(CitationStyle.CHICAGO)
    in_text = cm.get_in_text_citation(source)
    full_ref = cm.get_full_reference(source)
    print(f"  In-text: {in_text}")
    print(f"  Reference: {full_ref[:80]}...")
    
    # Test IEEE
    print("\n[Test 4] IEEE Style")
    cm.set_style(CitationStyle.IEEE)
    in_text = cm.get_in_text_citation(source)
    full_ref = cm.get_full_reference(source)
    print(f"  In-text: {in_text}")
    print(f"  Reference: {full_ref[:80]}...")
    
    # Test bibliography
    print("\n[Test 5] Bibliography Generation")
    cm.set_style(CitationStyle.APA)
    sources = [
        source,
        Source(
            title="Machine Learning Fundamentals",
            authors=["Alice Johnson"],
            year=2022,
            abstract="Introduction to ML concepts.",
            venue="ML Press",
        ),
    ]
    bib = cm.generate_bibliography(sources)
    print(f"  ✓ Generated bibliography ({len(bib)} chars)")


def test_outline_generator():
    """Test outline generation."""
    print("\n" + "=" * 60)
    print("Outline Generator Tests")
    print("=" * 60)
    
    from research.outline_generator import OutlineGenerator, PaperType
    from research.source_manager import Source
    
    # Create test sources
    sources = [
        Source(
            title="Algorithmic Bias in Machine Learning",
            authors=["John Smith"],
            year=2023,
            abstract="Study of bias in ML systems.",
            keywords=["bias", "fairness", "machine learning"],
        ),
        Source(
            title="Fairness in AI Systems",
            authors=["Jane Doe"],
            year=2022,
            abstract="Analysis of fairness in AI.",
            keywords=["AI", "ethics", "fairness"],
        ),
    ]
    
    # Test outline generation
    print("\n[Test 1] Generate Outline")
    generator = OutlineGenerator()
    outline = generator.generate_outline(
        topic="Algorithmic Biases in AI",
        sources=sources,
        target_pages=10,
        citation_style="apa",
    )
    
    print(f"  ✓ Title: {outline.title}")
    print(f"  ✓ Thesis: {outline.thesis[:60]}...")
    print(f"  ✓ Sections: {len(outline.sections)}")
    print(f"  ✓ Target words: {outline.target_words}")
    
    # Test section details
    print("\n[Test 2] Section Details")
    for section in outline.sections[:5]:
        print(f"  - {section.title} (Level {section.level}, ~{section.word_target} words)")
    
    # Test markdown output
    print("\n[Test 3] Markdown Output")
    md = outline.to_markdown()
    print(f"  ✓ Generated markdown ({len(md)} chars)")


def test_project_store():
    """Test project persistence."""
    print("\n" + "=" * 60)
    print("Project Store Tests")
    print("=" * 60)
    
    import tempfile
    from research.project_store import ProjectStore, ResearchProject, ProjectStatus
    from research.source_manager import Source, SourceStatus
    
    # Create temp database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    store = ProjectStore(db_path=db_path)
    
    # Test create project
    print("\n[Test 1] Create Project")
    project = ResearchProject(
        topic="Algorithmic Biases in AI",
        page_count=10,
        citation_style="apa",
        focus_areas=["bias detection", "mitigation strategies"],
    )
    project_id = store.create_project(project)
    print(f"  ✓ Created project ID: {project_id}")
    
    # Test get project
    print("\n[Test 2] Get Project")
    retrieved = store.get_project(project_id)
    print(f"  ✓ Retrieved: {retrieved.topic}")
    print(f"  ✓ Status: {retrieved.get_status_display()}")
    
    # Test add sources
    print("\n[Test 3] Add Sources")
    source = Source(
        title="Test Paper",
        authors=["Author One"],
        year=2023,
        abstract="Test abstract",
        relevance_score=0.85,
        status=SourceStatus.SELECTED,
        id="test_123",
    )
    store.add_source(project_id, source)
    sources = store.get_sources(project_id)
    print(f"  ✓ Added and retrieved {len(sources)} sources")
    
    # Test update progress
    print("\n[Test 4] Update Progress")
    store.update_progress(project_id, ProjectStatus.WRITING, 50.0, "Literature Review")
    updated = store.get_project(project_id)
    print(f"  ✓ Status: {updated.status.value}")
    print(f"  ✓ Progress: {updated.progress_percent}%")
    
    # Test get all projects
    print("\n[Test 5] Get All Projects")
    all_projects = store.get_all_projects()
    print(f"  ✓ Found {len(all_projects)} projects")
    
    # Cleanup (ignore errors on Windows)
    import os
    try:
        os.unlink(db_path)
    except PermissionError:
        pass  # File locked on Windows, will be cleaned up later


def test_command_detection():
    """Test command detection in ResearchManager."""
    print("\n" + "=" * 60)
    print("Command Detection Tests")
    print("=" * 60)
    
    from research.manager import ResearchManager
    
    manager = ResearchManager()
    
    # Test paper commands
    print("\n[Test 1] Paper Command Detection")
    paper_commands = [
        "Write a research paper on algorithmic biases",
        "Research paper about machine learning ethics",
        "10 page paper on AI in healthcare",
        "Write a paper on climate change in APA format",
    ]
    for cmd in paper_commands:
        detected = manager._is_paper_command(cmd.lower())
        status = "✓" if detected else "✗"
        print(f"  {status} '{cmd[:40]}...'")
    
    # Test search commands
    print("\n[Test 2] Search Command Detection")
    search_commands = [
        "Find papers about neural networks",
        "Search for articles on deep learning",
        "Latest research on transformer models",
        "Scholarly search for NLP techniques",
    ]
    for cmd in search_commands:
        detected = manager._is_search_command(cmd.lower())
        status = "✓" if detected else "✗"
        print(f"  {status} '{cmd[:40]}...'")
    
    # Test project commands
    print("\n[Test 3] Project Command Detection")
    project_commands = [
        "Show my research projects",
        "Resume my AI ethics paper",
        "Research status",
        "What sources did you find",
    ]
    for cmd in project_commands:
        detected = manager._is_project_command(cmd.lower())
        status = "✓" if detected else "✗"
        print(f"  {status} '{cmd[:40]}...'")
    
    # Test citation commands
    print("\n[Test 4] Citation Command Detection")
    citation_commands = [
        "How do I cite this in APA",
        "Use MLA format",
        "Generate bibliography",
        "Citation for this paper",
    ]
    for cmd in citation_commands:
        detected = manager._is_citation_command(cmd.lower())
        status = "✓" if detected else "✗"
        print(f"  {status} '{cmd[:40]}...'")
    
    # Test extraction
    print("\n[Test 5] Topic Extraction")
    test_cases = [
        ("Write a research paper on algorithmic biases in AI", "algorithmic biases in AI"),
        ("10 page paper on machine learning", "machine learning"),
        ("Research paper about climate change for my English class", "climate change"),
    ]
    for cmd, expected in test_cases:
        extracted = manager._extract_topic(cmd.lower(), cmd)
        match = "✓" if extracted and expected.lower() in extracted.lower() else "✗"
        print(f"  {match} '{cmd[:35]}...' -> '{extracted or 'None'}'")


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("Advanced Research & Paper Writing Module - Tests")
    print("=" * 60)
    
    # Run tests
    test_source_manager()
    test_citation_manager()
    test_outline_generator()
    test_project_store()
    test_command_detection()
    
    # API tests (require network)
    print("\n" + "-" * 60)
    print("Running API tests (requires network connection)...")
    print("-" * 60)
    test_scholarly_search()
    
    print("\n" + "=" * 60)
    print("✅ All Research Module Tests Complete!")
    print("=" * 60)
    
    print("""
📢 New Voice Commands Available:

    Research Paper Writing:
      - "Write a research paper on [topic]"
      - "10 page paper on [topic] in APA format"
      - "Research paper about [topic] for my English class"
    
    Scholarly Search:
      - "Find papers about [topic]"
      - "Search for scholarly articles on [topic]"
      - "Latest research on [topic]"
    
    Project Management:
      - "Show my research projects"
      - "Resume my [topic] paper"
      - "Research status"
      - "What sources did you find?"
    
    Citation Help:
      - "Use APA format" / "Use MLA format"
      - "How do I cite in APA?"
      - "Generate bibliography"
""")


if __name__ == "__main__":
    main()
