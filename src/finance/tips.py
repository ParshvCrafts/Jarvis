"""
Money-Saving Tips for JARVIS.

Student-specific savings and wealth building:
- Student discounts
- Free resources
- Negotiation tips
- Cash back optimization
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

from loguru import logger


@dataclass
class Discount:
    name: str
    category: str
    discount: str
    how_to_get: str
    url: str = ""


class MoneySavingTips:
    """
    Money-saving tips and strategies.
    
    Features:
    - Student discounts database
    - Free resources for students
    - Negotiation strategies
    - Cash back optimization
    """
    
    # Student discounts
    STUDENT_DISCOUNTS = [
        Discount("Spotify", "Entertainment", "50% off Premium", "Verify with .edu email", "spotify.com/student"),
        Discount("Apple Music", "Entertainment", "50% off", "Verify student status", "apple.com/shop/browse/home/education"),
        Discount("Amazon Prime", "Shopping", "50% off ($7.49/mo)", "Verify with .edu email", "amazon.com/primestudent"),
        Discount("YouTube Premium", "Entertainment", "$7.99/mo (vs $13.99)", "Verify student status", "youtube.com/premium/student"),
        Discount("Hulu", "Entertainment", "$1.99/mo with Spotify Student", "Bundle with Spotify", "hulu.com"),
        Discount("Adobe Creative Cloud", "Software", "60% off", "Verify student status", "adobe.com/creativecloud/buy/students.html"),
        Discount("Microsoft 365", "Software", "FREE", "Use .edu email", "microsoft.com/education"),
        Discount("GitHub Pro", "Software", "FREE", "GitHub Student Developer Pack", "education.github.com"),
        Discount("Notion", "Software", "FREE Plus plan", "Use .edu email", "notion.so/students"),
        Discount("Figma", "Software", "FREE Education plan", "Verify student status", "figma.com/education"),
        Discount("JetBrains", "Software", "FREE all IDEs", "Verify student status", "jetbrains.com/student"),
        Discount("Autodesk", "Software", "FREE", "Verify student status", "autodesk.com/education"),
        Discount("Apple", "Hardware", "Education pricing", "Shop education store", "apple.com/us-edu/store"),
        Discount("Dell", "Hardware", "Up to 20% off", "Dell University program", "dell.com/en-us/lp/students"),
        Discount("Lenovo", "Hardware", "Up to 20% off", "ID.me verification", "lenovo.com/us/en/d/deals/students"),
        Discount("Samsung", "Hardware", "Up to 30% off", "Student discount program", "samsung.com/us/shop/discount-program/education"),
        Discount("The New York Times", "News", "$1/week", "Academic rate", "nytimes.com/subscription/education"),
        Discount("Wall Street Journal", "News", "$4/month", "Student rate", "wsj.com/student"),
        Discount("Headspace", "Wellness", "85% off", "Student plan", "headspace.com/students"),
        Discount("Calm", "Wellness", "85% off", "Student plan", "calm.com/student"),
    ]
    
    # Free resources for students
    FREE_RESOURCES = {
        "software": [
            "Microsoft 365 - Free with .edu email",
            "GitHub Student Pack - $200+ in free tools",
            "JetBrains IDEs - All professional IDEs free",
            "Notion - Free Plus plan",
            "Figma - Free Education plan",
            "Canva Pro - Free for students",
            "Grammarly Premium - Often free through school",
        ],
        "learning": [
            "LinkedIn Learning - Often free through library",
            "Coursera - Audit courses free",
            "edX - Audit courses free",
            "Khan Academy - Always free",
            "MIT OpenCourseWare - Always free",
            "freeCodeCamp - Always free",
        ],
        "campus": [
            "Campus gym - Usually included in fees",
            "Campus health center - Basic care included",
            "Career services - Resume reviews, mock interviews",
            "Library resources - Databases, journals, software",
            "Tutoring centers - Free academic help",
            "Campus events - Free food, entertainment",
        ],
        "financial": [
            "FAFSA - Free money for school",
            "Scholarships - Check Fastweb, Scholarships.com",
            "Work-study - On-campus jobs",
            "RA positions - Free housing",
            "Research positions - Paid + experience",
        ],
    }
    
    def __init__(self):
        logger.info("Money Saving Tips initialized")
    
    def get_student_discounts(self, category: Optional[str] = None) -> str:
        """Get list of student discounts."""
        discounts = self.STUDENT_DISCOUNTS
        
        if category:
            discounts = [d for d in discounts if category.lower() in d.category.lower()]
        
        if not discounts:
            return f"No discounts found for category '{category}'."
        
        lines = ["🎓 **Student Discounts**\n"]
        
        # Group by category
        by_category = {}
        for d in discounts:
            if d.category not in by_category:
                by_category[d.category] = []
            by_category[d.category].append(d)
        
        for cat, cat_discounts in by_category.items():
            lines.append(f"\n**{cat}:**")
            for d in cat_discounts:
                lines.append(f"  • **{d.name}**: {d.discount}")
                lines.append(f"    How: {d.how_to_get}")
        
        lines.append("\n*Always verify with your .edu email or student ID!*")
        
        return "\n".join(lines)
    
    def get_free_resources(self, category: Optional[str] = None) -> str:
        """Get list of free resources for students."""
        if category and category.lower() in self.FREE_RESOURCES:
            resources = {category.lower(): self.FREE_RESOURCES[category.lower()]}
        else:
            resources = self.FREE_RESOURCES
        
        lines = ["🆓 **Free Resources for Students**\n"]
        
        for cat, items in resources.items():
            lines.append(f"\n**{cat.title()}:**")
            for item in items:
                lines.append(f"  • {item}")
        
        return "\n".join(lines)
    
    def food_saving_tips(self) -> str:
        """Tips for saving money on food."""
        return """🍕 **Save Money on Food**

