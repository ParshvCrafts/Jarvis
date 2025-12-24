"""
Application Analytics Dashboard for JARVIS Internship Module.

Provides comprehensive statistics and insights on internship applications.
"""

import os
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from .tracker import ApplicationTracker
from .models import Application, ApplicationStatus, ApplicationStats


@dataclass
class ApplicationFunnel:
    """Application funnel metrics."""
    saved: int = 0
    applied: int = 0
    phone_screen: int = 0
    interview: int = 0
    final_round: int = 0
    offer: int = 0
    accepted: int = 0
    rejected: int = 0


@dataclass
class TimeMetrics:
    """Time-based metrics."""
    avg_response_days: float = 0.0
    avg_interview_days: float = 0.0
    avg_offer_days: float = 0.0
    fastest_response: Optional[int] = None
    slowest_response: Optional[int] = None


@dataclass
class PerformanceInsights:
    """Performance insights."""
    best_resume_version: Optional[str] = None
    best_company_type: Optional[str] = None
    best_role_type: Optional[str] = None
    most_successful_source: Optional[str] = None
    peak_application_day: Optional[str] = None


@dataclass
class DashboardData:
    """Complete dashboard data."""
    # Overview
    total_applications: int = 0
    this_week: int = 0
    this_month: int = 0
    
    # Funnel
    funnel: ApplicationFunnel = field(default_factory=ApplicationFunnel)
    
    # Rates
    response_rate: float = 0.0
    interview_rate: float = 0.0
    offer_rate: float = 0.0
    
    # Time metrics
    time_metrics: TimeMetrics = field(default_factory=TimeMetrics)
    
    # Insights
    insights: PerformanceInsights = field(default_factory=PerformanceInsights)
    
    # Action items
    follow_ups_needed: List[Application] = field(default_factory=list)
    upcoming_interviews: List[Application] = field(default_factory=list)
    upcoming_deadlines: List[Tuple[str, date]] = field(default_factory=list)
    
    # Top companies
    top_companies: List[str] = field(default_factory=list)


