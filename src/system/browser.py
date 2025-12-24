"""
Browser Automation Module for JARVIS.

Provides comprehensive browser control using Playwright:
- Navigate to URLs
- Google Docs integration
- Web research automation
- Form filling
- Screenshot capture
"""

from __future__ import annotations

import asyncio
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote_plus, urlparse

from loguru import logger

try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright not available. Install with: pip install playwright && playwright install")


class BrowserType(Enum):
    """Supported browser types."""
    CHROMIUM = "chromium"
    FIREFOX = "firefox"
    WEBKIT = "webkit"


@dataclass
class WebPage:
    """Information about a web page."""
    url: str
    title: str
    content: str = ""
    screenshot_path: Optional[Path] = None
    links: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class SearchResult:
    """A search result."""
    title: str
    url: str
    snippet: str
    position: int


class BrowserController:
    """
    Browser automation controller using Playwright.
    
    Features:
    - Multi-browser support (Chrome, Firefox, WebKit)
    - Persistent sessions with user profiles
    - Google Docs integration
    - Web search and research
    - Screenshot capture
    """
    
    def __init__(
        self,
        browser_type: BrowserType = BrowserType.CHROMIUM,
        headless: bool = False,
        user_data_dir: Optional[Path] = None,
        slow_mo: int = 0,
    ):
        """
        Initialize browser controller.
        
        Args:
            browser_type: Browser to use.
            headless: Run in headless mode.
            user_data_dir: Directory for persistent browser data.
            slow_mo: Slow down operations by this many ms.
        """
        self.browser_type = browser_type
        self.headless = headless
        self.user_data_dir = user_data_dir
        self.slow_mo = slow_mo
        
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
    
    @property
    def is_available(self) -> bool:
        return PLAYWRIGHT_AVAILABLE
    
    async def start(self) -> bool:
        """Start the browser."""
        if not PLAYWRIGHT_AVAILABLE:
            logger.error("Playwright not available")
            return False
        
        try:
            self._playwright = await async_playwright().start()
            
            # Select browser
            if self.browser_type == BrowserType.CHROMIUM:
                browser_launcher = self._playwright.chromium
            elif self.browser_type == BrowserType.FIREFOX:
                browser_launcher = self._playwright.firefox
            else:
                browser_launcher = self._playwright.webkit
            
            # Launch with persistent context if user_data_dir provided
            if self.user_data_dir:
                self.user_data_dir.mkdir(parents=True, exist_ok=True)
                self._context = await browser_launcher.launch_persistent_context(
                    str(self.user_data_dir),
                    headless=self.headless,
                    slow_mo=self.slow_mo,
                )
                self._page = self._context.pages[0] if self._context.pages else await self._context.new_page()
            else:
                self._browser = await browser_launcher.launch(
                    headless=self.headless,
                    slow_mo=self.slow_mo,
                )
                self._context = await self._browser.new_context()
                self._page = await self._context.new_page()
            
            logger.info(f"Browser started: {self.browser_type.value}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to start browser: {e}")
            return False
    
    async def stop(self) -> None:
        """Stop the browser."""
        try:
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
            
            self._page = None
            self._context = None
            self._browser = None
            self._playwright = None
            
            logger.info("Browser stopped")
        except Exception as e:
            logger.error(f"Error stopping browser: {e}")
    
    async def navigate(self, url: str, wait_until: str = "domcontentloaded") -> Optional[WebPage]:
        """
        Navigate to a URL.
        
        Args:
            url: URL to navigate to.
            wait_until: Wait condition (load, domcontentloaded, networkidle).
            
        Returns:
            WebPage with page information.
        """
        if not self._page:
            logger.error("Browser not started")
            return None
        
        try:
            # Add protocol if missing
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            
            await self._page.goto(url, wait_until=wait_until)
            
            title = await self._page.title()
            
            return WebPage(
                url=self._page.url,
                title=title,
            )
        
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            return None
    
    async def search_google(self, query: str, num_results: int = 5) -> List[SearchResult]:
        """
        Search Google and return results.
        
        Args:
            query: Search query.
            num_results: Number of results to return.
            
        Returns:
            List of search results.
        """
        if not self._page:
            return []
        
        try:
            # Navigate to Google
            search_url = f"https://www.google.com/search?q={quote_plus(query)}"
            await self._page.goto(search_url, wait_until="domcontentloaded")
            
            # Wait for results
            await self._page.wait_for_selector("div#search", timeout=10000)
            
            # Extract results
            results = []
            search_results = await self._page.query_selector_all("div.g")
            
            for i, result in enumerate(search_results[:num_results]):
                try:
                    title_el = await result.query_selector("h3")
                    link_el = await result.query_selector("a")
                    snippet_el = await result.query_selector("div[data-sncf]")
                    
                    if title_el and link_el:
                        title = await title_el.inner_text()
                        url = await link_el.get_attribute("href")
                        snippet = await snippet_el.inner_text() if snippet_el else ""
                        
                        results.append(SearchResult(
                            title=title,
                            url=url or "",
                            snippet=snippet,
                            position=i + 1,
                        ))
                except Exception:
                    continue
            
            return results
        
        except Exception as e:
            logger.error(f"Google search failed: {e}")
            return []
    
    async def get_page_content(self, selector: Optional[str] = None) -> str:
        """
        Get page content.
        
        Args:
            selector: Optional CSS selector to get specific content.
            
        Returns:
            Page text content.
        """
        if not self._page:
            return ""
        
        try:
            if selector:
                element = await self._page.query_selector(selector)
                if element:
                    return await element.inner_text()
                return ""
            else:
                return await self._page.inner_text("body")
        
        except Exception as e:
            logger.error(f"Failed to get content: {e}")
            return ""
    
    async def take_screenshot(
        self,
        path: Optional[Path] = None,
        full_page: bool = False,
    ) -> Optional[Path]:
        """
        Take a screenshot.
        
        Args:
            path: Path to save screenshot.
            full_page: Capture full page.
            
        Returns:
            Path to screenshot.
        """
        if not self._page:
            return None
        
        try:
            if path is None:
                path = Path.home() / "Desktop" / f"screenshot_{int(time.time())}.png"
            
            await self._page.screenshot(path=str(path), full_page=full_page)
            logger.info(f"Screenshot saved: {path}")
            return path
        
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return None
    
    async def click(self, selector: str) -> bool:
        """Click an element."""
        if not self._page:
            return False
        
        try:
            await self._page.click(selector)
            return True
        except Exception as e:
            logger.error(f"Click failed: {e}")
            return False
    
    async def type_text(self, selector: str, text: str, delay: int = 50) -> bool:
        """Type text into an element."""
        if not self._page:
            return False
        
        try:
            await self._page.fill(selector, "")  # Clear first
            await self._page.type(selector, text, delay=delay)
            return True
        except Exception as e:
            logger.error(f"Type failed: {e}")
            return False
    
    async def press_key(self, key: str) -> bool:
        """Press a keyboard key."""
        if not self._page:
            return False
        
        try:
            await self._page.keyboard.press(key)
            return True
        except Exception as e:
            logger.error(f"Key press failed: {e}")
            return False


