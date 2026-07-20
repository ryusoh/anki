#!/usr/bin/env python3
"""
Background watcher for incremental graph updates

Watches for changes and auto-increments sample size.

Usage:
    python3 watch_and_update.py              # Start watching
    python3 watch_and_update.py --interval 60  # Check every 60 seconds
    python3 watch_and_update.py --max 1000   # Stop at 1000 nodes
"""

import argparse
import subprocess
import sys
import time
from datetime import datetime

from graph._paths import ANKI_ADDONS_DIR

BASE = ANKI_ADDONS_DIR
CONFIG_FILE = BASE / 'graph' / '.incremental_config.json'
EXPORT_SCRIPT = BASE / 'graph' / 'incremental_export.py'


def get_current_size():
    """Get current sample size from config."""
    if CONFIG_FILE.exists():
        import json

        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            return config.get('sample_size', 100)
    return 100


def increment():
    """Run incremental export."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Incrementing...")

    result = subprocess.run(
        [sys.executable, str(EXPORT_SCRIPT), '--next'], capture_output=True, text=True
    )

    if result.returncode == 0:
        print(result.stdout)
    else:
        print(f"Error: {result.stderr}")


def refresh_browser():
    """Refresh browser tab (AppleScript for macOS)."""
    try:
        subprocess.run(
            [
                'osascript',
                '-e',
                'tell application "Google Chrome" to tell active tab of window 1 to reload',
            ],
            capture_output=True,
        )
        print("  🔄 Browser refreshed")
    except Exception as e:
        print(f"  ⚠️  Could not refresh browser: {e}")


def main():
    parser = argparse.ArgumentParser(description='Watch and update graph')
    parser.add_argument(
        '--interval', '-i', type=int, default=30, help='Check interval in seconds (default: 30)'
    )
    parser.add_argument(
        '--max', '-m', type=int, default=None, help='Maximum sample size (default: unlimited)'
    )
    parser.add_argument('--auto-refresh', '-r', action='store_true', help='Auto-refresh browser')
    parser.add_argument('--once', '-o', action='store_true', help='Run once and exit')

    args = parser.parse_args()

    print("👁️  Watcher started")
    print(f"   Interval: {args.interval}s")
    print(f"   Max size: {args.max or 'unlimited'}")
    print(f"   Auto-refresh: {args.auto_refresh}")
    print()

    if args.once:
        increment()
        if args.auto_refresh:
            refresh_browser()
        return

    last_size = get_current_size()

    try:
        while True:
            time.sleep(args.interval)

            current_size = get_current_size()

            # Check if we hit max
            if args.max and current_size >= args.max:
                print(f"✅ Reached max size: {current_size:,}")
                break

            # If size changed (manual update), skip
            if current_size != last_size:
                print(
                    f"[{datetime.now().strftime('%H:%M:%S')}] Size changed: {last_size:,} → {current_size:,}"
                )
                last_size = current_size
                continue

            # Auto-increment
            increment()

            if args.auto_refresh:
                refresh_browser()

            last_size = get_current_size()

    except KeyboardInterrupt:
        print("\n👋 Watcher stopped")


if __name__ == "__main__":
    main()
