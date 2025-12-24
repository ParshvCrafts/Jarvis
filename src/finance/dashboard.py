"""
Financial Health Dashboard for JARVIS.

Track key financial metrics:
- Net worth
- Savings rate
- Emergency fund status
- Investment portfolio value
- Monthly cash flow
"""

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger


@dataclass
class FinancialSnapshot:
    date: date
    total_assets: float = 0.0
    total_liabilities: float = 0.0
    net_worth: float = 0.0
    monthly_income: float = 0.0
    monthly_expenses: float = 0.0
    savings_rate: float = 0.0
    emergency_fund: float = 0.0
    investment_value: float = 0.0
    
    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "FinancialSnapshot":
        return cls(
            date=date.fromisoformat(row["date"]),
            total_assets=row["total_assets"] or 0,
            total_liabilities=row["total_liabilities"] or 0,
            net_worth=row["net_worth"] or 0,
            monthly_income=row["monthly_income"] or 0,
            monthly_expenses=row["monthly_expenses"] or 0,
            savings_rate=row["savings_rate"] or 0,
            emergency_fund=row["emergency_fund"] or 0,
            investment_value=row["investment_value"] or 0,
        )


@dataclass
class FinancialGoal:
    id: Optional[int] = None
    name: str = ""
    target_amount: float = 0.0
    current_amount: float = 0.0
    deadline: Optional[date] = None
    priority: int = 1
    category: str = "savings"
    
    @property
    def progress(self) -> float:
        if self.target_amount <= 0:
            return 0
        return min(100, (self.current_amount / self.target_amount) * 100)
    
    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "FinancialGoal":
        return cls(
            id=row["id"],
            name=row["name"],
            target_amount=row["target_amount"],
            current_amount=row["current_amount"] or 0,
            deadline=date.fromisoformat(row["deadline"]) if row["deadline"] else None,
            priority=row["priority"] or 1,
            category=row["category"] or "savings",
        )


