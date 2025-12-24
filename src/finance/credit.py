"""
Credit Score Building for JARVIS.

Credit score education and improvement:
- Credit score factors
- Building credit as a student
- Credit card tips
- Score improvement strategies
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

from loguru import logger


@dataclass
class CreditFactor:
    name: str
    weight: int  # Percentage
    description: str
    tips: List[str]


class CreditAdvisor:
    """
    Credit score building guidance.
    
    Features:
    - Credit score education
    - Student credit strategies
    - Credit card recommendations
    - Score improvement tips
    """
    
    # Credit score factors and weights
    CREDIT_FACTORS = {
        "payment_history": CreditFactor(
            name="Payment History",
            weight=35,
            description="Whether you pay bills on time",
            tips=[
                "Set up autopay for at least minimum payment",
                "Never miss a payment - even one late payment hurts",
                "If you miss, pay ASAP - 30+ days late is reported",
            ]
        ),
        "credit_utilization": CreditFactor(
            name="Credit Utilization",
            weight=30,
            description="How much of your available credit you use",
            tips=[
                "Keep utilization under 30% (under 10% is ideal)",
                "Pay before statement closes to lower reported utilization",
                "Request credit limit increases (don't spend more!)",
            ]
        ),
        "credit_history": CreditFactor(
            name="Length of Credit History",
            weight=15,
            description="How long you've had credit accounts",
            tips=[
                "Keep old accounts open (even if unused)",
                "Become authorized user on parent's old card",
                "Start building credit early",
            ]
        ),
        "credit_mix": CreditFactor(
            name="Credit Mix",
            weight=10,
            description="Variety of credit types (cards, loans, etc.)",
            tips=[
                "Don't open accounts just for mix",
                "Student loans count toward mix",
                "Credit cards + installment loan = good mix",
            ]
        ),
        "new_credit": CreditFactor(
            name="New Credit",
            weight=10,
            description="Recent credit applications and new accounts",
            tips=[
                "Avoid opening many accounts at once",
                "Hard inquiries stay for 2 years",
                "Rate shopping (mortgages, auto) within 14-45 days counts as one inquiry",
            ]
        ),
    }
    
    # Credit score ranges
    SCORE_RANGES = {
        "excellent": (800, 850, "Excellent - Best rates available"),
        "very_good": (740, 799, "Very Good - Better than average"),
        "good": (670, 739, "Good - Near or above average"),
        "fair": (580, 669, "Fair - Below average"),
        "poor": (300, 579, "Poor - Difficulty getting approved"),
    }
    
    # Student-friendly credit cards
    STUDENT_CARDS = [
        {
            "name": "Discover it Student Cash Back",
            "annual_fee": 0,
            "rewards": "5% rotating categories, 1% everything else",
            "features": ["No credit history needed", "Good grades reward", "Cashback match first year"],
        },
        {
            "name": "Capital One SavorOne Student",
            "annual_fee": 0,
            "rewards": "3% dining/entertainment, 1% everything else",
            "features": ["No credit history needed", "No foreign transaction fees"],
        },
        {
            "name": "Bank of America Customized Cash",
            "annual_fee": 0,
            "rewards": "3% choice category, 2% grocery, 1% everything else",
            "features": ["Choose your 3% category", "Good for beginners"],
        },
        {
            "name": "Chase Freedom Rise",
            "annual_fee": 0,
            "rewards": "1.5% on everything",
            "features": ["No credit history needed", "Auto credit line increase after 6 months"],
        },
    ]
    
    def __init__(self):
        logger.info("Credit Advisor initialized")
    
    def explain_credit_score(self) -> str:
        """Explain how credit scores work."""
        lines = [
            "📊 **Understanding Your Credit Score**\n",
            "**Score Range:** 300 - 850\n",
            "**What Makes Up Your Score:**\n",
        ]
        
        for factor in self.CREDIT_FACTORS.values():
            lines.append(f"**{factor.name}** ({factor.weight}%)")
            lines.append(f"  {factor.description}")
        
        lines.append("\n**Score Ranges:**")
        for range_name, (low, high, desc) in self.SCORE_RANGES.items():
            lines.append(f"  • {low}-{high}: {desc}")
        
        lines.append("\n*Most lenders use FICO scores. You can check free at Credit Karma, Discover, or your bank.*")
        
        return "\n".join(lines)
    
    def get_factor_tips(self, factor: str) -> str:
        """Get tips for a specific credit factor."""
        factor_key = factor.lower().replace(" ", "_")
        
        # Try to match factor
        matched = None
        for key, f in self.CREDIT_FACTORS.items():
            if factor_key in key or factor_key in f.name.lower():
                matched = f
                break
        
        if not matched:
            return self.explain_credit_score()
        
        lines = [
            f"📊 **{matched.name}** ({matched.weight}% of score)\n",
            f"{matched.description}\n",
            "**Tips to Improve:**",
        ]
        
        for tip in matched.tips:
            lines.append(f"  • {tip}")
        
        return "\n".join(lines)
    
    def student_credit_guide(self) -> str:
        """Complete guide to building credit as a student."""
        return """🎓 **Building Credit as a Student**

