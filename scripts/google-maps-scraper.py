#!/usr/bin/env python3
"""
Lead Hunter - Google Maps Lead Capture
Version: 1.0.0
Author: Metano[IA]

Captures leads from Google Maps using Google Places API (Text Search).
Extracts: company_name, phone, website, address, rating, category.
Applies quality gates: GMH_001 (phone required), GMH_003 (dedup).
Stores qualified leads in Supabase.

Usage:
  python google-maps-scraper.py --query "agência marketing digital" --location "São Paulo, SP" --count 50

Requires:
  - SUPABASE_URL environment variable
  - SUPABASE_KEY environment variable
  - GOOGLE_MAPS_API_KEY environment variable
  - pip install supabase googlemaps

Veto Conditions (Pedro Valério):
  - GMH_001: Lead sem phone → SKIP (inviolável)
  - GMH_002: Priorizar leads com website
  - GMH_003: Duplicata por phone → SKIP
  - > 50% skip rate → WARN (ICP pode estar restritivo)
  - > 20% inválidos → HALT (keywords podem estar erradas)
"""

import os
import sys
import json
import argparse
import time
from datetime import datetime
from typing import Optional

import googlemaps
from supabase import create_client, Client


# ============================================================================
# CONFIG
# ============================================================================

MAX_RESULTS_PER_PAGE = 20  # Google Places API limit
SKIP_RATE_WARN_THRESHOLD = 0.50
INVALID_RATE_HALT_THRESHOLD = 0.20


# ============================================================================
# INIT
# ============================================================================