class FinancialDashboard:
    """
    Financial health tracking dashboard.
    
    Features:
    - Net worth tracking
    - Savings rate calculation
    - Goal tracking
    - Financial health score
    """
    
    # Financial health benchmarks
    BENCHMARKS = {
        "emergency_fund_months": 6,
        "savings_rate_good": 20,
        "savings_rate_excellent": 50,
        "debt_to_income_good": 36,
    }
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_dir / "financial_dashboard.db"
        
        self._init_db()
        logger.info("Financial Dashboard initialized")
    
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL UNIQUE,
                    total_assets REAL DEFAULT 0,
                    total_liabilities REAL DEFAULT 0,
                    net_worth REAL DEFAULT 0,
                    monthly_income REAL DEFAULT 0,
                    monthly_expenses REAL DEFAULT 0,
                    savings_rate REAL DEFAULT 0,
                    emergency_fund REAL DEFAULT 0,
                    investment_value REAL DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS goals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    target_amount REAL NOT NULL,
                    current_amount REAL DEFAULT 0,
                    deadline TEXT,
                    priority INTEGER DEFAULT 1,
                    category TEXT DEFAULT 'savings'
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    balance REAL DEFAULT 0,
                    is_asset INTEGER DEFAULT 1,
                    last_updated TEXT
                )
            """)
            conn.commit()
    
    def update_snapshot(
        self,
        total_assets: Optional[float] = None,
        total_liabilities: Optional[float] = None,
        monthly_income: Optional[float] = None,
        monthly_expenses: Optional[float] = None,
        emergency_fund: Optional[float] = None,
        investment_value: Optional[float] = None,
    ) -> str:
        """Update today's financial snapshot."""
        today = date.today().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            # Get existing snapshot or create new
            existing = conn.execute(
                "SELECT * FROM snapshots WHERE date = ?", (today,)
            ).fetchone()
            
            if existing:
                # Update existing
                updates = []
                params = []
                
                if total_assets is not None:
                    updates.append("total_assets = ?")
                    params.append(total_assets)
                if total_liabilities is not None:
                    updates.append("total_liabilities = ?")
                    params.append(total_liabilities)
                if monthly_income is not None:
                    updates.append("monthly_income = ?")
                    params.append(monthly_income)
                if monthly_expenses is not None:
                    updates.append("monthly_expenses = ?")
                    params.append(monthly_expenses)
                if emergency_fund is not None:
                    updates.append("emergency_fund = ?")
                    params.append(emergency_fund)
                if investment_value is not None:
                    updates.append("investment_value = ?")
                    params.append(investment_value)
                
                if updates:
                    # Calculate derived values
                    assets = total_assets if total_assets is not None else existing[2]
                    liabilities = total_liabilities if total_liabilities is not None else existing[3]
                    income = monthly_income if monthly_income is not None else existing[5]
                    expenses = monthly_expenses if monthly_expenses is not None else existing[6]
                    
                    net_worth = assets - liabilities
                    savings_rate = ((income - expenses) / income * 100) if income > 0 else 0
                    
                    updates.extend(["net_worth = ?", "savings_rate = ?"])
                    params.extend([net_worth, savings_rate])
                    
                    params.append(today)
                    conn.execute(
                        f"UPDATE snapshots SET {', '.join(updates)} WHERE date = ?",
                        params
                    )
            else:
                # Create new
                assets = total_assets or 0
                liabilities = total_liabilities or 0
                income = monthly_income or 0
                expenses = monthly_expenses or 0
                net_worth = assets - liabilities
                savings_rate = ((income - expenses) / income * 100) if income > 0 else 0
                
                conn.execute("""
                    INSERT INTO snapshots (date, total_assets, total_liabilities, net_worth,
                        monthly_income, monthly_expenses, savings_rate, emergency_fund, investment_value)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    today, assets, liabilities, net_worth,
                    income, expenses, savings_rate,
                    emergency_fund or 0, investment_value or 0
                ))
            
            conn.commit()
        
        return "✅ Financial snapshot updated!"
    
    def get_latest_snapshot(self) -> Optional[FinancialSnapshot]:
        """Get the most recent financial snapshot."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM snapshots ORDER BY date DESC LIMIT 1"
            ).fetchone()
            
            if row:
                return FinancialSnapshot.from_row(row)
        return None
    
    def get_financial_health(self) -> str:
        """Get comprehensive financial health summary."""
        snapshot = self.get_latest_snapshot()
        
        if not snapshot:
            return """📊 **Financial Health Dashboard**

No financial data recorded yet.

**To get started, update your numbers:**
- "Update net worth: assets $X, liabilities $Y"
- "Monthly income: $X"
- "Monthly expenses: $X"
- "Emergency fund: $X"
- "Investment value: $X"

*Track your progress over time!*"""
        
        # Calculate health score
        health_score = self._calculate_health_score(snapshot)
        health_emoji = "🟢" if health_score >= 80 else "🟡" if health_score >= 60 else "🔴"
        
        lines = [
            f"📊 **Financial Health Dashboard**",
            f"",
            f"{health_emoji} **Health Score: {health_score}/100**",
            f"",
            f"💰 **Net Worth:** ${snapshot.net_worth:,.2f}",
            f"   Assets: ${snapshot.total_assets:,.2f}",
            f"   Liabilities: ${snapshot.total_liabilities:,.2f}",
            f"",
            f"📈 **Monthly Cash Flow:**",
            f"   Income: ${snapshot.monthly_income:,.2f}",
            f"   Expenses: ${snapshot.monthly_expenses:,.2f}",
            f"   Savings: ${snapshot.monthly_income - snapshot.monthly_expenses:,.2f}",
            f"",
            f"💵 **Savings Rate:** {snapshot.savings_rate:.1f}%",
        ]
        
        # Savings rate assessment
        if snapshot.savings_rate >= 50:
            lines.append("   🔥 Excellent! FIRE territory!")
        elif snapshot.savings_rate >= 20:
            lines.append("   ✅ Good - on track for wealth building")
        elif snapshot.savings_rate >= 10:
            lines.append("   ⚠️ Okay - try to increase")
        else:
            lines.append("   🔴 Low - review expenses")
        
        lines.extend([
            f"",
            f"🏦 **Emergency Fund:** ${snapshot.emergency_fund:,.2f}",
        ])
        
        # Emergency fund assessment
        if snapshot.monthly_expenses > 0:
            months_covered = snapshot.emergency_fund / snapshot.monthly_expenses
            lines.append(f"   Covers {months_covered:.1f} months of expenses")
            if months_covered >= 6:
                lines.append("   ✅ Fully funded!")
            elif months_covered >= 3:
                lines.append("   ⚠️ Getting there - aim for 6 months")
            else:
                lines.append("   🔴 Priority: Build this up!")
        
        lines.extend([
            f"",
            f"📈 **Investments:** ${snapshot.investment_value:,.2f}",
            f"",
            f"*Last updated: {snapshot.date.strftime('%B %d, %Y')}*",
        ])
        
        return "\n".join(lines)
    
    def _calculate_health_score(self, snapshot: FinancialSnapshot) -> int:
        """Calculate overall financial health score (0-100)."""
        score = 0
        
        # Savings rate (0-30 points)
        if snapshot.savings_rate >= 50:
            score += 30
        elif snapshot.savings_rate >= 20:
            score += 25
        elif snapshot.savings_rate >= 10:
            score += 15
        elif snapshot.savings_rate > 0:
            score += 5
        
        # Emergency fund (0-25 points)
        if snapshot.monthly_expenses > 0:
            months = snapshot.emergency_fund / snapshot.monthly_expenses
            if months >= 6:
                score += 25
            elif months >= 3:
                score += 15
            elif months >= 1:
                score += 5
        
        # Net worth positive (0-20 points)
        if snapshot.net_worth > 0:
            score += 20
        elif snapshot.net_worth == 0:
            score += 10
        
        # Has investments (0-15 points)
        if snapshot.investment_value > 0:
            score += 15
        
        # Positive cash flow (0-10 points)
        if snapshot.monthly_income > snapshot.monthly_expenses:
            score += 10
        
        return min(100, score)
    
    def add_goal(
        self,
        name: str,
        target_amount: float,
        deadline: Optional[str] = None,
        category: str = "savings",
    ) -> str:
        """Add a financial goal."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO goals (name, target_amount, deadline, category)
                VALUES (?, ?, ?, ?)
            """, (name, target_amount, deadline, category))
            conn.commit()
        
        return f"✅ Goal added: {name} (${target_amount:,.2f})"
    
    def update_goal_progress(self, goal_name: str, current_amount: float) -> str:
        """Update progress on a goal."""
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute(
                "UPDATE goals SET current_amount = ? WHERE LOWER(name) LIKE ?",
                (current_amount, f"%{goal_name.lower()}%")
            )
            conn.commit()
            
            if result.rowcount == 0:
                return f"No goal found matching '{goal_name}'."
        
        return f"✅ Updated {goal_name}: ${current_amount:,.2f}"
    
    def get_goals(self) -> List[FinancialGoal]:
        """Get all financial goals."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM goals ORDER BY priority, deadline"
            ).fetchall()
        
        return [FinancialGoal.from_row(row) for row in rows]
    
    def format_goals(self) -> str:
        """Format goals for display."""
        goals = self.get_goals()
        
        if not goals:
            return """🎯 **Financial Goals**

