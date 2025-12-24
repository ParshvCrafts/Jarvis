"""
Investment Portfolio Tracker for JARVIS.

Track investment holdings:
- Add/remove holdings
- Track performance
- Asset allocation
- Rebalancing suggestions
- Dividend tracking
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
class Holding:
    id: Optional[int] = None
    symbol: str = ""
    shares: float = 0.0
    cost_basis: float = 0.0  # Total cost
    purchase_date: Optional[date] = None
    account_type: str = "taxable"  # taxable, roth_ira, traditional_ira, 401k
    notes: str = ""
    
    @property
    def cost_per_share(self) -> float:
        return self.cost_basis / self.shares if self.shares > 0 else 0
    
    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Holding":
        return cls(
            id=row["id"],
            symbol=row["symbol"],
            shares=row["shares"],
            cost_basis=row["cost_basis"],
            purchase_date=date.fromisoformat(row["purchase_date"]) if row["purchase_date"] else None,
            account_type=row["account_type"] or "taxable",
            notes=row["notes"] or "",
        )


@dataclass
class PortfolioSummary:
    total_value: float = 0.0
    total_cost: float = 0.0
    total_gain: float = 0.0
    total_gain_percent: float = 0.0
    holdings: List[Dict[str, Any]] = field(default_factory=list)


class PortfolioTracker:
    """
    Investment portfolio tracking.
    
    Features:
    - Track holdings across accounts
    - Real-time valuation
    - Performance tracking
    - Asset allocation
    - Rebalancing suggestions
    """
    
    # Target allocation for a young investor
    DEFAULT_ALLOCATION = {
        "US Stocks": 70,
        "International Stocks": 20,
        "Bonds": 10,
    }
    
    # Asset class mapping
    ASSET_CLASSES = {
        "VTI": "US Stocks",
        "VOO": "US Stocks",
        "FNILX": "US Stocks",
        "FZROX": "US Stocks",
        "FXAIX": "US Stocks",
        "SPY": "US Stocks",
        "QQQ": "US Stocks",
        "VXUS": "International Stocks",
        "FZILX": "International Stocks",
        "IXUS": "International Stocks",
        "BND": "Bonds",
        "FXNAX": "Bonds",
        "AGG": "Bonds",
        "BNDX": "International Bonds",
    }
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_dir / "portfolio.db"
        
        self._init_db()
        logger.info("Portfolio Tracker initialized")
    
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS holdings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    shares REAL NOT NULL,
                    cost_basis REAL NOT NULL,
                    purchase_date TEXT,
                    account_type TEXT DEFAULT 'taxable',
                    notes TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    transaction_type TEXT NOT NULL,
                    shares REAL NOT NULL,
                    price REAL NOT NULL,
                    date TEXT NOT NULL,
                    account_type TEXT DEFAULT 'taxable',
                    notes TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS dividends (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    amount REAL NOT NULL,
                    date TEXT NOT NULL,
                    reinvested INTEGER DEFAULT 0
                )
            """)
            conn.commit()
    
    def add_holding(
        self,
        symbol: str,
        shares: float,
        price: float,
        account_type: str = "taxable",
        purchase_date: Optional[str] = None,
        notes: str = "",
    ) -> str:
        """Add a new holding or add to existing position."""
        symbol = symbol.upper()
        cost_basis = shares * price
        pdate = purchase_date or date.today().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            # Check if holding exists in same account
            existing = conn.execute(
                "SELECT id, shares, cost_basis FROM holdings WHERE symbol = ? AND account_type = ?",
                (symbol, account_type)
            ).fetchone()
            
            if existing:
                # Add to existing position
                new_shares = existing[1] + shares
                new_cost = existing[2] + cost_basis
                conn.execute(
                    "UPDATE holdings SET shares = ?, cost_basis = ? WHERE id = ?",
                    (new_shares, new_cost, existing[0])
                )
            else:
                # Create new holding
                conn.execute("""
                    INSERT INTO holdings (symbol, shares, cost_basis, purchase_date, account_type, notes)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (symbol, shares, cost_basis, pdate, account_type, notes))
            
            # Record transaction
            conn.execute("""
                INSERT INTO transactions (symbol, transaction_type, shares, price, date, account_type, notes)
                VALUES (?, 'buy', ?, ?, ?, ?, ?)
            """, (symbol, shares, price, pdate, account_type, notes))
            
            conn.commit()
        
        return f"✅ Added {shares} shares of {symbol} at ${price:.2f}/share (${cost_basis:.2f} total)"
    
    def sell_holding(
        self,
        symbol: str,
        shares: float,
        price: float,
        account_type: str = "taxable",
    ) -> str:
        """Sell shares from a holding."""
        symbol = symbol.upper()
        
        with sqlite3.connect(self.db_path) as conn:
            existing = conn.execute(
                "SELECT id, shares, cost_basis FROM holdings WHERE symbol = ? AND account_type = ?",
                (symbol, account_type)
            ).fetchone()
            
            if not existing:
                return f"No {symbol} holdings found in {account_type} account."
            
            if existing[1] < shares:
                return f"Not enough shares. You have {existing[1]} shares of {symbol}."
            
            # Calculate cost basis for sold shares (average cost method)
            cost_per_share = existing[2] / existing[1]
            sold_cost_basis = shares * cost_per_share
            proceeds = shares * price
            gain = proceeds - sold_cost_basis
            
            new_shares = existing[1] - shares
            new_cost = existing[2] - sold_cost_basis
            
            if new_shares <= 0:
                conn.execute("DELETE FROM holdings WHERE id = ?", (existing[0],))
            else:
                conn.execute(
                    "UPDATE holdings SET shares = ?, cost_basis = ? WHERE id = ?",
                    (new_shares, new_cost, existing[0])
                )
            
            # Record transaction
            conn.execute("""
                INSERT INTO transactions (symbol, transaction_type, shares, price, date, account_type)
                VALUES (?, 'sell', ?, ?, ?, ?)
            """, (symbol, shares, price, date.today().isoformat(), account_type))
            
            conn.commit()
        
        gain_str = f"+${gain:.2f}" if gain >= 0 else f"-${abs(gain):.2f}"
        return f"✅ Sold {shares} shares of {symbol} at ${price:.2f} (Gain/Loss: {gain_str})"
    
    def get_holdings(self, account_type: Optional[str] = None) -> List[Holding]:
        """Get all holdings, optionally filtered by account type."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            if account_type:
                rows = conn.execute(
                    "SELECT * FROM holdings WHERE account_type = ? ORDER BY symbol",
                    (account_type,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM holdings ORDER BY account_type, symbol"
                ).fetchall()
        
        return [Holding.from_row(row) for row in rows]
    
    def get_portfolio_value(self) -> PortfolioSummary:
        """Get current portfolio value with real-time prices."""
        holdings = self.get_holdings()
        
        if not holdings:
            return PortfolioSummary()
        
        summary = PortfolioSummary()
        
        for holding in holdings:
            current_price = self._get_current_price(holding.symbol)
            current_value = holding.shares * current_price
            gain = current_value - holding.cost_basis
            gain_pct = (gain / holding.cost_basis * 100) if holding.cost_basis > 0 else 0
            
            summary.holdings.append({
                "symbol": holding.symbol,
                "shares": holding.shares,
                "cost_basis": holding.cost_basis,
                "current_price": current_price,
                "current_value": current_value,
                "gain": gain,
                "gain_percent": gain_pct,
                "account_type": holding.account_type,
            })
            
            summary.total_value += current_value
            summary.total_cost += holding.cost_basis
        
        summary.total_gain = summary.total_value - summary.total_cost
        summary.total_gain_percent = (
            (summary.total_gain / summary.total_cost * 100)
            if summary.total_cost > 0 else 0
        )
        
        return summary
    
    def _get_current_price(self, symbol: str) -> float:
        """Get current price for a symbol."""
        if not YFINANCE_AVAILABLE:
            return 0.0
        
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.fast_info
            return info.get('lastPrice', 0)
        except Exception as e:
            logger.debug(f"Failed to get price for {symbol}: {e}")
            return 0.0
    
    def format_portfolio(self) -> str:
        """Format portfolio for display."""
        summary = self.get_portfolio_value()
        
        if not summary.holdings:
            return """📊 **Your Portfolio**

No holdings yet.

**To add holdings:**
"Add 10 shares of VTI at $220"
"Add 5 shares VOO at $500 to Roth IRA"

**Recommended starter portfolio:**
- VTI or FZROX (Total US Market)
- VXUS or FZILX (International)
"""
        
        lines = [
            "📊 **Your Portfolio**\n",
            f"💰 **Total Value:** ${summary.total_value:,.2f}",
            f"📈 **Total Gain/Loss:** ${summary.total_gain:,.2f} ({'+' if summary.total_gain >= 0 else ''}{summary.total_gain_percent:.2f}%)\n",
            "**Holdings:**",
        ]
        
        # Group by account type
        by_account = {}
        for h in summary.holdings:
            acc = h["account_type"]
            if acc not in by_account:
                by_account[acc] = []
            by_account[acc].append(h)
        
        account_emoji = {
            "taxable": "💳",
            "roth_ira": "🌟",
            "traditional_ira": "📦",
            "401k": "🏢",
        }
        
        for account, holdings in by_account.items():
            emoji = account_emoji.get(account, "📁")
            lines.append(f"\n{emoji} **{account.replace('_', ' ').title()}:**")
            
            for h in holdings:
                arrow = "📈" if h["gain"] >= 0 else "📉"
                lines.append(
                    f"  {arrow} **{h['symbol']}**: {h['shares']:.2f} shares @ ${h['current_price']:.2f}"
                )
                lines.append(
                    f"      Value: ${h['current_value']:,.2f} ({'+' if h['gain'] >= 0 else ''}{h['gain_percent']:.1f}%)"
                )
        
        return "\n".join(lines)
    
    def get_asset_allocation(self) -> str:
        """Get current asset allocation."""
        summary = self.get_portfolio_value()
        
        if not summary.holdings:
            return "No holdings to analyze."
        
        # Calculate allocation by asset class
        allocation = {}
        for h in summary.holdings:
            asset_class = self.ASSET_CLASSES.get(h["symbol"], "Other")
            if asset_class not in allocation:
                allocation[asset_class] = 0
            allocation[asset_class] += h["current_value"]
        
        lines = [
            "📊 **Asset Allocation**\n",
            f"Total Portfolio: ${summary.total_value:,.2f}\n",
        ]
        
        for asset_class, value in sorted(allocation.items(), key=lambda x: x[1], reverse=True):
            pct = (value / summary.total_value * 100) if summary.total_value > 0 else 0
            target = self.DEFAULT_ALLOCATION.get(asset_class, 0)
            diff = pct - target
            
            status = "✅" if abs(diff) <= 5 else "⚠️"
            lines.append(f"{status} **{asset_class}:** {pct:.1f}% (${value:,.2f})")
            if target > 0:
                lines.append(f"    Target: {target}% (diff: {'+' if diff >= 0 else ''}{diff:.1f}%)")
        
        return "\n".join(lines)
    
    def should_rebalance(self) -> str:
        """Check if portfolio needs rebalancing."""
        summary = self.get_portfolio_value()
        
        if not summary.holdings:
            return "No holdings to rebalance."
        
        # Calculate current allocation
        allocation = {}
        for h in summary.holdings:
            asset_class = self.ASSET_CLASSES.get(h["symbol"], "Other")
            if asset_class not in allocation:
                allocation[asset_class] = 0
            allocation[asset_class] += h["current_value"]
        
        # Check deviations
        needs_rebalance = False
        suggestions = []
        
        for asset_class, target_pct in self.DEFAULT_ALLOCATION.items():
            current_value = allocation.get(asset_class, 0)
            current_pct = (current_value / summary.total_value * 100) if summary.total_value > 0 else 0
            diff = current_pct - target_pct
            
            if abs(diff) > 5:  # 5% threshold
                needs_rebalance = True
                if diff > 0:
                    suggestions.append(f"  • Sell some {asset_class} ({current_pct:.1f}% → {target_pct}%)")
                else:
                    suggestions.append(f"  • Buy more {asset_class} ({current_pct:.1f}% → {target_pct}%)")
        
        if not needs_rebalance:
            return """✅ **Portfolio is Balanced!**

Your allocation is within 5% of targets. No rebalancing needed.

**Tip:** Check quarterly or when adding new money."""
        
        lines = [
            "⚠️ **Rebalancing Suggested**\n",
            "Your portfolio has drifted from target allocation:\n",
        ] + suggestions + [
            "\n**Options:**",
            "1. Sell overweight assets, buy underweight",
            "2. Direct new contributions to underweight assets",
            "3. Wait for natural rebalancing (if close)",
            "\n*Consider tax implications before selling in taxable accounts.*",
        ]
        
        return "\n".join(lines)
    
    def record_dividend(self, symbol: str, amount: float, reinvested: bool = False) -> str:
        """Record a dividend payment."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO dividends (symbol, amount, date, reinvested)
                VALUES (?, ?, ?, ?)
            """, (symbol.upper(), amount, date.today().isoformat(), int(reinvested)))
            conn.commit()
        
        action = "reinvested" if reinvested else "received"
        return f"✅ Recorded ${amount:.2f} dividend from {symbol} ({action})"
    
    def get_dividend_summary(self, year: Optional[int] = None) -> str:
        """Get dividend summary."""
        year = year or date.today().year
        start = f"{year}-01-01"
        end = f"{year}-12-31"
        
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT symbol, SUM(amount) as total, COUNT(*) as count
                FROM dividends
                WHERE date >= ? AND date <= ?
                GROUP BY symbol
            """, (start, end)).fetchall()
            
            total = conn.execute("""
                SELECT SUM(amount) FROM dividends
                WHERE date >= ? AND date <= ?
            """, (start, end)).fetchone()[0] or 0
        
        if not rows:
            return f"No dividends recorded for {year}."
        
        lines = [
            f"💰 **Dividend Summary ({year})**\n",
            f"**Total Dividends:** ${total:,.2f}\n",
            "**By Symbol:**",
        ]
        
        for symbol, amount, count in rows:
            lines.append(f"  • {symbol}: ${amount:.2f} ({count} payments)")
        
        return "\n".join(lines)
    
    def investment_performance(self) -> str:
        """Get detailed investment performance."""
        summary = self.get_portfolio_value()
        
        if not summary.holdings:
            return "No holdings to analyze."
        
        lines = [
            "📈 **Investment Performance**\n",
            f"💰 **Total Invested:** ${summary.total_cost:,.2f}",
            f"💵 **Current Value:** ${summary.total_value:,.2f}",
            f"📊 **Total Return:** ${summary.total_gain:,.2f} ({'+' if summary.total_gain >= 0 else ''}{summary.total_gain_percent:.2f}%)\n",
            "**Individual Holdings:**\n",
        ]
        
        # Sort by gain percentage
        sorted_holdings = sorted(summary.holdings, key=lambda x: x["gain_percent"], reverse=True)
        
        for h in sorted_holdings:
            emoji = "🏆" if h["gain_percent"] > 20 else "📈" if h["gain_percent"] > 0 else "📉"
            lines.append(f"{emoji} **{h['symbol']}**")
            lines.append(f"   Cost: ${h['cost_basis']:,.2f} → Value: ${h['current_value']:,.2f}")
            lines.append(f"   Return: {'+' if h['gain'] >= 0 else ''}${h['gain']:,.2f} ({'+' if h['gain_percent'] >= 0 else ''}{h['gain_percent']:.1f}%)")
        
        return "\n".join(lines)
