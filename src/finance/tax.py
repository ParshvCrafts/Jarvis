"""
Tax Optimization Strategies for JARVIS.

Legal tax avoidance strategies:
- Tax-loss harvesting
- Roth conversions
- Capital gains brackets
- Education credits
- Student-specific deductions
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

from loguru import logger


@dataclass
class TaxBracket:
    rate: float
    single_min: int
    single_max: int
    married_min: int
    married_max: int


class TaxAdvisor:
    """
    Tax optimization guidance.
    
    Features:
    - Tax bracket education
    - Student tax tips
    - Capital gains strategies
    - Tax-advantaged account guidance
    """
    
    # 2024 Federal Tax Brackets (Single)
    TAX_BRACKETS_2024 = [
        TaxBracket(0.10, 0, 11600, 0, 23200),
        TaxBracket(0.12, 11601, 47150, 23201, 94300),
        TaxBracket(0.22, 47151, 100525, 94301, 201050),
        TaxBracket(0.24, 100526, 191950, 201051, 383900),
        TaxBracket(0.32, 191951, 243725, 383901, 487450),
        TaxBracket(0.35, 243726, 609350, 487451, 731200),
        TaxBracket(0.37, 609351, float('inf'), 731201, float('inf')),
    ]
    
    # 2024 Long-term Capital Gains Brackets (Single)
    CAPITAL_GAINS_BRACKETS = [
        (0.00, 0, 47025),      # 0% rate
        (0.15, 47026, 518900),  # 15% rate
        (0.20, 518901, float('inf')),  # 20% rate
    ]
    
    # Standard Deduction 2024
    STANDARD_DEDUCTION = {
        "single": 14600,
        "married": 29200,
        "head_of_household": 21900,
    }
    
    def __init__(self):
        logger.info("Tax Advisor initialized")
    
    def get_student_tax_tips(self) -> str:
        """Get tax tips specific to students."""
        return """🎓 **Tax Tips for Students**

**1. Education Credits (Big Savings!)**

**American Opportunity Tax Credit (AOTC):**
- Up to $2,500/year for first 4 years of college
- 40% refundable (get $1,000 even if you owe $0)
- Covers tuition, fees, books, supplies
- Income limit: $90,000 single

**Lifetime Learning Credit:**
- Up to $2,000/year
- No limit on years
- Good for grad school

**2. Student Loan Interest Deduction**
- Deduct up to $2,500 of interest paid
- Even if parents pay, you can claim if you're the borrower
- Income limit: $90,000 single

**3. Standard Deduction**
- 2024: $14,600 for single filers
- If you earn less, you likely owe $0 federal tax
- Still file to get refundable credits!

**4. Roth IRA Advantage**
- You're in the lowest tax bracket (10-12%)
- Pay taxes now at 12%, avoid 32% later
- Tax-free growth for 40+ years

**5. Dependent Status**
- If parents claim you, some credits go to them
- Coordinate with parents for best outcome
- Can still have your own Roth IRA

**Action Items:**
✅ File taxes even with low income (get refundable credits)
✅ Keep receipts for education expenses
✅ Open a Roth IRA while in low bracket
✅ Track student loan interest payments"""
    
    def explain_tax_loss_harvesting(self) -> str:
        """Explain tax-loss harvesting strategy."""
        return """📉 **Tax-Loss Harvesting Explained**

**What Is It?**
Selling investments at a loss to offset gains and reduce taxes.

**How It Works:**
1. You have $5,000 gain from selling Stock A
2. You have $3,000 loss from Stock B
3. Sell Stock B to "harvest" the loss
4. Net taxable gain: $5,000 - $3,000 = $2,000
5. Tax savings: $2,000 × 15% = $300 saved

**The Wash Sale Rule:**
⚠️ Can't buy "substantially identical" security within 30 days
- Sell VTI at a loss
- Wait 31 days OR buy similar (not identical) fund like ITOT
- Then you can buy VTI again

**When to Harvest:**
- Market downturns (like 2022)
- End of year tax planning
- When rebalancing portfolio

**Extra Benefit:**
If losses exceed gains, deduct up to $3,000 from ordinary income.
Remaining losses carry forward to future years.

**Example for Students:**
Even with small portfolios, harvesting $1,000 loss saves:
- $150 if in 15% capital gains bracket
- $120 if in 12% income bracket (if no gains to offset)

**Pro Tip:**
Many brokerages offer automatic tax-loss harvesting:
- Wealthfront
- Betterment
- M1 Finance

*This is a legal strategy used by wealthy investors. Now you know it too!*"""
    
    def explain_capital_gains(self) -> str:
        """Explain capital gains tax rates."""
        return """📊 **Capital Gains Tax Rates (2024)**

**Short-Term (held < 1 year):**
Taxed as ordinary income (your regular tax bracket)
- Could be 10%, 12%, 22%, 24%, etc.

**Long-Term (held > 1 year):**
Special lower rates!

| Taxable Income (Single) | Rate |
|-------------------------|------|
| $0 - $47,025 | **0%** |
| $47,026 - $518,900 | 15% |
| $518,901+ | 20% |

**🔥 The 0% Rate is HUGE for Students!**

If your taxable income is under $47,025:
- You pay $0 tax on long-term capital gains
- Standard deduction: $14,600
- Can earn up to $61,625 gross and pay 0% on gains!

**Example:**
- Part-time job: $15,000
- Minus standard deduction: -$14,600
- Taxable income: $400
- Long-term gains: $5,000
- Tax on gains: **$0** (under $47,025 threshold)

**Strategy:**
1. Hold investments for 1+ year (long-term)
2. Sell gains in low-income years (college!)
3. Avoid short-term trading (higher taxes)

