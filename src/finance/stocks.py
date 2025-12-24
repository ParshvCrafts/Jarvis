"""
Stock & Market Data for JARVIS.

Real-time stock prices and market data using yfinance:
- Current stock prices
- Daily change (% and $)
- 52-week high/low
- Company info
- Market indices
- Personal watchlist
"""

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    yf = None


@dataclass
class StockQuote:
    symbol: str
    name: str = ""
    price: float = 0.0
    change: float = 0.0
    change_percent: float = 0.0
    volume: int = 0
    market_cap: float = 0.0
    pe_ratio: Optional[float] = None
    dividend_yield: Optional[float] = None
    week_52_high: float = 0.0
    week_52_low: float = 0.0
    day_high: float = 0.0
    day_low: float = 0.0
    open_price: float = 0.0
    prev_close: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def is_up(self) -> bool:
        return self.change >= 0
    
    def format_price(self) -> str:
        """Format price with change indicator."""
        arrow = "📈" if self.is_up else "📉"
        sign = "+" if self.is_up else ""
        return f"{arrow} ${self.price:.2f} ({sign}{self.change_percent:.2f}%)"


@dataclass
class MarketIndex:
    symbol: str
    name: str
    value: float = 0.0
    change: float = 0.0
    change_percent: float = 0.0


class MarketData:
    """Market data and indices."""
    
    # Major market indices
    INDICES = {
        "^GSPC": "S&P 500",
        "^DJI": "Dow Jones",
        "^IXIC": "NASDAQ",
        "^RUT": "Russell 2000",
        "^VIX": "VIX (Volatility)",
    }
    
    @classmethod
    def get_market_summary(cls) -> str:
        """Get summary of major market indices."""
        if not YFINANCE_AVAILABLE:
            return "Market data unavailable (yfinance not installed)"
        
        lines = ["📊 **Market Summary**\n"]
        
        for symbol, name in cls.INDICES.items():
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.fast_info
                
                price = info.get('lastPrice', 0)
                prev_close = info.get('previousClose', price)
                change = price - prev_close
                change_pct = (change / prev_close * 100) if prev_close else 0
                
                arrow = "📈" if change >= 0 else "📉"
                sign = "+" if change >= 0 else ""
                
                lines.append(f"{arrow} **{name}**: {price:,.2f} ({sign}{change_pct:.2f}%)")
            except Exception as e:
                logger.debug(f"Failed to get {symbol}: {e}")
                lines.append(f"⚪ **{name}**: Data unavailable")
        
        return "\n".join(lines)


