#!/usr/bin/env python3
"""
Lead Hunter - Website Context Extraction
Version: 1.0.0
Author: Metano[IA]

Scrapes lead websites to extract actionable intelligence for personalization.
Scans: homepage, about, services, contact pages.
Identifies: services, pain points, company size, tech stack.
Stores context in Supabase lead_context table.

Usage:
  python website-scraper.py                      # Process all leads with status='new' and website
  python website-scraper.py --lead-id <uuid>     # Process specific lead
  python website-scraper.py --retry-failed        # Retry failed extractions

Requires:
  - SUPABASE_URL environment variable
  - SUPABASE_KEY environment variable
  - ANTHROPIC_API_KEY environment variable (for LLM-based analysis)
  - pip install supabase httpx anthropic beautifulsoup4

Veto Conditions (Pedro Valério):
  - SE inventa dados não presentes no site → VETO ABSOLUTO
  - SE não tenta retry em falha → VETO (max 3, LH_AT_002)
  - SE context_score > 5 quando só tem nome → VETO
  - SE extraction rate < 50% → PAUSE pipeline
"""

import os
import sys
import json
import argparse
import time
from datetime import datetime
from typing import Optional

import httpx
from bs4 import BeautifulSoup
from supabase import create_client, Client

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


# ============================================================================
# CONFIG
# ============================================================================

MAX_RETRIES = 3
RETRY_BACKOFF = [1800, 3600, 7200]  # 30min, 1h, 2h (exponential)
REQUEST_TIMEOUT = 15  # seconds
MAX_CONTENT_LENGTH = 50000  # chars per page
PAGES_TO_SCAN = ["", "/about", "/sobre", "/about-us", "/quem-somos",
                  "/services", "/servicos", "/contact", "/contato"]

EXTRACTION_PROMPT = """Analyze this website content and extract business intelligence.
Return ONLY valid JSON with these fields:

{
  "services_offered": ["list of services they provide"],
  "pain_points": ["potential pain points based on their business"],
  "company_size": "micro/small/medium/large or null if unknown",
  "tech_stack": ["technologies visible on website"],
  "target_audience": "who they serve",
  "urgency_signals": ["hiring, expanding, new office, etc."],
  "budget_signals": ["premium pricing, enterprise clients, etc."],
  "context_score": 1-10
}

Rules:
- ONLY extract information ACTUALLY PRESENT on the website
- DO NOT invent or assume information
- If a field has no data, use empty array [] or null
- context_score: 1-3 (minimal info), 4-6 (moderate), 7-10 (rich context)
- Pain points should be INFERRED from their services (what problems they solve = what problems their clients have)

Website content:
{content}
"""


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


def get_anthropic_client() -> Optional[object]:
    """Initialize Anthropic client for LLM analysis."""
    if not HAS_ANTHROPIC:
        print("⚠️  anthropic package not installed. Using basic extraction.")
        return None
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("⚠️  ANTHROPIC_API_KEY not set. Using basic extraction.")
        return None
    return anthropic.Anthropic(api_key=api_key)


# ============================================================================
# WEB SCRAPING
# ============================================================================

