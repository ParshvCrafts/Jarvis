"""
Debt & Loan Strategies for JARVIS.

Smart debt management:
- Good debt vs bad debt
- Leverage strategies
- Student loan optimization
- Pay off vs invest decision
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

from loguru import logger


@dataclass
class DebtType:
    name: str
    typical_rate: str
    is_good_debt: bool
    tax_deductible: bool
    description: str


class DebtAdvisor:
    """
    Debt and loan strategy guidance.
    
    Features:
    - Good vs bad debt education
    - Leverage strategies explained
    - Student loan optimization
    - Debt payoff strategies
    """
    
    # Types of debt
    DEBT_TYPES = {
        "mortgage": DebtType(
            name="Mortgage",
            typical_rate="6-7%",
            is_good_debt=True,
            tax_deductible=True,
            description="Builds equity in appreciating asset"
        ),
        "student_loans_federal": DebtType(
            name="Federal Student Loans",
            typical_rate="5-7%",
            is_good_debt=True,
            tax_deductible=True,
            description="Investment in earning potential"
        ),
        "student_loans_private": DebtType(
            name="Private Student Loans",
            typical_rate="4-12%",
            is_good_debt=False,
            tax_deductible=True,
            description="Less flexible than federal, can be predatory"
        ),
        "auto_loan": DebtType(
            name="Auto Loan",
            typical_rate="5-10%",
            is_good_debt=False,
            tax_deductible=False,
            description="Depreciating asset - minimize"
        ),
        "credit_card": DebtType(
            name="Credit Card",
            typical_rate="20-30%",
            is_good_debt=False,
            tax_deductible=False,
            description="Worst debt - pay off immediately"
        ),
        "personal_loan": DebtType(
            name="Personal Loan",
            typical_rate="8-15%",
            is_good_debt=False,
            tax_deductible=False,
            description="Better than credit cards, still avoid"
        ),
        "margin_loan": DebtType(
            name="Margin/Securities Loan",
            typical_rate="5-8%",
            is_good_debt=True,
            tax_deductible=True,
            description="Wealthy use this to avoid selling assets"
        ),
    }
    
    def __init__(self):
        logger.info("Debt Advisor initialized")
    
    def good_vs_bad_debt(self) -> str:
        """Explain good debt vs bad debt."""
        return """⚖️ **Good Debt vs Bad Debt**

**Good Debt:**
Debt that helps you build wealth or increase earning potential.

✅ **Mortgage**
- Builds equity in appreciating asset
- Interest is tax-deductible
- Leverage to own valuable asset
- Rate: ~6-7%

✅ **Federal Student Loans (in moderation)**
- Invests in your earning potential
- Interest deductible up to $2,500
- Income-driven repayment options
- Rate: ~5-7%

✅ **Business Loans**
- Grows income-producing asset
- Interest often deductible
- Leverage for growth

**Bad Debt:**
Debt for depreciating assets or consumption.

❌ **Credit Cards**
- 20-30% interest rates
- Compounds against you
- For consumption, not assets
- **Pay off immediately**

❌ **Auto Loans**
- Car loses 20% value year 1
- Financing a depreciating asset
- **Buy used, pay cash if possible**

❌ **Personal Loans**
- High rates (8-15%)
- Usually for consumption
- No asset backing

**The Key Question:**
*Does this debt help me build wealth or increase income?*
- Yes → Potentially good debt
- No → Bad debt, avoid

**The Math:**
- Borrow at 5% for asset growing at 8% = Good
- Borrow at 20% for thing losing value = Bad"""
    
    def why_rich_borrow(self) -> str:
        """Explain why wealthy people use debt strategically."""
        return """💎 **Why Rich People Take Loans Instead of Paying Cash**

**The Strategy: Leverage Arbitrage**

**Simple Example:**
- You have $100,000 cash
- Option A: Buy house cash
- Option B: Put 20% down, invest the rest

**Option A (Pay Cash):**
- House appreciates 5%/year
- After 10 years: $162,889
- Total gain: $62,889

