"""
401k & Retirement Guidance for JARVIS.

Retirement planning basics:
- 401k matching explained
- Roth vs Traditional
- Contribution limits
- Target date funds
- Vesting schedules
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

from loguru import logger


@dataclass
class RetirementAccount:
    name: str
    contribution_limit_2024: int
    catch_up_limit: int  # For 50+
    tax_treatment: str
    employer_match: bool
    description: str


class RetirementAdvisor:
    """
    Retirement planning guidance.
    
    Features:
    - 401k education
    - Roth vs Traditional comparison
    - Contribution strategies
    - Target date fund explanation
    """
    
    # 2024 contribution limits
    LIMITS_2024 = {
        "401k": 23000,
        "401k_catch_up": 7500,
        "ira": 7000,
        "ira_catch_up": 1000,
        "hsa_individual": 4150,
        "hsa_family": 8300,
    }
    
    # Account types
    ACCOUNTS = {
        "401k": RetirementAccount(
            name="401(k)",
            contribution_limit_2024=23000,
            catch_up_limit=7500,
            tax_treatment="Pre-tax (Traditional) or After-tax (Roth)",
            employer_match=True,
            description="Employer-sponsored retirement account with potential matching."
        ),
        "roth_401k": RetirementAccount(
            name="Roth 401(k)",
            contribution_limit_2024=23000,
            catch_up_limit=7500,
            tax_treatment="After-tax contributions, tax-free growth and withdrawals",
            employer_match=True,
            description="401k with Roth tax treatment - pay taxes now, withdraw tax-free."
        ),
        "traditional_ira": RetirementAccount(
            name="Traditional IRA",
            contribution_limit_2024=7000,
            catch_up_limit=1000,
            tax_treatment="Pre-tax contributions, taxed on withdrawal",
            employer_match=False,
            description="Individual retirement account with tax-deferred growth."
        ),
        "roth_ira": RetirementAccount(
            name="Roth IRA",
            contribution_limit_2024=7000,
            catch_up_limit=1000,
            tax_treatment="After-tax contributions, tax-free growth and withdrawals",
            employer_match=False,
            description="Best for young investors - tax-free growth forever!"
        ),
        "hsa": RetirementAccount(
            name="HSA (Health Savings Account)",
            contribution_limit_2024=4150,
            catch_up_limit=1000,
            tax_treatment="Triple tax advantage: deductible, grows tax-free, withdraws tax-free for medical",
            employer_match=False,
            description="The only triple-tax-advantaged account. Can be used for retirement after 65."
        ),
    }
    
    def __init__(self):
        logger.info("Retirement Advisor initialized")
    
    def explain_401k_matching(self) -> str:
        """Explain 401k matching - the free money concept."""
        return """💰 **401(k) Matching = FREE MONEY**

**What is 401k Matching?**
Your employer contributes money to your retirement when you contribute.

**Common Match Formulas:**
- **50% match up to 6%:** You put in 6%, they add 3% = 9% total
- **100% match up to 3%:** You put in 3%, they add 3% = 6% total
- **Dollar-for-dollar up to 4%:** You put in 4%, they add 4% = 8% total

**Example (50% match up to 6%):**
- Your salary: $60,000
- You contribute 6%: $3,600/year
- Employer adds 50%: $1,800/year
- **Total: $5,400/year**

🔥 **The Math:**
That employer match is a **50% instant return** before any investment gains!
No investment in the world guarantees 50% returns.

**Golden Rule:**
*Always contribute at least enough to get the FULL employer match.*
Not doing so is literally leaving free money on the table.

**Priority Order:**
1. 401k up to employer match (FREE MONEY)
2. Max Roth IRA ($7,000)
3. Back to 401k to max ($23,000)
4. Taxable brokerage"""
    
    def roth_vs_traditional(self) -> str:
        """Compare Roth vs Traditional accounts."""
        return """⚖️ **Roth vs Traditional: Which is Better?**

**The Key Difference:**
- **Traditional:** Pay taxes LATER (when you withdraw)
- **Roth:** Pay taxes NOW (withdrawals are tax-free)

**Traditional (Pre-tax):**
✅ Reduces taxable income now
✅ Good if you're in a HIGH tax bracket now
✅ Good if you expect LOWER taxes in retirement
❌ Pay taxes on withdrawals
❌ Required minimum distributions at 73

**Roth (After-tax):**
✅ Tax-FREE growth forever
✅ Tax-FREE withdrawals in retirement
✅ No required minimum distributions
✅ Can withdraw contributions anytime
❌ No immediate tax deduction

**For Students/Young Professionals: ROTH WINS**

Why? You're in the **lowest tax bracket** of your life!
- Current bracket: 10-12%
- Future bracket (hopefully): 22-32%+

Pay 12% tax now → Avoid 32% tax later = **Huge savings!**

**The Math:**
$7,000 Roth contribution at 12% tax = $840 in taxes now
Same money in Traditional, withdrawn at 32% = $2,240 in taxes later
**Savings: $1,400 per year of contributions**

**Recommendation for Students:**
1. Roth 401k if available
2. Roth IRA (max $7,000)
3. Traditional only if income is very high"""
    
    def get_contribution_limits(self) -> str:
        """Get current contribution limits."""
        return f"""📊 **2024 Retirement Contribution Limits**

**401(k) / 403(b) / 457:**
- Under 50: ${self.LIMITS_2024['401k']:,}/year
- 50 and over: ${self.LIMITS_2024['401k'] + self.LIMITS_2024['401k_catch_up']:,}/year

**IRA (Traditional or Roth):**
- Under 50: ${self.LIMITS_2024['ira']:,}/year
- 50 and over: ${self.LIMITS_2024['ira'] + self.LIMITS_2024['ira_catch_up']:,}/year