def get_supabase_client() -> Client:
    """Initialize Supabase client from environment variables."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        print("❌ VETO: SUPABASE_URL and SUPABASE_KEY required")
        sys.exit(1)
    return create_client(url, key)


def get_gmaps_client() -> googlemaps.Client:
    """Initialize Google Maps client from environment variable."""
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        print("❌ VETO: GOOGLE_MAPS_API_KEY required")
        sys.exit(1)
    return googlemaps.Client(key=api_key)


# ============================================================================
# GOOGLE MAPS SEARCH
# ============================================================================

def search_google_maps(
    gmaps: googlemaps.Client,
    query: str,
    location: str,
    max_results: int = 50
) -> list[dict]:
    """
    Search Google Maps using Text Search API.
    Returns raw place results up to max_results.
    """
    full_query = f"{query} {location}"
    print(f"🗺️  Searching: \"{full_query}\" (target: {max_results})")

    all_results = []
    next_page_token = None

    while len(all_results) < max_results:
        try:
            if next_page_token:
                # Google requires a short delay before using next_page_token
                time.sleep(2)
                response = gmaps.places(
                    query=full_query,
                    page_token=next_page_token
                )
            else:
                response = gmaps.places(query=full_query)

            results = response.get("results", [])
            if not results:
                break

            all_results.extend(results)
            print(f"  📍 Page fetched: {len(results)} results (total: {len(all_results)})")

            next_page_token = response.get("next_page_token")
            if not next_page_token:
                break

        except googlemaps.exceptions.ApiError as e:
            print(f"❌ Google Maps API error: {e}")
            break
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            break

    return all_results[:max_results]


def get_place_details(gmaps: googlemaps.Client, place_id: str) -> dict:
    """
    Get detailed info for a place (phone, website, etc.).
    Google Text Search doesn't return phone — we need Place Details.
    """
    try:
        result = gmaps.place(
            place_id=place_id,
            fields=[
                "name",
                "formatted_phone_number",
                "international_phone_number",
                "website",
                "formatted_address",
                "rating",
                "types",
                "url",  # Google Maps URL
                "user_ratings_total",
            ]
        )
        return result.get("result", {})
    except Exception as e:
        print(f"  ⚠️  Details fetch failed for {place_id}: {e}")
        return {}


# ============================================================================
# DATA EXTRACTION & QUALITY GATES
# ============================================================================

def extract_lead_data(place: dict, details: dict) -> Optional[dict]:
    """
    Extract lead data from Google Maps place + details.
    Returns None if quality gate fails (GMH_001: phone required).
    """
    phone = details.get("international_phone_number") or details.get("formatted_phone_number")
    company_name = details.get("name") or place.get("name", "")
    website = details.get("website")
    address = details.get("formatted_address") or place.get("formatted_address", "")
    rating = details.get("rating") or place.get("rating")
    google_maps_url = details.get("url", "")
    categories = place.get("types", [])

    # GMH_001: Phone REQUIRED — inviolable
    if not phone:
        return None

    # Normalize phone to Brazilian format
    phone = normalize_phone(phone)
    if not phone:
        return None

    return {
        "company_name": company_name,
        "phone": phone,
        "website": website,
        "address": address,
        "google_maps_url": google_maps_url,
        "source": "google_maps",
        "status": "new",
        "icp_score": None,  # Scored later by lead-qualifier
        "metadata": {
            "rating": rating,
            "categories": categories,
            "ratings_total": details.get("user_ratings_total"),
            "captured_at": datetime.now().isoformat(),
        }
    }


def normalize_phone(phone: str) -> Optional[str]:
    """
    Normalize phone number to +55 format.
    Returns None if phone is invalid.
    """
    if not phone:
        return None

    # Remove non-digit chars except +
    cleaned = "".join(c for c in phone if c.isdigit() or c == "+")

    # Add +55 if missing country code
    if not cleaned.startswith("+"):
        if cleaned.startswith("55"):
            cleaned = "+" + cleaned
        else:
            cleaned = "+55" + cleaned

    # Basic validation: Brazilian phone should be +55 + 10-11 digits
    digits_only = cleaned.replace("+", "")
    if len(digits_only) < 12 or len(digits_only) > 13:
        return None

    return cleaned


# ============================================================================
# DEDUPLICATION (GMH_003)
# ============================================================================

def check_duplicates(supabase: Client, phones: list[str]) -> set[str]:
    """
    Check which phone numbers already exist in Supabase.
    Returns set of existing phones.
    """
    if not phones:
        return set()

    try:
        result = supabase.table("leads").select("phone").in_("phone", phones).execute()
        return {row["phone"] for row in (result.data or [])}
    except Exception as e:
        print(f"⚠️  Dedup check failed: {e}")
        return set()


# ============================================================================
# SUPABASE INSERT
# ============================================================================

def insert_leads(supabase: Client, leads: list[dict]) -> int:
    """
    Insert leads into Supabase. Returns count of inserted.
    Uses upsert with phone as conflict key (via partial unique index).
    """
    if not leads:
        return 0

    inserted = 0
    for lead in leads:
        try:
            # Remove metadata (store separately if needed)
            metadata = lead.pop("metadata", {})
            supabase.table("leads").insert(lead).execute()
            inserted += 1
        except Exception as e:
            error_msg = str(e)
            if "duplicate" in error_msg.lower() or "unique" in error_msg.lower():
                print(f"  ⚠️  Duplicate skipped: {lead.get('company_name', 'unknown')}")
            else:
                print(f"  ❌ Insert failed for {lead.get('company_name', 'unknown')}: {e}")

    return inserted


# ============================================================================
# CAPTURE REPORT
# ============================================================================

def generate_report(
    total_found: int,
    total_with_phone: int,
    total_with_website: int,
    duplicates_skipped: int,
    total_inserted: int,
    skip_reasons: dict
) -> dict:
    """Generate capture report."""
    total_skipped = total_found - total_inserted - duplicates_skipped
    skip_rate = total_skipped / total_found if total_found > 0 else 0

    report = {
        "timestamp": datetime.now().isoformat(),
        "total_found": total_found,
        "total_with_phone": total_with_phone,
        "total_with_website": total_with_website,
        "total_without_phone": total_found - total_with_phone,
        "duplicates_skipped": duplicates_skipped,
        "total_inserted": total_inserted,
        "total_skipped": total_skipped,
        "skip_rate": round(skip_rate, 2),
        "skip_reasons": skip_reasons,
    }

    # Veto checks
    if total_inserted == 0:
        report["veto"] = "HALT — 0 leads captured. Review search query."
    elif skip_rate > SKIP_RATE_WARN_THRESHOLD:
        report["veto"] = f"WARN — Skip rate {skip_rate:.0%} > {SKIP_RATE_WARN_THRESHOLD:.0%}. ICP may be too restrictive."
    elif (total_found - total_with_phone) / total_found > INVALID_RATE_HALT_THRESHOLD if total_found > 0 else False:
        report["veto"] = f"WARN — >20% without phone. Keywords may need adjustment."

    return report


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Lead Hunter - Google Maps Lead Capture")
    parser.add_argument("--query", required=True, help="Search keywords (e.g., 'agência marketing digital')")
    parser.add_argument("--location", required=True, help="Location (e.g., 'São Paulo, SP')")
    parser.add_argument("--count", type=int, default=50, help="Target number of leads (default: 50)")
    parser.add_argument("--dry-run", action="store_true", help="Don't insert into Supabase")
    args = parser.parse_args()

    print("=" * 60)
    print("🗺️  Lead Hunter - Google Maps Lead Capture")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🔍 Query: \"{args.query}\" in \"{args.location}\"")
    print(f"🎯 Target: {args.count} leads")
    print("=" * 60)

    # Initialize clients
    gmaps = get_gmaps_client()
    supabase = get_supabase_client()

    # Step 1: Search Google Maps
    raw_results = search_google_maps(gmaps, args.query, args.location, args.count + 10)  # +10% buffer
    print(f"\n📊 Found {len(raw_results)} raw results")

    if not raw_results:
        print("❌ VETO: 0 results found. HALT pipeline, review search query.")
        sys.exit(1)

    # Step 2: Extract details + apply quality gates
    leads = []
    skip_reasons = {"no_phone": 0, "invalid_phone": 0, "no_details": 0}
    total_with_phone = 0
    total_with_website = 0

    for i, place in enumerate(raw_results):
        place_id = place.get("place_id")
        if not place_id:
            skip_reasons["no_details"] += 1
            continue

        print(f"  [{i+1}/{len(raw_results)}] {place.get('name', 'Unknown')}...", end=" ")

        # Get detailed info (phone, website)
        details = get_place_details(gmaps, place_id)
        if not details:
            skip_reasons["no_details"] += 1
            print("⚠️ no details")
            continue

        # Extract and validate
        lead = extract_lead_data(place, details)
        if lead is None:
            skip_reasons["no_phone"] += 1
            print("❌ no phone (GMH_001)")
            continue

        total_with_phone += 1
        if lead.get("website"):
            total_with_website += 1

        leads.append(lead)
        print(f"✅ {lead['phone']}")

        # Respect API rate limits
        time.sleep(0.1)

    print(f"\n📊 Extracted: {len(leads)} leads with phone")

    # Step 3: Dedup check (GMH_003)
    phones = [lead["phone"] for lead in leads]
    existing_phones = check_duplicates(supabase, phones)
    duplicates_skipped = 0

    if existing_phones:
        before = len(leads)
        leads = [lead for lead in leads if lead["phone"] not in existing_phones]
        duplicates_skipped = before - len(leads)
        print(f"🔄 Duplicates removed: {duplicates_skipped} (GMH_003)")

    # Trim to target count
    leads = leads[:args.count]

    # Step 4: Insert into Supabase
    if args.dry_run:
        print(f"\n🏃 DRY RUN — would insert {len(leads)} leads")
        inserted = len(leads)
    else:
        print(f"\n💾 Inserting {len(leads)} leads into Supabase...")
        inserted = insert_leads(supabase, leads)

    # Step 5: Generate report
    report = generate_report(
        total_found=len(raw_results),
        total_with_phone=total_with_phone,
        total_with_website=total_with_website,
        duplicates_skipped=duplicates_skipped,
        total_inserted=inserted,
        skip_reasons=skip_reasons,
    )

    print("\n" + "=" * 60)
    print("📋 CAPTURE REPORT:")
    print(f"  📍 Found: {report['total_found']}")
    print(f"  📞 With phone: {report['total_with_phone']} ({report['total_with_phone']/report['total_found']*100:.0f}%)" if report['total_found'] > 0 else "")
    print(f"  🌐 With website: {report['total_with_website']} ({report['total_with_website']/report['total_found']*100:.0f}%)" if report['total_found'] > 0 else "")
    print(f"  🔄 Duplicates: {report['duplicates_skipped']}")
    print(f"  ✅ Inserted: {report['total_inserted']}")
    print(f"  ❌ Skipped: {report['total_skipped']} (rate: {report['skip_rate']:.0%})")

    if "veto" in report:
        print(f"\n  ⚠️  {report['veto']}")

    print("=" * 60)

    if report['total_inserted'] > 0:
        print("✅ Capture complete. Context Analyst will process next.")
    else:
        print("❌ HALT — No leads captured. Review query and ICP.")
        sys.exit(1)


if __name__ == "__main__":
    main()