**Option B (Leverage):**
- $20,000 down payment
- $80,000 invested at 10%
- After 10 years:
  - House: $162,889
  - Investments: $207,455
  - Minus mortgage interest: ~$50,000
  - Total: $320,344
  - **Net gain: $220,344**

**Why It Works:**

1. **Interest Rate Arbitrage**
   - Borrow at 5-7%
   - Invest at 8-10%
   - Profit the spread

2. **Tax Benefits**
   - Mortgage interest deductible
   - Investment gains taxed favorably
   - Depreciation on real estate

3. **Inflation Hedge**
   - Debt is fixed, dollars inflate
   - Pay back with cheaper dollars
   - Asset values rise with inflation

4. **Liquidity**
   - Keep cash available for opportunities
   - Don't tie up capital in one asset

**The "Buy, Borrow, Die" Strategy:**
1. **Buy** appreciating assets (stocks, real estate)
2. **Borrow** against them instead of selling
3. **Die** - heirs get stepped-up basis, gains never taxed

**Cautions:**
⚠️ Leverage amplifies losses too
⚠️ Need stable income to service debt
⚠️ Don't over-leverage
⚠️ This is advanced - master basics first

*"If you're smart, you don't need debt. If you're not smart, debt won't help." - Warren Buffett*

*But strategically, debt can accelerate wealth building.*"""
    
    def student_loan_strategy(self) -> str:
        """Student loan optimization strategies."""
        return """🎓 **Student Loan Strategy**

**Federal vs Private:**
Always choose federal first:
- Income-driven repayment
- Forgiveness programs
- Deferment options
- Fixed rates

**Repayment Strategies:**

**1. Standard Repayment**
- 10-year term
- Highest monthly payment
- Lowest total interest
- Best if you can afford it

**2. Income-Driven Repayment (IDR)**
- Payment based on income (10-20%)
- 20-25 year forgiveness
- Good for low income or PSLF track
- More total interest paid

**3. Public Service Loan Forgiveness (PSLF)**
- Work for government/nonprofit
- 120 qualifying payments
- Remaining balance forgiven tax-free
- Use IDR to minimize payments

**Should You Pay Off Early or Invest?**

**Pay off if:**
- Rate > 6-7%
- Debt causes stress
- No employer 401k match
- Private loans with high rates

**Invest if:**
- Rate < 5%
- Have employer 401k match (free money!)
- Long time horizon
- Comfortable with debt

**The Math:**
- Loan at 5%, investments at 10%
- Investing wins mathematically
- But psychology matters too

**Refinancing:**
Consider if:
- Good credit (700+)
- Stable income
- Rate drop of 1%+
- Don't need federal protections

**Don't refinance if:**
- Pursuing PSLF
- Unstable income
- Need IDR options

**Action Plan:**
1. Know your loans (types, rates, balances)
2. Get employer 401k match first
3. Pay minimums on low-rate federal
4. Attack high-rate private loans
5. Consider refinancing private loans"""
    
    def pay_debt_or_invest(self) -> str:
        """Help decide between paying debt or investing."""
        return """🤔 **Should I Pay Off Debt or Invest?**

**The Simple Rule:**
Compare your debt interest rate to expected investment returns.

**Always Pay First:**
- Credit cards (20%+) - No investment beats this
- Private loans > 8%
- Any debt causing stress

**Always Invest First:**
- 401k up to employer match (50-100% instant return!)
- Debt under 4%

**The Gray Zone (5-7%):**
This is where it gets personal.

**Math Says Invest If:**
- Debt rate < 7%
- Long time horizon (10+ years)
- Comfortable with market volatility
- Have emergency fund

**Pay Debt If:**
- Debt rate > 7%
- Debt causes anxiety
- Uncertain income
- No emergency fund

**The Hybrid Approach:**
Why not both?
- Get full 401k match
- Pay minimums on low-rate debt
- Extra money: 50% debt, 50% invest
- Adjust based on comfort

