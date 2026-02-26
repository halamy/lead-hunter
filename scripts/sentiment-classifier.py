#!/usr/bin/env python3
"""
Lead Hunter - Sentiment Classification (LH_HE_004)
Version: 1.0.0
Author: Metano[IA]

Classifies WhatsApp responses from leads using LLM analysis.
Routes: positive → handoff (sales-closer), negative → closed-lost, unclear → manual review.
Enforces SLA: 30min for unclear → auto-archive.

Usage:
  python sentiment-classifier.py                    # Process all unclassified responses
  python sentiment-classifier.py --response-id <id> # Classify specific response
  python sentiment-classifier.py --check-sla         # Check SLA violations

Requires:
  - SUPABASE_URL environment variable
  - SUPABASE_KEY environment variable
  - ANTHROPIC_API_KEY environment variable
  - pip install supabase anthropic

Veto Conditions (Pedro Valério):
  - SE classifica negativo como positivo → VETO CRÍTICO (falso handoff)
  - SE confidence < 0.7 → manual review queue (não auto-classifica)
  - SE unclear > 30min sem decisão → auto-archive
  - SE lead já em closed-lost → HARD BLOCK (zero contato posterior)
"""

import os
import sys
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import anthropic
from supabase import create_client, Client

BRT = ZoneInfo("America/Sao_Paulo")

# ============================================================================
# CONFIG
# ============================================================================

CONFIDENCE_THRESHOLD = 0.7   # Below this → manual review
SLA_MINUTES = 30             # Unclear responses expire after 30min
MAX_BATCH = 50               # Max responses per run

CLASSIFICATION_PROMPT = """You are a lead response classifier for a B2B WhatsApp outreach campaign.

## Context
Our outreach message: {outreach_message}

Lead's response: {response_text}

## Task
Classify the lead's response sentiment. Return ONLY valid JSON:

{{
  "sentiment": "positive|negative|neutral|interested|not_interested",
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation",
  "routing": "handoff|closed_lost|manual_review",
  "key_signals": ["list of signals that informed classification"]
}}

## Classification Rules
- **positive/interested**: Shows interest, asks questions about service, wants more info, asks price
  → routing: "handoff" (to sales-closer squad)
- **negative/not_interested**: Explicit rejection ("não quero", "não tenho interesse", "para de mandar")
  → routing: "closed_lost" (HARD BLOCK — zero further contact, LGPD)
- **neutral**: Unclear intent, just acknowledgment ("ok", "hmm", single emoji), wrong number
  → routing: "manual_review" (SLA 30min → auto-archive)

## Critical Rules
- "quanto custa?" / "qual o valor?" = POSITIVE (interested in pricing)
- "não quero" / "para" / "stop" / "sem interesse" = NEGATIVE (must respect)
- Single emoji or "👍" = NEUTRAL (insufficient signal)
- If unsure, prefer manual_review over wrong classification
- NEVER classify negative as positive (VETO CRÍTICO)
"""


# ============================================================================
# INIT
# ============================================================================

def get_supabase_client() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        print("❌ VETO: SUPABASE_URL and SUPABASE_KEY required")
        sys.exit(1)
    return create_client(url, key)


def get_claude_client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ VETO: ANTHROPIC_API_KEY required for sentiment classification")
        sys.exit(1)
    return anthropic.Anthropic(api_key=api_key)


# ============================================================================
# DATA ACCESS
# ============================================================================

def get_unclassified_responses(supabase: Client, response_id: str = None) -> list[dict]:
    """Get responses that haven't been classified yet."""
    query = supabase.table("lead_responses").select(
        "id, lead_id, message_id, response_text, received_at"
    )

    if response_id:
        query = query.eq("id", response_id)
    else:
        query = query.is_("sentiment", "null")

    result = query.limit(MAX_BATCH).execute()
    return result.data or []


