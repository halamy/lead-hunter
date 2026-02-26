#!/usr/bin/env python3
"""
Lead Hunter - WhatsApp API Client (Evolution API)
Version: 1.0.0
Author: Metano[IA]

Sends WhatsApp messages via Evolution API (self-hosted).
Enforces: 9h-17h BRT, 30/hr, 200/day, random delays 30-180s.
Integrates with Supabase for queue processing and rate limit logging.

Usage:
  python whatsapp-api-client.py                  # Process message queue
  python whatsapp-api-client.py --status          # Check API status
  python whatsapp-api-client.py --rate-status     # Show rate limit usage
  python whatsapp-api-client.py --pause           # Pause dispatch (manual escape)

Requires:
  - SUPABASE_URL environment variable
  - SUPABASE_KEY environment variable
  - EVOLUTION_API_URL environment variable (e.g., http://localhost:8080)
  - EVOLUTION_API_KEY environment variable
  - EVOLUTION_INSTANCE environment variable (WhatsApp instance name)
  - pip install supabase httpx

Veto Conditions (Pedro Valério):
  - SCH_001: Outside 9h-17h BRT → HARD BLOCK
  - SCH_002: 30/hr exceeded → HARD BLOCK
  - SCH_003: 200/day exceeded → HARD BLOCK
  - Random delay 30-180s between messages → OBRIGATÓRIO
  - 5 guardrails: loop prevention, idempotency, audit trail, manual escape, retry logic
"""

import os
import sys
import json
import argparse
import time
import random
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
from supabase import create_client, Client


# ============================================================================
# CONFIG
# ============================================================================

BRT = ZoneInfo("America/Sao_Paulo")
WINDOW_START = 9   # 09:00
WINDOW_END = 17    # 17:00
MAX_PER_HOUR = 30
MAX_PER_DAY = 200
DELAY_MIN = 30     # seconds
DELAY_MAX = 180    # seconds
MAX_SEND_RETRIES = 3
RETRY_BACKOFF = [60, 300, 900]  # 1min, 5min, 15min

# Pause file — manual escape (guardrail #4)
PAUSE_FILE = os.path.join(os.path.dirname(__file__), ".dispatch-paused")


# ============================================================================
# INIT
# ============================================================================