No goals set yet.

**Suggested goals for students:**
- Emergency fund: $1,000 → $3,000
- Roth IRA: $7,000/year
- First investment: $100
- Pay off credit card

Add a goal: "Add goal: Emergency fund, $3000"
"""
        
        lines = ["🎯 **Financial Goals**\n"]
        
        for goal in goals:
            progress_bar = self._progress_bar(goal.progress)
            lines.append(f"**{goal.name}**")
            lines.append(f"  ${goal.current_amount:,.0f} / ${goal.target_amount:,.0f}")
            lines.append(f"  {progress_bar} {goal.progress:.0f}%")
            if goal.deadline:
                days_left = (goal.deadline - date.today()).days
                if days_left > 0:
                    lines.append(f"  ⏰ {days_left} days left")
                else:
                    lines.append(f"  ⚠️ Past deadline!")
            lines.append("")
        
        return "\n".join(lines)
    
    def _progress_bar(self, percentage: float, width: int = 10) -> str:
        """Create a text progress bar."""
        filled = int(width * min(percentage, 100) / 100)
        empty = width - filled
        return f"[{'█' * filled}{'░' * empty}]"
    
    def get_net_worth_history(self, months: int = 12) -> str:
        """Get net worth history."""
        cutoff = (date.today() - timedelta(days=months * 30)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT date, net_worth FROM snapshots 
                WHERE date >= ?
                ORDER BY date
            """, (cutoff,)).fetchall()
        
        if not rows:
            return "No net worth history available yet."
        
        lines = [f"📈 **Net Worth History ({months} months)**\n"]
        
        for row_date, net_worth in rows:
            d = date.fromisoformat(row_date)
            lines.append(f"  {d.strftime('%b %Y')}: ${net_worth:,.2f}")
        
        if len(rows) >= 2:
            first = rows[0][1]
            last = rows[-1][1]
            change = last - first
            pct = (change / abs(first) * 100) if first != 0 else 0
            
            emoji = "📈" if change >= 0 else "📉"
            lines.append(f"\n{emoji} **Change:** ${change:,.2f} ({'+' if change >= 0 else ''}{pct:.1f}%)")
        
        return "\n".join(lines)
    
    def am_i_on_track(self, age: int = 20) -> str:
        """Check if on track for financial milestones."""
        snapshot = self.get_latest_snapshot()
        
        # Age-based milestones
        milestones = {
            20: {"emergency_fund": 1000, "net_worth": 0, "investing": True},
            25: {"emergency_fund": 5000, "net_worth": 10000, "investing": True},
            30: {"emergency_fund": 10000, "net_worth": 50000, "investing": True},
        }
        
        target = milestones.get(age, milestones[20])
        
        lines = [f"🎯 **Am I On Track? (Age {age})**\n"]
        
        if not snapshot:
            lines.append("No financial data recorded. Update your numbers first!")
            return "\n".join(lines)
        
        # Emergency fund check
        ef_target = target["emergency_fund"]
        ef_status = "✅" if snapshot.emergency_fund >= ef_target else "⚠️"
        lines.append(f"{ef_status} **Emergency Fund:** ${snapshot.emergency_fund:,.0f} / ${ef_target:,.0f}")
        
        # Net worth check
        nw_target = target["net_worth"]
        nw_status = "✅" if snapshot.net_worth >= nw_target else "⚠️"
        lines.append(f"{nw_status} **Net Worth:** ${snapshot.net_worth:,.0f} / ${nw_target:,.0f}")
        
        # Investing check
        inv_status = "✅" if snapshot.investment_value > 0 else "⚠️"
        lines.append(f"{inv_status} **Investing:** {'Yes' if snapshot.investment_value > 0 else 'Not yet'}")
        
        # Savings rate check
        sr_status = "✅" if snapshot.savings_rate >= 20 else "⚠️"
        lines.append(f"{sr_status} **Savings Rate:** {snapshot.savings_rate:.1f}% (target: 20%+)")
        
        # Overall assessment
        checks_passed = sum([
            snapshot.emergency_fund >= ef_target,
            snapshot.net_worth >= nw_target,
            snapshot.investment_value > 0,
            snapshot.savings_rate >= 20,
        ])
        
        lines.append("")
        if checks_passed == 4:
            lines.append("🌟 **Excellent!** You're ahead of the game!")
        elif checks_passed >= 2:
            lines.append("👍 **Good progress!** Keep building those habits.")
        else:
            lines.append("💪 **Room to grow!** Focus on one area at a time.")
        
        return "\n".join(lines)