class GoogleDocsController:
    """
    Google Docs automation controller.
    
    Features:
    - Create new documents
    - Open existing documents
    - Dictate content
    - Basic formatting
    """
    
    def __init__(self, browser: BrowserController):
        """
        Initialize Google Docs controller.
        
        Args:
            browser: Browser controller instance.
        """
        self.browser = browser
    
    async def create_document(self, title: Optional[str] = None) -> Optional[str]:
        """
        Create a new Google Doc.
        
        Args:
            title: Optional document title.
            
        Returns:
            Document URL if successful.
        """
        if not self.browser._page:
            return None
        
        try:
            # Navigate to Google Docs
            await self.browser.navigate("https://docs.google.com/document/create")
            
            # Wait for editor to load
            await self.browser._page.wait_for_selector("div.kix-appview-editor", timeout=15000)
            
            # Set title if provided
            if title:
                # Click on title area
                title_input = await self.browser._page.query_selector("input.docs-title-input")
                if title_input:
                    await title_input.fill(title)
                    await self.browser._page.keyboard.press("Enter")
            
            return self.browser._page.url
        
        except Exception as e:
            logger.error(f"Failed to create document: {e}")
            return None
    
    async def open_document(self, url: str) -> bool:
        """
        Open an existing Google Doc.
        
        Args:
            url: Document URL.
            
        Returns:
            True if successful.
        """
        try:
            result = await self.browser.navigate(url)
            if result:
                await self.browser._page.wait_for_selector("div.kix-appview-editor", timeout=15000)
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to open document: {e}")
            return False
    
    async def type_content(self, text: str) -> bool:
        """
        Type content into the document.
        
        Args:
            text: Text to type.
            
        Returns:
            True if successful.
        """
        if not self.browser._page:
            return False
        
        try:
            # Click on editor to focus
            editor = await self.browser._page.query_selector("div.kix-appview-editor")
            if editor:
                await editor.click()
            
            # Type text
            await self.browser._page.keyboard.type(text, delay=20)
            return True
        
        except Exception as e:
            logger.error(f"Failed to type content: {e}")
            return False
    
    async def format_bold(self) -> bool:
        """Apply bold formatting to selection."""
        return await self.browser.press_key("Control+b")
    
    async def format_italic(self) -> bool:
        """Apply italic formatting to selection."""
        return await self.browser.press_key("Control+i")
    
    async def format_heading(self, level: int = 1) -> bool:
        """Apply heading formatting."""
        if not self.browser._page:
            return False
        
        try:
            # Use keyboard shortcut
            await self.browser._page.keyboard.press(f"Control+Alt+{level}")
            return True
        except Exception:
            return False
    
    async def insert_newline(self) -> bool:
        """Insert a new line."""
        return await self.browser.press_key("Enter")


