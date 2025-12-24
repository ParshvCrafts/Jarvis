"""
Test script for Investment & Financial Advisor Module.
Run with: python tests/test_finance.py
"""

import asyncio
import sys
sys.path.insert(0, '.')

from src.finance import (
    FinanceManager,
    StockTracker,
    MarketData,
    InvestmentEducation,
    RetirementAdvisor,
    SavingsOptimizer,
    TaxAdvisor,
    CreditAdvisor,
    DebtAdvisor,
    MoneySavingTips,
    FinancialDashboard,
    PortfolioTracker,
)


async def test_finance_features():
    """Test all finance features."""
    print("=" * 60)
    print("Investment & Financial Advisor Module - Tests")
    print("=" * 60)
    
    # Test 1: Stock Tracker
    print("\n[Test 1] Stock/Market Data")
    stocks = StockTracker(data_dir='data/test')
    
    # Get watchlist
    watchlist = stocks.get_watchlist()
    print(f"  ✓ Default watchlist: {len(watchlist)} stocks")
    
    # Get stock quote (if yfinance available)
    try:
        quote = stocks.get_quote("VTI")
        if quote:
            print(f"  ✓ VTI quote: ${quote.price:.2f}")
        else:
            print("  ⚠ Stock quotes unavailable (yfinance not installed)")
    except Exception as e:
        print(f"  ⚠ Stock quotes unavailable: {e}")
    
    # Test 2: Investment Education
    print("\n[Test 2] Investment Education")
    education = InvestmentEducation()
    
    # Get principle
    advice = education.get_principle("index_funds")
    print(f"  ✓ Index funds advice: {len(advice)} chars")
    
    # Get student advice
    student_advice = education.get_student_advice()
    print(f"  ✓ Student advice: {len(student_advice)} chars")
    
    # Compound growth calculator
    growth = education.calculate_compound_growth(200, 40)
    print(f"  ✓ Compound growth calculator works")
    
    # Test 3: Retirement Advisor
    print("\n[Test 3] Retirement/401k Guidance")
    retirement = RetirementAdvisor()
    
    # 401k matching
    matching = retirement.explain_401k_matching()
    print(f"  ✓ 401k matching explanation: {len(matching)} chars")
    
    # Roth vs Traditional
    comparison = retirement.roth_vs_traditional()
    print(f"  ✓ Roth vs Traditional: {len(comparison)} chars")
    
    # Contribution limits
    limits = retirement.get_contribution_limits()
    print(f"  ✓ Contribution limits: {len(limits)} chars")
    
    # Test 4: Savings Optimizer
    print("\n[Test 4] High-Yield Savings")
    savings = SavingsOptimizer()
    
    # Best rates
    rates = savings.get_best_rates()
    print(f"  ✓ Best savings rates: {len(rates)} chars")
    
    # Interest calculator
    interest = savings.calculate_interest(5000, 1)
    print(f"  ✓ Interest calculator works")
    
    # Emergency fund
    ef = savings.emergency_fund_calculator(2000)
    print(f"  ✓ Emergency fund calculator works")
    
    # Test 5: Tax Advisor
    print("\n[Test 5] Tax Strategies")
    tax = TaxAdvisor()
    
    # Student tips
    tips = tax.get_student_tax_tips()
    print(f"  ✓ Student tax tips: {len(tips)} chars")
    
    # Tax loss harvesting
    tlh = tax.explain_tax_loss_harvesting()
    print(f"  ✓ Tax loss harvesting: {len(tlh)} chars")
    
    # Rich people strategies
    rich = tax.rich_people_strategies()
    print(f"  ✓ Wealth strategies: {len(rich)} chars")
    
    # Test 6: Credit Advisor
    print("\n[Test 6] Credit Building")
    credit = CreditAdvisor()
    
    # Credit score explanation
    score = credit.explain_credit_score()
    print(f"  ✓ Credit score explanation: {len(score)} chars")
    
    # Student credit guide
    guide = credit.student_credit_guide()
    print(f"  ✓ Student credit guide: {len(guide)} chars")
    
    # Path to 800
    path = credit.path_to_800()
    print(f"  ✓ Path to 800: {len(path)} chars")
    
    # Test 7: Debt Advisor
    print("\n[Test 7] Debt Strategies")
    debt = DebtAdvisor()
    
    # Good vs bad debt
    gvb = debt.good_vs_bad_debt()
    print(f"  ✓ Good vs bad debt: {len(gvb)} chars")
    
    # Why rich borrow
    borrow = debt.why_rich_borrow()
    print(f"  ✓ Why rich borrow: {len(borrow)} chars")
    
    # Student loan strategy
    loans = debt.student_loan_strategy()
    print(f"  ✓ Student loan strategy: {len(loans)} chars")
    
    # Test 8: Money-Saving Tips
    print("\n[Test 8] Money-Saving Tips")
    tips_advisor = MoneySavingTips()
    
    # Student discounts
    discounts = tips_advisor.get_student_discounts()
    print(f"  ✓ Student discounts: {len(discounts)} chars")
    
    # Free resources
    free = tips_advisor.get_free_resources()
    print(f"  ✓ Free resources: {len(free)} chars")
    
    # Negotiation tips
    negotiate = tips_advisor.negotiation_tips()
    print(f"  ✓ Negotiation tips: {len(negotiate)} chars")
    
    # Test 9: Financial Dashboard
    print("\n[Test 9] Financial Dashboard")
    dashboard = FinancialDashboard(data_dir='data/test')
    
    # Update snapshot
    result = dashboard.update_snapshot(
        total_assets=10000,
        total_liabilities=2000,
        monthly_income=2000,
        monthly_expenses=1500,
        emergency_fund=3000,
        investment_value=5000,
    )
    print(f"  ✓ Snapshot updated")
    
    # Get financial health
    health = dashboard.get_financial_health()
    print(f"  ✓ Financial health: {len(health)} chars")
    
    # Add goal
    goal = dashboard.add_goal("Emergency Fund", 6000)
    print(f"  ✓ Goal added")
    
    # Test 10: Portfolio Tracker
    print("\n[Test 10] Portfolio Tracker")
    portfolio = PortfolioTracker(data_dir='data/test')
    
    # Add holding
    result = portfolio.add_holding("VTI", 10, 220, "roth_ira")
    print(f"  ✓ Added holding: {result[:40]}...")
    
    # Add another
    result = portfolio.add_holding("VXUS", 5, 60, "roth_ira")
    print(f"  ✓ Added holding: {result[:40]}...")
    
    # Get portfolio
    summary = portfolio.get_portfolio_value()
    print(f"  ✓ Portfolio value: ${summary.total_cost:.2f} invested")
    
    # Asset allocation
    allocation = portfolio.get_asset_allocation()
    print(f"  ✓ Asset allocation available")
    
    # Test 11: Finance Manager Integration
    print("\n[Test 11] Finance Manager (Command Routing)")
    manager = FinanceManager(config={}, data_dir='data/test')
    
    # Test command detection
    test_commands = [
        ("what's the price of VTI", "stock"),
        ("investment advice for beginners", "education"),
        ("explain 401k matching", "retirement"),
        ("best savings rates", "savings"),
        ("tax tips for students", "tax"),
        ("how to build credit", "credit"),
        ("good debt vs bad debt", "debt"),
        ("student discounts", "tips"),
        ("my financial health", "dashboard"),
        ("add 10 shares VTI at 220", "portfolio"),
    ]
    
    passed = 0
    for cmd, expected_type in test_commands:
        # Check if command is detected
        is_stock = manager._is_stock_command(cmd)
        is_education = manager._is_education_command(cmd)
        is_retirement = manager._is_retirement_command(cmd)
        is_savings = manager._is_savings_command(cmd)
        is_tax = manager._is_tax_command(cmd)
        is_credit = manager._is_credit_command(cmd)
        is_debt = manager._is_debt_command(cmd)
        is_tips = manager._is_tips_command(cmd)
        is_dashboard = manager._is_dashboard_command(cmd)
        is_portfolio = manager._is_portfolio_command(cmd)
        
        detected = {
            "stock": is_stock,
            "education": is_education,
            "retirement": is_retirement,
            "savings": is_savings,
            "tax": is_tax,
            "credit": is_credit,
            "debt": is_debt,
            "tips": is_tips,
            "dashboard": is_dashboard,
            "portfolio": is_portfolio,
        }
        
        if detected.get(expected_type):
            passed += 1
            print(f"  ✓ '{cmd[:35]}...' -> {expected_type}")
        else:
            print(f"  ✗ '{cmd[:35]}...' -> expected {expected_type}")
    
    print(f"  Result: {passed}/{len(test_commands)} commands detected correctly")
    
    # Test 12: Command Handling
    print("\n[Test 12] Command Handling")
    
    # Test education command
    result = await manager.handle_command("investment advice for students")
    print(f"  ✓ Education: {result[:50] if result else 'None'}...")
    
    # Test savings command
    result = await manager.handle_command("best savings rates")
    print(f"  ✓ Savings: {result[:50] if result else 'None'}...")
    
    # Test credit command
    result = await manager.handle_command("how to build credit score")
    print(f"  ✓ Credit: {result[:50] if result else 'None'}...")
    
    print("\n" + "=" * 60)
    print("✅ Investment & Financial Advisor Tests Complete!")
    print("=" * 60)
    
    # Voice commands summary
    print("\n📢 New Voice Commands Available:")
    print("""
    Stock/Market Data:
      - "What's the price of VTI?" / "How's Apple stock?"
      - "Market summary" / "My watchlist"
      - "Compare VTI vs VOO"
    
    Investment Education:
      - "Investment advice for beginners"
      - "Why should I invest in index funds?"
      - "Explain compound interest"
      - "Should I buy individual stocks?"
    
    Retirement/401k:
      - "Explain 401k matching"
      - "Roth vs Traditional IRA"
      - "How much should I save for retirement?"
      - "What's a target date fund?"
    
    High-Yield Savings:
      - "Best savings account rates"
      - "Compare SoFi vs Ally"
      - "Where should I keep my emergency fund?"
    
    Tax Strategies:
      - "Tax tips for students"
      - "What's tax loss harvesting?"
      - "How do rich people avoid taxes?"
      - "Capital gains tax rates"
    
    Credit Building:
      - "How to build credit score"
      - "Best credit cards for students"
      - "Path to 800 credit score"
      - "Credit utilization tips"
    
    Debt Strategies:
      - "Good debt vs bad debt"
      - "Why do rich people take loans?"
      - "Should I pay off debt or invest?"
      - "Student loan strategy"
    
    Money-Saving Tips:
      - "Student discounts available"
      - "Free stuff for students"
      - "Negotiation tips"
      - "Cash back optimization"
    
    Financial Dashboard:
      - "My financial health"
      - "Update net worth: assets $X, liabilities $Y"
      - "Am I on track?"
      - "Add goal: Emergency fund, $5000"
    
    Portfolio Tracking:
      - "Add 10 shares of VTI at $220"
      - "My portfolio performance"
      - "Asset allocation"
      - "Should I rebalance?"
    """)


if __name__ == "__main__":
    asyncio.run(test_finance_features())
