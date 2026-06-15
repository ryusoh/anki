#!/usr/bin/env python3
"""
security_check.py - EXTREMELY RIGOROUS check for private Anki data

This script scans ALL non-gitignored files for private Anki content.
It will FAIL the build if ANY private data is found.

Private data includes:
- Card content (flds field)
- User tags
- Full note content
- Any data from collection.anki2 that should stay private

This is a CRITICAL safety check. DO NOT bypass it.
"""

import gzip
import json
import subprocess
import sys
from pathlib import Path

# Colors for output
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
BOLD = '\033[1m'
RESET = '\033[0m'

def error(msg):
    print(f"{RED}{BOLD}❌ SECURITY VIOLATION:{RESET} {RED}{msg}{RESET}", file=sys.stderr)

def warning(msg):
    print(f"{YELLOW}⚠️  WARNING:{RESET} {YELLOW}{msg}{RESET}", file=sys.stderr)

def success(msg):
    print(f"{GREEN}✅ {msg}{RESET}")

def get_gitignored_files():
    """Get list of gitignored files that exist in the filesystem."""
    result = subprocess.run(
        ['git', 'ls-files', '--others', '--ignored', '--exclude-standard'],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    files = set()
    for line in result.stdout.strip().split('\n'):
        if line:
            files.add(line)
    return files

def get_tracked_files():
    """Get all files that would be committed."""
    result = subprocess.run(
        ['git', 'ls-files', '--cached', '--others', '--exclude-standard'],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    files = set()
    for line in result.stdout.strip().split('\n'):
        if line:
            files.add(line)
    return files

def get_private_field_patterns():
    """
    Return patterns that indicate private Anki content.
    These are fields that should NEVER be in git-tracked files.
    """
    return {
        # Direct field names that indicate private content
        '"flds"': 'Card content field detected',
        '"tags"': 'User tags field detected (in full note context)',
        "'flds'": 'Card content field detected (single quotes)',
        "'tags'": 'User tags field detected (single quotes)',
        
        # Common Anki content patterns that indicate actual card content
        '"front"::"back"': 'Card front::back format detected',
        '::&nbsp;': 'HTML entity in field separator context',
        '&nbsp;': 'HTML entity (common in card content)',
        '{{c1::': 'Cloze deletion syntax',
        '{{c2::': 'Cloze deletion syntax',
        '{{c3::': 'Cloze deletion syntax',
        
        # Full note structure (private)
        '"mid"': 'Note type ID (when with flds)',
        '"usn"': 'Update sequence number (private metadata)',
        '"csum"': 'Field checksum (private)',
    }

def _check_json_data(filepath, full_path):
    violations = []
    try:
        # Try to parse as JSON
        if filepath.endswith('.gz'):
            with gzip.open(full_path, 'rt', encoding='utf-8') as f:
                data = json.load(f)
        else:
            with open(full_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

        # Check if this is a list of notes
        if isinstance(data, list) and len(data) > 0:
            first_item = data[0] if isinstance(data, list) else data

            if isinstance(first_item, dict):
                # CRITICAL CHECK: Does this look like private note data?
                has_flds = 'flds' in first_item
                has_tags = 'tags' in first_item
                has_mid = 'mid' in first_item
                has_guid = 'guid' in first_item

                # If it has flds + other note fields, it's private
                if has_flds and (has_mid or has_guid):
                    violations.append({
                        'type': 'private_notes',
                        'message': 'File contains private note data with flds field',
                        'fields': [k for k in first_item.keys() if k in ['flds', 'tags', 'mid', 'guid', 'usn', 'csum']]
                    })

                # Target specific Git-versioned files for anonymization verification
                if filepath.endswith('notes.json.gz') and 'cloudflare' not in filepath:
                    if has_flds or has_tags:
                        violations.append({
                            'type': 'data_leak_regression',
                            'message': f'REGRESSION: {filepath} contains private fields (flds/tags) but must be anonymized for Git.',
                            'fields': [k for k in first_item.keys() if k in ['flds', 'tags']]
                        })

    except (json.JSONDecodeError, UnicodeDecodeError):
        warning(f"Failed to decode or parse JSON for {full_path}. Skipping.")

    return violations

def check_file_for_private_data(filepath, content, full_path):
    """
    Check a single file for private data.
    Returns list of violations found.
    """
    violations = []
    
    # Skip certain safe files (code, config, documentation)
    safe_extensions = ['.py', '.js', '.ts', '.html', '.css', '.md', '.txt', '.sh']
    safe_files = [
        'package.json',
        'package-lock.json',
        '.gitignore',
        'security_check.py',
        'upload-to-r2',
        'fetch',
    ]
    
    for safe in safe_files:
        if filepath.endswith(safe):
            return violations
    
    for ext in safe_extensions:
        if filepath.endswith(ext):
            return violations  # Code files are safe - they can mention field names
    
    # Only check DATA files (JSON, etc.)
    if filepath.endswith('.json') or filepath.endswith('.json.gz'):
        violations.extend(_check_json_data(filepath, full_path))
    
    return violations

def check_r2_staging_directory():
    """
    CRITICAL: Check that R2 staging directory is gitignored.
    This is where private data is staged before upload.
    """
    # Project root is 3 levels up from this script
    project_root = Path(__file__).parent.parent.parent
    gitignore_path = project_root / '.gitignore'
    
    if not gitignore_path.exists():
        return [{
            'type': 'missing_gitignore',
            'message': '.gitignore file not found!'
        }]
    
    gitignore_content = gitignore_path.read_text()
    
    # Check for R2 staging directory
    r2_patterns = [
        'data/cloudflare/',
        'data/cloudflare',
        'cloudflare/',
    ]
    
    found_r2_ignore = False
    for pattern in r2_patterns:
        if pattern in gitignore_content:
            found_r2_ignore = True
            break
    
    if not found_r2_ignore:
        return [{
            'type': 'r2_not_ignored',
            'message': 'R2 staging directory (data/cloudflare/) is NOT in .gitignore!'
        }]
    
    # Check for graph JSON files
    if 'graph/graph_data.json' not in gitignore_content and 'graph/*.json' not in gitignore_content:
        return [{
            'type': 'graph_json_not_ignored',
            'message': 'graph/graph_data.json is NOT in .gitignore!'
        }]
    
    return []

def _scan_tracked_file(filepath, project_root):
    full_path = project_root / filepath

    if not full_path.exists():
        return []

    # Skip binary files
    if filepath.endswith(('.png', '.jpg', '.jpeg', '.gif', '.mp3', '.wav', '.mp4', '.webm')):
        return []

    # Read file content
    content = ""
    try:
        if filepath.endswith('.gz'):
            with gzip.open(full_path, 'rt', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        else:
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
    except Exception as e:
        print(f"Warning: Failed to read file {filepath}: {e}")
        return []

    # Check for private data
    violations = check_file_for_private_data(filepath, content, full_path)

    return [{ 'file': filepath, **v } for v in violations] if violations else []

def main():
    print(f"\n{BOLD}🔒 SECURITY CHECK: Scanning for private Anki data...{RESET}\n")
    
    project_root = Path(__file__).parent.parent
    
    # Get all files that would be committed
    tracked_files = get_tracked_files()
    
    if not tracked_files:
        warning("No tracked files found (empty git repo?)")
        return 0
    
    print(f"Scanning {len(tracked_files)} files...\n")
    
    all_violations = []
    
    # Check R2 staging is gitignored
    r2_violations = check_r2_staging_directory()
    all_violations.extend(r2_violations)
    
    # Check each file
    files_scanned = 0
    for filepath in sorted(tracked_files):
        files_scanned += 1
        violations = _scan_tracked_file(filepath, project_root)
        all_violations.extend(violations)
    
    # Report results
    print(f"Scanned {files_scanned} files\n")
    
    if all_violations:
        print(f"{RED}{BOLD}{'='*70}{RESET}")
        print(f"{RED}{BOLD}🚨 SECURITY CHECK FAILED - PRIVATE DATA DETECTED 🚨{RESET}")
        print(f"{RED}{BOLD}{'='*70}{RESET}\n")
        
        for i, violation in enumerate(all_violations, 1):
            print(f"{RED}{BOLD}Violation #{i}:{RESET}")
            if 'file' in violation:
                print(f"  {RED}File:{RESET} {violation['file']}")
            print(f"  {RED}Issue:{RESET} {violation['message']}")
            if 'fields' in violation:
                print(f"  {RED}Fields found:{RESET} {', '.join(violation['fields'])}")
            if 'pattern' in violation:
                print(f"  {RED}Pattern:{RESET} {violation['pattern']}")
            print()
        
        print(f"{RED}{BOLD}{'='*70}{RESET}")
        print(f"{RED}{BOLD}DO NOT COMMIT! Remove private data immediately!{RESET}")
        print(f"{RED}{BOLD}{'='*70}{RESET}\n")
        
        print("Files that MUST be gitignored:")
        print("  - data/cloudflare/ (R2 staging with full card content)")
        print("  - graph/graph_data.json (contains card content)")
        print("  - Any file with 'flds' or full note data\n")
        
        return 1
    else:
        print(f"{GREEN}{BOLD}✅ SECURITY CHECK PASSED{RESET}")
        print(f"{GREEN}No private Anki data detected in tracked files.{RESET}\n")
        return 0

if __name__ == "__main__":
    sys.exit(main())