class StockTracker:
    """
    Stock tracking and watchlist management.
    
    Features:
    - Real-time stock prices via yfinance
    - Personal watchlist
    - Price alerts
    - Historical data
    """
    
    # Default watchlist for students (low-cost index funds)
    DEFAULT_WATCHLIST = [
        ("VTI", "Vanguard Total Stock Market ETF"),
        ("VOO", "Vanguard S&P 500 ETF"),
        ("VXUS", "Vanguard Total International Stock ETF"),
        ("BND", "Vanguard Total Bond Market ETF"),
        ("FNILX", "Fidelity ZERO Large Cap Index"),
        ("FZROX", "Fidelity ZERO Total Market Index"),
    ]
    
    # Popular stocks for quick lookup
    POPULAR_STOCKS = {
        "apple": "AAPL",
        "google": "GOOGL",
        "alphabet": "GOOGL",
        "microsoft": "MSFT",
        "amazon": "AMZN",
        "tesla": "TSLA",
        "nvidia": "NVDA",
        "meta": "META",
        "facebook": "META",
        "netflix": "NFLX",
        "disney": "DIS",
        "berkshire": "BRK-B",
        "jpmorgan": "JPM",
        "visa": "V",
        "mastercard": "MA",
    }
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_dir / "stocks.db"
        
        self._init_db()
        self._init_watchlist()
        
        logger.info("Stock Tracker initialized")
    
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS watchlist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL UNIQUE,
                    name TEXT,
                    notes TEXT,
                    added_date TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS price_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    target_price REAL NOT NULL,
                    alert_type TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL
                )
            """)
            conn.commit()
    
    def _init_watchlist(self):
        """Initialize default watchlist if empty."""
        with sqlite3.connect(self.db_path) as conn:
            count = conn.execute("SELECT COUNT(*) FROM watchlist").fetchone()[0]
            if count == 0:
                for symbol, name in self.DEFAULT_WATCHLIST:
                    conn.execute(
                        "INSERT INTO watchlist (symbol, name, added_date) VALUES (?, ?, ?)",
                        (symbol, name, datetime.now().isoformat())
                    )
                conn.commit()
    
    def _resolve_symbol(self, query: str) -> str:
        """Resolve company name to stock symbol."""
        query_lower = query.lower().strip()
        
        # Check popular stocks mapping
        if query_lower in self.POPULAR_STOCKS:
            return self.POPULAR_STOCKS[query_lower]
        
        # Already a symbol (uppercase, short)
        if query.isupper() and len(query) <= 5:
            return query
        
        # Return as-is (user might have typed symbol)
        return query.upper()
    
    def get_quote(self, symbol: str) -> Optional[StockQuote]:
        """Get real-time quote for a stock."""
        if not YFINANCE_AVAILABLE:
            logger.warning("yfinance not available")
            return None
        
        symbol = self._resolve_symbol(symbol)
        
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            fast_info = ticker.fast_info
            
            # Get price data
            price = fast_info.get('lastPrice', info.get('currentPrice', 0))
            prev_close = fast_info.get('previousClose', info.get('previousClose', price))
            change = price - prev_close
            change_pct = (change / prev_close * 100) if prev_close else 0
            
            quote = StockQuote(
                symbol=symbol,
                name=info.get('shortName', info.get('longName', symbol)),
                price=price,
                change=change,
                change_percent=change_pct,
                volume=fast_info.get('lastVolume', 0),
                market_cap=info.get('marketCap', 0),
                pe_ratio=info.get('trailingPE'),
                dividend_yield=info.get('dividendYield'),
                week_52_high=info.get('fiftyTwoWeekHigh', 0),
                week_52_low=info.get('fiftyTwoWeekLow', 0),
                day_high=info.get('dayHigh', 0),
                day_low=info.get('dayLow', 0),
                open_price=info.get('open', 0),
                prev_close=prev_close,
            )
            
            return quote
            
        except Exception as e:
            logger.error(f"Failed to get quote for {symbol}: {e}")
            return None
    
    def format_quote(self, quote: StockQuote) -> str:
        """Format a stock quote for display."""
        arrow = "📈" if quote.is_up else "📉"
        sign = "+" if quote.is_up else ""
        
        lines = [
            f"{arrow} **{quote.symbol}** - {quote.name}",
            f"",
            f"💵 **Price:** ${quote.price:.2f} ({sign}${quote.change:.2f}, {sign}{quote.change_percent:.2f}%)",
            f"📊 **Day Range:** ${quote.day_low:.2f} - ${quote.day_high:.2f}",
            f"📈 **52-Week Range:** ${quote.week_52_low:.2f} - ${quote.week_52_high:.2f}",
        ]
        
        if quote.market_cap:
            cap_str = self._format_large_number(quote.market_cap)
            lines.append(f"🏢 **Market Cap:** {cap_str}")
        
        if quote.pe_ratio:
            lines.append(f"📐 **P/E Ratio:** {quote.pe_ratio:.2f}")
        
        if quote.dividend_yield:
            lines.append(f"💰 **Dividend Yield:** {quote.dividend_yield * 100:.2f}%")
        
        return "\n".join(lines)
    
    def _format_large_number(self, num: float) -> str:
        """Format large numbers (billions, millions)."""
        if num >= 1e12:
            return f"${num/1e12:.2f}T"
        elif num >= 1e9:
            return f"${num/1e9:.2f}B"
        elif num >= 1e6:
            return f"${num/1e6:.2f}M"
        else:
            return f"${num:,.0f}"
    
    def get_stock_price(self, symbol: str) -> str:
        """Get formatted stock price for voice response."""
        quote = self.get_quote(symbol)
        if not quote:
            return f"Sorry, I couldn't find data for {symbol}."
        
        return self.format_quote(quote)
    
    def add_to_watchlist(self, symbol: str, notes: str = "") -> str:
        """Add a stock to watchlist."""
        symbol = self._resolve_symbol(symbol)
        
        # Verify symbol exists
        quote = self.get_quote(symbol)
        if not quote:
            return f"Couldn't verify {symbol}. Please check the symbol."
        
        with sqlite3.connect(self.db_path) as conn:
            try:
                conn.execute(
                    "INSERT INTO watchlist (symbol, name, notes, added_date) VALUES (?, ?, ?, ?)",
                    (symbol, quote.name, notes, datetime.now().isoformat())
                )
                conn.commit()
                return f"✅ Added {symbol} ({quote.name}) to your watchlist!"
            except sqlite3.IntegrityError:
                return f"{symbol} is already on your watchlist."
    
    def remove_from_watchlist(self, symbol: str) -> str:
        """Remove a stock from watchlist."""
        symbol = self._resolve_symbol(symbol)
        
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute(
                "DELETE FROM watchlist WHERE symbol = ?",
                (symbol,)
            )
            conn.commit()
            
            if result.rowcount > 0:
                return f"✅ Removed {symbol} from your watchlist."
            return f"{symbol} wasn't on your watchlist."
    
    def get_watchlist(self) -> List[Tuple[str, str]]:
        """Get all stocks in watchlist."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT symbol, name FROM watchlist ORDER BY symbol"
            ).fetchall()
        return rows
    
    def get_watchlist_summary(self) -> str:
        """Get formatted watchlist with current prices."""
        watchlist = self.get_watchlist()
        
        if not watchlist:
            return "Your watchlist is empty. Add stocks with 'add [symbol] to watchlist'."
        
        lines = ["👀 **Your Watchlist**\n"]
        
        for symbol, name in watchlist:
            quote = self.get_quote(symbol)
            if quote:
                arrow = "📈" if quote.is_up else "📉"
                sign = "+" if quote.is_up else ""
                lines.append(f"{arrow} **{symbol}**: ${quote.price:.2f} ({sign}{quote.change_percent:.2f}%)")
            else:
                lines.append(f"⚪ **{symbol}**: Data unavailable")
        
        return "\n".join(lines)
    
    def compare_stocks(self, symbol1: str, symbol2: str) -> str:
        """Compare two stocks."""
        quote1 = self.get_quote(symbol1)
        quote2 = self.get_quote(symbol2)
        
        if not quote1 or not quote2:
            return "Couldn't get data for one or both stocks."
        
        lines = [
            f"📊 **{quote1.symbol} vs {quote2.symbol}**\n",
            f"| Metric | {quote1.symbol} | {quote2.symbol} |",
            f"|--------|---------|---------|",
            f"| Price | ${quote1.price:.2f} | ${quote2.price:.2f} |",
            f"| Day Change | {'+' if quote1.is_up else ''}{quote1.change_percent:.2f}% | {'+' if quote2.is_up else ''}{quote2.change_percent:.2f}% |",
        ]
        
        if quote1.pe_ratio and quote2.pe_ratio:
            lines.append(f"| P/E Ratio | {quote1.pe_ratio:.2f} | {quote2.pe_ratio:.2f} |")
        
        if quote1.dividend_yield and quote2.dividend_yield:
            lines.append(f"| Dividend | {quote1.dividend_yield*100:.2f}% | {quote2.dividend_yield*100:.2f}% |")
        
        return "\n".join(lines)
    
    def set_price_alert(self, symbol: str, target_price: float, alert_type: str = "above") -> str:
        """Set a price alert for a stock."""
        symbol = self._resolve_symbol(symbol)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO price_alerts (symbol, target_price, alert_type, created_at)
                VALUES (?, ?, ?, ?)
            """, (symbol, target_price, alert_type, datetime.now().isoformat()))
            conn.commit()
        
        return f"✅ Alert set: Notify when {symbol} goes {alert_type} ${target_price:.2f}"
    
    def check_alerts(self) -> List[str]:
        """Check if any price alerts have triggered."""
        triggered = []
        
        with sqlite3.connect(self.db_path) as conn:
            alerts = conn.execute(
                "SELECT id, symbol, target_price, alert_type FROM price_alerts WHERE is_active = 1"
            ).fetchall()
            
            for alert_id, symbol, target, alert_type in alerts:
                quote = self.get_quote(symbol)
                if not quote:
                    continue
                
                if alert_type == "above" and quote.price >= target:
                    triggered.append(f"🔔 {symbol} is now ${quote.price:.2f} (above ${target:.2f})")
                    conn.execute("UPDATE price_alerts SET is_active = 0 WHERE id = ?", (alert_id,))
                elif alert_type == "below" and quote.price <= target:
                    triggered.append(f"🔔 {symbol} is now ${quote.price:.2f} (below ${target:.2f})")
                    conn.execute("UPDATE price_alerts SET is_active = 0 WHERE id = ?", (alert_id,))
            
            conn.commit()
        
        return triggered