def get_outreach_message(supabase: Client, lead_id: str) -> str:
    """Get the outreach message we sent to this lead."""
    try:
        result = (
            supabase.table("messages")
            .select("message_text")
            .eq("lead_id", lead_id)
            .eq("status", "sent")
            .order("sent_at", desc=True)
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0]["message_text"]
    except Exception:
        pass
    return "(outreach message not found)"


def get_lead_status(supabase: Client, lead_id: str) -> str:
    """Get current lead status."""
    try:
        result = supabase.table("leads").select("status").eq("id", lead_id).single().execute()
        return result.data["status"]
    except Exception:
        return "unknown"


# ============================================================================
# CLASSIFICATION
# ============================================================================

def classify_response(
    claude: anthropic.Anthropic,
    outreach_message: str,
    response_text: str
) -> dict:
    """Classify a response using Claude LLM."""
    prompt = CLASSIFICATION_PROMPT.replace("{outreach_message}", outreach_message)
    prompt = prompt.replace("{response_text}", response_text)

    try:
        message = claude.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}]
        )
        text = message.content[0].text

        # Parse JSON
        if "```json" in text:
            json_str = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            json_str = text.split("```")[1].split("```")[0]
        else:
            json_str = text

        result = json.loads(json_str.strip())

        # Validate required fields
        required = ["sentiment", "confidence", "routing"]
        if not all(k in result for k in required):
            raise ValueError(f"Missing fields: {[k for k in required if k not in result]}")

        # VETO: confidence below threshold → force manual review
        if result["confidence"] < CONFIDENCE_THRESHOLD:
            result["routing"] = "manual_review"
            result["reasoning"] = f"Low confidence ({result['confidence']:.2f} < {CONFIDENCE_THRESHOLD}). " + result.get("reasoning", "")

        return result

    except json.JSONDecodeError as e:
        return {
            "sentiment": "neutral",
            "confidence": 0.0,
            "routing": "manual_review",
            "reasoning": f"Classification parse error: {e}",
            "key_signals": [],
        }
    except Exception as e:
        return {
            "sentiment": "neutral",
            "confidence": 0.0,
            "routing": "manual_review",
            "reasoning": f"Classification error: {e}",
            "key_signals": [],
        }


# ============================================================================
# ROUTING
# ============================================================================

def route_positive(supabase: Client, lead_id: str, response_id: str):
    """Route positive response → handoff to sales-closer."""
    # Update lead status: sent → responded (triggers auto_create_handoff_on_response)
    try:
        supabase.table("leads").update({"status": "responded"}).eq("id", lead_id).execute()
    except Exception as e:
        print(f"  ⚠️  Lead status update failed: {e}")

    # Mark response for handoff
    supabase.table("lead_responses").update({
        "needs_handoff": True,
        "handoff_reason": "positive_sentiment",
    }).eq("id", response_id).execute()


def route_negative(supabase: Client, lead_id: str, sentiment: str):
    """Route negative response → closed-lost (HARD BLOCK)."""
    try:
        supabase.table("leads").update({
            "status": "closed",
        }).eq("id", lead_id).execute()
    except Exception as e:
        print(f"  ⚠️  Lead close failed: {e}")


def route_manual_review(supabase: Client, response_id: str):
    """Route unclear response → manual review queue."""
    # Just update the response — hunter-chief will review via *check-responses
    supabase.table("lead_responses").update({
        "needs_handoff": False,
        "handoff_reason": "manual_review_pending",
    }).eq("id", response_id).execute()


# ============================================================================
# SLA ENFORCEMENT
# ============================================================================

