"""
High-Yield Savings & Banking for JARVIS.

Track and compare savings account rates:
- High-yield savings accounts
- Emergency fund guidance
- CD rates
- Money market accounts
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Dict, List, Optional

from loguru import logger


@dataclass
class SavingsAccount:
    name: str
    apy: float
    minimum_balance: float = 0
    monthly_fee: float = 0
    fdic_insured: bool = True
    features: List[str] = field(default_factory=list)
    url: str = ""
    last_updated: date = field(default_factory=date.today)


class SavingsOptimizer:
    """
    High-yield savings account comparison and optimization.
    
    Features:
    - Compare savings rates
    - Emergency fund calculator
    - Interest earnings calculator
    - Account recommendations
    """
    
    # Current high-yield savings rates (manually updated)
    # Last updated: December 2024
    SAVINGS_ACCOUNTS = {
        "sofi": SavingsAccount(
            name="SoFi Checking & Savings",
            apy=4.30,
            minimum_balance=0,
            features=["No minimum", "No fees", "Up to 4.30% with direct deposit"],
            url="https://www.sofi.com/banking/"
        ),
        "marcus": SavingsAccount(
            name="Marcus by Goldman Sachs",
            apy=4.20,
            minimum_balance=0,
            features=["No minimum", "No fees", "Trusted brand"],
            url="https://www.marcus.com/"
        ),
        "ally": SavingsAccount(
            name="Ally Bank",
            apy=4.20,
            minimum_balance=0,
            features=["No minimum", "No fees", "Great app", "Buckets feature"],
            url="https://www.ally.com/"
        ),
        "discover": SavingsAccount(
            name="Discover Online Savings",
            apy=4.10,
            minimum_balance=0,
            features=["No minimum", "No fees", "Cash back debit card"],
            url="https://www.discover.com/online-banking/"
        ),
        "capital_one": SavingsAccount(
            name="Capital One 360",
            apy=4.00,
            minimum_balance=0,
            features=["No minimum", "No fees", "Physical branches"],
            url="https://www.capitalone.com/bank/"
        ),
        "wealthfront": SavingsAccount(
            name="Wealthfront Cash Account",
            apy=4.50,
            minimum_balance=0,
            features=["No minimum", "No fees", "FDIC insured up to $8M"],
            url="https://www.wealthfront.com/"
        ),
        "betterment": SavingsAccount(
            name="Betterment Cash Reserve",
            apy=4.50,
            minimum_balance=0,
            features=["No minimum", "No fees", "FDIC insured up to $2M"],
            url="https://www.betterment.com/"
        ),
    }
    
    # Traditional bank rates for comparison
    TRADITIONAL_RATES = {
        "chase": 0.01,
        "bank_of_america": 0.01,
        "wells_fargo": 0.01,
        "citi": 0.01,
    }
    
    def __init__(self):
        logger.info("Savings Optimizer initialized")
    
    def get_best_rates(self, top_n: int = 5) -> str:
        """Get the best current savings rates."""
        sorted_accounts = sorted(
            self.SAVINGS_ACCOUNTS.values(),
            key=lambda x: x.apy,
            reverse=True
        )[:top_n]
        
        lines = ["💰 **Best High-Yield Savings Rates**\n"]
        
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
        
        for i, account in enumerate(sorted_accounts):
            medal = medals[i] if i < len(medals) else f"{i+1}."
            lines.append(f"{medal} **{account.name}**: {account.apy:.2f}% APY")
            if account.features:
                lines.append(f"   {', '.join(account.features[:2])}")
        
        lines.append(f"\n*Rates as of {date.today().strftime('%B %Y')}. Rates change frequently.*")
        lines.append("\n**Compare to traditional banks:** ~0.01% APY")
        
        return "\n".join(lines)
    
    def compare_accounts(self, account1: str, account2: str) -> str:
        """Compare two savings accounts."""
        acc1 = self.SAVINGS_ACCOUNTS.get(account1.lower().replace(" ", "_"))
        acc2 = self.SAVINGS_ACCOUNTS.get(account2.lower().replace(" ", "_"))
        
        if not acc1 or not acc2:
            return "Couldn't find one or both accounts. Try: SoFi, Marcus, Ally, Discover, Capital One"
        
        return f"""⚖️ **{acc1.name} vs {acc2.name}**

| Feature | {acc1.name} | {acc2.name} |
|---------|-------------|-------------|
| APY | {acc1.apy:.2f}% | {acc2.apy:.2f}% |
| Minimum | ${acc1.minimum_balance:,.0f} | ${acc2.minimum_balance:,.0f} |
| Monthly Fee | ${acc1.monthly_fee:.2f} | ${acc2.monthly_fee:.2f} |
| FDIC Insured | {'Yes' if acc1.fdic_insured else 'No'} | {'Yes' if acc2.fdic_insured else 'No'} |

**Winner by APY:** {acc1.name if acc1.apy > acc2.apy else acc2.name}"""
    
    def calculate_interest(self, principal: float, years: int = 1, apy: float = 4.30) -> str:
        """Calculate interest earnings."""
        # Simple interest for savings (compounded daily, but simplified)
        final_amount = principal * ((1 + apy/100) ** years)
        interest_earned = final_amount - principal
        
        # Compare to traditional bank
        traditional_final = principal * ((1 + 0.01/100) ** years)
        traditional_interest = traditional_final - principal
        
        difference = interest_earned - traditional_interest
        
        return f"""📊 **Interest Calculator**

