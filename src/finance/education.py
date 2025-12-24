"""
Investment Education & Advice for JARVIS.

Core investment principles and personalized advice:
- Index funds over individual stocks
- Dollar-cost averaging
- Compound interest calculations
- Tax-advantaged accounts
- Student-specific recommendations
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

from loguru import logger


@dataclass
class InvestmentTip:
    title: str
    content: str
    category: str
    priority: int = 0


class InvestmentEducation:
    """
    Investment education and advice engine.
    
    Features:
    - Core investment principles
    - Personalized recommendations
    - Compound interest calculator
    - Investment term explanations
    """
    
    # Core investment principles
    PRINCIPLES = {
        "index_funds": InvestmentTip(
            title="Index Funds Over Individual Stocks",
            content="""**Why Index Funds Win:**

📊 **The Data:**
- 90% of actively managed funds underperform index funds over 15 years
- Warren Buffett bet $1M that an S&P 500 index fund would beat hedge funds - he won

💡 **Key Benefits:**
- **Diversification:** Own 500+ companies with one purchase
- **Low fees:** 0.03% vs 1%+ for active funds (saves thousands over time)
- **Less stress:** No need to pick winners
- **Tax efficient:** Lower turnover = fewer taxable events

🎯 **Best Index Funds for Students:**
- **FNILX** - Fidelity ZERO Large Cap (0% expense ratio!)
- **FZROX** - Fidelity ZERO Total Market (0% expense ratio!)
- **VTI** - Vanguard Total Stock Market (0.03%)
- **VOO** - Vanguard S&P 500 (0.03%)

*"Don't look for the needle in the haystack. Just buy the haystack."* - John Bogle""",
            category="investing",
            priority=1
        ),
        
        "dollar_cost_averaging": InvestmentTip(
            title="Dollar-Cost Averaging",
            content="""**What is Dollar-Cost Averaging (DCA)?**

Investing a fixed amount regularly, regardless of market conditions.

📅 **Example:**
- Invest $100 every month
- When prices are high → buy fewer shares
- When prices are low → buy more shares
- Result: Lower average cost over time

💪 **Why It Works:**
1. **Removes emotion** - No trying to time the market
2. **Builds habit** - Automatic wealth building
3. **Reduces risk** - Smooths out volatility
4. **Accessible** - Start with any amount

🎯 **How to Start:**
1. Set up automatic transfers to brokerage
2. Choose your index fund (VTI, FNILX, etc.)
3. Set it and forget it
4. Increase amount as income grows

*Time in the market beats timing the market.*""",
            category="strategy",
            priority=2
        ),
        
        "compound_interest": InvestmentTip(
            title="The Magic of Compound Interest",
            content="""**Einstein called it the 8th wonder of the world.**

📈 **The Power of Starting Early:**

Starting at 18 vs 28 (investing $200/month at 10% return):

| Start Age | Total Invested | Value at 65 |
|-----------|----------------|-------------|
| 18 | $112,800 | $2,200,000+ |
| 28 | $88,800 | $900,000 |

**That 10-year delay costs you $1.3 MILLION!**

🔢 **Rule of 72:**
Divide 72 by your return rate = years to double
- 10% return → doubles every 7.2 years
- 7% return → doubles every 10.3 years

💡 **Key Insight:**
Your money works 24/7. The earlier you start, the more time it has to compound. Even $50/month starting now is worth more than $500/month starting in 10 years.""",
            category="fundamentals",
            priority=1
        ),
        
        "expense_ratios": InvestmentTip(
            title="Why Expense Ratios Matter",
            content="""**Small Fees = Big Losses Over Time**

📊 **The Math:**
$10,000 invested for 30 years at 7% return:

| Expense Ratio | Final Value | Lost to Fees |
|---------------|-------------|--------------|
| 0.03% (VTI) | $74,000 | $700 |
| 0.50% | $66,000 | $8,700 |
| 1.00% | $57,000 | $17,700 |