**Meal Prep Basics:**
- Cook in batches on Sunday
- Rice, beans, chicken = cheap + healthy
- Freeze portions for busy days
- Saves $200-400/month vs eating out

**Grocery Shopping:**
- Make a list, stick to it
- Buy store brands (same quality)
- Shop sales, use coupons
- Buy in bulk for staples
- Avoid pre-cut/prepared foods

**Campus Hacks:**
- Meal plan if cost-effective
- Free food at campus events
- Food pantry if needed (no shame!)
- Club meetings often have food

**Eating Out Smarter:**
- Happy hour specials
- Student discounts (Chipotle, etc.)
- Split meals with friends
- Water instead of drinks ($3-5 savings)
- Skip appetizers and desserts

**Apps to Use:**
- Too Good To Go - Discounted surplus food
- Flashfood - Grocery markdowns
- Ibotta - Cash back on groceries
- Fetch - Receipt scanning rewards

**The Math:**
| Option | Monthly Cost |
|--------|--------------|
| Eating out daily | $600+ |
| Mix of cooking/out | $300-400 |
| Mostly cooking | $150-250 |

**Quick Cheap Meals:**
- Rice + beans + veggies: $1-2
- Pasta + sauce: $1-2
- Eggs + toast: $1
- Oatmeal: $0.50
- Stir fry: $2-3

*Cooking is a life skill that saves thousands per year.*"""
    
    def negotiation_tips(self) -> str:
        """Tips for negotiating better deals."""
        return """💬 **Negotiation Tips**

**Everything is Negotiable:**
- Rent
- Salary
- Bills
- Prices
- Fees

**The Basic Script:**
"Hi, I've been a customer for [X time] and I'm looking to reduce my costs. What can you do for me?"

**Specific Strategies:**

**Credit Card Annual Fees:**
- Call and ask to waive
- Mention you'll cancel otherwise
- Success rate: 70%+
- Script: "I'd like to keep the card but the annual fee is hard to justify. Can you waive it or offer a retention bonus?"

**Cable/Internet Bills:**
- Call to cancel
- Get transferred to retention
- They'll offer discounts
- Save $20-50/month typically

**Rent:**
- Research comparable units
- Offer longer lease for discount
- Pay multiple months upfront
- Ask about move-in specials

**Medical Bills:**
- Always ask for itemized bill
- Errors are common
- Ask for cash pay discount (20-40% off)
- Set up payment plan if needed

**Salary Negotiation:**
- Research market rates (Glassdoor, Levels.fyi)
- Never give first number
- Negotiate total comp (salary + bonus + equity)
- Get offers in writing

**General Tips:**
1. Be polite but firm
2. Know your alternatives
3. Be willing to walk away
4. Ask for the manager
5. Timing matters (end of month/quarter)

**The Worst They Can Say is No**
You lose nothing by asking. Most people don't ask, so companies budget for discounts that go unclaimed.

