#!/usr/bin/env python3
"""
JARVIS Security Audit Script

Performs security checks on the JARVIS installation:
- Credential security (API keys, secrets)
- File permissions
- Input validation
- Network security
- IoT security

Usage:
    python scripts/security_audit.py [--fix] [--json]

Options:
    --fix   Attempt to fix issues automatically
    --json  Output results as JSON
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class Severity:
    """Security issue severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class SecurityFinding:
    """A security finding."""
    category: str
    severity: str
    title: str
    description: str
    recommendation: str
    auto_fixable: bool = False
    fixed: bool = False
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AuditResult:
    """Result of security audit."""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    findings: List[SecurityFinding] = field(default_factory=list)
    
    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.CRITICAL)
    
    @property
    def high_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.HIGH)
    
    @property
    def medium_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.MEDIUM)
    
    @property
    def low_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.LOW)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "summary": {
                "critical": self.critical_count,
                "high": self.high_count,
                "medium": self.medium_count,
                "low": self.low_count,
                "total": len(self.findings),
            },
            "findings": [
                {
                    "category": f.category,
                    "severity": f.severity,
                    "title": f.title,
                    "description": f.description,
                    "recommendation": f.recommendation,
                    "auto_fixable": f.auto_fixable,
                    "fixed": f.fixed,
                }
                for f in self.findings
            ],
        }


