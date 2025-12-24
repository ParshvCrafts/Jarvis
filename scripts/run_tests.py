#!/usr/bin/env python3
"""
Test runner script for JARVIS.

Runs all tests and generates a report.
"""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


def run_tests(verbose: bool = True, coverage: bool = False) -> int:
    """
    Run all tests.
    
    Args:
        verbose: Show verbose output.
        coverage: Generate coverage report.
        
    Returns:
        Exit code (0 = success).
    """
    cmd = [sys.executable, "-m", "pytest", "tests/"]
    
    if verbose:
        cmd.append("-v")
    
    if coverage:
        cmd.extend(["--cov=src", "--cov-report=html", "--cov-report=term"])
    
    # Add markers to skip slow tests by default
    cmd.extend(["-m", "not slow"])
    
    print(f"Running: {' '.join(cmd)}")
    print("=" * 60)
    
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    
    return result.returncode


def run_specific_tests(pattern: str) -> int:
    """Run tests matching a pattern."""
    cmd = [sys.executable, "-m", "pytest", "-v", "-k", pattern, "tests/"]
    
    print(f"Running tests matching: {pattern}")
    print("=" * 60)
    
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    
    return result.returncode


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run JARVIS tests")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("-c", "--coverage", action="store_true", help="Generate coverage report")
    parser.add_argument("-k", "--pattern", type=str, help="Run tests matching pattern")
    parser.add_argument("--all", action="store_true", help="Run all tests including slow ones")
    
    args = parser.parse_args()
    
    if args.pattern:
        exit_code = run_specific_tests(args.pattern)
    else:
        exit_code = run_tests(verbose=args.verbose, coverage=args.coverage)
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
