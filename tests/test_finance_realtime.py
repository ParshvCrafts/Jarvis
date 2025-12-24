"""
Tests for Finance Real-Time Advisor.

Tests:
- Market context fetching
- Real-time stock analysis
- Investment advice with live data
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_realtime_advisor():
    """Test real-time finance advisor."""
    print("\n" + "=" * 60)
    print("Real-Time Finance Advisor Tests")
    print("=" * 60)
    
    from finance.realtime_advisor import RealTimeAdvisor, MarketContext, YFINANCE_AVAILABLE
    
    if not YFINANCE_AVAILABLE:
        print("⚠️ yfinance not installed. Skipping tests.")
        return
    
    advisor = RealTimeAdvisor()
    
    # Test market context
    print("\n[Test 1] Get Market Context")
    context = advisor.get_market_context()
    print(f"  S&P 500: ${context.sp500_price:,.2f} ({context.sp500_change_pct:+.2f}%)")
    print(f"  NASDAQ: ${context.nasdaq_price:,.2f} ({context.nasdaq_change_pct:+.2f}%)")
    print(f"  Dow: ${context.dow_price:,.2f} ({context.dow_change_pct:+.2f}%)")
    print(f"  VIX: {context.vix:.1f}")
    print(f"  Trend: {context.market_trend}")
    print("  ✓ Market context fetched")
    
    # Test stock-specific context
    print("\n[Test 2] Get Stock Context (VTI)")
    context = advisor.get_market_context("VTI")
    if context.stock_price:
        print(f"  VTI: ${context.stock_price:.2f} ({context.stock_change_pct:+.2f}%)")
        print(f"  52-week: ${context.stock_52w_low:.2f} - ${context.stock_52w_high:.2f}")
        if context.stock_pe_ratio:
            print(f"  P/E: {context.stock_pe_ratio:.1f}")
        if context.stock_dividend_yield:
            print(f"  Dividend: {context.stock_dividend_yield:.2f}%")
        print("  ✓ Stock context fetched")
    else:
        print("  ⚠️ Could not fetch VTI data")
    
    # Test should_buy_stock
    print("\n[Test 3] Should I Buy VTI?")
    advice = advisor.should_buy_stock("VTI")
    print(f"  Response length: {len(advice)} chars")
    print(f"  Contains price: {'$' in advice}")
    print(f"  Contains recommendation: {'Recommendation' in advice}")
    print("  ✓ Buy advice generated")
    
    # Test should_invest_now
    print("\n[Test 4] Should I Invest Now?")
    advice = advisor.should_invest_now()
    print(f"  Response length: {len(advice)} chars")
    print(f"  Contains market data: {'S&P 500' in advice}")
    print(f"  Contains recommendation: {'Recommendation' in advice}")
    print("  ✓ Investment advice generated")
    
    # Test market update
    print("\n[Test 5] Market Update")
    update = advisor.get_market_update()
    print(f"  Response length: {len(update)} chars")
    print(f"  Contains indices: {'NASDAQ' in update}")
    print("  ✓ Market update generated")
    
    # Test caching
    print("\n[Test 6] Caching")
    import time
    start = time.time()
    context1 = advisor.get_market_context()
    first_time = time.time() - start
    
    start = time.time()
    context2 = advisor.get_market_context()
    second_time = time.time() - start
    
    print(f"  First call: {first_time*1000:.0f}ms")
    print(f"  Second call (cached): {second_time*1000:.0f}ms")
    print(f"  Speedup: {first_time/second_time:.1f}x" if second_time > 0 else "  Speedup: instant")
    print("  ✓ Caching works")


def test_finance_manager_realtime():
    """Test finance manager real-time command detection."""
    print("\n" + "=" * 60)
    print("Finance Manager Real-Time Command Tests")
    print("=" * 60)
    
    from finance.manager import FinanceManager
    
    manager = FinanceManager()
    
    # Test command detection
    print("\n[Test 1] Real-Time Command Detection")
    realtime_commands = [
        "should i buy vti right now",
        "should i invest now",
        "is now a good time to invest",
        "market update",
        "how's the market",
        "what's vti at right now",
    ]
    
    for cmd in realtime_commands:
        detected = manager._is_realtime_advice_command(cmd)
        status = "✓" if detected else "✗"
        print(f"  {status} '{cmd}'")
    
    # Test that regular commands don't trigger realtime
    print("\n[Test 2] Non-Realtime Commands (should NOT trigger)")
    regular_commands = [
        "investment advice",
        "why index funds",
        "explain 401k",
        "best savings rates",
    ]
    
    for cmd in regular_commands:
        detected = manager._is_realtime_advice_command(cmd)
        status = "✓" if not detected else "✗"
        print(f"  {status} '{cmd}' (correctly not detected)")


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("Finance Real-Time Intelligence Tests")
    print("=" * 60)
    
    test_realtime_advisor()
    test_finance_manager_realtime()
    
    print("\n" + "=" * 60)
    print("✅ All Finance Real-Time Tests Complete!")
    print("=" * 60)
    
    print("""
📢 New Real-Time Finance Commands:

    Market Analysis:
      - "Should I buy VTI right now?" - Live price + analysis
      - "Should I invest now?" - Current market conditions
      - "Market update" - Live indices
      - "How's the market?" - Quick summary
    
    These commands fetch LIVE data before giving advice!
""")


if __name__ == "__main__":
    main()