**HSA (Health Savings Account):**
- Individual: ${self.LIMITS_2024['hsa_individual']:,}/year
- Family: ${self.LIMITS_2024['hsa_family']:,}/year

**Important Notes:**
- 401k and IRA limits are separate (you can max both!)
- Roth IRA has income limits ($161K single, $240K married)
- Employer match does NOT count toward your limit

**Ideal Order of Contributions:**
1. 401k to employer match
2. Max Roth IRA ($7,000)
3. Max HSA if eligible
4. Back to 401k to max
5. Taxable brokerage"""
    
    def explain_target_date_funds(self) -> str:
        """Explain target date funds."""
        return """🎯 **Target Date Funds: Set It and Forget It**

**What Are They?**
A single fund that automatically adjusts your investment mix as you age.

**How They Work:**
- Pick your retirement year (e.g., 2065 for someone retiring around then)
- Fund starts aggressive (more stocks)
- Gradually shifts conservative (more bonds) as you approach retirement
- One fund = complete diversification

**Example: Vanguard Target Retirement 2065 (VLXVX)**
- Today: ~90% stocks, 10% bonds
- In 20 years: ~70% stocks, 30% bonds
- At retirement: ~50% stocks, 50% bonds

**Pros:**
✅ Ultimate simplicity - one fund does everything
✅ Automatic rebalancing
✅ Age-appropriate risk
✅ Great for beginners

**Cons:**
❌ Slightly higher fees than DIY (but still low)
❌ Less control over allocation
❌ One-size-fits-all approach

**Best Target Date Funds:**
- **Vanguard Target Retirement** - 0.14% expense ratio
- **Fidelity Freedom Index** - 0.12% expense ratio
- **Schwab Target Index** - 0.08% expense ratio

**Who Should Use Them:**
- Beginners who want simplicity
- People who don't want to manage investments
- Anyone who might forget to rebalance

*If you want to "set it and forget it," target date funds are perfect.*"""
    
    def explain_vesting(self) -> str:
        """Explain vesting schedules."""
        return """⏰ **Vesting Schedules: When Employer Money Becomes Yours**

**What is Vesting?**
The process by which employer contributions become fully yours.

**Your contributions:** Always 100% yours immediately
**Employer contributions:** May have a vesting schedule

**Common Vesting Schedules:**

**Immediate Vesting:**
- 100% yours right away
- Best case scenario!

**Cliff Vesting:**
- 0% until a certain date, then 100%
- Example: 0% for 3 years, then 100%

**Graded Vesting:**
- Increases over time
- Example: 20% per year for 5 years

| Year | Graded | Cliff (3yr) |
|------|--------|-------------|
| 1 | 20% | 0% |
| 2 | 40% | 0% |
| 3 | 60% | 100% |
| 4 | 80% | 100% |
| 5 | 100% | 100% |

**Why It Matters:**
If you leave before fully vested, you lose unvested employer contributions.

**Example:**
- Employer contributed $10,000 over 2 years
- You're 40% vested
- You leave → You keep $4,000, lose $6,000

**Pro Tips:**
1. Know your vesting schedule before accepting a job
2. Consider vesting when timing a job change
3. Some companies accelerate vesting for layoffs
4. Your contributions are ALWAYS 100% yours"""
    
    def how_much_to_save(self) -> str:
        """Advice on how much to save for retirement."""
        return """💵 **How Much Should You Save for Retirement?**

**General Guidelines:**
- **Minimum:** 10-15% of income (including employer match)
- **Ideal:** 20%+ if possible
- **Aggressive:** 50%+ (FIRE movement)

**For Students/New Grads:**
Start with what you can, increase over time.

**The 1% Rule:**
Increase savings by 1% each year or with each raise.
- Year 1: 6% (get full match)
- Year 2: 7%
- Year 3: 8%
- Eventually: 15-20%

**Retirement Savings Milestones:**
| Age | Target (x Salary) |
|-----|-------------------|
| 30 | 1x salary saved |
| 40 | 3x salary saved |
| 50 | 6x salary saved |
| 60 | 8x salary saved |
| 67 | 10x salary saved |

**The 4% Rule:**
You can withdraw 4% of your portfolio annually in retirement.
- Need $40K/year? Save $1,000,000
- Need $80K/year? Save $2,000,000

**For a Student Starting Now:**
- Even $100/month is a great start
- At 10% return, $100/month from 18-65 = $1.1 million
- Increase as income grows

*The best time to start was yesterday. The second best time is today.*"""
    
    def get_retirement_advice(self) -> str:
        """Get general retirement advice for young people."""
        return """🎓 **Retirement Advice for Young Investors**

**Priority Order:**
1. **Emergency Fund** - 3-6 months expenses in high-yield savings
2. **401k to Match** - Never leave free money on the table
3. **Pay High-Interest Debt** - Credit cards, etc.
4. **Max Roth IRA** - $7,000/year of tax-free growth
5. **Max HSA** - If eligible, triple tax advantage
6. **Back to 401k** - Up to $23,000 limit
7. **Taxable Brokerage** - After maxing tax-advantaged

**Key Principles:**
- **Start NOW** - Time is your biggest advantage
- **Automate** - Set up automatic contributions
- **Roth first** - You're in a low tax bracket
- **Index funds** - Low fees, broad diversification
- **Stay invested** - Don't panic sell during downturns

**Common Mistakes to Avoid:**
❌ Not getting full employer match
❌ Waiting to start investing
❌ Trying to time the market
❌ Paying high fees
❌ Cashing out 401k when changing jobs

**The Power of Starting Early:**
$200/month from age 22 = $1.4M at 65
$200/month from age 32 = $560K at 65
**10 years of delay costs $840,000!**"""
