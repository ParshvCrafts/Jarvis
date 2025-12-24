"""
Expense Tracker for JARVIS.

Simple student budget management:
- Track income and expenses
- Budget by category
- Spending alerts
- Trends and summaries
"""

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger


class ExpenseCategory(Enum):
    FOOD = "food"
    TRANSPORTATION = "transportation"
    BOOKS = "books"
    ENTERTAINMENT = "entertainment"
    SUBSCRIPTIONS = "subscriptions"
    PERSONAL = "personal"
    HOUSING = "housing"
    UTILITIES = "utilities"
    HEALTH = "health"
    CLOTHING = "clothing"
    MISC = "misc"


@dataclass
class Expense:
    id: Optional[int] = None
    date: date = field(default_factory=date.today)
    amount: float = 0.0
    category: ExpenseCategory = ExpenseCategory.MISC
    description: str = ""
    is_income: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    
    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Expense":
        return cls(
            id=row["id"],
            date=date.fromisoformat(row["date"]),
            amount=row["amount"],
            category=ExpenseCategory(row["category"]),
            description=row["description"] or "",
            is_income=bool(row["is_income"]),
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
        )


@dataclass
class Budget:
    id: Optional[int] = None
    category: ExpenseCategory = ExpenseCategory.MISC
    monthly_limit: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    
    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Budget":
        return cls(
            id=row["id"],
            category=ExpenseCategory(row["category"]),
            monthly_limit=row["monthly_limit"],
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
        )