💵 **Your Deposit:** ${principal:,.2f}
📅 **Time Period:** {years} year{'s' if years > 1 else ''}
📈 **APY:** {apy:.2f}%

**High-Yield Savings:**
- Final Balance: ${final_amount:,.2f}
- Interest Earned: **${interest_earned:,.2f}**

**Traditional Bank (0.01% APY):**
- Final Balance: ${traditional_final:,.2f}
- Interest Earned: ${traditional_interest:,.2f}

🎯 **You earn ${difference:,.2f} MORE with high-yield savings!**

*That's free money just for keeping your savings in the right place.*"""
    
    def emergency_fund_calculator(self, monthly_expenses: float, months: int = 6) -> str:
        """Calculate emergency fund target."""
        target = monthly_expenses * months
        
        # Calculate interest at different rates
        hy_interest = target * 0.043  # 4.3% APY
        trad_interest = target * 0.0001  # 0.01% APY
        
        return f"""🏦 **Emergency Fund Calculator**

📊 **Your Numbers:**
- Monthly expenses: ${monthly_expenses:,.2f}
- Recommended months: {months}
- **Target amount: ${target:,.2f}**

💰 **Annual Interest on Emergency Fund:**
- High-yield (4.3%): **${hy_interest:,.2f}/year**
- Traditional (0.01%): ${trad_interest:,.2f}/year
- **Difference: ${hy_interest - trad_interest:,.2f}/year FREE**

📈 **Building Your Fund:**
| Monthly Savings | Time to Goal |
|-----------------|--------------|
| $200 | {target/200:.0f} months |
| $500 | {target/500:.0f} months |
| $1,000 | {target/1000:.0f} months |

**Recommended Accounts:**
1. SoFi (4.30% APY)
2. Wealthfront (4.50% APY)
3. Ally (4.20% APY, great app)

*Keep emergency fund separate from checking to avoid spending it.*"""
    
    def where_to_keep_money(self) -> str:
        """Advice on where to keep different types of money."""
        return """🏦 **Where to Keep Your Money**

**Checking Account (Daily Spending):**
- Keep 1-2 months expenses
- Use for bills and daily purchases
- Doesn't need high interest
- Recommended: Local bank or SoFi

**High-Yield Savings (Emergency Fund):**
- Keep 3-6 months expenses
- Don't touch unless emergency
- Get 4%+ APY
- Recommended: SoFi, Ally, Marcus

**Short-Term Savings (1-2 years):**
- Down payment, vacation, etc.
- High-yield savings or CDs
- Keep liquid and safe
- Recommended: Same as emergency fund

**Long-Term Investing (5+ years):**
- Retirement, wealth building
- Invest in index funds
- Accept some volatility
- Recommended: Fidelity, Vanguard

**Quick Reference:**
| Purpose | Where | Why |
|---------|-------|-----|
| Daily spending | Checking | Easy access |
| Emergency fund | HYSA | Safe + 4% return |
| Short-term goals | HYSA/CD | Safe + decent return |
| Retirement | Roth IRA | Tax-free growth |
| Long-term wealth | Brokerage | Higher returns |

*Never keep more than 1-2 months in regular checking - you're losing money to inflation!*"""
    
    def get_account_info(self, account_name: str) -> str:
        """Get detailed info about a specific account."""
        key = account_name.lower().replace(" ", "_")
        
        # Try to find account
        account = self.SAVINGS_ACCOUNTS.get(key)
        
        if not account:
            # Fuzzy match
            for k, v in self.SAVINGS_ACCOUNTS.items():
                if account_name.lower() in v.name.lower() or account_name.lower() in k:
                    account = v
                    break
        
        if not account:
            return f"Couldn't find info for '{account_name}'. Try: SoFi, Marcus, Ally, Discover, Capital One"
        
        lines = [
            f"🏦 **{account.name}**\n",
            f"📈 **APY:** {account.apy:.2f}%",
            f"💵 **Minimum Balance:** ${account.minimum_balance:,.0f}",
            f"💳 **Monthly Fee:** ${account.monthly_fee:.2f}",
            f"🔒 **FDIC Insured:** {'Yes' if account.fdic_insured else 'No'}",
        ]
        
        if account.features:
            lines.append(f"\n✨ **Features:**")
            for feature in account.features:
                lines.append(f"  • {feature}")
        
        if account.url:
            lines.append(f"\n🔗 {account.url}")
        
        return "\n".join(lines)
    
    def hysa_vs_traditional(self) -> str:
        """Compare high-yield vs traditional savings."""
        return """📊 **High-Yield vs Traditional Savings**

**The Difference:**
- High-Yield Savings: ~4.30% APY
- Traditional Bank: ~0.01% APY

**On $10,000 over 1 year:**
| Account Type | Interest Earned |
|--------------|-----------------|
| High-Yield (4.3%) | $430 |
| Traditional (0.01%) | $1 |
| **Difference** | **$429** |

**Why Traditional Banks Pay So Little:**
- They have expensive branches
- They spend on marketing
- They know most people won't switch
- They profit from your inertia

**Why High-Yield Banks Pay More:**
- Online-only = lower costs
- Competing for deposits
- Pass savings to customers

**Is It Safe?**
✅ FDIC insured up to $250,000
✅ Same protection as traditional banks
✅ Your money is just as safe

**The Only Downside:**
- No physical branches (but who needs them?)
- Transfers take 1-2 days (plan ahead)

**Bottom Line:**
Keeping money in a traditional savings account is like leaving $400+ on the table every year. Takes 10 minutes to open a high-yield account."""