**Why Start Now?**
- Credit history length matters (15% of score)
- Good credit = lower rates on everything
- Needed for apartments, car loans, even jobs
- Easier to build than repair

**Step 1: Get Your First Card**
Options for no credit history:
1. **Student credit card** (Discover it Student, Capital One)
2. **Secured card** (deposit becomes your limit)
3. **Authorized user** on parent's card

**Step 2: Use It Wisely**
- Put one small recurring charge on it (Netflix, Spotify)
- Set up autopay for full balance
- Never use more than 30% of limit

**Step 3: Build History**
- Keep the card open (even after graduation)
- Don't close old accounts
- Let it age

**The Perfect Strategy:**
1. Get student card with $500 limit
2. Put $20/month subscription on it
3. Autopay full balance
4. After 6 months, request limit increase
5. After 1 year, consider second card
6. Never carry a balance (pay in full!)

**Timeline to Good Credit:**
- 6 months: Establish score
- 1 year: Score in 600s
- 2 years: Score in 700s
- 3+ years: 750+ possible

**Common Mistakes:**
❌ Maxing out cards
❌ Missing payments
❌ Closing old accounts
❌ Applying for too many cards at once
❌ Carrying a balance (paying interest)"""
    
    def credit_utilization_tips(self) -> str:
        """Tips for managing credit utilization."""
        return """📊 **Credit Utilization: The 30% Rule**

**What Is It?**
Credit utilization = (Balance ÷ Credit Limit) × 100

**Example:**
- Credit limit: $1,000
- Balance: $300
- Utilization: 30%

**The Rules:**
- Under 30%: Good
- Under 10%: Excellent
- Over 30%: Hurts your score

**Pro Tips:**

**1. Pay Before Statement Closes**
Your balance on statement date is what's reported.
- Statement closes on 15th
- Pay on 14th
- Reported utilization: near 0%

**2. Request Limit Increases**
- Same spending, higher limit = lower utilization
- $300 on $1,000 = 30%
- $300 on $3,000 = 10%
- Don't spend more just because you can!

**3. Multiple Cards Strategy**
- Total utilization matters
- Per-card utilization matters too
- Spread spending across cards

**4. Pay Multiple Times Per Month**
- High spender? Pay weekly
- Keeps utilization low at all times

**Quick Math:**
| Limit | 30% Max | 10% Ideal |
|-------|---------|-----------|
| $500 | $150 | $50 |
| $1,000 | $300 | $100 |
| $2,000 | $600 | $200 |
| $5,000 | $1,500 | $500 |

*Utilization has no memory - improve it instantly by paying down!*"""
    
    def best_student_cards(self) -> str:
        """Recommend best credit cards for students."""
        lines = ["💳 **Best Credit Cards for Students**\n"]
        
        for card in self.STUDENT_CARDS:
            lines.append(f"**{card['name']}**")
            lines.append(f"  • Annual Fee: ${card['annual_fee']}")
            lines.append(f"  • Rewards: {card['rewards']}")
            lines.append(f"  • Features: {', '.join(card['features'])}")
            lines.append("")
        
        lines.append("**My Top Pick:** Discover it Student")
        lines.append("  - Easiest approval for no credit")
        lines.append("  - Cashback match doubles rewards first year")
        lines.append("  - Good grades bonus ($20/year for 3.0+ GPA)")
        lines.append("\n*Start with ONE card. Add more after 6-12 months.*")
        
        return "\n".join(lines)
    
    def path_to_800(self) -> str:
        """Guide to achieving 800+ credit score."""
        return """🎯 **The Path to 800+ Credit Score**