class ExpenseTracker:
    """
    Student expense tracking system.
    
    Features:
    - Log expenses and income
    - Category budgets
    - Spending alerts
    - Weekly/monthly summaries
    """
    
    # Default budgets for students
    DEFAULT_BUDGETS = {
        ExpenseCategory.FOOD: 400,
        ExpenseCategory.TRANSPORTATION: 100,
        ExpenseCategory.BOOKS: 150,
        ExpenseCategory.ENTERTAINMENT: 100,
        ExpenseCategory.SUBSCRIPTIONS: 50,
        ExpenseCategory.PERSONAL: 75,
        ExpenseCategory.MISC: 100,
    }
    
    # Category aliases for voice commands
    CATEGORY_ALIASES = {
        "food": ExpenseCategory.FOOD,
        "lunch": ExpenseCategory.FOOD,
        "dinner": ExpenseCategory.FOOD,
        "breakfast": ExpenseCategory.FOOD,
        "groceries": ExpenseCategory.FOOD,
        "coffee": ExpenseCategory.FOOD,
        "snacks": ExpenseCategory.FOOD,
        "transport": ExpenseCategory.TRANSPORTATION,
        "transportation": ExpenseCategory.TRANSPORTATION,
        "uber": ExpenseCategory.TRANSPORTATION,
        "lyft": ExpenseCategory.TRANSPORTATION,
        "bart": ExpenseCategory.TRANSPORTATION,
        "bus": ExpenseCategory.TRANSPORTATION,
        "gas": ExpenseCategory.TRANSPORTATION,
        "books": ExpenseCategory.BOOKS,
        "textbook": ExpenseCategory.BOOKS,
        "supplies": ExpenseCategory.BOOKS,
        "entertainment": ExpenseCategory.ENTERTAINMENT,
        "movies": ExpenseCategory.ENTERTAINMENT,
        "games": ExpenseCategory.ENTERTAINMENT,
        "concert": ExpenseCategory.ENTERTAINMENT,
        "subscription": ExpenseCategory.SUBSCRIPTIONS,
        "subscriptions": ExpenseCategory.SUBSCRIPTIONS,
        "netflix": ExpenseCategory.SUBSCRIPTIONS,
        "spotify": ExpenseCategory.SUBSCRIPTIONS,
        "personal": ExpenseCategory.PERSONAL,
        "haircut": ExpenseCategory.PERSONAL,
        "clothes": ExpenseCategory.CLOTHING,
        "clothing": ExpenseCategory.CLOTHING,
        "health": ExpenseCategory.HEALTH,
        "medicine": ExpenseCategory.HEALTH,
        "doctor": ExpenseCategory.HEALTH,
        "rent": ExpenseCategory.HOUSING,
        "housing": ExpenseCategory.HOUSING,
        "utilities": ExpenseCategory.UTILITIES,
        "electric": ExpenseCategory.UTILITIES,
        "internet": ExpenseCategory.UTILITIES,
    }
    
    def __init__(
        self,
        data_dir: str = "data",
        currency: str = "USD",
        monthly_budget: float = 1000,
        budget_threshold: int = 80,
    ):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_dir / "expenses.db"
        
        self.currency = currency
        self.monthly_budget = monthly_budget
        self.budget_threshold = budget_threshold
        
        self._init_db()
        logger.info("Expense Tracker initialized")
    
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    amount REAL NOT NULL,
                    category TEXT NOT NULL,
                    description TEXT,
                    is_income INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS budgets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL UNIQUE,
                    monthly_limit REAL NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            conn.commit()
    
    def _detect_category(self, description: str) -> ExpenseCategory:
        """Detect category from description."""
        desc_lower = description.lower()
        
        for keyword, category in self.CATEGORY_ALIASES.items():
            if keyword in desc_lower:
                return category
        
        return ExpenseCategory.MISC
    
    def log_expense(
        self,
        amount: float,
        description: str = "",
        category: Optional[str] = None,
        expense_date: Optional[str] = None,
    ) -> str:
        """Log an expense."""
        # Detect or parse category
        if category:
            try:
                cat = ExpenseCategory(category.lower())
            except ValueError:
                cat = self.CATEGORY_ALIASES.get(category.lower(), ExpenseCategory.MISC)
        else:
            cat = self._detect_category(description)
        
        exp_date = date.fromisoformat(expense_date) if expense_date else date.today()
        
        expense = Expense(
            date=exp_date,
            amount=amount,
            category=cat,
            description=description,
            is_income=False,
        )
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO expenses (date, amount, category, description, is_income, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                expense.date.isoformat(), expense.amount, expense.category.value,
                expense.description, int(expense.is_income), expense.created_at.isoformat()
            ))
            expense.id = cursor.lastrowid
            conn.commit()
        
        # Check budget status
        alert = self._check_budget_alert(cat)
        
        result = f"💸 Logged ${amount:.2f} for {cat.value.title()}"
        if description:
            result += f" ({description})"
        
        if alert:
            result += f"\n{alert}"
        
        return result
    
    def log_income(
        self,
        amount: float,
        description: str = "",
        income_date: Optional[str] = None,
    ) -> str:
        """Log income."""
        inc_date = date.fromisoformat(income_date) if income_date else date.today()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO expenses (date, amount, category, description, is_income, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                inc_date.isoformat(), amount, "misc", description, 1, datetime.now().isoformat()
            ))
            conn.commit()
        
        return f"💰 Logged income: ${amount:.2f}" + (f" ({description})" if description else "")
    
    def _check_budget_alert(self, category: ExpenseCategory) -> Optional[str]:
        """Check if spending is approaching budget limit."""
        budget = self.get_budget(category)
        if not budget:
            return None
        
        spent = self.get_monthly_spending(category)
        percentage = (spent / budget.monthly_limit) * 100 if budget.monthly_limit > 0 else 0
        
        if percentage >= 100:
            return f"⚠️ You've exceeded your {category.value} budget! (${spent:.2f}/${budget.monthly_limit:.2f})"
        elif percentage >= self.budget_threshold:
            return f"⚠️ You've spent {percentage:.0f}% of your {category.value} budget (${spent:.2f}/${budget.monthly_limit:.2f})"
        
        return None
    
    def set_budget(self, category: str, limit: float) -> str:
        """Set monthly budget for a category."""
        try:
            cat = ExpenseCategory(category.lower())
        except ValueError:
            cat = self.CATEGORY_ALIASES.get(category.lower())
            if not cat:
                return f"Unknown category: {category}"
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO budgets (category, monthly_limit, created_at)
                VALUES (?, ?, ?)
                ON CONFLICT(category) DO UPDATE SET monthly_limit = excluded.monthly_limit
            """, (cat.value, limit, datetime.now().isoformat()))
            conn.commit()
        
        return f"✅ Set {cat.value.title()} budget to ${limit:.2f}/month"
    
    def get_budget(self, category: ExpenseCategory) -> Optional[Budget]:
        """Get budget for a category."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM budgets WHERE category = ?",
                (category.value,)
            ).fetchone()
            
            if row:
                return Budget.from_row(row)
            
            # Return default if exists
            if category in self.DEFAULT_BUDGETS:
                return Budget(
                    category=category,
                    monthly_limit=self.DEFAULT_BUDGETS[category]
                )
        
        return None
    
    def get_monthly_spending(self, category: Optional[ExpenseCategory] = None) -> float:
        """Get total spending for current month."""
        today = date.today()
        month_start = date(today.year, today.month, 1).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            if category:
                result = conn.execute("""
                    SELECT COALESCE(SUM(amount), 0) FROM expenses 
                    WHERE date >= ? AND is_income = 0 AND category = ?
                """, (month_start, category.value)).fetchone()[0]
            else:
                result = conn.execute("""
                    SELECT COALESCE(SUM(amount), 0) FROM expenses 
                    WHERE date >= ? AND is_income = 0
                """, (month_start,)).fetchone()[0]
        
        return result
    
    def get_weekly_spending(self) -> float:
        """Get total spending for current week."""
        today = date.today()
        week_start = (today - timedelta(days=today.weekday())).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute("""
                SELECT COALESCE(SUM(amount), 0) FROM expenses 
                WHERE date >= ? AND is_income = 0
            """, (week_start,)).fetchone()[0]
        
        return result
    
    def get_spending_by_category(self, days: int = 30) -> Dict[str, float]:
        """Get spending breakdown by category."""
        cutoff = (date.today() - timedelta(days=days)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("""
                SELECT category, SUM(amount) as total FROM expenses 
                WHERE date >= ? AND is_income = 0
                GROUP BY category
                ORDER BY total DESC
            """, (cutoff,)).fetchall()
        
        return {row[0]: row[1] for row in rows}
    
    def get_budget_status(self) -> str:
        """Get overall budget status."""
        today = date.today()
        month_start = date(today.year, today.month, 1)
        days_in_month = 30  # Approximate
        days_passed = (today - month_start).days + 1
        
        total_spent = self.get_monthly_spending()
        total_income = self._get_monthly_income()
        
        # Get spending by category
        spending = self.get_spending_by_category(days=days_passed)
        
        lines = [
            "💰 **Budget Status**\n",
            f"📅 Month: {today.strftime('%B %Y')}",
            f"💵 Income: ${total_income:.2f}",
            f"💸 Spent: ${total_spent:.2f}",
            f"💳 Remaining: ${total_income - total_spent:.2f}\n",
            "**By Category:**",
        ]
        
        for cat_value, amount in spending.items():
            try:
                cat = ExpenseCategory(cat_value)
                budget = self.get_budget(cat)
                if budget:
                    pct = (amount / budget.monthly_limit) * 100
                    bar = self._progress_bar(pct)
                    lines.append(f"  {cat.value.title()}: ${amount:.2f}/${budget.monthly_limit:.2f} {bar}")
                else:
                    lines.append(f"  {cat.value.title()}: ${amount:.2f}")
            except ValueError:
                lines.append(f"  {cat_value}: ${amount:.2f}")
        
        return "\n".join(lines)
    
    def _progress_bar(self, percentage: float, width: int = 10) -> str:
        """Create a text progress bar."""
        filled = int(width * min(percentage, 100) / 100)
        empty = width - filled
        
        if percentage >= 100:
            return f"[{'█' * width}] ⚠️ {percentage:.0f}%"
        elif percentage >= 80:
            return f"[{'█' * filled}{'░' * empty}] ⚠️ {percentage:.0f}%"
        else:
            return f"[{'█' * filled}{'░' * empty}] {percentage:.0f}%"
    
    def _get_monthly_income(self) -> float:
        """Get total income for current month."""
        today = date.today()
        month_start = date(today.year, today.month, 1).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute("""
                SELECT COALESCE(SUM(amount), 0) FROM expenses 
                WHERE date >= ? AND is_income = 1
            """, (month_start,)).fetchone()[0]
        
        return result or self.monthly_budget
    
    def get_recent_expenses(self, limit: int = 10) -> List[Expense]:
        """Get recent expenses."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM expenses 
                WHERE is_income = 0
                ORDER BY date DESC, created_at DESC
                LIMIT ?
            """, (limit,)).fetchall()
        
        return [Expense.from_row(row) for row in rows]
    
    def format_expenses(self, expenses: List[Expense]) -> str:
        """Format expenses for display."""
        if not expenses:
            return "No expenses recorded."
        
        lines = ["📋 **Recent Expenses**\n"]
        
        current_date = None
        for exp in expenses:
            if exp.date != current_date:
                current_date = exp.date
                lines.append(f"\n**{exp.date.strftime('%b %d, %Y')}**")
            
            lines.append(f"  • ${exp.amount:.2f} - {exp.category.value.title()}" + 
                        (f" ({exp.description})" if exp.description else ""))
        
        return "\n".join(lines)
    
    def get_weekly_summary(self) -> str:
        """Get weekly spending summary."""
        weekly = self.get_weekly_spending()
        spending = self.get_spending_by_category(days=7)
        
        lines = [
            "📊 **This Week's Spending**\n",
            f"Total: ${weekly:.2f}\n",
            "**Breakdown:**",
        ]
        
        for cat, amount in sorted(spending.items(), key=lambda x: x[1], reverse=True):
            pct = (amount / weekly * 100) if weekly > 0 else 0
            lines.append(f"  • {cat.title()}: ${amount:.2f} ({pct:.0f}%)")
        
        return "\n".join(lines)
    
    def compare_to_last_month(self) -> str:
        """Compare spending to last month."""
        today = date.today()
        
        # This month
        month_start = date(today.year, today.month, 1)
        this_month = self.get_monthly_spending()
        
        # Last month
        if today.month == 1:
            last_month_start = date(today.year - 1, 12, 1)
            last_month_end = date(today.year - 1, 12, 31)
        else:
            last_month_start = date(today.year, today.month - 1, 1)
            last_month_end = month_start - timedelta(days=1)
        
        with sqlite3.connect(self.db_path) as conn:
            last_month = conn.execute("""
                SELECT COALESCE(SUM(amount), 0) FROM expenses 
                WHERE date >= ? AND date <= ? AND is_income = 0
            """, (last_month_start.isoformat(), last_month_end.isoformat())).fetchone()[0]
        
        diff = this_month - last_month
        pct_change = ((this_month - last_month) / last_month * 100) if last_month > 0 else 0
        
        emoji = "📈" if diff > 0 else "📉" if diff < 0 else "➡️"
        
        return f"""📊 **Month Comparison**

Last month: ${last_month:.2f}
This month: ${this_month:.2f}
{emoji} Change: ${abs(diff):.2f} ({'+' if diff > 0 else ''}{pct_change:.1f}%)"""