class ApplicationAnalytics:
    """
    Generate analytics and insights for internship applications.
    
    Features:
    - Application funnel analysis
    - Response time metrics
    - Success rate calculations
    - Performance insights
    - Action item identification
    """
    
    def __init__(self, tracker: ApplicationTracker):
        self.tracker = tracker
    
    def get_dashboard_data(self) -> DashboardData:
        """Get complete dashboard data."""
        apps = self.tracker.get_all_applications()
        
        if not apps:
            return DashboardData()
        
        dashboard = DashboardData()
        
        # Overview
        dashboard.total_applications = len(apps)
        dashboard.this_week = self._count_recent(apps, days=7)
        dashboard.this_month = self._count_recent(apps, days=30)
        
        # Funnel
        dashboard.funnel = self._calculate_funnel(apps)
        
        # Rates
        applied_count = dashboard.total_applications - dashboard.funnel.saved
        if applied_count > 0:
            responded = (
                dashboard.funnel.phone_screen +
                dashboard.funnel.interview +
                dashboard.funnel.final_round +
                dashboard.funnel.offer +
                dashboard.funnel.accepted +
                dashboard.funnel.rejected
            )
            dashboard.response_rate = responded / applied_count
            
            interviewed = (
                dashboard.funnel.phone_screen +
                dashboard.funnel.interview +
                dashboard.funnel.final_round +
                dashboard.funnel.offer +
                dashboard.funnel.accepted
            )
            dashboard.interview_rate = interviewed / applied_count
            
            offers = dashboard.funnel.offer + dashboard.funnel.accepted
            dashboard.offer_rate = offers / applied_count
        
        # Time metrics
        dashboard.time_metrics = self._calculate_time_metrics(apps)
        
        # Insights
        dashboard.insights = self._generate_insights(apps)
        
        # Action items
        dashboard.follow_ups_needed = self.tracker.get_follow_up_reminders()[:5]
        dashboard.upcoming_interviews = [
            app for app in apps 
            if app.status in [ApplicationStatus.PHONE_SCREEN, ApplicationStatus.INTERVIEW]
        ][:5]
        
        # Top companies
        company_counts = {}
        for app in apps:
            company_counts[app.company] = company_counts.get(app.company, 0) + 1
        dashboard.top_companies = sorted(
            company_counts.keys(),
            key=lambda c: company_counts[c],
            reverse=True
        )[:5]
        
        return dashboard
    
    def _count_recent(self, apps: List[Application], days: int) -> int:
        """Count applications from recent days."""
        cutoff = datetime.now() - timedelta(days=days)
        return sum(
            1 for app in apps
            if app.date_saved and app.date_saved >= cutoff
        )
    
    def _calculate_funnel(self, apps: List[Application]) -> ApplicationFunnel:
        """Calculate application funnel."""
        funnel = ApplicationFunnel()
        
        for app in apps:
            status = app.status
            if status == ApplicationStatus.SAVED:
                funnel.saved += 1
            elif status == ApplicationStatus.APPLIED:
                funnel.applied += 1
            elif status == ApplicationStatus.PHONE_SCREEN:
                funnel.phone_screen += 1
            elif status in [ApplicationStatus.TECHNICAL, ApplicationStatus.INTERVIEW]:
                funnel.interview += 1
            elif status == ApplicationStatus.FINAL_ROUND:
                funnel.final_round += 1
            elif status == ApplicationStatus.OFFER:
                funnel.offer += 1
            elif status == ApplicationStatus.ACCEPTED:
                funnel.accepted += 1
            elif status == ApplicationStatus.REJECTED:
                funnel.rejected += 1
        
        return funnel
    
    def _calculate_time_metrics(self, apps: List[Application]) -> TimeMetrics:
        """Calculate time-based metrics."""
        metrics = TimeMetrics()
        
        response_times = []
        for app in apps:
            if app.date_applied and app.response_date:
                days = (app.response_date - app.date_applied).days
                response_times.append(days)
        
        if response_times:
            metrics.avg_response_days = sum(response_times) / len(response_times)
            metrics.fastest_response = min(response_times)
            metrics.slowest_response = max(response_times)
        
        return metrics
    
    def _generate_insights(self, apps: List[Application]) -> PerformanceInsights:
        """Generate performance insights."""
        insights = PerformanceInsights()
        
        # Find best performing role type
        role_success = {}
        for app in apps:
            if app.status in [ApplicationStatus.INTERVIEW, ApplicationStatus.OFFER, ApplicationStatus.ACCEPTED]:
                role = self._categorize_role(app.role)
                role_success[role] = role_success.get(role, 0) + 1
        
        if role_success:
            insights.best_role_type = max(role_success.keys(), key=lambda r: role_success[r])
        
        # Find peak application day
        day_counts = {}
        for app in apps:
            if app.date_applied:
                day = app.date_applied.strftime("%A")
                day_counts[day] = day_counts.get(day, 0) + 1
        
        if day_counts:
            insights.peak_application_day = max(day_counts.keys(), key=lambda d: day_counts[d])
        
        return insights
    
    def _categorize_role(self, role: str) -> str:
        """Categorize a role into a type."""
        role_lower = role.lower()
        
        if "data" in role_lower:
            return "Data Science"
        elif "ml" in role_lower or "machine learning" in role_lower:
            return "Machine Learning"
        elif "software" in role_lower or "swe" in role_lower:
            return "Software Engineering"
        elif "research" in role_lower:
            return "Research"
        else:
            return "Other"