def get_supabase_client() -> Client:
    """Initialize Supabase client."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        print("❌ VETO: SUPABASE_URL and SUPABASE_KEY required")
        sys.exit(1)
    return create_client(url, key)


def get_evolution_config() -> dict:
    """Get Evolution API configuration."""
    config = {
        "url": os.environ.get("EVOLUTION_API_URL", "http://localhost:8080"),
        "api_key": os.environ.get("EVOLUTION_API_KEY"),
        "instance": os.environ.get("EVOLUTION_INSTANCE", "lead-hunter"),
    }
    if not config["api_key"]:
        print("❌ VETO: EVOLUTION_API_KEY required")
        sys.exit(1)
    return config


# ============================================================================
# GUARDRAIL #1: TIME WINDOW CHECK (SCH_001)
# ============================================================================

def check_time_window() -> dict:
    """Check if current time is within business hours (9h-17h BRT)."""
    now_brt = datetime.now(BRT)
    current_hour = now_brt.hour
    current_minute = now_brt.minute
    is_sunday = now_brt.weekday() == 6

    result = {
        "current_time": now_brt.strftime("%H:%M"),
        "is_within_window": WINDOW_START <= current_hour < WINDOW_END and not is_sunday,
        "is_sunday": is_sunday,
        "minutes_remaining": 0,
    }

    if result["is_within_window"]:
        result["minutes_remaining"] = (WINDOW_END - current_hour) * 60 - current_minute

    return result


# ============================================================================
# GUARDRAIL #2: RATE LIMIT CHECK (SCH_002, SCH_003)
# ============================================================================

def check_rate_limit(supabase: Client) -> dict:
    """Check rate limits via Supabase function."""
    try:
        result = supabase.rpc("check_rate_limit", {
            "p_action_type": "whatsapp_send",
            "p_max_per_hour": MAX_PER_HOUR,
            "p_max_per_day": MAX_PER_DAY,
        }).execute()

        if result.data:
            row = result.data[0]
            return {
                "allowed": row["allowed"],
                "hour_count": row["current_hour_count"],
                "day_count": row["current_day_count"],
                "hour_remaining": MAX_PER_HOUR - row["current_hour_count"],
                "day_remaining": MAX_PER_DAY - row["current_day_count"],
                "reason": row["reason"],
            }
    except Exception as e:
        print(f"⚠️  Rate limit check failed: {e}")

    return {"allowed": False, "reason": "rate_check_failed", "hour_count": 0, "day_count": 0,
            "hour_remaining": 0, "day_remaining": 0}


def log_rate_limit(supabase: Client, lead_id: str, batch_id: str = None):
    """Log a send action for rate limiting (guardrail #3: audit trail)."""
    try:
        supabase.rpc("log_rate_limit_action", {
            "p_action_type": "whatsapp_send",
            "p_lead_id": lead_id,
            "p_batch_id": batch_id,
        }).execute()
    except Exception as e:
        print(f"  ⚠️  Rate limit log failed: {e}")


# ============================================================================
# GUARDRAIL #4: MANUAL ESCAPE
# ============================================================================

def is_paused() -> bool:
    """Check if dispatch is paused (manual escape)."""
    return os.path.exists(PAUSE_FILE)


def pause_dispatch():
    """Create pause file to halt dispatch."""
    with open(PAUSE_FILE, "w") as f:
        f.write(f"Paused at {datetime.now(BRT).isoformat()}\n")
    print("⏸️  Dispatch PAUSED. Delete .dispatch-paused or run --resume to continue.")


def resume_dispatch():
    """Remove pause file to resume dispatch."""
    if os.path.exists(PAUSE_FILE):
        os.remove(PAUSE_FILE)
        print("▶️  Dispatch RESUMED.")
    else:
        print("ℹ️  Dispatch is not paused.")


# ============================================================================
# EVOLUTION API CLIENT
# ============================================================================

def check_api_status(config: dict) -> dict:
    """Check Evolution API health."""
    try:
        with httpx.Client(timeout=10) as client:
            response = client.get(
                f"{config['url']}/instance/connectionState/{config['instance']}",
                headers={"apikey": config["api_key"]}
            )
            data = response.json()
            return {
                "healthy": response.status_code == 200,
                "state": data.get("instance", {}).get("state", "unknown"),
                "details": data,
            }
    except Exception as e:
        return {"healthy": False, "state": "error", "error": str(e)}


def send_whatsapp_message(config: dict, phone: str, message: str) -> dict:
    """
    Send a WhatsApp text message via Evolution API.
    Returns: {success, message_id, error}
    """
    # Normalize phone: remove + and non-digits
    phone_clean = "".join(c for c in phone if c.isdigit())

    payload = {
        "number": phone_clean,
        "text": message,
    }

    try:
        with httpx.Client(timeout=30) as client:
            response = client.post(
                f"{config['url']}/message/sendText/{config['instance']}",
                json=payload,
                headers={
                    "apikey": config["api_key"],
                    "Content-Type": "application/json",
                }
            )

            if response.status_code == 201 or response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "message_id": data.get("key", {}).get("id", ""),
                    "error": None,
                }
            else:
                return {
                    "success": False,
                    "message_id": None,
                    "error": f"HTTP {response.status_code}: {response.text[:200]}",
                }

    except httpx.TimeoutException:
        return {"success": False, "message_id": None, "error": "timeout"}
    except Exception as e:
        return {"success": False, "message_id": None, "error": str(e)}


# ============================================================================
# QUEUE PROCESSING
# ============================================================================

def get_pending_messages(supabase: Client, limit: int = 50) -> list[dict]:
    """Get pending messages from queue with lead and message data."""
    try:
        result = (
            supabase.table("message_queue")
            .select("id, lead_id, message_id, scheduled_time, attempts, status")
            .eq("status", "pending")
            .order("scheduled_time")
            .limit(limit)
            .execute()
        )
        return result.data or []
    except Exception as e:
        print(f"❌ Queue fetch failed: {e}")
        return []