*I've saved thousands just by asking. You can too.*"""
    
    def subscription_audit(self) -> str:
        """Guide to auditing subscriptions."""
        return """📱 **Subscription Audit Guide**

**The Problem:**
Average American spends $219/month on subscriptions.
Many are forgotten or barely used.

**Step 1: Find All Subscriptions**
Check:
- Bank/credit card statements
- Email for receipts
- App store subscriptions
- PayPal recurring payments

**Step 2: List and Evaluate**

| Subscription | Cost | Use Frequency | Keep? |
|--------------|------|---------------|-------|
| Netflix | $15 | Weekly | ✅ |
| Gym | $50 | Never | ❌ |
| Magazine | $10 | Never read | ❌ |

**Step 3: Cancel Ruthlessly**
- If you haven't used it in 30 days, cancel
- You can always resubscribe
- Free trials → Set calendar reminder to cancel

**Step 4: Optimize What You Keep**
- Share family plans (Spotify, Netflix, etc.)
- Use student discounts
- Annual vs monthly (usually 15-20% savings)
- Negotiate or threaten to cancel

**Common Subscription Wastes:**
- Gym memberships (use campus gym)
- Multiple streaming services
- Premium app versions you don't need
- Magazines/newspapers you don't read
- Cloud storage (use free tiers)

**Smart Subscription Strategy:**
- Rotate streaming services (1-2 at a time)
- Use free tiers when possible
- Share costs with roommates/family
- Review quarterly

**Tools to Help:**
- Rocket Money (Truebill) - Finds and cancels
- Trim - Negotiates bills
- Bank apps - Track recurring charges

**The Math:**
Cancel $50/month in unused subscriptions:
- Save $600/year
- Invested at 10% for 40 years = $26,000+

*That forgotten gym membership could cost you $26,000 in retirement.*"""
    
    def cash_back_optimization(self) -> str:
        """Optimize cash back and rewards."""
        return """💳 **Cash Back Optimization**

**The Strategy:**
Use the right card for each purchase category.

**Recommended Setup:**

**Card 1: Rotating Categories (5%)**
- Discover it or Chase Freedom Flex
- 5% on quarterly categories
- Activate each quarter!

**Card 2: Flat Rate (2%)**
- Citi Double Cash or Wells Fargo Active Cash
- 2% on everything
- Use when no bonus category applies

**Card 3: Dining/Entertainment (3-4%)**
- Capital One SavorOne
- 3% dining, entertainment, groceries

**Example Monthly Spending:**
| Category | Amount | Card | Cash Back |
|----------|--------|------|-----------|
| Groceries | $300 | Rotating (5%) | $15 |
| Dining | $150 | SavorOne (3%) | $4.50 |
| Gas | $100 | Rotating (5%) | $5 |
| Other | $200 | Double Cash (2%) | $4 |
| **Total** | $750 | | **$28.50** |

**Annual: $342 in free money!**

**Pro Tips:**
1. **Pay in full** - Interest kills rewards
2. **Activate categories** - Don't forget!
3. **Use portals** - Rakuten, airline portals for extra %
4. **Stack rewards** - Portal + card + promo
5. **Gift cards** - Buy at 5% category, use anywhere

**Shopping Portals:**
- Rakuten - Up to 10% back at stores
- TopCashback - Often highest rates
- Airline portals - Earn miles on purchases

**The Stacking Example:**
Buying $100 at Target:
- Rakuten: 1% = $1
- Credit card: 2% = $2
- Target Circle: 1% = $1
- **Total: 4% back**

**For Students:**
Start with ONE good card:
- Discover it Student (5% rotating + match)
- Build credit while earning rewards
- Add more cards after 1 year

*Never pay interest. Rewards only matter if you pay in full.*"""
    
    def wealth_building_habits(self) -> str:
        """Daily habits for building wealth."""
        return """💰 **Wealth-Building Habits**

**Daily Habits:**
- Check spending (5 min)
- Pack lunch instead of buying
- Use cash back apps
- Avoid impulse purchases (24-hour rule)

**Weekly Habits:**
- Review budget
- Meal prep
- Check for deals before buying
- Transfer to savings

**Monthly Habits:**
- Pay all bills on time
- Review subscriptions
- Check credit score
- Invest consistently

**Yearly Habits:**
- Review and adjust budget
- Rebalance investments
- Tax planning
- Negotiate bills
- Review insurance

**The Latte Factor:**
Small daily expenses add up:
| Daily Expense | Monthly | Yearly | 40 Years (10%) |
|---------------|---------|--------|----------------|
| $5 coffee | $150 | $1,800 | $790,000 |
| $10 lunch | $300 | $3,600 | $1,580,000 |
| $3 snack | $90 | $1,080 | $474,000 |

**I'm Not Saying Never Buy Coffee**
But be intentional. Know what you're trading.

**The 24-Hour Rule:**
Want something? Wait 24 hours.
- Often the urge passes
- Prevents impulse buys
- Saves thousands yearly

**Pay Yourself First:**
1. Income arrives
2. Automatically transfer to savings/investments
3. Live on what's left
4. Not: spend first, save what's left

**The Wealth Formula:**
Wealth = (Income - Expenses) × Time × Returns

You control:
- Expenses (reduce)
- Time (start now)
- Returns (invest wisely)

*Wealth is built through consistent habits, not windfalls.*"""