class SecurityAuditor:
    """
    Security auditor for JARVIS.
    
    Checks:
    - Credential exposure
    - File permissions
    - Configuration security
    - Input validation
    - Network security
    """
    
    # Patterns that indicate secrets
    SECRET_PATTERNS = [
        (r"sk-[a-zA-Z0-9]{48}", "OpenAI API Key"),
        (r"sk-ant-[a-zA-Z0-9-]{95}", "Anthropic API Key"),
        (r"gsk_[a-zA-Z0-9]{52}", "Groq API Key"),
        (r"AIza[a-zA-Z0-9_-]{35}", "Google API Key"),
        (r"[0-9]+:[a-zA-Z0-9_-]{35}", "Telegram Bot Token"),
        (r"ghp_[a-zA-Z0-9]{36}", "GitHub Personal Access Token"),
        (r"-----BEGIN (RSA |EC |)PRIVATE KEY-----", "Private Key"),
        (r"password\s*[=:]\s*['\"][^'\"]+['\"]", "Hardcoded Password"),
    ]
    
    # Files that should never be committed
    SENSITIVE_FILES = [
        ".env",
        "*.pem",
        "*.key",
        "*_secret*",
        "*credentials*",
    ]
    
    # Files to scan for secrets
    CODE_EXTENSIONS = [".py", ".js", ".ts", ".yaml", ".yml", ".json", ".toml"]
    
    def __init__(self, project_root: Optional[Path] = None, auto_fix: bool = False):
        self.project_root = project_root or PROJECT_ROOT
        self.auto_fix = auto_fix
        self.result = AuditResult()
    
    def add_finding(
        self,
        category: str,
        severity: str,
        title: str,
        description: str,
        recommendation: str,
        auto_fixable: bool = False,
        **details,
    ) -> SecurityFinding:
        """Add a security finding."""
        finding = SecurityFinding(
            category=category,
            severity=severity,
            title=title,
            description=description,
            recommendation=recommendation,
            auto_fixable=auto_fixable,
            details=details,
        )
        self.result.findings.append(finding)
        return finding
    
    # =========================================================================
    # Credential Security
    # =========================================================================
    
    def audit_env_file(self) -> None:
        """Audit .env file security."""
        env_path = self.project_root / ".env"
        
        if not env_path.exists():
            self.add_finding(
                category="credentials",
                severity=Severity.INFO,
                title="No .env file found",
                description="Environment file not present",
                recommendation="Create .env file for API keys",
            )
            return
        
        # Check file permissions (Unix only)
        if os.name != "nt":
            mode = os.stat(env_path).st_mode
            if mode & stat.S_IROTH or mode & stat.S_IWOTH:
                finding = self.add_finding(
                    category="credentials",
                    severity=Severity.HIGH,
                    title=".env file world-readable",
                    description=f"File permissions: {oct(mode)}",
                    recommendation="Run: chmod 600 .env",
                    auto_fixable=True,
                )
                
                if self.auto_fix:
                    os.chmod(env_path, stat.S_IRUSR | stat.S_IWUSR)
                    finding.fixed = True
        
        # Check for placeholder values
        with open(env_path) as f:
            content = f.read()
        
        placeholders = ["your_", "xxx", "changeme", "placeholder", "example"]
        for line in content.split("\n"):
            if "=" in line and not line.strip().startswith("#"):
                key, _, value = line.partition("=")
                value = value.strip().strip("'\"")
                
                for placeholder in placeholders:
                    if placeholder in value.lower():
                        self.add_finding(
                            category="credentials",
                            severity=Severity.MEDIUM,
                            title=f"Placeholder value in {key.strip()}",
                            description="API key appears to be a placeholder",
                            recommendation=f"Replace placeholder in {key.strip()} with actual value",
                        )
                        break
    
    def audit_gitignore(self) -> None:
        """Audit .gitignore for sensitive files."""
        gitignore_path = self.project_root / ".gitignore"
        
        if not gitignore_path.exists():
            self.add_finding(
                category="credentials",
                severity=Severity.HIGH,
                title="No .gitignore file",
                description="Sensitive files may be committed to git",
                recommendation="Create .gitignore with .env and other sensitive patterns",
                auto_fixable=True,
            )
            return
        
        with open(gitignore_path) as f:
            gitignore_content = f.read()
        
        required_patterns = [".env", "*.pem", "*.key", "__pycache__", "*.pyc"]
        missing = []
        
        for pattern in required_patterns:
            if pattern not in gitignore_content:
                missing.append(pattern)
        
        if missing:
            self.add_finding(
                category="credentials",
                severity=Severity.MEDIUM,
                title="Missing .gitignore patterns",
                description=f"Patterns not in .gitignore: {', '.join(missing)}",
                recommendation="Add missing patterns to .gitignore",
            )
    
    def audit_hardcoded_secrets(self) -> None:
        """Scan code for hardcoded secrets."""
        for ext in self.CODE_EXTENSIONS:
            for file_path in self.project_root.rglob(f"*{ext}"):
                # Skip venv and node_modules
                if "venv" in str(file_path) or "node_modules" in str(file_path):
                    continue
                if ".git" in str(file_path):
                    continue
                
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    
                    for pattern, secret_type in self.SECRET_PATTERNS:
                        matches = re.findall(pattern, content)
                        if matches:
                            # Check if it's in a comment or example
                            for match in matches:
                                if "example" not in content[max(0, content.find(match)-50):content.find(match)+len(match)+50].lower():
                                    self.add_finding(
                                        category="credentials",
                                        severity=Severity.CRITICAL,
                                        title=f"Hardcoded {secret_type}",
                                        description=f"Found in {file_path.relative_to(self.project_root)}",
                                        recommendation="Move secret to .env file and use environment variable",
                                        file=str(file_path.relative_to(self.project_root)),
                                    )
                                    break
                except Exception:
                    pass
    
    # =========================================================================
    # Configuration Security
    # =========================================================================
    
    def audit_config_security(self) -> None:
        """Audit configuration file security."""
        settings_path = self.project_root / "config" / "settings.yaml"
        
        if not settings_path.exists():
            return
        
        try:
            import yaml
            with open(settings_path) as f:
                config = yaml.safe_load(f)
            
            if not config:
                return
            
            # Check for debug mode in production
            if config.get("jarvis", {}).get("debug", False):
                self.add_finding(
                    category="configuration",
                    severity=Severity.LOW,
                    title="Debug mode enabled",
                    description="Debug mode may expose sensitive information",
                    recommendation="Set debug: false in production",
                )
            
            # Check Telegram security
            telegram = config.get("telegram", {})
            if telegram.get("enabled", False):
                allowed_users = telegram.get("allowed_users", [])
                if not allowed_users:
                    self.add_finding(
                        category="configuration",
                        severity=Severity.HIGH,
                        title="Telegram whitelist empty",
                        description="No user whitelist configured for Telegram",
                        recommendation="Add allowed_users list to telegram config",
                    )
            
            # Check IoT security
            iot = config.get("iot", {})
            if iot.get("enabled", False):
                if not os.getenv("IOT_SHARED_SECRET"):
                    self.add_finding(
                        category="configuration",
                        severity=Severity.HIGH,
                        title="IoT shared secret not configured",
                        description="IoT devices may be accessible without authentication",
                        recommendation="Set IOT_SHARED_SECRET in .env file",
                    )
                    
        except Exception as e:
            self.add_finding(
                category="configuration",
                severity=Severity.LOW,
                title="Could not parse settings.yaml",
                description=str(e),
                recommendation="Fix YAML syntax errors",
            )
    
    # =========================================================================
    # Network Security
    # =========================================================================
    
    def audit_network_security(self) -> None:
        """Audit network-related security."""
        # Check for HTTP (non-HTTPS) URLs in config
        settings_path = self.project_root / "config" / "settings.yaml"
        
        if settings_path.exists():
            with open(settings_path) as f:
                content = f.read()
            
            http_urls = re.findall(r'http://[^\s\'"]+', content)
            for url in http_urls:
                if "localhost" not in url and "127.0.0.1" not in url:
                    self.add_finding(
                        category="network",
                        severity=Severity.MEDIUM,
                        title="Non-HTTPS URL in configuration",
                        description=f"Found: {url}",
                        recommendation="Use HTTPS for external URLs",
                    )
    
    # =========================================================================
    # IoT Security
    # =========================================================================
    
    def audit_iot_security(self) -> None:
        """Audit IoT-related security."""
        from dotenv import load_dotenv
        load_dotenv(self.project_root / ".env")
        
        shared_secret = os.getenv("IOT_SHARED_SECRET", "")
        
        if shared_secret:
            # Check secret strength
            if len(shared_secret) < 16:
                self.add_finding(
                    category="iot",
                    severity=Severity.MEDIUM,
                    title="Weak IoT shared secret",
                    description=f"Secret length: {len(shared_secret)} characters",
                    recommendation="Use at least 32 character random secret",
                )
            
            # Check for common weak secrets
            weak_secrets = ["secret", "password", "123456", "jarvis", "test"]
            if shared_secret.lower() in weak_secrets:
                self.add_finding(
                    category="iot",
                    severity=Severity.CRITICAL,
                    title="Common/weak IoT shared secret",
                    description="Using easily guessable secret",
                    recommendation="Generate a strong random secret",
                )
        
        # Check firmware for hardcoded credentials
        firmware_dir = self.project_root / "firmware" / "esp32"
        if firmware_dir.exists():
            for py_file in firmware_dir.rglob("*.py"):
                with open(py_file) as f:
                    content = f.read()
                
                # Check for hardcoded WiFi credentials
                if re.search(r'WIFI_SSID\s*=\s*["\'][^"\']+["\']', content):
                    if "your_" not in content and "example" not in content.lower():
                        self.add_finding(
                            category="iot",
                            severity=Severity.MEDIUM,
                            title="Hardcoded WiFi credentials in firmware",
                            description=f"Found in {py_file.name}",
                            recommendation="Use config file for WiFi credentials",
                        )
    
    # =========================================================================
    # Input Validation
    # =========================================================================
    
    def audit_input_validation(self) -> None:
        """Audit input validation practices."""
        # Check for eval/exec usage
        dangerous_functions = ["eval(", "exec(", "compile(", "__import__("]
        
        for py_file in self.project_root.rglob("*.py"):
            if "venv" in str(py_file) or ".git" in str(py_file):
                continue
            
            try:
                with open(py_file) as f:
                    content = f.read()
                
                for func in dangerous_functions:
                    if func in content:
                        # Check if it's in a comment
                        lines = content.split("\n")
                        for i, line in enumerate(lines):
                            if func in line and not line.strip().startswith("#"):
                                self.add_finding(
                                    category="input_validation",
                                    severity=Severity.HIGH,
                                    title=f"Dangerous function: {func[:-1]}",
                                    description=f"Found in {py_file.relative_to(self.project_root)}:{i+1}",
                                    recommendation="Avoid eval/exec, use safer alternatives",
                                )
                                break
            except Exception:
                pass
    
    # =========================================================================
    # Dependency Security
    # =========================================================================
    
    def audit_dependencies(self) -> None:
        """Audit dependency security."""
        requirements_path = self.project_root / "requirements.txt"
        
        if not requirements_path.exists():
            return
        
        with open(requirements_path) as f:
            requirements = f.read()
        
        # Check for unpinned dependencies
        unpinned = []
        for line in requirements.split("\n"):
            line = line.strip()
            if line and not line.startswith("#"):
                if "==" not in line and ">=" not in line and "<=" not in line:
                    unpinned.append(line.split("[")[0])
        
        if unpinned:
            self.add_finding(
                category="dependencies",
                severity=Severity.LOW,
                title="Unpinned dependencies",
                description=f"Packages without version pins: {', '.join(unpinned[:5])}{'...' if len(unpinned) > 5 else ''}",
                recommendation="Pin dependency versions for reproducible builds",
            )
    
    # =========================================================================
    # Run All Audits
    # =========================================================================
    
    def run_all(self) -> AuditResult:
        """Run all security audits."""
        print("\n" + "=" * 60)
        print("  JARVIS SECURITY AUDIT")
        print("=" * 60 + "\n")
        
        audits = [
            ("Credential Security", [
                self.audit_env_file,
                self.audit_gitignore,
                self.audit_hardcoded_secrets,
            ]),
            ("Configuration Security", [
                self.audit_config_security,
            ]),
            ("Network Security", [
                self.audit_network_security,
            ]),
            ("IoT Security", [
                self.audit_iot_security,
            ]),
            ("Input Validation", [
                self.audit_input_validation,
            ]),
            ("Dependency Security", [
                self.audit_dependencies,
            ]),
        ]
        
        for category, checks in audits:
            print(f"[{category}]")
            for check in checks:
                try:
                    check()
                except Exception as e:
                    print(f"  Error in {check.__name__}: {e}")
            print()
        
        return self.result
    
    def print_results(self) -> None:
        """Print audit results."""
        print("=" * 60)
        print("  AUDIT RESULTS")
        print("=" * 60)
        
        # Group by severity
        by_severity = {
            Severity.CRITICAL: [],
            Severity.HIGH: [],
            Severity.MEDIUM: [],
            Severity.LOW: [],
            Severity.INFO: [],
        }
        
        for finding in self.result.findings:
            by_severity[finding.severity].append(finding)
        
        colors = {
            Severity.CRITICAL: "\033[91m",  # Red
            Severity.HIGH: "\033[93m",      # Yellow
            Severity.MEDIUM: "\033[33m",    # Orange
            Severity.LOW: "\033[94m",       # Blue
            Severity.INFO: "\033[90m",      # Gray
        }
        reset = "\033[0m"
        
        for severity in [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO]:
            findings = by_severity[severity]
            if findings:
                print(f"\n{colors[severity]}[{severity.upper()}]{reset}")
                for f in findings:
                    status = " (FIXED)" if f.fixed else ""
                    print(f"  • {f.title}{status}")
                    print(f"    {f.description}")
                    print(f"    → {f.recommendation}")
        
        # Summary
        print("\n" + "=" * 60)
        print("  SUMMARY")
        print("=" * 60)
        print(f"  Critical: {self.result.critical_count}")
        print(f"  High:     {self.result.high_count}")
        print(f"  Medium:   {self.result.medium_count}")
        print(f"  Low:      {self.result.low_count}")
        print(f"  Total:    {len(self.result.findings)}")
        
        if self.result.critical_count > 0:
            print(f"\n  {colors[Severity.CRITICAL]}⚠ CRITICAL ISSUES FOUND - Address immediately{reset}")
        elif self.result.high_count > 0:
            print(f"\n  {colors[Severity.HIGH]}⚠ HIGH SEVERITY ISSUES - Review recommended{reset}")
        else:
            print(f"\n  \033[92m✓ No critical or high severity issues{reset}")
        
        print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="JARVIS Security Audit",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--fix", action="store_true", help="Attempt to fix issues")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    args = parser.parse_args()
    
    auditor = SecurityAuditor(auto_fix=args.fix)
    auditor.run_all()
    
    if args.json:
        print(json.dumps(auditor.result.to_dict(), indent=2))
    else:
        auditor.print_results()
    
    # Exit code based on findings
    if auditor.result.critical_count > 0:
        sys.exit(2)
    elif auditor.result.high_count > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