**Example Decision Tree:**

```
Do you have high-interest debt (>8%)?
├── Yes → Pay it off first
└── No → Does employer match 401k?
    ├── Yes → Contribute to get full match
    └── Then → Is debt rate > 6%?
        ├── Yes → Pay extra on debt
        └── No → Invest (Roth IRA)
```

**The Psychology Factor:**
- Some people HATE debt
- Peace of mind has value
- Being debt-free feels amazing
- Do what helps you sleep

**My Recommendation for Students:**
1. Build $1,000 emergency fund
2. Get full 401k match (if working)
3. Pay minimums on federal loans
4. Max Roth IRA ($7,000)
5. Then attack debt or invest more

*There's no wrong answer if you're doing something productive with your money.*"""
    
    def zero_percent_financing(self) -> str:
        """Explain 0% financing strategy."""
        return """🎯 **The 0% Financing Strategy**

**What Is It?**
Using 0% APR offers to keep your money invested longer.

**How It Works:**
1. Get 0% APR offer (credit card, car, furniture)
2. Instead of paying cash, use the 0% financing
3. Keep your cash invested earning returns
4. Pay off before 0% period ends

**Example:**
- Need to buy $5,000 laptop
- Option A: Pay cash
- Option B: 0% for 18 months, invest $5,000

**Option B Math:**
- $5,000 invested at 5% for 18 months = $5,382
- Pay off laptop: $5,000
- Profit: $382

**Where to Find 0% Offers:**
- Credit card balance transfers
- Credit card purchases (intro APR)
- Car dealership financing
- Store financing (Best Buy, Apple, etc.)

**Rules for Success:**
✅ NEVER miss a payment
✅ Pay off BEFORE 0% ends
✅ Set calendar reminders
✅ Have the cash to pay anytime
✅ Don't buy more than you would with cash

**The Trap to Avoid:**
⚠️ Deferred interest - If not paid in full, you owe ALL interest from day 1
⚠️ Read the fine print!
⚠️ One late payment can cancel 0% rate

**Who Should Use This:**
- Disciplined people only
- Those who would buy anyway
- People with emergency fund
- Those who won't overspend

**Who Should NOT:**
- Anyone who might miss payments
- People tempted to buy more
- Those without cash backup
- Anyone with existing credit card debt

*This is a tool, not a license to spend. Use responsibly.*"""
    
    def debt_payoff_methods(self) -> str:
        """Compare debt payoff methods."""
        return """📊 **Debt Payoff Methods**

**1. Avalanche Method (Mathematically Optimal)**
Pay highest interest rate first.

**How:**
1. List debts by interest rate (highest first)
2. Pay minimums on all
3. Extra money → highest rate debt
4. When paid, move to next highest

**Pros:**
- Saves most money on interest
- Mathematically optimal

**Cons:**
- Might take longer to see progress
- Can feel slow

**2. Snowball Method (Psychologically Optimal)**
Pay smallest balance first.

**How:**
1. List debts by balance (smallest first)
2. Pay minimums on all
3. Extra money → smallest balance
4. When paid, move to next smallest

**Pros:**
- Quick wins build momentum
- Psychologically motivating
- Reduces number of payments

**Cons:**
- May pay more interest overall
- Not mathematically optimal

**3. Hybrid Method**
Best of both worlds.

**How:**
1. Pay off any small debts quickly (under $500)
2. Then switch to avalanche for the rest

**Which to Choose?**

| Method | Best For |
|--------|----------|
| Avalanche | Math-focused, patient people |
| Snowball | Need motivation, many small debts |
| Hybrid | Want quick wins + optimization |

**Example:**
Debts:
- Card A: $500 at 22%
- Card B: $3,000 at 18%
- Car: $8,000 at 6%
- Student: $20,000 at 5%

**Avalanche order:** A → B → Car → Student
**Snowball order:** A → B → Car → Student (same in this case!)

**The Truth:**
The best method is the one you'll stick with.
Paying off debt is always better than not paying it off."""