class WebResearcher:
    """
    Web research automation.
    
    Features:
    - Multi-source search
    - Content extraction
    - Result summarization
    """
    
    def __init__(self, browser: BrowserController):
        """
        Initialize web researcher.
        
        Args:
            browser: Browser controller instance.
        """
        self.browser = browser
    
    async def research(
        self,
        query: str,
        num_sources: int = 3,
        extract_content: bool = True,
    ) -> Dict[str, Any]:
        """
        Perform web research on a topic.
        
        Args:
            query: Research query.
            num_sources: Number of sources to check.
            extract_content: Extract content from pages.
            
        Returns:
            Research results.
        """
        results = {
            "query": query,
            "sources": [],
            "content": [],
        }
        
        try:
            # Search Google
            search_results = await self.browser.search_google(query, num_sources)
            
            for result in search_results:
                source = {
                    "title": result.title,
                    "url": result.url,
                    "snippet": result.snippet,
                }
                results["sources"].append(source)
                
                # Extract content if requested
                if extract_content and result.url:
                    await self.browser.navigate(result.url)
                    content = await self.browser.get_page_content()
                    
                    # Truncate content
                    if len(content) > 5000:
                        content = content[:5000] + "..."
                    
                    results["content"].append({
                        "url": result.url,
                        "content": content,
                    })
            
            return results
        
        except Exception as e:
            logger.error(f"Research failed: {e}")
            results["error"] = str(e)
            return results


class BrowserManager:
    """
    High-level browser management for JARVIS.
    
    Provides simple interface for common browser operations.
    """
    
    def __init__(
        self,
        user_data_dir: Optional[Path] = None,
        headless: bool = False,
    ):
        """
        Initialize browser manager.
        
        Args:
            user_data_dir: Directory for browser profile.
            headless: Run headless.
        """
        self.browser = BrowserController(
            browser_type=BrowserType.CHROMIUM,
            headless=headless,
            user_data_dir=user_data_dir,
        )
        self.docs = GoogleDocsController(self.browser)
        self.researcher = WebResearcher(self.browser)
        
        self._started = False
    
    async def start(self) -> bool:
        """Start the browser."""
        if self._started:
            return True
        
        self._started = await self.browser.start()
        return self._started
    
    async def stop(self) -> None:
        """Stop the browser."""
        await self.browser.stop()
        self._started = False
    
    async def open_url(self, url: str) -> bool:
        """Open a URL."""
        if not self._started:
            await self.start()
        
        result = await self.browser.navigate(url)
        return result is not None
    
    async def google_search(self, query: str) -> List[SearchResult]:
        """Search Google."""
        if not self._started:
            await self.start()
        
        return await self.browser.search_google(query)
    
    async def create_google_doc(self, title: Optional[str] = None) -> Optional[str]:
        """Create a new Google Doc."""
        if not self._started:
            await self.start()
        
        return await self.docs.create_document(title)
    
    async def dictate_to_doc(self, text: str) -> bool:
        """Type text into current Google Doc."""
        return await self.docs.type_content(text)
    
    async def research_topic(self, query: str) -> Dict[str, Any]:
        """Research a topic."""
        if not self._started:
            await self.start()
        
        return await self.researcher.research(query)
    
    async def screenshot(self, path: Optional[Path] = None) -> Optional[Path]:
        """Take a screenshot."""
        return await self.browser.take_screenshot(path)


def run_browser_sync(coro):
    """Run async browser operation synchronously."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