**What It Takes:**
- Time (average age of accounts matters)
- Perfect payment history
- Low utilization
- Mix of credit types
- Minimal new accounts

**Timeline (Starting from Zero):**

**Year 1: Foundation (Score: 650-700)**
- Get first credit card
- Perfect payment history
- Keep utilization under 10%
- Don't apply for other credit

**Year 2: Growth (Score: 700-740)**
- Add second credit card
- Continue perfect payments
- Request limit increases
- Let accounts age

**Year 3-4: Optimization (Score: 740-780)**
- Maintain perfect history
- Consider credit builder loan for mix
- Keep old accounts open
- Minimal new applications

**Year 5+: Excellence (Score: 780-800+)**
- Long credit history
- Perfect payment record
- Low utilization
- Diverse credit mix

**The 800 Club Requirements:**
✅ 0 late payments (ever)
✅ Utilization under 10%
✅ Average account age 7+ years
✅ Mix of credit types
✅ Few recent inquiries

**Shortcuts Don't Exist, But:**
- Authorized user on old account helps
- Higher limits help utilization
- Time is your friend

**Why 800 Matters:**
- Best interest rates
- Best credit card offers
- Easy approval for anything
- Bragging rights 😎

*800 is achievable by your late 20s if you start now and stay disciplined.*"""
    
    def authorized_user_strategy(self) -> str:
        """Explain authorized user strategy."""
        return """👥 **Authorized User Strategy**

**What Is It?**
Being added to someone else's credit card account.

**How It Helps:**
- Their account history appears on YOUR credit report
- Instant credit history boost
- No liability for the debt

**Best Practices:**

**For Parents Adding You:**
1. Use a card with long history (5+ years ideal)
2. Card should have low utilization
3. Perfect payment history
4. You don't even need the physical card

**What Gets Reported:**
- Account age
- Credit limit
- Payment history
- Utilization

**Example Impact:**
- Parent has card open since 2010
- You're added in 2024
- Your report shows account since 2010
- Instant 14-year credit history!

**Cautions:**
⚠️ Their bad behavior affects you too
⚠️ High utilization hurts your score
⚠️ Late payments appear on your report
⚠️ Some lenders discount AU accounts

**The Strategy:**
1. Ask parent with oldest, cleanest card
2. Get added as authorized user
3. Don't need to use the card
4. Build your own credit simultaneously
5. Eventually your own accounts mature

*This is 100% legal and a common strategy for building credit fast.*"""
    
    def credit_mistakes(self) -> str:
        """Common credit mistakes to avoid."""
        return """❌ **Credit Mistakes to Avoid**

**1. Missing Payments**
- Single biggest factor (35% of score)
- One 30-day late payment can drop score 100+ points
- Stays on report for 7 years
- **Fix:** Set up autopay for at least minimum

**2. Maxing Out Cards**
- High utilization kills your score
- Even if you pay in full, statement balance matters
- **Fix:** Keep under 30%, ideally under 10%

**3. Closing Old Accounts**
- Reduces average account age
- Reduces total available credit
- **Fix:** Keep old cards open, even unused

**4. Applying for Too Much Credit**
- Each application = hard inquiry
- Multiple inquiries look desperate
- **Fix:** Space applications 6+ months apart

**5. Only Paying Minimums**
- Interest charges add up fast
- 20%+ APR is brutal
- **Fix:** Always pay full balance

**6. Ignoring Your Credit Report**
- Errors are common
- Identity theft happens
- **Fix:** Check free at annualcreditreport.com yearly

**7. Co-signing Loans**
- You're 100% responsible if they don't pay
- Their late payments hurt YOUR credit
- **Fix:** Just say no (seriously)

**8. Not Having Credit**
- No credit ≠ good credit
- Need history to have a score
- **Fix:** Start building now with student card

**The Golden Rules:**
✅ Pay on time, every time
✅ Keep utilization low
✅ Don't close old accounts
✅ Apply sparingly
✅ Monitor your credit"""
