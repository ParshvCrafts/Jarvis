"""
Finance Manager for JARVIS.

Orchestrates all financial features:
- Stock/Market Data
- Investment Education
- Retirement Guidance
- Savings Optimization
- Tax Strategies
- Credit Building
- Debt Strategies
- Money-Saving Tips
- Financial Dashboard
- Portfolio Tracking
"""

import re
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from .stocks import StockTracker, MarketData, YFINANCE_AVAILABLE
from .education import InvestmentEducation
from .retirement import RetirementAdvisor
from .savings import SavingsOptimizer
from .tax import TaxAdvisor
from .credit import CreditAdvisor
from .debt import DebtAdvisor
from .tips import MoneySavingTips
from .dashboard import FinancialDashboard
from .portfolio import PortfolioTracker
from .realtime_advisor import RealTimeAdvisor


class FinanceManager:
    """
    Orchestrates all financial features.
    
    Features:
    - Real-time stock prices
    - Investment education
    - Retirement planning
    - Savings optimization
    - Tax strategies
    - Credit building
    - Debt management
    - Money-saving tips
    - Financial dashboard
    - Portfolio tracking
    """
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        data_dir: str = "data",
    ):
        self.config = config or {}
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.stocks = StockTracker(data_dir=str(self.data_dir))
        self.education = InvestmentEducation()
        self.retirement = RetirementAdvisor()
        self.savings = SavingsOptimizer()
        self.tax = TaxAdvisor()
        self.credit = CreditAdvisor()
        self.debt = DebtAdvisor()
        self.tips = MoneySavingTips()
        self.dashboard = FinancialDashboard(data_dir=str(self.data_dir))
        self.portfolio = PortfolioTracker(data_dir=str(self.data_dir))
        self.realtime_advisor = RealTimeAdvisor()
        
        logger.info("Finance Manager initialized")
    
    # =========================================================================
    # Command Handling
    # =========================================================================
    
    async def handle_command(self, text: str) -> Optional[str]:
        """Route and handle finance-related commands."""
        text_lower = text.lower().strip()
        
        # Real-time advice commands (check first - these need live data)
        if self._is_realtime_advice_command(text_lower):
            return self._handle_realtime_advice(text_lower, text)
        
        # Stock/Market commands
        if self._is_stock_command(text_lower):
            return self._handle_stock(text_lower, text)
        
        # Investment education commands
        if self._is_education_command(text_lower):
            return self._handle_education(text_lower, text)
        
        # Retirement commands
        if self._is_retirement_command(text_lower):
            return self._handle_retirement(text_lower, text)
        
        # Savings commands
        if self._is_savings_command(text_lower):
            return self._handle_savings(text_lower, text)
        
        # Tax commands
        if self._is_tax_command(text_lower):
            return self._handle_tax(text_lower, text)
        
        # Credit commands
        if self._is_credit_command(text_lower):
            return self._handle_credit(text_lower, text)
        
        # Debt commands
        if self._is_debt_command(text_lower):
            return self._handle_debt(text_lower, text)
        
        # Money-saving tips commands
        if self._is_tips_command(text_lower):
            return self._handle_tips(text_lower, text)
        
        # Dashboard commands
        if self._is_dashboard_command(text_lower):
            return self._handle_dashboard(text_lower, text)
        
        # Portfolio commands
        if self._is_portfolio_command(text_lower):
            return self._handle_portfolio(text_lower, text)
        
        return None
    
    # =========================================================================
    # Command Detection
    # =========================================================================
    
    def _is_realtime_advice_command(self, text: str) -> bool:
        """Check if command needs real-time market data for advice."""
        patterns = [
            "should i buy", "should i invest", "is now a good time",
            "good time to invest", "good time to buy",
            "market update", "how's the market", "how is the market",
            "what's vti at", "what is vti at", "vti right now",
            "what's spy at", "what is spy at", "spy right now",
            "buy right now", "invest right now", "invest now",
        ]
        return any(p in text for p in patterns)
    
    def _is_stock_command(self, text: str) -> bool:
        patterns = [
            "stock price", "price of", "how is", "how's",
            "market summary", "watchlist", "add to watchlist",
            "compare", "vs", "stock", "ticker",
            "s&p", "nasdaq", "dow", "market today",
        ]
        # Check for stock symbols (uppercase 1-5 letters)
        has_symbol = bool(re.search(r'\b[A-Z]{1,5}\b', text.upper()))
        return any(p in text for p in patterns) or (has_symbol and "stock" in text)
    
    def _is_education_command(self, text: str) -> bool:
        patterns = [
            "investment advice", "investing advice", "why index",
            "dollar cost", "compound interest", "expense ratio",
            "should i invest", "best investment", "beginner invest",
            "individual stock", "etf", "what is", "explain",
            "investment tip", "how to invest",
        ]
        return any(p in text for p in patterns)
    
    def _is_retirement_command(self, text: str) -> bool:
        patterns = [
            "401k", "401(k)", "roth ira", "traditional ira",
            "retirement", "matching", "vesting", "target date",
            "how much to save", "contribution limit",
        ]
        return any(p in text for p in patterns)
    
    def _is_savings_command(self, text: str) -> bool:
        patterns = [
            "savings rate", "apy", "high yield", "hysa",
            "best savings", "sofi", "marcus", "ally",
            "emergency fund", "where to keep", "savings account",
            "interest rate", "compare savings",
        ]
        return any(p in text for p in patterns)
    
    def _is_tax_command(self, text: str) -> bool:
        patterns = [
            "tax", "taxes", "deduction", "capital gains",
            "tax loss", "harvesting", "tax bracket",
            "education credit", "aotc", "rich people",
            "avoid taxes", "reduce taxes",
        ]
        return any(p in text for p in patterns)
    
    def _is_credit_command(self, text: str) -> bool:
        patterns = [
            "credit score", "credit card", "build credit",
            "utilization", "fico", "authorized user",
            "first credit", "student card", "800 credit",
        ]
        return any(p in text for p in patterns)
    
    def _is_debt_command(self, text: str) -> bool:
        patterns = [
            "debt", "loan", "pay off", "student loan",
            "good debt", "bad debt", "leverage", "borrow",
            "rich people loan", "0% financing", "avalanche",
            "snowball",
        ]
        return any(p in text for p in patterns)
    
    def _is_tips_command(self, text: str) -> bool:
        patterns = [
            "save money", "money saving", "student discount",
            "free stuff", "subscription", "cash back",
            "negotiate", "food saving", "wealth habit",
        ]
        return any(p in text for p in patterns)
    
    def _is_dashboard_command(self, text: str) -> bool:
        patterns = [
            "financial health", "net worth", "savings rate",
            "am i on track", "financial goal", "update",
            "my finances", "financial summary", "dashboard",
        ]
        return any(p in text for p in patterns)
    
    def _is_portfolio_command(self, text: str) -> bool:
        patterns = [
            "portfolio", "my holdings", "add shares",
            "sell shares", "asset allocation", "rebalance",
            "dividend", "investment performance",
            "add.*shares.*at",  # "add 10 shares VTI at 220"
        ]
        import re
        for p in patterns:
            if ".*" in p:
                if re.search(p, text):
                    return True
            elif p in text:
                return True
        return False
    
    # =========================================================================
    # Command Handlers
    # =========================================================================
    
    def _handle_realtime_advice(self, text: str, original: str) -> str:
        """Handle advice commands that need real-time market data."""
        # Market update
        if "market update" in text or "how's the market" in text or "how is the market" in text:
            return self.realtime_advisor.get_market_update()
        
        # Should I invest now (general)
        if "should i invest" in text and "in" not in text.replace("invest in", ""):
            return self.realtime_advisor.should_invest_now()
        
        if "good time to invest" in text or "good time to buy" in text:
            return self.realtime_advisor.should_invest_now()
        
        if "invest now" in text or "invest right now" in text:
            return self.realtime_advisor.should_invest_now()
        
        # Should I buy [specific stock]
        buy_match = re.search(r'(?:should i buy|buy right now)\s+(\w+)', text)
        if buy_match:
            symbol = buy_match.group(1).upper()
            return self.realtime_advisor.should_buy_stock(symbol)
        
        # What's [symbol] at right now
        price_match = re.search(r"what(?:'s| is)\s+(\w+)\s+at", text)
        if price_match:
            symbol = price_match.group(1).upper()
            return self.realtime_advisor.should_buy_stock(symbol)
        
        # [symbol] right now
        now_match = re.search(r'(\w+)\s+right now', text)
        if now_match:
            symbol = now_match.group(1).upper()
            if symbol not in ['INVEST', 'BUY', 'THE', 'MARKET']:
                return self.realtime_advisor.should_buy_stock(symbol)
        
        # Default: general investment advice with market context
        return self.realtime_advisor.should_invest_now()
    
    def _handle_stock(self, text: str, original: str) -> str:
        """Handle stock/market commands."""
        # Market summary
        if "market summary" in text or "market today" in text:
            return MarketData.get_market_summary()
        
        # Watchlist
        if "watchlist" in text:
            if "add" in text:
                # Extract symbol
                match = re.search(r'add\s+(\w+)\s+to\s+watchlist', text)
                if match:
                    symbol = match.group(1).upper()
                    return self.stocks.add_to_watchlist(symbol)
            return self.stocks.get_watchlist_summary()
        
        # Compare stocks
        compare_match = re.search(r'compare\s+(\w+)\s+(?:vs|and|to)\s+(\w+)', text)
        if compare_match:
            return self.stocks.compare_stocks(
                compare_match.group(1),
                compare_match.group(2)
            )
        
        # Get stock price
        # Try to extract symbol from various patterns
        patterns = [
            r'price\s+(?:of\s+)?(\w+)',
            r'how\s+is\s+(\w+)',
            r"how's\s+(\w+)",
            r'(\w+)\s+stock',
            r'stock\s+(\w+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                symbol = match.group(1)
                # Skip common words
                if symbol.lower() not in ['the', 'my', 'a', 'an', 'doing', 'today']:
                    return self.stocks.get_stock_price(symbol)
        
        # Check for uppercase symbols in original text
        symbols = re.findall(r'\b([A-Z]{1,5})\b', original)
        if symbols:
            return self.stocks.get_stock_price(symbols[0])
        
        return self.stocks.get_watchlist_summary()
    
    def _handle_education(self, text: str, original: str) -> str:
        """Handle investment education commands."""
        # Specific topics
        if "index fund" in text or "why index" in text:
            return self.education.get_principle("index_funds")
        
        if "dollar cost" in text or "dca" in text:
            return self.education.get_principle("dollar_cost_averaging")
        
        if "compound" in text:
            return self.education.get_principle("compound_interest")
        
        if "expense ratio" in text or "fee" in text:
            return self.education.get_principle("expense_ratios")
        
        if "roth" in text and "ira" in text:
            return self.education.get_principle("roth_ira")
        
        if "time" in text and "market" in text:
            return self.education.get_principle("time_in_market")
        
        if "individual stock" in text or "should i buy" in text:
            return self.education.should_buy_individual_stocks()
        
        if "beginner" in text or "how to invest" in text or "start investing" in text:
            return self.education.get_beginner_guide()
        
        # Calculate compound growth
        calc_match = re.search(r'(\d+)\s*(?:dollars?|per month|monthly).*?(\d+)\s*years?', text)
        if calc_match:
            monthly = float(calc_match.group(1))
            years = int(calc_match.group(2))
            return self.education.calculate_compound_growth(monthly, years)
        
        # Compare start ages
        if "start" in text and ("early" in text or "age" in text or "wait" in text):
            return self.education.compare_start_ages()
        
        # Default: student advice
        return self.education.get_student_advice()
    
    def _handle_retirement(self, text: str, original: str) -> str:
        """Handle retirement/401k commands."""
        if "match" in text:
            return self.retirement.explain_401k_matching()
        
        if "roth" in text and "traditional" in text:
            return self.retirement.roth_vs_traditional()
        
        if "limit" in text or "contribution" in text:
            return self.retirement.get_contribution_limits()
        
        if "target date" in text:
            return self.retirement.explain_target_date_funds()
        
        if "vest" in text:
            return self.retirement.explain_vesting()
        
        if "how much" in text and "save" in text:
            return self.retirement.how_much_to_save()
        
        # Default: general retirement advice
        return self.retirement.get_retirement_advice()
    
    def _handle_savings(self, text: str, original: str) -> str:
        """Handle savings/banking commands."""
        # Best rates
        if "best" in text or "rate" in text or "apy" in text:
            return self.savings.get_best_rates()
        
        # Compare accounts
        compare_match = re.search(r'compare\s+(\w+)\s+(?:vs|and|to)\s+(\w+)', text)
        if compare_match:
            return self.savings.compare_accounts(
                compare_match.group(1),
                compare_match.group(2)
            )
        
        # Specific account info
        for account in ["sofi", "marcus", "ally", "discover", "capital one", "wealthfront"]:
            if account in text:
                return self.savings.get_account_info(account)
        
        # Emergency fund calculator
        ef_match = re.search(r'emergency\s+fund.*?(\d+)', text)
        if ef_match or "emergency fund" in text:
            expenses = float(ef_match.group(1)) if ef_match else 2000
            return self.savings.emergency_fund_calculator(expenses)
        
        # Interest calculator
        int_match = re.search(r'(\d+)\s*(?:dollars?|in savings)', text)
        if int_match:
            principal = float(int_match.group(1))
            return self.savings.calculate_interest(principal)
        
        # Where to keep money
        if "where" in text and "keep" in text:
            return self.savings.where_to_keep_money()
        
        # HYSA vs traditional
        if "traditional" in text or "vs" in text:
            return self.savings.hysa_vs_traditional()
        
        return self.savings.get_best_rates()
    
    def _handle_tax(self, text: str, original: str) -> str:
        """Handle tax commands."""
        if "student" in text:
            return self.tax.get_student_tax_tips()
        
        if "loss harvest" in text or "harvesting" in text:
            return self.tax.explain_tax_loss_harvesting()
        
        if "capital gain" in text:
            return self.tax.explain_capital_gains()
        
        if "rich" in text or "wealthy" in text:
            return self.tax.rich_people_strategies()
        
        if "bracket" in text:
            return self.tax.get_tax_brackets()
        
        if "education" in text or "credit" in text or "aotc" in text:
            return self.tax.education_credits()
        
        if "checklist" in text or "optimize" in text:
            return self.tax.tax_optimization_checklist()
        
        # Default: student tax tips
        return self.tax.get_student_tax_tips()
    
    def _handle_credit(self, text: str, original: str) -> str:
        """Handle credit commands."""
        if "build" in text or "improve" in text:
            return self.credit.student_credit_guide()
        
        if "utilization" in text:
            return self.credit.credit_utilization_tips()
        
        if "card" in text and ("best" in text or "student" in text or "first" in text):
            return self.credit.best_student_cards()
        
        if "800" in text or "excellent" in text:
            return self.credit.path_to_800()
        
        if "authorized" in text:
            return self.credit.authorized_user_strategy()
        
        if "mistake" in text or "avoid" in text:
            return self.credit.credit_mistakes()
        
        if "factor" in text or "what affects" in text:
            return self.credit.explain_credit_score()
        
        # Default: explain credit score
        return self.credit.explain_credit_score()
    
    def _handle_debt(self, text: str, original: str) -> str:
        """Handle debt/loan commands."""
        if "good" in text and "bad" in text:
            return self.debt.good_vs_bad_debt()
        
        if "rich" in text or "why" in text and "borrow" in text:
            return self.debt.why_rich_borrow()
        
        if "student loan" in text:
            return self.debt.student_loan_strategy()
        
        if "pay off" in text or "invest" in text:
            return self.debt.pay_debt_or_invest()
        
        if "0%" in text or "zero percent" in text or "financing" in text:
            return self.debt.zero_percent_financing()
        
        if "avalanche" in text or "snowball" in text or "method" in text:
            return self.debt.debt_payoff_methods()
        
        # Default: good vs bad debt
        return self.debt.good_vs_bad_debt()
    
    def _handle_tips(self, text: str, original: str) -> str:
        """Handle money-saving tips commands."""
        if "discount" in text or "student" in text:
            return self.tips.get_student_discounts()
        
        if "free" in text:
            return self.tips.get_free_resources()
        
        if "food" in text or "eat" in text or "meal" in text:
            return self.tips.food_saving_tips()
        
        if "negotiate" in text:
            return self.tips.negotiation_tips()
        
        if "subscription" in text or "audit" in text:
            return self.tips.subscription_audit()
        
        if "cash back" in text or "reward" in text:
            return self.tips.cash_back_optimization()
        
        if "habit" in text or "wealth" in text:
            return self.tips.wealth_building_habits()
        
        # Default: student discounts
        return self.tips.get_student_discounts()
    
    def _handle_dashboard(self, text: str, original: str) -> str:
        """Handle financial dashboard commands."""
        # Update snapshot
        if "update" in text:
            # Try to extract values
            assets_match = re.search(r'assets?\s*[:\$]?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)', text)
            liabilities_match = re.search(r'liabilities?\s*[:\$]?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)', text)
            income_match = re.search(r'income\s*[:\$]?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)', text)
            expenses_match = re.search(r'expenses?\s*[:\$]?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)', text)
            ef_match = re.search(r'emergency\s*(?:fund)?\s*[:\$]?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)', text)
            inv_match = re.search(r'investment\s*[:\$]?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)', text)
            
            return self.dashboard.update_snapshot(
                total_assets=float(assets_match.group(1).replace(',', '')) if assets_match else None,
                total_liabilities=float(liabilities_match.group(1).replace(',', '')) if liabilities_match else None,
                monthly_income=float(income_match.group(1).replace(',', '')) if income_match else None,
                monthly_expenses=float(expenses_match.group(1).replace(',', '')) if expenses_match else None,
                emergency_fund=float(ef_match.group(1).replace(',', '')) if ef_match else None,
                investment_value=float(inv_match.group(1).replace(',', '')) if inv_match else None,
            )
        
        # Add goal
        goal_match = re.search(r'(?:add\s+)?goal[:\s]+(.+?)[,\s]+\$?(\d+(?:,\d{3})*)', text)
        if goal_match:
            name = goal_match.group(1).strip()
            target = float(goal_match.group(2).replace(',', ''))
            return self.dashboard.add_goal(name, target)
        
        # Goals
        if "goal" in text:
            return self.dashboard.format_goals()
        
        # Net worth history
        if "history" in text or "trend" in text:
            return self.dashboard.get_net_worth_history()
        
        # Am I on track
        if "on track" in text:
            age_match = re.search(r'(\d+)', text)
            age = int(age_match.group(1)) if age_match else 20
            return self.dashboard.am_i_on_track(age)
        
        # Default: financial health
        return self.dashboard.get_financial_health()
    
    def _handle_portfolio(self, text: str, original: str) -> str:
        """Handle portfolio commands."""
        # Add holding
        add_match = re.search(r'add\s+(\d+(?:\.\d+)?)\s+shares?\s+(?:of\s+)?(\w+)\s+(?:at\s+)?\$?(\d+(?:\.\d+)?)', text)
        if add_match:
            shares = float(add_match.group(1))
            symbol = add_match.group(2).upper()
            price = float(add_match.group(3))
            
            # Check for account type
            account = "taxable"
            if "roth" in text:
                account = "roth_ira"
            elif "traditional" in text or "trad" in text:
                account = "traditional_ira"
            elif "401k" in text or "401(k)" in text:
                account = "401k"
            
            return self.portfolio.add_holding(symbol, shares, price, account)
        
        # Sell holding
        sell_match = re.search(r'sell\s+(\d+(?:\.\d+)?)\s+shares?\s+(?:of\s+)?(\w+)\s+(?:at\s+)?\$?(\d+(?:\.\d+)?)', text)
        if sell_match:
            shares = float(sell_match.group(1))
            symbol = sell_match.group(2).upper()
            price = float(sell_match.group(3))
            return self.portfolio.sell_holding(symbol, shares, price)
        
        # Asset allocation
        if "allocation" in text:
            return self.portfolio.get_asset_allocation()
        
        # Rebalance
        if "rebalance" in text:
            return self.portfolio.should_rebalance()
        
        # Dividend
        if "dividend" in text:
            div_match = re.search(r'dividend\s+(?:from\s+)?(\w+)\s+\$?(\d+(?:\.\d+)?)', text)
            if div_match:
                symbol = div_match.group(1).upper()
                amount = float(div_match.group(2))
                reinvested = "reinvest" in text
                return self.portfolio.record_dividend(symbol, amount, reinvested)
            return self.portfolio.get_dividend_summary()
        
        # Performance
        if "performance" in text:
            return self.portfolio.investment_performance()
        
        # Default: show portfolio
        return self.portfolio.format_portfolio()
    
    # =========================================================================
    # Briefing Integration
    # =========================================================================
    
    def get_finance_briefing(self) -> str:
        """Get finance-related items for daily briefing."""
        lines = []
        
        # Market summary (brief)
        if YFINANCE_AVAILABLE:
            try:
                import yfinance as yf
                spy = yf.Ticker("SPY")
                info = spy.fast_info
                price = info.get('lastPrice', 0)
                prev = info.get('previousClose', price)
                change = ((price - prev) / prev * 100) if prev else 0
                arrow = "📈" if change >= 0 else "📉"
                lines.append(f"{arrow} S&P 500: {'+' if change >= 0 else ''}{change:.1f}%")
            except:
                pass
        
        # Portfolio value
        summary = self.portfolio.get_portfolio_value()
        if summary.total_value > 0:
            lines.append(f"💰 Portfolio: ${summary.total_value:,.0f} ({'+' if summary.total_gain_percent >= 0 else ''}{summary.total_gain_percent:.1f}%)")
        
        # Financial health score
        snapshot = self.dashboard.get_latest_snapshot()
        if snapshot:
            score = self.dashboard._calculate_health_score(snapshot)
            lines.append(f"📊 Financial Health: {score}/100")
        
        return "\n".join(lines) if lines else ""
