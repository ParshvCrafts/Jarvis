"""
Real-Time Finance Advisor for JARVIS.

Fetches current market data before providing investment advice.
Ensures answers are based on live data, not static content.
"""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    logger.warning("yfinance not installed. Run: pip install yfinance")


@dataclass
class MarketContext:
    """Current market conditions for informed advice."""
    # Major indices
    sp500_price: float = 0.0
    sp500_change_pct: float = 0.0
    nasdaq_price: float = 0.0
    nasdaq_change_pct: float = 0.0
    dow_price: float = 0.0
    dow_change_pct: float = 0.0
    
    # Market sentiment
    vix: float = 0.0  # Volatility index
    market_trend: str = "neutral"  # bullish, bearish, neutral
    
    # Specific stock (if queried)
    stock_symbol: Optional[str] = None
    stock_price: float = 0.0
    stock_change_pct: float = 0.0
    stock_52w_high: float = 0.0
    stock_52w_low: float = 0.0
    stock_pe_ratio: Optional[float] = None
    stock_dividend_yield: Optional[float] = None
    
    # Timestamp
    fetched_at: datetime = None
    
    def __post_init__(self):
        if self.fetched_at is None:
            self.fetched_at = datetime.now()
    
    def get_market_summary(self) -> str:
        """Get formatted market summary."""
        lines = []
        
        # S&P 500
        arrow = "📈" if self.sp500_change_pct >= 0 else "📉"
        lines.append(f"{arrow} S&P 500: ${self.sp500_price:,.2f} ({'+' if self.sp500_change_pct >= 0 else ''}{self.sp500_change_pct:.2f}%)")
        
        # NASDAQ
        arrow = "📈" if self.nasdaq_change_pct >= 0 else "📉"
        lines.append(f"{arrow} NASDAQ: ${self.nasdaq_price:,.2f} ({'+' if self.nasdaq_change_pct >= 0 else ''}{self.nasdaq_change_pct:.2f}%)")
        
        # Dow
        arrow = "📈" if self.dow_change_pct >= 0 else "📉"
        lines.append(f"{arrow} Dow Jones: ${self.dow_price:,.2f} ({'+' if self.dow_change_pct >= 0 else ''}{self.dow_change_pct:.2f}%)")
        
        # VIX
        if self.vix > 0:
            vix_status = "Low volatility" if self.vix < 15 else "Moderate volatility" if self.vix < 25 else "High volatility"
            lines.append(f"📊 VIX: {self.vix:.1f} ({vix_status})")
        
        return "\n".join(lines)
    
    def get_stock_summary(self) -> str:
        """Get formatted stock summary."""
        if not self.stock_symbol:
            return ""
        
        lines = []
        arrow = "📈" if self.stock_change_pct >= 0 else "📉"
        lines.append(f"{arrow} **{self.stock_symbol}**: ${self.stock_price:.2f} ({'+' if self.stock_change_pct >= 0 else ''}{self.stock_change_pct:.2f}%)")
        
        # 52-week range
        if self.stock_52w_high > 0:
            pct_from_high = ((self.stock_price - self.stock_52w_high) / self.stock_52w_high) * 100
            lines.append(f"   52-week range: ${self.stock_52w_low:.2f} - ${self.stock_52w_high:.2f}")
            lines.append(f"   Currently {abs(pct_from_high):.1f}% {'below' if pct_from_high < 0 else 'above'} 52-week high")
        
        # Valuation
        if self.stock_pe_ratio:
            lines.append(f"   P/E Ratio: {self.stock_pe_ratio:.1f}")
        
        if self.stock_dividend_yield:
            lines.append(f"   Dividend Yield: {self.stock_dividend_yield:.2f}%")
        
        return "\n".join(lines)