**A 1% fee costs you 24% of your returns!**

🎯 **Best Low-Cost Options:**
- **FNILX** - 0.00% (FREE!)
- **FZROX** - 0.00% (FREE!)
- **VTI** - 0.03%
- **VOO** - 0.03%

💡 **Rule:** Never pay more than 0.20% for an index fund.""",
            category="fees",
            priority=2
        ),
        
        "roth_ira": InvestmentTip(
            title="Roth IRA - Your Secret Weapon",
            content="""**Why Students Should Prioritize Roth IRA:**

🎯 **The Roth Advantage:**
- Contribute after-tax money NOW (when you're in low tax bracket)
- All growth is TAX-FREE forever
- Withdraw tax-free in retirement

📊 **2024 Limits:**
- Contribution limit: $7,000/year
- Must have earned income
- Income limit: $161,000 (single)

💡 **Why It's Perfect for Students:**
1. You're in the lowest tax bracket now (10-12%)
2. By retirement, you'll likely be in 22-32% bracket
3. Pay taxes now at 12%, avoid 32% later = huge savings

🔥 **The Math:**
$7,000/year from age 18-65 at 10% return = **$5.4 MILLION tax-free**

**Best Roth IRA Providers:**
- Fidelity (FNILX, FZROX - zero fees)
- Vanguard (VTI, VOO)
- Schwab""",
            category="accounts",
            priority=1
        ),
        
        "time_in_market": InvestmentTip(
            title="Time in Market > Timing the Market",
            content="""**Missing the Best Days Destroys Returns**

📊 **S&P 500 (1990-2020):**

| Strategy | Annual Return |
|----------|---------------|
| Stay invested | 9.9% |
| Miss best 10 days | 5.6% |
| Miss best 20 days | 2.9% |
| Miss best 30 days | 0.4% |

**Missing just 10 days cut returns by 44%!**

💡 **The Problem with Timing:**
- Best days often follow worst days
- If you're out during crashes, you miss the recovery
- Nobody consistently times the market

🎯 **The Solution:**
1. Invest regularly (DCA)
2. Stay invested through volatility
3. Don't check daily (reduces anxiety)
4. Think in decades, not days

*"Far more money has been lost by investors preparing for corrections than has been lost in corrections themselves."* - Peter Lynch""",
            category="strategy",
            priority=2
        ),
    }
    
    # Investment terms glossary
    GLOSSARY = {
        "etf": "**ETF (Exchange-Traded Fund):** A basket of stocks that trades like a single stock. VTI is an ETF holding 4,000+ US stocks.",
        "index_fund": "**Index Fund:** A fund that tracks a market index (like S&P 500). Low fees, broad diversification.",
        "expense_ratio": "**Expense Ratio:** Annual fee charged by a fund. 0.03% means $3/year per $10,000 invested.",
        "dividend": "**Dividend:** Cash payment from company profits to shareholders. Usually paid quarterly.",
        "capital_gains": "**Capital Gains:** Profit from selling an investment for more than you paid. Taxed differently than income.",
        "market_cap": "**Market Cap:** Total value of a company's shares. Large-cap = $10B+, Mid-cap = $2-10B, Small-cap = <$2B.",
        "pe_ratio": "**P/E Ratio:** Price divided by earnings. Higher = more expensive relative to profits.",
        "diversification": "**Diversification:** Spreading investments across many assets to reduce risk.",
        "volatility": "**Volatility:** How much an investment's price fluctuates. Higher volatility = more risk.",
        "bull_market": "**Bull Market:** Extended period of rising prices (20%+ gain).",
        "bear_market": "**Bear Market:** Extended period of falling prices (20%+ decline).",
        "rebalancing": "**Rebalancing:** Adjusting portfolio back to target allocation (e.g., 80% stocks, 20% bonds).",
    }
    
    # Student-specific advice
    STUDENT_ADVICE = [
        "**Start a Roth IRA** - You're in the lowest tax bracket now. Pay taxes at 12% instead of 32% later.",
        "**Use Fidelity** - FNILX and FZROX have 0% expense ratios. Literally free to invest.",
        "**Even $50/month matters** - Starting at 18, $50/month becomes $500K+ by 65.",
        "**Index funds beat 90% of pros** - Don't try to pick stocks. Buy the whole market.",
        "**Automate everything** - Set up automatic monthly investments. Remove the decision.",
        "**Time > Timing** - Starting now with $50 beats starting later with $500.",
        "**Emergency fund first** - Keep 3-6 months expenses in high-yield savings before investing.",
        "**Ignore the noise** - Don't check daily. Think in decades.",
    ]
    
    def __init__(self):
        logger.info("Investment Education initialized")
    
    def get_principle(self, topic: str) -> str:
        """Get explanation of an investment principle."""
        topic_lower = topic.lower()
        
        # Map common queries to principles
        topic_map = {
            "index": "index_funds",
            "index fund": "index_funds",
            "etf": "index_funds",
            "vti": "index_funds",
            "voo": "index_funds",
            "dca": "dollar_cost_averaging",
            "dollar cost": "dollar_cost_averaging",
            "averaging": "dollar_cost_averaging",
            "compound": "compound_interest",
            "interest": "compound_interest",
            "growth": "compound_interest",
            "expense": "expense_ratios",
            "fee": "expense_ratios",
            "ratio": "expense_ratios",
            "roth": "roth_ira",
            "ira": "roth_ira",
            "retirement account": "roth_ira",
            "time": "time_in_market",
            "timing": "time_in_market",
            "market timing": "time_in_market",
        }
        
        key = topic_map.get(topic_lower)
        if key and key in self.PRINCIPLES:
            tip = self.PRINCIPLES[key]
            return f"📚 **{tip.title}**\n\n{tip.content}"
        
        # Direct lookup
        if topic_lower in self.PRINCIPLES:
            tip = self.PRINCIPLES[topic_lower]
            return f"📚 **{tip.title}**\n\n{tip.content}"
        
        return self.get_student_advice()
    
    def get_definition(self, term: str) -> str:
        """Get definition of an investment term."""
        term_lower = term.lower().replace(" ", "_")
        
        if term_lower in self.GLOSSARY:
            return self.GLOSSARY[term_lower]
        
        # Fuzzy match
        for key, definition in self.GLOSSARY.items():
            if term_lower in key or key in term_lower:
                return definition
        
        return f"I don't have a definition for '{term}'. Try asking about: ETF, index fund, expense ratio, dividend, P/E ratio, etc."
    
    def get_student_advice(self) -> str:
        """Get personalized advice for students."""
        lines = ["💡 **Investment Advice for Students**\n"]
        
        for i, advice in enumerate(self.STUDENT_ADVICE, 1):
            lines.append(f"{i}. {advice}")
        
        lines.append("\n*Want me to explain any of these in detail?*")
        
        return "\n".join(lines)
    
    def calculate_compound_growth(
        self,
        monthly_investment: float,
        years: int,
        annual_return: float = 0.10,
        starting_amount: float = 0,
    ) -> str:
        """Calculate compound growth over time."""
        monthly_return = annual_return / 12
        months = years * 12
        
        # Future value of series of payments + initial investment
        if monthly_return > 0:
            fv_payments = monthly_investment * (((1 + monthly_return) ** months - 1) / monthly_return)
        else:
            fv_payments = monthly_investment * months
        
        fv_initial = starting_amount * ((1 + annual_return) ** years)
        total = fv_payments + fv_initial
        total_invested = (monthly_investment * months) + starting_amount
        
        return f"""📈 **Compound Growth Calculator**

💰 **Your Investment:**
- Monthly: ${monthly_investment:,.0f}
- Starting amount: ${starting_amount:,.0f}
- Time horizon: {years} years
- Expected return: {annual_return*100:.0f}%

📊 **Results:**
- Total invested: ${total_invested:,.0f}
- Final value: **${total:,.0f}**
- Growth: ${total - total_invested:,.0f} ({((total/total_invested)-1)*100:.0f}% gain)

*This assumes {annual_return*100:.0f}% average annual return (S&P 500 historical average is ~10%).*"""
    
    def compare_start_ages(self, monthly: float = 200, return_rate: float = 0.10) -> str:
        """Show impact of starting early."""
        scenarios = [
            (18, 65),
            (22, 65),
            (25, 65),
            (30, 65),
        ]
        
        lines = [
            f"⏰ **The Cost of Waiting** (${monthly}/month at {return_rate*100:.0f}% return)\n",
            "| Start Age | Years | Total Invested | Value at 65 |",
            "|-----------|-------|----------------|-------------|",
        ]
        
        for start_age, end_age in scenarios:
            years = end_age - start_age
            months = years * 12
            monthly_return = return_rate / 12
            
            fv = monthly * (((1 + monthly_return) ** months - 1) / monthly_return)
            invested = monthly * months
            
            lines.append(f"| {start_age} | {years} | ${invested:,.0f} | ${fv:,.0f} |")
        
        lines.append(f"\n**Starting at 18 vs 30 = ${self._calc_diff(monthly, return_rate):,.0f} more!**")
        lines.append("\n*Every year you wait costs you significantly.*")
        
        return "\n".join(lines)
    
    def _calc_diff(self, monthly: float, rate: float) -> float:
        """Calculate difference between starting at 18 vs 30."""
        monthly_rate = rate / 12
        
        fv_18 = monthly * (((1 + monthly_rate) ** (47*12) - 1) / monthly_rate)
        fv_30 = monthly * (((1 + monthly_rate) ** (35*12) - 1) / monthly_rate)
        
        return fv_18 - fv_30
    
    def get_beginner_guide(self) -> str:
        """Get complete beginner's guide to investing."""
        return """🎓 **Beginner's Guide to Investing**

**Step 1: Build Emergency Fund**
- Save 3-6 months of expenses
- Keep in high-yield savings (4%+ APY)
- This is your safety net before investing

**Step 2: Open a Roth IRA**
- Best account for students (tax-free growth!)
- Recommended: Fidelity (zero-fee funds)
- 2024 limit: $7,000/year

**Step 3: Choose Your Investments**
- Start with total market index fund
- FZROX (Fidelity) or VTI (Vanguard)
- One fund = instant diversification

**Step 4: Automate**
- Set up automatic monthly transfers
- Even $50/month is a great start
- Increase as income grows

**Step 5: Stay the Course**
- Don't panic during market drops
- Don't check daily
- Think in decades, not days

**Recommended Portfolio for Beginners:**
- 90% US Total Market (FZROX/VTI)
- 10% International (FZILX/VXUS)

*Simple beats complex. Low fees beat high fees. Time beats timing.*"""
    
    def should_buy_individual_stocks(self) -> str:
        """Advice on individual stocks vs index funds."""
        return """🤔 **Should You Buy Individual Stocks?**

**The Short Answer:** Probably not, especially starting out.

**Why Index Funds Win:**
- 90% of professional stock pickers underperform index funds
- If pros can't beat the market, why would you?
- One bad pick can wipe out years of gains
- Index funds give you instant diversification

**When Individual Stocks MIGHT Make Sense:**
- You have a solid index fund foundation first
- It's "play money" you can afford to lose (5-10% of portfolio)
- You understand the business deeply
- You're prepared to hold 5+ years

**The Smart Approach:**
1. Max out index funds first (Roth IRA, etc.)
2. If you want to pick stocks, use only 5-10% of portfolio
3. Treat it as education/entertainment, not strategy

**Remember:**
Even Warren Buffett recommends index funds for most people:
*"A low-cost index fund is the most sensible equity investment for the great majority of investors."*"""
