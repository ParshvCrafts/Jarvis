"""
Finance Module for JARVIS.

Personal Financial Advisor with:
- Real-time stock/market data
- Investment education & advice
- 401k & retirement guidance
- High-yield savings optimization
- Tax optimization strategies
- Credit score building
- Debt & loan strategies
- Money-saving tips
- Financial health dashboard
- Portfolio tracking
"""

# Stock/Market Data
STOCKS_AVAILABLE = False
try:
    from .stocks import StockTracker, MarketData
    STOCKS_AVAILABLE = True
except ImportError:
    StockTracker = None
    MarketData = None

# Investment Education
INVESTMENT_EDUCATION_AVAILABLE = False
try:
    from .education import InvestmentEducation
    INVESTMENT_EDUCATION_AVAILABLE = True
except ImportError:
    InvestmentEducation = None

# Retirement/401k Guidance
RETIREMENT_AVAILABLE = False
try:
    from .retirement import RetirementAdvisor
    RETIREMENT_AVAILABLE = True
except ImportError:
    RetirementAdvisor = None

# Savings Optimization
SAVINGS_AVAILABLE = False
try:
    from .savings import SavingsOptimizer
    SAVINGS_AVAILABLE = True
except ImportError:
    SavingsOptimizer = None

# Tax Strategies
TAX_AVAILABLE = False
try:
    from .tax import TaxAdvisor
    TAX_AVAILABLE = True
except ImportError:
    TaxAdvisor = None

# Credit Building
CREDIT_AVAILABLE = False
try:
    from .credit import CreditAdvisor
    CREDIT_AVAILABLE = True
except ImportError:
    CreditAdvisor = None

# Debt/Loan Strategies
DEBT_AVAILABLE = False
try:
    from .debt import DebtAdvisor
    DEBT_AVAILABLE = True
except ImportError:
    DebtAdvisor = None

# Money-Saving Tips
SAVINGS_TIPS_AVAILABLE = False
try:
    from .tips import MoneySavingTips
    SAVINGS_TIPS_AVAILABLE = True
except ImportError:
    MoneySavingTips = None

# Financial Dashboard
DASHBOARD_AVAILABLE = False
try:
    from .dashboard import FinancialDashboard
    DASHBOARD_AVAILABLE = True
except ImportError:
    FinancialDashboard = None

# Portfolio Tracker
PORTFOLIO_AVAILABLE = False
try:
    from .portfolio import PortfolioTracker
    PORTFOLIO_AVAILABLE = True
except ImportError:
    PortfolioTracker = None

# Real-Time Advisor
REALTIME_ADVISOR_AVAILABLE = False
try:
    from .realtime_advisor import RealTimeAdvisor, MarketContext
    REALTIME_ADVISOR_AVAILABLE = True
except ImportError:
    RealTimeAdvisor = None
    MarketContext = None

# Finance Manager (orchestrates all features)
FINANCE_MANAGER_AVAILABLE = False
try:
    from .manager import FinanceManager
    FINANCE_MANAGER_AVAILABLE = True
except ImportError as e:
    import logging
    logging.debug(f"FinanceManager not available: {e}")
    FinanceManager = None

__all__ = [
    # Availability flags
    "STOCKS_AVAILABLE",
    "INVESTMENT_EDUCATION_AVAILABLE",
    "RETIREMENT_AVAILABLE",
    "SAVINGS_AVAILABLE",
    "TAX_AVAILABLE",
    "CREDIT_AVAILABLE",
    "DEBT_AVAILABLE",
    "SAVINGS_TIPS_AVAILABLE",
    "DASHBOARD_AVAILABLE",
    "PORTFOLIO_AVAILABLE",
    "FINANCE_MANAGER_AVAILABLE",
    # Classes
    "StockTracker",
    "MarketData",
    "InvestmentEducation",
    "RetirementAdvisor",
    "SavingsOptimizer",
    "TaxAdvisor",
    "CreditAdvisor",
    "DebtAdvisor",
    "MoneySavingTips",
    "FinancialDashboard",
    "PortfolioTracker",
    "FinanceManager",
]
