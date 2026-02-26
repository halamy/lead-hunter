#!/usr/bin/env python3
"""
Lead Hunter - Queue Processor (Orchestrator)
Version: 1.0.0
Author: Metano[IA]

Orchestrates the full dispatch + response monitoring cycle.
Designed to run as a cron job every 5 minutes during business hours.

Usage:
  python queue-processor.py              # Full cycle: dispatch + classify + report
  python queue-processor.py --dispatch    # Only dispatch messages
  python queue-processor.py --classify    # Only classify responses
  python queue-processor.py --report      # Only generate pipeline report

Requires:
  - All env vars from whatsapp-api-client.py and sentiment-classifier.py
  - pip install supabase httpx anthropic

Cron setup (every 5 minutes, 9h-17h BRT):
  */5 9-16 * * 1-6 cd /path/to/scripts && python queue-processor.py
"""

import os
import sys
import subprocess
from datetime import datetime
from zoneinfo import ZoneInfo

BRT = ZoneInfo("America/Sao_Paulo")
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))


def run_script(name: str, args: list = None) -> int:
    """Run a script and return exit code."""
    cmd = [sys.executable, os.path.join(SCRIPTS_DIR, name)]
    if args:
        cmd.extend(args)

    print(f"\n{'='*40}")
    print(f"▶ Running: {name} {' '.join(args or [])}")
    print(f"{'='*40}")

    result = subprocess.run(cmd, cwd=SCRIPTS_DIR)
    return result.returncode


def check_business_hours() -> bool:
    """Check if within 9h-17h BRT, Mon-Sat."""
    now = datetime.now(BRT)
    if now.weekday() == 6:  # Sunday
        return False
    return 9 <= now.hour < 17


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Lead Hunter - Queue Processor")
    parser.add_argument("--dispatch", action="store_true", help="Only dispatch")
    parser.add_argument("--classify", action="store_true", help="Only classify responses")
    parser.add_argument("--report", action="store_true", help="Only generate report")
    args = parser.parse_args()

    now = datetime.now(BRT)
    print("=" * 60)
    print("🔄 Lead Hunter - Queue Processor")
    print(f"⏰ {now.strftime('%Y-%m-%d %H:%M:%S')} BRT")
    print(f"📅 {now.strftime('%A')}")
    print("=" * 60)

    # Specific mode
    if args.dispatch:
        run_script("whatsapp-api-client.py")
        return
    if args.classify:
        run_script("sentiment-classifier.py")
        run_script("sentiment-classifier.py", ["--check-sla"])
        return
    if args.report:
        # Report is generated via hunter-chief agent
        print("📊 Pipeline report should be generated via hunter-chief agent (*pipeline-report)")
        return

    # Full cycle
    print("\n🔄 Running full cycle: dispatch → classify → sla-check")

    # Step 1: Dispatch messages (only during business hours)
    if check_business_hours():
        exit_code = run_script("whatsapp-api-client.py")
        if exit_code != 0:
            print(f"⚠️  Dispatch exited with code {exit_code}")
    else:
        print(f"\nℹ️  Outside business hours ({now.strftime('%H:%M')} BRT). Skipping dispatch.")

    # Step 2: Classify responses (always — responses can arrive anytime)
    run_script("sentiment-classifier.py")

    # Step 3: Check SLA violations
    run_script("sentiment-classifier.py", ["--check-sla"])

    # Step 4: End-of-day cleanup (only at 23:00)
    if now.hour == 23 and now.minute < 10:
        print("\n🌙 End-of-day cleanup triggered")
        run_script("end-of-day-cleanup.py")

    print("\n" + "=" * 60)
    print("✅ Queue processor cycle complete")
    print(f"⏰ Next run: ~5 minutes")
    print("=" * 60)


if __name__ == "__main__":
    main()