class RealTimeAdvisor:
    """
    Provides investment advice backed by real-time market data.
    
    Instead of giving generic advice, fetches current data first
    and provides context-aware recommendations.
    """
    
    def __init__(self, llm_router=None):
        """
        Initialize advisor.
        
        Args:
            llm_router: Optional LLM router for synthesizing advice
        """
        self.llm_router = llm_router
        self._cache: Dict[str, Tuple[Any, datetime]] = {}
        self._cache_ttl = timedelta(minutes=5)
    
    def _get_cached(self, key: str) -> Optional[Any]:
        """Get cached value if not expired."""
        if key in self._cache:
            value, timestamp = self._cache[key]
            if datetime.now() - timestamp < self._cache_ttl:
                return value
        return None
    
    def _set_cached(self, key: str, value: Any):
        """Cache a value."""
        self._cache[key] = (value, datetime.now())
    
    def get_market_context(self, symbol: Optional[str] = None) -> MarketContext:
        """
        Fetch current market conditions.
        
        Args:
            symbol: Optional specific stock to include
            
        Returns:
            MarketContext with current data
        """
        if not YFINANCE_AVAILABLE:
            logger.warning("yfinance not available, returning empty context")
            return MarketContext()
        
        context = MarketContext()
        
        try:
            # Fetch major indices
            indices = {
                "^GSPC": ("sp500_price", "sp500_change_pct"),  # S&P 500
                "^IXIC": ("nasdaq_price", "nasdaq_change_pct"),  # NASDAQ
                "^DJI": ("dow_price", "dow_change_pct"),  # Dow Jones
                "^VIX": ("vix", None),  # Volatility
            }
            
            for ticker_symbol, (price_attr, change_attr) in indices.items():
                cached = self._get_cached(ticker_symbol)
                if cached:
                    price, change = cached
                else:
                    try:
                        ticker = yf.Ticker(ticker_symbol)
                        info = ticker.fast_info
                        price = info.get('lastPrice', 0) or info.get('regularMarketPrice', 0)
                        prev = info.get('previousClose', price)
                        change = ((price - prev) / prev * 100) if prev else 0
                        self._set_cached(ticker_symbol, (price, change))
                    except Exception as e:
                        logger.debug(f"Failed to fetch {ticker_symbol}: {e}")
                        price, change = 0, 0
                
                setattr(context, price_attr, price)
                if change_attr:
                    setattr(context, change_attr, change)
            
            # Determine market trend
            avg_change = (context.sp500_change_pct + context.nasdaq_change_pct + context.dow_change_pct) / 3
            if avg_change > 0.5:
                context.market_trend = "bullish"
            elif avg_change < -0.5:
                context.market_trend = "bearish"
            else:
                context.market_trend = "neutral"
            
            # Fetch specific stock if requested
            if symbol:
                context = self._add_stock_data(context, symbol)
            
        except Exception as e:
            logger.error(f"Error fetching market context: {e}")
        
        return context
    
    def _add_stock_data(self, context: MarketContext, symbol: str) -> MarketContext:
        """Add specific stock data to context."""
        try:
            symbol = symbol.upper()
            cached = self._get_cached(f"stock_{symbol}")
            
            if cached:
                context.stock_symbol = symbol
                context.stock_price = cached.get('price', 0)
                context.stock_change_pct = cached.get('change', 0)
                context.stock_52w_high = cached.get('52w_high', 0)
                context.stock_52w_low = cached.get('52w_low', 0)
                context.stock_pe_ratio = cached.get('pe', None)
                context.stock_dividend_yield = cached.get('div_yield', None)
            else:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                fast_info = ticker.fast_info
                
                context.stock_symbol = symbol
                context.stock_price = fast_info.get('lastPrice', 0) or info.get('regularMarketPrice', 0)
                prev = fast_info.get('previousClose', context.stock_price)
                context.stock_change_pct = ((context.stock_price - prev) / prev * 100) if prev else 0
                context.stock_52w_high = info.get('fiftyTwoWeekHigh', 0)
                context.stock_52w_low = info.get('fiftyTwoWeekLow', 0)
                context.stock_pe_ratio = info.get('trailingPE', None)
                context.stock_dividend_yield = info.get('dividendYield', None)
                if context.stock_dividend_yield:
                    context.stock_dividend_yield *= 100  # Convert to percentage
                
                # Cache the data
                self._set_cached(f"stock_{symbol}", {
                    'price': context.stock_price,
                    'change': context.stock_change_pct,
                    '52w_high': context.stock_52w_high,
                    '52w_low': context.stock_52w_low,
                    'pe': context.stock_pe_ratio,
                    'div_yield': context.stock_dividend_yield,
                })
                
        except Exception as e:
            logger.error(f"Error fetching stock {symbol}: {e}")
        
        return context
    
    def should_buy_stock(self, symbol: str) -> str:
        """
        Provide advice on whether to buy a specific stock.
        Uses real-time data to inform the recommendation.
        
        Args:
            symbol: Stock symbol to analyze
            
        Returns:
            Informed advice with current data
        """
        context = self.get_market_context(symbol)
        
        if not context.stock_price:
            return f"Unable to fetch data for {symbol.upper()}. Please verify the ticker symbol."
        
        lines = [
            f"## {symbol.upper()} Analysis",
            "",
            context.get_stock_summary(),
            "",
            "### Current Market Context",
            context.get_market_summary(),
            "",
            "### Analysis",
        ]
        
        # Price position analysis
        if context.stock_52w_high > 0:
            pct_from_high = ((context.stock_price - context.stock_52w_high) / context.stock_52w_high) * 100
            pct_from_low = ((context.stock_price - context.stock_52w_low) / context.stock_52w_low) * 100
            
            if pct_from_high > -5:
                lines.append(f"- **Near 52-week high**: The stock is trading near its yearly peak. This could mean strong momentum, but also limited upside in the short term.")
            elif pct_from_high < -20:
                lines.append(f"- **Significant pullback**: Down {abs(pct_from_high):.1f}% from 52-week high. Could be a buying opportunity if fundamentals are strong, or a warning sign.")
            else:
                lines.append(f"- **Mid-range**: Trading in the middle of its 52-week range.")
        
        # Valuation analysis
        if context.stock_pe_ratio:
            if context.stock_pe_ratio < 15:
                lines.append(f"- **Valuation**: P/E of {context.stock_pe_ratio:.1f} suggests relatively cheap valuation.")
            elif context.stock_pe_ratio > 30:
                lines.append(f"- **Valuation**: P/E of {context.stock_pe_ratio:.1f} indicates premium valuation. Growth expectations are high.")
            else:
                lines.append(f"- **Valuation**: P/E of {context.stock_pe_ratio:.1f} is in normal range.")
        
        # Market conditions
        if context.vix > 25:
            lines.append(f"- **High volatility**: VIX at {context.vix:.1f} indicates market uncertainty. Consider smaller position sizes.")
        elif context.vix < 15:
            lines.append(f"- **Low volatility**: VIX at {context.vix:.1f} indicates calm markets. Good for steady investing.")
        
        # Dividend
        if context.stock_dividend_yield and context.stock_dividend_yield > 2:
            lines.append(f"- **Income**: {context.stock_dividend_yield:.2f}% dividend yield provides income while you wait.")
        
        lines.extend([
            "",
            "### Recommendation",
        ])
        
        # Generate recommendation based on data
        if symbol.upper() in ["VTI", "VOO", "SPY", "VXUS", "VT"]:
            # Index funds - always reasonable for long-term
            lines.append(f"**{symbol.upper()}** is a diversified index fund, suitable for long-term investing regardless of current price.")
            lines.append("")
            lines.append("For index funds, the best strategy is:")
            lines.append("1. **Dollar-cost averaging**: Invest regularly regardless of price")
            lines.append("2. **Time in market > timing**: Don't wait for 'the perfect moment'")
            lines.append("3. **Stay consistent**: Market timing rarely works")
            
            if context.market_trend == "bearish":
                lines.append("")
                lines.append(f"*Current market is down, which historically has been a good time to buy index funds for long-term investors.*")
        else:
            # Individual stock
            lines.append(f"For individual stocks like **{symbol.upper()}**, consider:")
            lines.append("1. Does this fit your overall portfolio strategy?")
            lines.append("2. Are you comfortable with single-stock risk?")
            lines.append("3. Do you understand the business?")
            lines.append("")
            lines.append("*Remember: Most individual stock pickers underperform index funds over time.*")
        
        lines.extend([
            "",
            f"*Data as of {context.fetched_at.strftime('%Y-%m-%d %H:%M')}*",
        ])
        
        return "\n".join(lines)
    
    def should_invest_now(self) -> str:
        """
        Provide advice on whether now is a good time to invest.
        Uses real-time market data for context.
        
        Returns:
            Informed advice with current market conditions
        """
        context = self.get_market_context()
        
        lines = [
            "## Is Now a Good Time to Invest?",
            "",
            "### Current Market Conditions",
            context.get_market_summary(),
            "",
        ]
        
        # Market analysis
        if context.market_trend == "bullish":
            lines.append("📈 **Markets are up**: Positive momentum, but don't chase returns.")
        elif context.market_trend == "bearish":
            lines.append("📉 **Markets are down**: Historically, buying during downturns leads to better long-term returns.")
        else:
            lines.append("➡️ **Markets are flat**: No strong directional signal.")
        
        # Volatility analysis
        if context.vix > 30:
            lines.append(f"⚠️ **High volatility (VIX: {context.vix:.1f})**: Markets are nervous. Good for long-term buyers, but expect swings.")
        elif context.vix > 20:
            lines.append(f"📊 **Elevated volatility (VIX: {context.vix:.1f})**: Some uncertainty in markets.")
        else:
            lines.append(f"✅ **Low volatility (VIX: {context.vix:.1f})**: Markets are calm.")
        
        lines.extend([
            "",
            "### The Truth About Market Timing",
            "",
            "Research consistently shows:",
            "- **Time in market beats timing the market** - Missing the best 10 days can cut returns in half",
            "- **Nobody can predict short-term movements** - Not even professionals",
            "- **Dollar-cost averaging works** - Regular investing smooths out volatility",
            "",
            "### My Recommendation",
            "",
        ])
        
        # Personalized recommendation
        if context.market_trend == "bearish" and context.vix > 25:
            lines.append("**This could be a good buying opportunity.** Markets are down and volatile, which historically has been a good entry point for long-term investors.")
            lines.append("")
            lines.append("However, don't invest money you'll need in the next 5 years.")
        elif context.market_trend == "bullish" and context.sp500_change_pct > 1:
            lines.append("**Markets are hot right now.** Don't let FOMO drive your decisions.")
            lines.append("")
            lines.append("Stick to your regular investment schedule rather than making a large lump sum purchase.")
        else:
            lines.append("**There's no 'perfect' time to invest.** The best time was yesterday; the second best time is today.")
            lines.append("")
            lines.append("If you have money to invest for the long term, start now with a consistent plan.")
        
        lines.extend([
            "",
            "### Action Steps",
            "1. Ensure you have 3-6 months emergency fund first",
            "2. Max out any employer 401(k) match",
            "3. Invest in low-cost index funds (VTI, VOO, VXUS)",
            "4. Set up automatic monthly investments",
            "5. Don't check your portfolio daily",
            "",
            f"*Data as of {context.fetched_at.strftime('%Y-%m-%d %H:%M')}*",
        ])
        
        return "\n".join(lines)
    
    def get_market_update(self) -> str:
        """
        Get current market update with real-time data.
        
        Returns:
            Formatted market update
        """
        context = self.get_market_context()
        
        lines = [
            "## 📊 Market Update",
            f"*As of {context.fetched_at.strftime('%Y-%m-%d %H:%M')}*",
            "",
            context.get_market_summary(),
            "",
        ]
        
        # Market commentary
        if context.market_trend == "bullish":
            lines.append("**Overall**: Markets are positive today. 📈")
        elif context.market_trend == "bearish":
            lines.append("**Overall**: Markets are down today. 📉")
        else:
            lines.append("**Overall**: Markets are relatively flat today. ➡️")
        
        # Volatility commentary
        if context.vix > 25:
            lines.append(f"**Volatility**: Elevated (VIX: {context.vix:.1f}). Expect larger swings.")
        elif context.vix < 15:
            lines.append(f"**Volatility**: Low (VIX: {context.vix:.1f}). Markets are calm.")
        
        return "\n".join(lines)
    
    def analyze_portfolio_timing(self, symbols: List[str]) -> str:
        """
        Analyze current conditions for a list of holdings.
        
        Args:
            symbols: List of stock symbols
            
        Returns:
            Analysis of each holding with current data
        """
        context = self.get_market_context()
        
        lines = [
            "## Portfolio Analysis",
            f"*As of {context.fetched_at.strftime('%Y-%m-%d %H:%M')}*",
            "",
            "### Market Context",
            context.get_market_summary(),
            "",
            "### Holdings Analysis",
            "",
        ]
        
        for symbol in symbols[:10]:  # Limit to 10 to avoid rate limits
            stock_context = self.get_market_context(symbol)
            if stock_context.stock_price:
                lines.append(stock_context.get_stock_summary())
                lines.append("")
        
        return "\n".join(lines)
