#!/usr/bin/env python3
"""
Lead Hunter - End of Day Data Cleanup
Version: 1.0.0
Author: Metano[IA]

This script runs at end-of-day (23:00) to:
1. Archive non-responders (leads that didn't respond after 1 day)
2. Schedule retry messages (+3 business days)
3. Cleanup failed retries (delete after retry also failed)

Usage:
  python end-of-day-cleanup.py

Requires:
  - SUPABASE_URL environment variable
  - SUPABASE_KEY environment variable
  - pip install supabase-py
"""

import os
import sys
from datetime import datetime
from supabase import create_client, Client

def get_supabase_client() -> Client:
    """Initialize Supabase client from environment variables."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    if not url or not key:
        print("❌ Error: SUPABASE_URL and SUPABASE_KEY environment variables required")
        sys.exit(1)

    return create_client(url, key)

def archive_non_responders(supabase: Client):
    """
    Archive leads that didn't respond after 1 day.
    Schedule retry for +3 business days.
    """
    print("\n🗄️  Archiving non-responders...")

    try:
        # Call Supabase function
        result = supabase.rpc('archive_non_responders').execute()

        if result.data:
            archived = result.data[0]['archived_count']
            retries = result.data[0]['retry_scheduled_count']

            print(f"✅ Archived: {archived} leads")
            print(f"✅ Retry scheduled: {retries} leads (+3 business days)")

            return archived, retries
        else:
            print("⚠️  No non-responders to archive")
            return 0, 0

    except Exception as e:
        print(f"❌ Error archiving: {e}")
        return 0, 0

def process_retry_queue(supabase: Client):
    """
    Process retry queue for leads whose retry date has arrived.
    """
    print("\n🔄 Processing retry queue...")

    try:
        result = supabase.rpc('process_retry_queue').execute()

        if result.data:
            ready = result.data[0]['retries_ready']
            print(f"✅ Retries ready to send: {ready}")
            return ready
        else:
            print("⚠️  No retries ready")
            return 0

    except Exception as e:
        print(f"❌ Error processing retries: {e}")
        return 0

def cleanup_failed_retries(supabase: Client):
    """
    Delete archived leads where retry also failed (no response).
    """
    print("\n🧹 Cleaning up failed retries...")

    try:
        result = supabase.rpc('cleanup_failed_retries').execute()

        if result.data:
            deleted = result.data[0]['deleted_count']
            print(f"✅ Deleted: {deleted} failed retries")
            return deleted
        else:
            print("⚠️  No failed retries to clean")
            return 0

    except Exception as e:
        print(f"❌ Error cleaning up: {e}")
        return 0

def get_stats(supabase: Client):
    """Get current database stats."""
    print("\n📊 Current Stats:")

    try:
        # Active leads
        leads = supabase.table('leads').select('*', count='exact').execute()
        print(f"  Active leads: {leads.count}")

        # Archived leads
        archived = supabase.table('archived_leads').select('*', count='exact').execute()
        print(f"  Archived leads: {archived.count}")

        # Retry queue
        retries = supabase.table('retry_queue').select('*', count='exact').execute()
        print(f"  Retry queue: {retries.count}")

    except Exception as e:
        print(f"❌ Error getting stats: {e}")

def main():
    """Main execution."""
    print("=" * 60)
    print("🌙 Lead Hunter - End of Day Cleanup")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Initialize client
    supabase = get_supabase_client()

    # Get stats before
    print("\n📈 BEFORE:")
    get_stats(supabase)

    # Execute cleanup operations
    archived, retries_scheduled = archive_non_responders(supabase)
    retries_ready = process_retry_queue(supabase)
    deleted = cleanup_failed_retries(supabase)

    # Get stats after
    print("\n📉 AFTER:")
    get_stats(supabase)

    # Summary
    print("\n" + "=" * 60)
    print("📋 SUMMARY:")
    print(f"  ✅ Archived: {archived} non-responders")
    print(f"  🔄 Retry scheduled: {retries_scheduled} leads")
    print(f"  📨 Retry ready: {retries_ready} messages")
    print(f"  🗑️  Deleted: {deleted} failed retries")
    print("=" * 60)
    print("✅ End-of-day cleanup complete!\n")

if __name__ == "__main__":
    main()