def format_dashboard(data: DashboardData) -> str:
    """Format dashboard data as a readable report."""
    lines = [
        "📊 **Your Internship Application Dashboard**",
        "",
        "**Overview:**",
        f"  📝 Total Applications: {data.total_applications}",
        f"  📅 This Week: {data.this_week}",
        f"  📆 This Month: {data.this_month}",
        "",
    ]
    
    # Funnel visualization
    funnel = data.funnel
    max_count = max(
        funnel.saved + funnel.applied,
        funnel.phone_screen + funnel.interview,
        funnel.offer + funnel.accepted,
        funnel.rejected,
        1
    )
    
    def bar(count: int, max_val: int, width: int = 20) -> str:
        filled = int((count / max_val) * width) if max_val > 0 else 0
        return "█" * filled + "░" * (width - filled)
    
    total_applied = funnel.applied + funnel.phone_screen + funnel.interview + funnel.final_round + funnel.offer + funnel.accepted + funnel.rejected
    total_interview = funnel.phone_screen + funnel.interview + funnel.final_round + funnel.offer + funnel.accepted
    total_offer = funnel.offer + funnel.accepted
    
    lines.extend([
        "**Funnel:**",
        f"  Saved:     {bar(funnel.saved, max_count)} {funnel.saved}",
        f"  Applied:   {bar(total_applied, max_count)} {total_applied}",
        f"  Interview: {bar(total_interview, max_count)} {total_interview}",
        f"  Offer:     {bar(total_offer, max_count)} {total_offer}",
        f"  Rejected:  {bar(funnel.rejected, max_count)} {funnel.rejected}",
        "",
    ])
    
    # Rates
    lines.extend([
        "**Metrics:**",
        f"  📈 Response Rate: {data.response_rate:.0%}",
        f"  🎯 Interview Rate: {data.interview_rate:.0%}",
        f"  🏆 Offer Rate: {data.offer_rate:.0%}",
    ])
    
    if data.time_metrics.avg_response_days > 0:
        lines.append(f"  ⏱️ Avg Response Time: {data.time_metrics.avg_response_days:.1f} days")
    
    lines.append("")
    
    # Insights
    if data.insights.best_role_type or data.insights.peak_application_day:
        lines.append("**Insights:**")
        if data.insights.best_role_type:
            lines.append(f"  🎯 Best Role Type: {data.insights.best_role_type}")
        if data.insights.peak_application_day:
            lines.append(f"  📅 Peak Day: {data.insights.peak_application_day}")
        lines.append("")
    
    # Action items
    if data.follow_ups_needed:
        lines.append("**Follow-ups Needed:**")
        for app in data.follow_ups_needed[:3]:
            days_ago = (datetime.now() - app.date_applied).days if app.date_applied else 0
            lines.append(f"  ⏰ {app.company} (applied {days_ago} days ago)")
        lines.append("")
    
    if data.upcoming_interviews:
        lines.append("**Upcoming Interviews:**")
        for app in data.upcoming_interviews[:3]:
            lines.append(f"  📞 {app.company} - {app.role}")
        lines.append("")
    
    # Top companies
    if data.top_companies:
        lines.append(f"**Top Companies:** {', '.join(data.top_companies[:3])}")
    
    return "\n".join(lines)