def fetch_page(url: str, timeout: int = REQUEST_TIMEOUT) -> Optional[str]:
    """Fetch a webpage and return cleaned text content."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; LeadHunterBot/1.0)",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
        }
        with httpx.Client(follow_redirects=True, timeout=timeout) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Remove scripts, styles, nav, footer
            for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
                tag.decompose()

            text = soup.get_text(separator=" ", strip=True)
            return text[:MAX_CONTENT_LENGTH]

    except httpx.TimeoutException:
        return None
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return None
        return None
    except Exception:
        return None


def scrape_website(website_url: str) -> dict:
    """
    Scrape multiple pages of a website.
    Returns combined content from all accessible pages.
    """
    # Normalize URL
    if not website_url.startswith("http"):
        website_url = "https://" + website_url
    website_url = website_url.rstrip("/")

    content_parts = {}
    pages_found = 0

    for path in PAGES_TO_SCAN:
        url = website_url + path
        content = fetch_page(url)
        if content and len(content) > 100:  # Skip near-empty pages
            page_name = path.strip("/") or "homepage"
            content_parts[page_name] = content
            pages_found += 1

    return {
        "url": website_url,
        "pages_scraped": pages_found,
        "content": content_parts,
        "total_chars": sum(len(c) for c in content_parts.values()),
    }


# ============================================================================
# CONTEXT EXTRACTION
# ============================================================================

def extract_context_llm(claude_client: object, scraped_data: dict) -> dict:
    """Extract context using Claude LLM analysis."""
    # Combine all page content
    combined_content = ""
    for page_name, content in scraped_data["content"].items():
        combined_content += f"\n--- {page_name.upper()} ---\n{content}\n"

    # Truncate if too long
    combined_content = combined_content[:30000]

    prompt = EXTRACTION_PROMPT.replace("{content}", combined_content)

    try:
        message = claude_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        response_text = message.content[0].text

        # Parse JSON from response
        # Find JSON block
        if "```json" in response_text:
            json_str = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            json_str = response_text.split("```")[1].split("```")[0]
        else:
            json_str = response_text

        return json.loads(json_str.strip())

    except json.JSONDecodeError:
        print("  ⚠️  LLM response not valid JSON, using basic extraction")
        return extract_context_basic(scraped_data)
    except Exception as e:
        print(f"  ⚠️  LLM extraction failed: {e}")
        return extract_context_basic(scraped_data)


def extract_context_basic(scraped_data: dict) -> dict:
    """Basic context extraction without LLM (fallback)."""
    combined = " ".join(scraped_data["content"].values()).lower()

    # Basic service detection
    service_keywords = {
        "marketing digital": "Marketing Digital",
        "tráfego pago": "Tráfego Pago",
        "seo": "SEO",
        "desenvolvimento": "Desenvolvimento Web",
        "design": "Design",
        "social media": "Social Media",
        "e-commerce": "E-commerce",
        "consultoria": "Consultoria",
        "automação": "Automação",
    }
    services = [v for k, v in service_keywords.items() if k in combined]

    # Basic pain point inference
    pain_keywords = {
        "resultado": "Busca por resultados mensuráveis",
        "crescimento": "Necessidade de crescimento",
        "leads": "Geração de leads",
        "vendas": "Aumento de vendas",
        "custo": "Otimização de custos",
    }
    pain_points = [v for k, v in pain_keywords.items() if k in combined]

    # Score based on content richness
    score = min(10, max(1, scraped_data["pages_scraped"] * 2 + len(services)))

    return {
        "services_offered": services,
        "pain_points": pain_points[:3],
        "company_size": None,
        "tech_stack": [],
        "target_audience": None,
        "urgency_signals": [],
        "budget_signals": [],
        "context_score": score,
    }


# ============================================================================
# SUPABASE OPERATIONS
# ============================================================================

def get_leads_to_process(supabase: Client, lead_id: Optional[str] = None) -> list[dict]:
    """Get leads that need context extraction."""
    query = supabase.table("leads").select("id, company_name, website, context_retry_count")

    if lead_id:
        query = query.eq("id", lead_id)
    else:
        query = query.eq("status", "new").not_.is_("website", "null")

    result = query.limit(50).execute()
    return result.data or []


def get_failed_leads(supabase: Client) -> list[dict]:
    """Get leads with failed context extraction for retry."""
    result = (
        supabase.table("leads")
        .select("id, company_name, website, context_retry_count")
        .eq("status", "context_failed")
        .lt("context_retry_count", MAX_RETRIES)
        .execute()
    )
    return result.data or []


def update_lead_status(supabase: Client, lead_id: str, status: str, retry_count: int = None):
    """Update lead status in Supabase."""
    data = {"status": status}
    if retry_count is not None:
        data["context_retry_count"] = retry_count
    supabase.table("leads").update(data).eq("id", lead_id).execute()


def save_context(supabase: Client, lead_id: str, context: dict):
    """Save extracted context to lead_context table."""
    record = {
        "lead_id": lead_id,
        "pain_points": json.dumps(context.get("pain_points", [])),
        "services_offered": context.get("services_offered", []),
        "company_size": context.get("company_size"),
        "tech_stack": context.get("tech_stack", []),
        "urgency_signals": context.get("urgency_signals", []),
        "budget_signals": context.get("budget_signals", []),
        "confidence_score": context.get("context_score", 1),
    }

    try:
        # Upsert (update if exists for this lead_id)
        supabase.table("lead_context").upsert(record, on_conflict="lead_id").execute()
    except Exception as e:
        print(f"  ❌ Save failed: {e}")
        raise


# ============================================================================
# MAIN PROCESSING
# ============================================================================

def process_lead(
    supabase: Client,
    claude_client: Optional[object],
    lead: dict
) -> dict:
    """Process a single lead: scrape website, extract context, save."""
    lead_id = lead["id"]
    company = lead["company_name"]
    website = lead.get("website")
    retry_count = lead.get("context_retry_count", 0)

    result = {"lead_id": lead_id, "company": company, "status": "unknown"}

    # No website = skip context, proceed with basic info
    if not website:
        result["status"] = "skipped_no_website"
        update_lead_status(supabase, lead_id, "ready")
        return result

    # Update status to context_pending
    try:
        update_lead_status(supabase, lead_id, "context_pending")
    except Exception as e:
        if "lead_status_transition_error" in str(e):
            result["status"] = "invalid_transition"
            return result
        raise

    # Scrape website
    print(f"  🌐 Scraping {website}...", end=" ")
    scraped = scrape_website(website)

    if scraped["pages_scraped"] == 0:
        print("❌ no pages accessible")
        retry_count += 1
        if retry_count >= MAX_RETRIES:
            update_lead_status(supabase, lead_id, "context_failed", retry_count)
            result["status"] = "failed_max_retries"
        else:
            update_lead_status(supabase, lead_id, "context_failed", retry_count)
            result["status"] = f"retry_{retry_count}/{MAX_RETRIES}"
        return result

    print(f"✅ {scraped['pages_scraped']} pages, {scraped['total_chars']} chars")

    # Extract context
    if claude_client:
        context = extract_context_llm(claude_client, scraped)
    else:
        context = extract_context_basic(scraped)

    # Validate context score (VETO: score > 5 when only name)
    if context["context_score"] > 5 and not context.get("services_offered") and not context.get("pain_points"):
        context["context_score"] = min(context["context_score"], 3)

    # Save to Supabase
    save_context(supabase, lead_id, context)
    update_lead_status(supabase, lead_id, "ready")

    result["status"] = "success"
    result["context_score"] = context["context_score"]
    result["pain_points"] = len(context.get("pain_points", []))
    result["services"] = len(context.get("services_offered", []))
    return result


def main():
    parser = argparse.ArgumentParser(description="Lead Hunter - Website Context Extraction")
    parser.add_argument("--lead-id", help="Process specific lead by UUID")
    parser.add_argument("--retry-failed", action="store_true", help="Retry failed extractions")
    args = parser.parse_args()

    print("=" * 60)
    print("🔍 Lead Hunter - Website Context Extraction")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    supabase = get_supabase_client()
    claude_client = get_anthropic_client()

    # Get leads to process
    if args.retry_failed:
        leads = get_failed_leads(supabase)
        print(f"\n🔄 Retrying {len(leads)} failed extractions")
    elif args.lead_id:
        leads = get_leads_to_process(supabase, args.lead_id)
        print(f"\n🎯 Processing specific lead: {args.lead_id}")
    else:
        leads = get_leads_to_process(supabase)
        print(f"\n📋 Processing {len(leads)} leads with websites")

    if not leads:
        print("⚠️  No leads to process")
        return

    # Process each lead
    results = {"success": 0, "failed": 0, "skipped": 0, "retry": 0}

    for i, lead in enumerate(leads):
        print(f"\n[{i+1}/{len(leads)}] {lead['company_name']}")
        result = process_lead(supabase, claude_client, lead)

        if result["status"] == "success":
            results["success"] += 1
            print(f"  ✅ Score: {result['context_score']}/10 | "
                  f"Pain points: {result['pain_points']} | "
                  f"Services: {result['services']}")
        elif "retry" in result["status"]:
            results["retry"] += 1
            print(f"  🔄 {result['status']}")
        elif "skipped" in result["status"]:
            results["skipped"] += 1
            print(f"  ⏭️  {result['status']}")
        else:
            results["failed"] += 1
            print(f"  ❌ {result['status']}")

        # Small delay between requests
        time.sleep(0.5)

    # Report
    total = len(leads)
    extraction_rate = results["success"] / total if total > 0 else 0

    print("\n" + "=" * 60)
    print("📋 EXTRACTION REPORT:")
    print(f"  ✅ Success: {results['success']}/{total} ({extraction_rate:.0%})")
    print(f"  🔄 Retry queued: {results['retry']}")
    print(f"  ⏭️  Skipped: {results['skipped']}")
    print(f"  ❌ Failed: {results['failed']}")

    if extraction_rate < 0.50:
        print(f"\n  ⚠️  VETO: Extraction rate {extraction_rate:.0%} < 50%. PAUSE pipeline.")
    elif extraction_rate < 0.80:
        print(f"\n  ⚠️  WARN: Extraction rate {extraction_rate:.0%} < 80%. Monitor.")
    else:
        print(f"\n  ✅ Extraction rate healthy: {extraction_rate:.0%}")

    print("=" * 60)
    print("✅ Context extraction complete. Message Crafter can proceed.")


if __name__ == "__main__":
    main()