def get_message_and_lead(supabase: Client, message_id: str, lead_id: str) -> dict:
    """Get message text and lead phone."""
    try:
        msg = supabase.table("messages").select("message_text, personalization_score").eq("id", message_id).single().execute()
        lead = supabase.table("leads").select("phone, company_name, status").eq("id", lead_id).single().execute()
        return {
            "message_text": msg.data["message_text"],
            "personalization_score": msg.data["personalization_score"],
            "phone": lead.data["phone"],
            "company_name": lead.data["company_name"],
            "lead_status": lead.data["status"],
        }
    except Exception as e:
        return {"error": str(e)}


def update_queue_status(supabase: Client, queue_id: str, status: str, attempts: int = None):
    """Update message queue entry status."""
    data = {"status": status, "processed_at": datetime.now().isoformat()}
    if attempts is not None:
        data["attempts"] = attempts
    supabase.table("message_queue").update(data).eq("id", queue_id).execute()


def update_message_status(supabase: Client, message_id: str, status: str, whatsapp_id: str = None, error: str = None):
    """Update message status after send attempt."""
    data = {"status": status}
    if status == "sent":
        data["sent_at"] = datetime.now().isoformat()
    if whatsapp_id:
        data["whatsapp_message_id"] = whatsapp_id
    if error:
        data["error_message"] = error
    supabase.table("messages").update(data).eq("id", message_id).execute()


def update_lead_status(supabase: Client, lead_id: str, status: str):
    """Update lead status after send."""
    try:
        supabase.table("leads").update({"status": status}).eq("id", lead_id).execute()
    except Exception as e:
        print(f"  ⚠️  Lead status update failed: {e}")