def generate_html_dashboard(data: DashboardData) -> str:
    """Generate an HTML dashboard."""
    funnel = data.funnel
    total_applied = funnel.applied + funnel.phone_screen + funnel.interview + funnel.final_round + funnel.offer + funnel.accepted + funnel.rejected
    total_interview = funnel.phone_screen + funnel.interview + funnel.final_round + funnel.offer + funnel.accepted
    total_offer = funnel.offer + funnel.accepted
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>JARVIS Internship Dashboard</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #eee;
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ text-align: center; margin-bottom: 30px; color: #00d4ff; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }}
        .card {{
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 20px;
            border: 1px solid rgba(255,255,255,0.1);
        }}
        .card h2 {{ color: #00d4ff; margin-bottom: 15px; font-size: 1.2em; }}
        .stat {{ display: flex; justify-content: space-between; margin: 10px 0; }}
        .stat-value {{ font-size: 1.5em; font-weight: bold; color: #00d4ff; }}
        .funnel-bar {{
            height: 30px;
            background: rgba(0,212,255,0.2);
            border-radius: 5px;
            margin: 5px 0;
            position: relative;
            overflow: hidden;
        }}
        .funnel-fill {{
            height: 100%;
            background: linear-gradient(90deg, #00d4ff, #0099ff);
            border-radius: 5px;
            transition: width 0.5s ease;
        }}
        .funnel-label {{
            position: absolute;
            left: 10px;
            top: 50%;
            transform: translateY(-50%);
            font-size: 0.9em;
        }}
        .funnel-count {{
            position: absolute;
            right: 10px;
            top: 50%;
            transform: translateY(-50%);
            font-weight: bold;
        }}
        .metric {{ text-align: center; padding: 15px; }}
        .metric-value {{ font-size: 2em; color: #00d4ff; }}
        .metric-label {{ color: #888; }}
        .action-item {{
            background: rgba(255,193,7,0.1);
            border-left: 3px solid #ffc107;
            padding: 10px;
            margin: 5px 0;
            border-radius: 0 5px 5px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>💼 JARVIS Internship Dashboard</h1>
        
        <div class="grid">
            <div class="card">
                <h2>📊 Overview</h2>
                <div class="stat">
                    <span>Total Applications</span>
                    <span class="stat-value">{data.total_applications}</span>
                </div>
                <div class="stat">
                    <span>This Week</span>
                    <span class="stat-value">{data.this_week}</span>
                </div>
                <div class="stat">
                    <span>This Month</span>
                    <span class="stat-value">{data.this_month}</span>
                </div>
            </div>
            
            <div class="card">
                <h2>📈 Funnel</h2>
                <div class="funnel-bar">
                    <div class="funnel-fill" style="width: 100%"></div>
                    <span class="funnel-label">Saved</span>
                    <span class="funnel-count">{funnel.saved}</span>
                </div>
                <div class="funnel-bar">
                    <div class="funnel-fill" style="width: {(total_applied / max(data.total_applications, 1)) * 100}%"></div>
                    <span class="funnel-label">Applied</span>
                    <span class="funnel-count">{total_applied}</span>
                </div>
                <div class="funnel-bar">
                    <div class="funnel-fill" style="width: {(total_interview / max(data.total_applications, 1)) * 100}%"></div>
                    <span class="funnel-label">Interview</span>
                    <span class="funnel-count">{total_interview}</span>
                </div>
                <div class="funnel-bar">
                    <div class="funnel-fill" style="width: {(total_offer / max(data.total_applications, 1)) * 100}%"></div>
                    <span class="funnel-label">Offer</span>
                    <span class="funnel-count">{total_offer}</span>
                </div>
            </div>
            
            <div class="card">
                <h2>🎯 Metrics</h2>
                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px;">
                    <div class="metric">
                        <div class="metric-value">{data.response_rate:.0%}</div>
                        <div class="metric-label">Response Rate</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{data.interview_rate:.0%}</div>
                        <div class="metric-label">Interview Rate</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{data.offer_rate:.0%}</div>
                        <div class="metric-label">Offer Rate</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{data.time_metrics.avg_response_days:.0f}d</div>
                        <div class="metric-label">Avg Response</div>
                    </div>
                </div>
            </div>
            
            <div class="card">
                <h2>⏰ Action Items</h2>
                {"".join(f'<div class="action-item">Follow up: {app.company}</div>' for app in data.follow_ups_needed[:5]) or '<p>No action items</p>'}
            </div>
        </div>
        
        <p style="text-align: center; margin-top: 30px; color: #666;">
            Generated by JARVIS • {datetime.now().strftime('%Y-%m-%d %H:%M')}
        </p>
    </div>
</body>
</html>"""
    
    return html


def save_html_dashboard(data: DashboardData, output_path: str = "data/internship_dashboard.html") -> str:
    """Save HTML dashboard to file."""
    html = generate_html_dashboard(data)
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    
    logger.info(f"Dashboard saved to {output_path}")
    return output_path