**Pro Tip:**
Your college years are the BEST time to realize gains because you're likely in the 0% bracket!"""
    
    def rich_people_strategies(self) -> str:
        """Explain wealth strategies used by the wealthy."""
        return """💎 **How the Wealthy Minimize Taxes (Legally)**

**1. Buy, Borrow, Die**
The ultimate wealth strategy:
- **Buy:** Acquire appreciating assets (stocks, real estate)
- **Borrow:** Take loans against assets instead of selling
- **Die:** Heirs get "stepped-up basis" - gains are never taxed!

*Example: Buy stock at $100, worth $1M at death. Heirs' basis = $1M, not $100. The $999,900 gain is never taxed.*

**2. Stepped-Up Basis**
When you inherit assets, your cost basis = value at death.
- Parent bought Apple at $10/share
- Worth $200/share when inherited
- Your basis: $200 (not $10)
- Sell at $200 = $0 taxable gain

**3. Charitable Giving**
Donate appreciated stock instead of cash:
- Avoid capital gains tax on the appreciation
- Get full deduction for current value
- Double tax benefit!

**4. Real Estate Depreciation**
- Deduct "depreciation" even as property gains value
- Can show paper losses while building wealth
- 1031 exchanges defer gains indefinitely

**5. Business Deductions**
Side business unlocks deductions:
- Home office
- Equipment
- Travel
- Education related to business

**6. Qualified Opportunity Zones**
Invest capital gains in designated areas:
- Defer original gain
- Reduce gain by 10-15%
- New gains tax-free if held 10+ years

**What Students Can Use Now:**
✅ 0% capital gains rate (low income)
✅ Roth IRA (pay low taxes now)
✅ Tax-loss harvesting
✅ Education credits
✅ Start a side business for deductions

*Knowledge is power. These strategies are legal and available to everyone who understands them.*"""
    
    def get_tax_brackets(self) -> str:
        """Show current tax brackets."""
        return """📊 **2024 Federal Tax Brackets (Single)**

| Taxable Income | Tax Rate |
|----------------|----------|
| $0 - $11,600 | 10% |
| $11,601 - $47,150 | 12% |
| $47,151 - $100,525 | 22% |
| $100,526 - $191,950 | 24% |
| $191,951 - $243,725 | 32% |
| $243,726 - $609,350 | 35% |
| $609,351+ | 37% |

**Standard Deduction:** $14,600

**How Brackets Work:**
Brackets are MARGINAL - only income in each bracket is taxed at that rate.

**Example ($50,000 income):**
- First $14,600: $0 (standard deduction)
- Taxable: $35,400
- $0-$11,600 at 10%: $1,160
- $11,601-$35,400 at 12%: $2,856
- **Total tax: $4,016** (effective rate: 8%)

**Key Insight:**
Even if you're "in the 22% bracket," you don't pay 22% on everything - only on income above $47,150.

**For Students:**
Most students are in the 10-12% bracket, making Roth contributions extremely valuable!"""
    
    def education_credits(self) -> str:
        """Explain education tax credits."""
        return """🎓 **Education Tax Credits**

**American Opportunity Tax Credit (AOTC)**
- **Amount:** Up to $2,500/year
- **Years:** First 4 years of undergrad only
- **Refundable:** 40% ($1,000 max) even if you owe $0
- **Covers:** Tuition, fees, books, supplies
- **Income Limit:** Phases out $80K-$90K (single)

**How to Claim:**
1. School sends Form 1098-T
2. Keep receipts for books/supplies
3. Claim on Form 8863

**Lifetime Learning Credit**
- **Amount:** Up to $2,000/year
- **Years:** Unlimited (grad school, continuing ed)
- **Refundable:** No
- **Income Limit:** Phases out $80K-$90K (single)

**Which to Choose:**
- Undergrad (years 1-4): AOTC (worth more)
- Grad school: Lifetime Learning
- Can't claim both in same year

**Student Loan Interest Deduction**
- Deduct up to $2,500 of interest paid
- "Above the line" - don't need to itemize
- Income limit: $75K-$90K (single)

**529 Plan Benefits**
- Contributions grow tax-free
- Withdrawals tax-free for education
- Some states give deduction for contributions

**Pro Tip:**
Coordinate with parents! If they claim you as dependent, they get the credits. Make sure someone claims them!"""
    
    def tax_optimization_checklist(self) -> str:
        """Get a tax optimization checklist."""
        return """✅ **Tax Optimization Checklist**

**Before Year End:**
□ Max out 401k contributions ($23,000)
□ Max out Roth IRA ($7,000)
□ Max out HSA if eligible ($4,150 individual)
□ Review for tax-loss harvesting opportunities
□ Make charitable donations (if itemizing)
□ Prepay deductible expenses if beneficial

**For Students Specifically:**
□ Gather 1098-T from school
□ Keep receipts for books and supplies
□ Track student loan interest paid
□ Determine if you or parents should claim credits
□ Consider Roth contributions while in low bracket

**Investment Tax Strategies:**
□ Hold investments 1+ year for long-term rates
□ Harvest losses to offset gains
□ Realize gains in low-income years
□ Use tax-advantaged accounts first

**Year-Round Habits:**
□ Keep organized records
□ Track deductible expenses
□ Contribute to retirement accounts regularly
□ Review withholding (avoid big refund = interest-free loan to IRS)

**Common Mistakes to Avoid:**
❌ Not filing (even with low income - miss refundable credits)
❌ Missing education credits
❌ Short-term trading (higher tax rates)
❌ Not coordinating with parents on dependent status
❌ Leaving 401k match on the table"""