def process_queue(supabase: Client, evolution_config: dict):
    """Main queue processing loop with all 5 guardrails."""
    print("\n⏰ Processing message queue...")

    # Guardrail #4: Manual escape check
    if is_paused():
        print("⏸️  PAUSED — dispatch halted by manual escape. Run --resume to continue.")
        return

    # Guardrail #1: Time window check
    window = check_time_window()
    if not window["is_within_window"]:
        reason = "Sunday" if window["is_sunday"] else f"outside 9h-17h (current: {window['current_time']})"
        print(f"❌ VETO (SCH_001): {reason}. Dispatch blocked.")
        return

    print(f"✅ Time window: {window['current_time']} BRT ({window['minutes_remaining']}min remaining)")

    # Guardrail #2: Rate limit check
    rate = check_rate_limit(supabase)
    if not rate["allowed"]:
        print(f"❌ VETO (SCH_002/003): {rate['reason']}")
        return

    print(f"✅ Rate limit: {rate['hour_count']}/{MAX_PER_HOUR} hour | {rate['day_count']}/{MAX_PER_DAY} day")

    # API health check
    api_status = check_api_status(evolution_config)
    if not api_status["healthy"]:
        print(f"❌ VETO: WhatsApp API unhealthy: {api_status.get('error', api_status['state'])}")
        return

    print(f"✅ API status: {api_status['state']}")

    # Get pending messages
    max_to_process = min(rate["hour_remaining"], rate["day_remaining"], 20)  # Process max 20 per run
    queue = get_pending_messages(supabase, limit=max_to_process)

    if not queue:
        print("ℹ️  No pending messages in queue")
        return

    print(f"\n📨 Processing {len(queue)} messages (max capacity: {max_to_process})")

    sent = 0
    failed = 0

    for i, entry in enumerate(queue):
        # Re-check guardrails before each send
        if is_paused():
            print("\n⏸️  PAUSED mid-batch. Stopping.")
            break

        window = check_time_window()
        if not window["is_within_window"]:
            print(f"\n❌ Time window closed at {window['current_time']}. Stopping batch.")
            break

        rate = check_rate_limit(supabase)
        if not rate["allowed"]:
            print(f"\n❌ Rate limit reached. Stopping batch.")
            break

        # Get message and lead data
        data = get_message_and_lead(supabase, entry["message_id"], entry["lead_id"])
        if "error" in data:
            print(f"  [{i+1}] ❌ Data fetch error: {data['error']}")
            failed += 1
            continue

        # Pre-send validation
        if data["lead_status"] not in ("ready",):
            print(f"  [{i+1}] ⏭️  {data['company_name']}: lead status '{data['lead_status']}' != 'ready', skipping")
            update_queue_status(supabase, entry["id"], "cancelled")
            continue

        # Guardrail #1: Loop prevention — check if already processed
        if entry["status"] != "pending":
            continue

        # Apply random delay (anti-detection)
        if i > 0:
            delay = random.randint(DELAY_MIN, DELAY_MAX)
            print(f"  ⏳ Random delay: {delay}s", end="", flush=True)
            time.sleep(delay)
            print(" ✓")

        # Update queue to processing (triggers rate limit enforcement in DB)
        try:
            update_queue_status(supabase, entry["id"], "processing", entry.get("attempts", 0))
        except Exception as e:
            if "rate_limit_exceeded" in str(e):
                print(f"  [{i+1}] ❌ Rate limit enforced by DB. Stopping.")
                break
            if "business_hours_violation" in str(e):
                print(f"  [{i+1}] ❌ Business hours enforced by DB. Stopping.")
                break
            raise

        # Send message
        print(f"  [{i+1}/{len(queue)}] {data['company_name']} ({data['phone']})...", end=" ")
        result = send_whatsapp_message(evolution_config, data["phone"], data["message_text"])

        if result["success"]:
            # Guardrail #3: Audit trail
            log_rate_limit(supabase, entry["lead_id"])
            update_queue_status(supabase, entry["id"], "sent")
            update_message_status(supabase, entry["message_id"], "sent", result["message_id"])
            update_lead_status(supabase, entry["lead_id"], "sent")
            sent += 1
            print(f"✅ sent (id: {result['message_id'][:8]}...)")
        else:
            # Guardrail #5: Retry logic
            attempts = entry.get("attempts", 0) + 1
            if attempts >= MAX_SEND_RETRIES:
                update_queue_status(supabase, entry["id"], "failed", attempts)
                update_message_status(supabase, entry["message_id"], "failed", error=result["error"])
                failed += 1
                print(f"❌ failed after {attempts} attempts: {result['error']}")
            else:
                update_queue_status(supabase, entry["id"], "pending", attempts)
                failed += 1
                print(f"⚠️ retry {attempts}/{MAX_SEND_RETRIES}: {result['error']}")

    # Summary
    print("\n" + "=" * 60)
    print("📋 DISPATCH REPORT:")
    print(f"  ✅ Sent: {sent}")
    print(f"  ❌ Failed: {failed}")
    print(f"  📊 Rate used: {rate['hour_count'] + sent}/{MAX_PER_HOUR} hour | {rate['day_count'] + sent}/{MAX_PER_DAY} day")
    print("=" * 60)


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Lead Hunter - WhatsApp Dispatch")
    parser.add_argument("--status", action="store_true", help="Check WhatsApp API status")
    parser.add_argument("--rate-status", action="store_true", help="Show rate limit usage")
    parser.add_argument("--pause", action="store_true", help="Pause dispatch (manual escape)")
    parser.add_argument("--resume", action="store_true", help="Resume dispatch")
    args = parser.parse_args()

    print("=" * 60)
    print("📨 Lead Hunter - WhatsApp Dispatch")
    print(f"⏰ {datetime.now(BRT).strftime('%Y-%m-%d %H:%M:%S')} BRT")
    print("=" * 60)

    if args.pause:
        pause_dispatch()
        return

    if args.resume:
        resume_dispatch()
        return

    supabase = get_supabase_client()
    evolution_config = get_evolution_config()

    if args.status:
        status = check_api_status(evolution_config)
        print(f"\n📡 API Status: {'✅ Healthy' if status['healthy'] else '❌ Unhealthy'}")
        print(f"   State: {status['state']}")
        if not status["healthy"]:
            print(f"   Error: {status.get('error', 'unknown')}")
        return

    if args.rate_status:
        rate = check_rate_limit(supabase)
        window = check_time_window()
        print(f"\n⏰ Time: {window['current_time']} BRT ({'✅ OPEN' if window['is_within_window'] else '❌ CLOSED'})")
        print(f"📊 Hourly: {rate['hour_count']}/{MAX_PER_HOUR} (remaining: {rate['hour_remaining']})")
        print(f"📊 Daily:  {rate['day_count']}/{MAX_PER_DAY} (remaining: {rate['day_remaining']})")
        print(f"🔒 Allowed: {'✅ Yes' if rate['allowed'] else '❌ No — ' + rate['reason']}")
        return

    # Process queue
    process_queue(supabase, evolution_config)


if __name__ == "__main__":
    main()
