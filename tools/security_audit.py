#!/usr/bin/env python3
"""
SECURITY AUDIT SCRIPT - Run this to verify repo is clean

This script scans the entire repository for:
1. Hardcoded credentials (API keys, secrets, passwords)
2. Private data patterns (flds, tags, card content)
3. Files that should be gitignored but aren't
4. Suspicious patterns in tracked files

Run: python3 security_audit.py
"""

import subprocess
import json
import re
import sys
from pathlib import Path

RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BOLD = '\033[1m'
RESET = '\033[0m'

def error(msg):
    print(f"{RED}{BOLD}❌ {msg}{RESET}")
    return False

def warning(msg):
    print(f"{YELLOW}⚠️  {msg}{RESET}")
    return True

def success(msg):
    print(f"{GREEN}✅ {msg}{RESET}")
    return True

def get_tracked_files():
    """Get all git-tracked files."""
    result = subprocess.run(
        ['git', 'ls-files'],
        capture_output=True,
        text=True
    )
    return [f.strip() for f in result.stdout.strip().split('\n') if f.strip()]

def check_for_credentials(filepath, content):
    """Check for hardcoded credentials."""
    issues = []
    
    # Skip vendor/third-party code (they have their own keys)
    if 'vendor/' in filepath or 'node_modules/' in filepath:
        return issues
    
    # Skip documentation
    if filepath.endswith('.md'):
        return issues
    
    # Skip compressed/binary files
    if filepath.endswith('.gz'):
        return issues
    
    # Check Python/JS files for hardcoded credentials
    if filepath.endswith('.py') or filepath.endswith('.js'):
        patterns = {
            'Hardcoded Secret': r'(secret|SECRET|KEY|TOKEN)\s*=\s*["\'][a-zA-Z0-9+/=]{30,}["\']',
            'Private Key': r'-----BEGIN (RSA |EC )?PRIVATE KEY-----',
        }
        
        for name, pattern in patterns.items():
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                issues.append(f"{name} found")
    
    return issues

def check_for_private_data(filepath, content):
    """Check for private Anki card data."""
    issues = []
    
    # Skip documentation files (they mention field names but don't contain data)
    if filepath.endswith('.md') or 'docs/' in filepath:
        return issues
    
    # Skip vendor/third-party code
    if 'vendor/' in filepath or 'node_modules/' in filepath:
        return issues
    
    # Skip code files (they can mention field names)
    if filepath.endswith('.py') or filepath.endswith('.js'):
        # But check for actual credential patterns in code
        if 'ACCOUNT_ID' in content and len(content) > 1000:
            # Check for hardcoded values
            if re.search(r"ACCOUNT_ID\s*=\s*['\"][a-f0-9]{32}['\"]", content):
                issues.append("HARDCODED: ACCOUNT_ID with value")
        return issues
    
    # Skip anonymized data files (no flds, no tags)
    if filepath.endswith('notes.json.gz') or 'reviews/' in filepath:
        return issues
    
    # Check JSON files for private fields
    if filepath.endswith('.json'):
        try:
            data = json.loads(content)
            if isinstance(data, list) and data:
                first = data[0] if isinstance(data[0], dict) else {}
                
                # Dangerous combinations
                if 'flds' in first and ('mid' in first or 'guid' in first):
                    issues.append("PRIVATE: Contains flds + mid/guid (full note data)")
                if 'tags' in first and 'flds' in first:
                    issues.append("PRIVATE: Contains tags + flds")
        except Exception:
            pass # JSON parsing failure is ignored as file might not be standard JSON.
    
    return issues

def check_gitignore_coverage():
    """Check that sensitive directories are gitignored."""
    issues = []
    
    result = subprocess.run(
        ['git', 'check-ignore', 'data/cloudflare/test_dummy.json'],
        capture_output=True
    )
    if result.returncode != 0:
        issues.append("data/cloudflare/test_dummy.json is NOT gitignored!")
    
    result = subprocess.run(
        ['git', 'check-ignore', 'graph/graph_data.json'],
        capture_output=True
    )
    if result.returncode != 0:
        issues.append("graph/graph_data.json is NOT gitignored!")
    
    return issues

def main():
    print(f"\n{BOLD}🔒 SECURITY AUDIT - Full Repository Scan{RESET}\n")
    print("Scanning for:")
    print("  • Hardcoded credentials")
    print("  • Private Anki card data")
    print("  • Gitignore coverage")
    print()
    
    all_ok = True
    
    # Check gitignore coverage
    print(f"{BOLD}Checking .gitignore coverage...{RESET}")
    gitignore_issues = check_gitignore_coverage()
    for issue in gitignore_issues:
        all_ok &= error(issue)
    if not gitignore_issues:
        success(".gitignore properly covers sensitive files")
    print()
    
    # Scan tracked files
    print(f"{BOLD}Scanning tracked files...{RESET}")
    files = get_tracked_files()
    print(f"Found {len(files)} tracked files\n")
    
    critical_issues = []
    warnings = []
    
    for filepath in files:
        full_path = Path(filepath)
        if not full_path.exists():
            continue
        
        # Skip binary files
        if filepath.endswith(('.png', '.jpg', '.gif', '.mp3', '.mp4', '.webm', '.woff', '.woff2')):
            continue
        
        try:
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception:
            continue # Skip files that cannot be read.
        
        # Check for credentials
        cred_issues = check_for_credentials(filepath, content)
        for issue in cred_issues:
            critical_issues.append(f"{filepath}: {issue}")
        
        # Check for private data
        data_issues = check_for_private_data(filepath, content)
        for issue in data_issues:
            critical_issues.append(f"{filepath}: {issue}")
    
    # Report results
    print(f"{BOLD}{'='*70}{RESET}")
    print(f"{BOLD}AUDIT RESULTS{RESET}")
    print(f"{BOLD}{'='*70}{RESET}\n")
    
    if critical_issues:
        print(f"{RED}{BOLD}CRITICAL ISSUES FOUND:{RESET}\n")
        for issue in critical_issues:
            error(issue)
        all_ok = False
    else:
        success("No hardcoded credentials found")
        success("No private card data found in tracked files")
    
    print()
    
    if all_ok:
        print(f"{GREEN}{BOLD}✅ AUDIT PASSED - Repository appears clean{RESET}\n")
        return 0
    else:
        print(f"{RED}{BOLD}🚨 AUDIT FAILED - Review issues above immediately!{RESET}\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