def check_sla_violations(supabase: Client):
    """Check for unclear responses that exceeded 30min SLA → auto-archive."""
    cutoff = (datetime.now(BRT) - timedelta(minutes=SLA_MINUTES)).isoformat()

    try:
        result = (
            supabase.table("lead_responses")
            .select("id, lead_id, received_at")
            .eq("sentiment", "neutral")
            .eq("handoff_reason", "manual_review_pending")
            .lt("received_at", cutoff)
            .execute()
        )

        expired = result.data or []
        if not expired:
            print("✅ No SLA violations")
            return

        print(f"⚠️  {len(expired)} responses exceeded {SLA_MINUTES}min SLA")

        for resp in expired:
            # Auto-archive: close the lead
            try:
                supabase.table("leads").update({"status": "closed"}).eq("id", resp["lead_id"]).execute()
                supabase.table("lead_responses").update({
                    "handoff_reason": "auto_archived_sla_exceeded",
                }).eq("id", resp["id"]).execute()
                print(f"  📦 Lead {resp['lead_id'][:8]}... auto-archived (SLA exceeded)")
            except Exception as e:
                print(f"  ⚠️  Archive failed for {resp['lead_id'][:8]}...: {e}")

    except Exception as e:
        print(f"❌ SLA check failed: {e}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Lead Hunter - Sentiment Classification")
    parser.add_argument("--response-id", help="Classify specific response")
    parser.add_argument("--check-sla", action="store_true", help="Check SLA violations")
    args = parser.parse_args()

    print("=" * 60)
    print("🧠 Lead Hunter - Sentiment Classification (LH_HE_004)")
    print(f"⏰ {datetime.now(BRT).strftime('%Y-%m-%d %H:%M:%S')} BRT")
    print("=" * 60)

    supabase = get_supabase_client()

    if args.check_sla:
        check_sla_violations(supabase)
        return

    claude = get_claude_client()

    # Get unclassified responses
    responses = get_unclassified_responses(supabase, args.response_id)
    if not responses:
        print("\nℹ️  No unclassified responses")
        return

    print(f"\n📬 Processing {len(responses)} unclassified responses")

    stats = {"positive": 0, "negative": 0, "manual_review": 0, "errors": 0}

    for i, resp in enumerate(responses):
        lead_id = resp["lead_id"]
        response_text = resp["response_text"]

        # Check lead status — VETO if already closed
        lead_status = get_lead_status(supabase, lead_id)
        if lead_status in ("closed",):
            print(f"  [{i+1}] ⏭️  Lead already closed. Skipping.")
            continue

        # Get outreach message for context
        outreach = get_outreach_message(supabase, lead_id)

        # Classify
        print(f"  [{i+1}/{len(responses)}] \"{response_text[:50]}...\"", end=" → ")
        classification = classify_response(claude, outreach, response_text)

        sentiment = classification["sentiment"]
        routing = classification["routing"]
        confidence = classification["confidence"]

        # Update response record
        try:
            supabase.table("lead_responses").update({
                "sentiment": sentiment,
            }).eq("id", resp["id"]).execute()
        except Exception as e:
            print(f"❌ update failed: {e}")
            stats["errors"] += 1
            continue

        # Route based on classification
        if routing == "handoff":
            route_positive(supabase, lead_id, resp["id"])
            stats["positive"] += 1
            print(f"✅ {sentiment} (conf: {confidence:.0%}) → HANDOFF")

        elif routing == "closed_lost":
            route_negative(supabase, lead_id, sentiment)
            stats["negative"] += 1
            print(f"❌ {sentiment} (conf: {confidence:.0%}) → CLOSED-LOST")

        else:  # manual_review
            route_manual_review(supabase, resp["id"])
            stats["manual_review"] += 1
            print(f"⚠️  {sentiment} (conf: {confidence:.0%}) → MANUAL REVIEW")

    # Check SLA after processing
    check_sla_violations(supabase)

    # Summary
    print("\n" + "=" * 60)
    print("📋 CLASSIFICATION REPORT:")
    print(f"  ✅ Positive (→ handoff): {stats['positive']}")
    print(f"  ❌ Negative (→ closed): {stats['negative']}")
    print(f"  ⚠️  Manual review: {stats['manual_review']}")
    print(f"  🔴 Errors: {stats['errors']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
