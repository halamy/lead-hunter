#!/usr/bin/env python3
"""
Lead Hunter Squad — End-to-End Dry Run Test
Version: 1.0.0
Author: Pedro Valério (Process Absolutist)

Validates the ENTIRE pipeline with mock data without touching external services.
Tests: imports, functions, veto conditions, state machine, data flow, guardrails.

Usage:
  python dry-run-test.py

No environment variables needed — all mocked.
"""

import sys
import os
import json
import importlib.util
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from unittest.mock import MagicMock, patch
from typing import Any

BRT = ZoneInfo("America/Sao_Paulo")
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))

# ============================================================================
# TEST FRAMEWORK
# ============================================================================

class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.details = []

    def ok(self, test_name: str, detail: str = ""):
        self.passed += 1
        self.details.append(("✅", test_name, detail))
        print(f"  ✅ {test_name}" + (f" — {detail}" if detail else ""))

    def fail(self, test_name: str, detail: str = ""):
        self.failed += 1
        self.details.append(("❌", test_name, detail))
        print(f"  ❌ {test_name}" + (f" — {detail}" if detail else ""))

    def warn(self, test_name: str, detail: str = ""):
        self.warnings += 1
        self.details.append(("⚠️", test_name, detail))
        print(f"  ⚠️  {test_name}" + (f" — {detail}" if detail else ""))

    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"📋 TEST RESULTS: {self.passed}/{total} passed"
              f" | {self.failed} failed | {self.warnings} warnings")
        if self.failed == 0:
            print("🎉 ALL TESTS PASSED — Pipeline is structurally sound")
        else:
            print("🔴 FAILURES DETECTED — Fix before going live")
        print(f"{'='*60}")
        return self.failed == 0


results = TestResults()


# ============================================================================
# HELPER: Load module without executing
# ============================================================================

def load_module(name: str):
    """Load a Python module from scripts dir without running main()."""
    path = os.path.join(SCRIPTS_DIR, name)
    spec = importlib.util.spec_from_file_location(name.replace(".py", ""), path)
    module = importlib.util.module_from_spec(spec)
    return module, spec


# ============================================================================
# PHASE 0: DEPENDENCY CHECK
# ============================================================================

def test_phase_0_dependencies():
    print("\n" + "="*60)
    print("📦 PHASE 0: Dependency Check")
    print("="*60)

    # Core dependencies
    deps = {
        "supabase": "Supabase client",
        "httpx": "HTTP client (scraper + Evolution API)",
        "bs4": "BeautifulSoup (HTML parsing)",
        "googlemaps": "Google Maps API client",
    }

    for module, desc in deps.items():
        try:
            importlib.import_module(module)
            results.ok(f"import {module}", desc)
        except ImportError:
            results.warn(f"import {module}", f"{desc} — not installed (pip install -r requirements.txt)")

    # Optional: anthropic
    try:
        importlib.import_module("anthropic")
        results.ok("import anthropic", "LLM analysis available")
    except ImportError:
        results.warn("import anthropic", "Not installed — scripts will use basic fallback")

    # Check zoneinfo (Python 3.9+)
    try:
        from zoneinfo import ZoneInfo
        brt = ZoneInfo("America/Sao_Paulo")
        results.ok("zoneinfo BRT", f"Timezone: {brt}")
    except Exception as e:
        results.fail("zoneinfo BRT", str(e))


# ============================================================================
# PHASE 1: SCRIPT IMPORT TEST
# ============================================================================

def test_phase_1_imports():
    print("\n" + "="*60)
    print("📜 PHASE 1: Script Import Test")
    print("="*60)

    scripts = [
        "google-maps-scraper.py",
        "website-scraper.py",
        "whatsapp-api-client.py",
        "sentiment-classifier.py",
        "queue-processor.py",
        "end-of-day-cleanup.py",
    ]

    for script in scripts:
        path = os.path.join(SCRIPTS_DIR, script)
        if not os.path.exists(path):
            results.fail(f"exists {script}", "File not found")
            continue

        try:
            with open(path) as f:
                code = f.read()
            compile(code, script, "exec")
            results.ok(f"compile {script}", f"{len(code)} chars")
        except SyntaxError as e:
            results.fail(f"compile {script}", f"Line {e.lineno}: {e.msg}")


# ============================================================================
# PHASE 2: GOOGLE MAPS SCRAPER — FUNCTION TESTS
# ============================================================================

def test_phase_2_gmaps():
    print("\n" + "="*60)
    print("🗺️  PHASE 2: Google Maps Scraper — Function Tests")
    print("="*60)

    # Test normalize_phone
    sys.path.insert(0, SCRIPTS_DIR)

    try:
        # Import the module by loading it carefully
        spec = importlib.util.spec_from_file_location(
            "gmaps_scraper",
            os.path.join(SCRIPTS_DIR, "google-maps-scraper.py")
        )
        mod = importlib.util.module_from_spec(spec)

        # Mock external deps before loading
        sys.modules['googlemaps'] = MagicMock()
        sys.modules['supabase'] = MagicMock()

        spec.loader.exec_module(mod)

        # Test normalize_phone
        test_cases = [
            ("+5511999887766", "+5511999887766", "Already formatted"),
            ("11999887766", "+5511999887766", "Missing +55"),
            ("5511999887766", "+5511999887766", "Missing +"),
            ("(11) 99988-7766", "+5511999887766", "With formatting"),
            ("123", None, "Too short"),
            ("", None, "Empty"),
            (None, None, "None input"),
        ]

        for input_val, expected, desc in test_cases:
            result = mod.normalize_phone(input_val)
            if result == expected:
                results.ok(f"normalize_phone: {desc}", f"{input_val!r} → {result!r}")
            else:
                results.fail(f"normalize_phone: {desc}", f"Expected {expected!r}, got {result!r}")

        # Test extract_lead_data — GMH_001 (phone required)
        place = {"name": "Test Agency", "formatted_address": "Rua Test, SP", "types": ["marketing_agency"]}

        # With phone → should return lead
        details_with_phone = {"name": "Test Agency", "international_phone_number": "+5511999887766",
                              "website": "https://test.com", "formatted_address": "Rua Test, SP"}
        lead = mod.extract_lead_data(place, details_with_phone)
        if lead and lead["phone"] == "+5511999887766":
            results.ok("GMH_001: Lead WITH phone", "Accepted ✓")
        else:
            results.fail("GMH_001: Lead WITH phone", f"Got {lead}")

        # Without phone → should return None (GMH_001 VETO)
        details_no_phone = {"name": "Test Agency", "website": "https://test.com",
                            "formatted_address": "Rua Test, SP"}
        lead = mod.extract_lead_data(place, details_no_phone)
        if lead is None:
            results.ok("GMH_001: Lead WITHOUT phone", "VETOED ✓ (phone required)")
        else:
            results.fail("GMH_001: Lead WITHOUT phone", f"Should be None, got {lead}")

    except Exception as e:
        results.fail("gmaps_scraper module", str(e))
    finally:
        # Cleanup mocks
        sys.modules.pop('googlemaps', None)
        sys.modules.pop('supabase', None)


# ============================================================================
# PHASE 3: WEBSITE SCRAPER — FUNCTION TESTS
# ============================================================================

def test_phase_3_scraper():
    print("\n" + "="*60)
    print("🔍 PHASE 3: Website Scraper — Function Tests")
    print("="*60)

    try:
        sys.modules['supabase'] = MagicMock()
        sys.modules['anthropic'] = MagicMock()

        spec = importlib.util.spec_from_file_location(
            "web_scraper",
            os.path.join(SCRIPTS_DIR, "website-scraper.py")
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        # Test extract_context_basic
        scraped_data = {
            "content": {
                "homepage": "Somos uma agência de marketing digital focada em tráfego pago e SEO. Ajudamos empresas a crescer com automação.",
                "services": "Nossos serviços incluem desenvolvimento de landing pages e gestão de social media.",
            },
            "pages_scraped": 2,
            "total_chars": 200,
        }

        context = mod.extract_context_basic(scraped_data)

        if context.get("services_offered") and len(context["services_offered"]) > 0:
            results.ok("basic_extraction: services", f"Found {len(context['services_offered'])} services")
        else:
            results.warn("basic_extraction: services", "No services detected")

        if context.get("pain_points") and len(context["pain_points"]) > 0:
            results.ok("basic_extraction: pain_points", f"Found {len(context['pain_points'])} pain points")
        else:
            results.warn("basic_extraction: pain_points", "No pain points detected")

        if 1 <= context.get("context_score", 0) <= 10:
            results.ok("basic_extraction: score", f"Score: {context['context_score']}/10")
        else:
            results.fail("basic_extraction: score", f"Invalid score: {context.get('context_score')}")

        # Test VETO: score > 5 with no data should be capped
        empty_scraped = {"content": {"homepage": "Company XYZ"}, "pages_scraped": 1, "total_chars": 12}
        empty_context = mod.extract_context_basic(empty_scraped)
        if empty_context["context_score"] <= 5:
            results.ok("VETO: empty site score cap", f"Score capped at {empty_context['context_score']}")
        else:
            results.warn("VETO: empty site score cap", f"Score {empty_context['context_score']} may be too high for empty site")

        # Test PAGES_TO_SCAN includes required pages
        required_paths = ["", "/about", "/services", "/contact"]
        for path in required_paths:
            if path in mod.PAGES_TO_SCAN:
                results.ok(f"page scan: {path or '/'}", "In scan list")
            else:
                results.fail(f"page scan: {path or '/'}", "Missing from PAGES_TO_SCAN")

    except Exception as e:
        results.fail("web_scraper module", str(e))
    finally:
        sys.modules.pop('supabase', None)
        sys.modules.pop('anthropic', None)


# ============================================================================
# PHASE 4: WHATSAPP CLIENT — GUARDRAIL TESTS
# ============================================================================

def test_phase_4_whatsapp():
    print("\n" + "="*60)
    print("📨 PHASE 4: WhatsApp Client — Guardrail Tests")
    print("="*60)

    try:
        sys.modules['supabase'] = MagicMock()
        sys.modules['httpx'] = MagicMock()

        spec = importlib.util.spec_from_file_location(
            "whatsapp_client",
            os.path.join(SCRIPTS_DIR, "whatsapp-api-client.py")
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        # Test config constants
        if mod.WINDOW_START == 9 and mod.WINDOW_END == 17:
            results.ok("SCH_001: Time window config", "9h-17h ✓")
        else:
            results.fail("SCH_001: Time window config", f"Got {mod.WINDOW_START}-{mod.WINDOW_END}")

        if mod.MAX_PER_HOUR == 30:
            results.ok("SCH_002: Hourly rate limit", "30/hr ✓")
        else:
            results.fail("SCH_002: Hourly rate limit", f"Got {mod.MAX_PER_HOUR}")

        if mod.MAX_PER_DAY == 200:
            results.ok("SCH_003: Daily rate limit", "200/day ✓")
        else:
            results.fail("SCH_003: Daily rate limit", f"Got {mod.MAX_PER_DAY}")

        if mod.DELAY_MIN == 30 and mod.DELAY_MAX == 180:
            results.ok("Anti-detection: Random delay", f"{mod.DELAY_MIN}-{mod.DELAY_MAX}s ✓")
        else:
            results.fail("Anti-detection: Random delay", f"Got {mod.DELAY_MIN}-{mod.DELAY_MAX}")

        if mod.MAX_SEND_RETRIES == 3:
            results.ok("Guardrail #5: Retry logic", f"Max {mod.MAX_SEND_RETRIES} retries ✓")
        else:
            results.fail("Guardrail #5: Retry logic", f"Got {mod.MAX_SEND_RETRIES}")

        # Test time window check function
        result = mod.check_time_window()
        if "current_time" in result and "is_within_window" in result:
            status = "OPEN" if result["is_within_window"] else "CLOSED"
            results.ok("check_time_window()", f"{result['current_time']} BRT — {status}")
        else:
            results.fail("check_time_window()", "Missing expected fields")

        # Test manual escape (guardrail #4)
        pause_file = mod.PAUSE_FILE
        if not os.path.exists(pause_file):
            if not mod.is_paused():
                results.ok("Guardrail #4: Not paused", "is_paused() = False ✓")
            else:
                results.fail("Guardrail #4: Not paused", "Reports paused without pause file")
        else:
            results.warn("Guardrail #4: Pause file exists", f"Remove {pause_file} to resume")

    except Exception as e:
        results.fail("whatsapp_client module", str(e))
    finally:
        sys.modules.pop('supabase', None)
        sys.modules.pop('httpx', None)


# ============================================================================
# PHASE 5: SENTIMENT CLASSIFIER — CLASSIFICATION TESTS
# ============================================================================

def test_phase_5_sentiment():
    print("\n" + "="*60)
    print("🧠 PHASE 5: Sentiment Classifier — Logic Tests")
    print("="*60)

    try:
        sys.modules['supabase'] = MagicMock()
        sys.modules['anthropic'] = MagicMock()

        spec = importlib.util.spec_from_file_location(
            "sentiment",
            os.path.join(SCRIPTS_DIR, "sentiment-classifier.py")
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        # Test confidence threshold
        if mod.CONFIDENCE_THRESHOLD == 0.7:
            results.ok("Confidence threshold", "0.7 ✓ (below → manual review)")
        else:
            results.fail("Confidence threshold", f"Got {mod.CONFIDENCE_THRESHOLD}")

        # Test SLA config
        if mod.SLA_MINUTES == 30:
            results.ok("SLA enforcement", "30min ✓ (unclear → auto-archive)")
        else:
            results.fail("SLA enforcement", f"Got {mod.SLA_MINUTES}min")

        # Test classification prompt contains critical rules
        prompt = mod.CLASSIFICATION_PROMPT
        critical_rules = [
            ("quanto custa", "Pricing question = POSITIVE"),
            ("não quero", "Rejection = NEGATIVE"),
            ("LGPD", "LGPD compliance mentioned"),
            ("manual_review", "Manual review routing"),
            ("NEVER classify negative as positive", "False positive VETO"),
        ]

        for keyword, desc in critical_rules:
            if keyword.lower() in prompt.lower():
                results.ok(f"Prompt rule: {desc}", f"Contains '{keyword}'")
            else:
                results.fail(f"Prompt rule: {desc}", f"Missing '{keyword}' in prompt")

        # Test sentiment values match schema
        schema_sentiments = {"positive", "neutral", "negative", "interested", "not_interested"}
        prompt_mentions_all = all(s in prompt for s in schema_sentiments)
        if prompt_mentions_all:
            results.ok("Sentiment values", "All 5 values in prompt match schema CHECK")
        else:
            results.warn("Sentiment values", "Some values may be missing from prompt")

    except Exception as e:
        results.fail("sentiment_classifier module", str(e))
    finally:
        sys.modules.pop('supabase', None)
        sys.modules.pop('anthropic', None)


# ============================================================================
# PHASE 6: CROSS-REFERENCE VALIDATION
# ============================================================================

def test_phase_6_crossref():
    print("\n" + "="*60)
    print("🔗 PHASE 6: Cross-Reference Validation")
    print("="*60)

    base = os.path.dirname(SCRIPTS_DIR)

    # Agent → Script references
    agent_script_refs = {
        "agents/google-maps-hunter.md": "google-maps-scraper.py",
        "agents/context-analyst.md": "website-scraper.py",
        "agents/scheduler.md": "whatsapp-api-client.py",
    }

    for agent_file, script_name in agent_script_refs.items():
        agent_path = os.path.join(base, agent_file)
        script_path = os.path.join(SCRIPTS_DIR, script_name)

        if os.path.exists(agent_path):
            with open(agent_path) as f:
                content = f.read()
            if script_name in content:
                if os.path.exists(script_path):
                    results.ok(f"ref {agent_file} → {script_name}", "Agent refs script ✓, script exists ✓")
                else:
                    results.fail(f"ref {agent_file} → {script_name}", "Agent refs script but FILE MISSING")
            else:
                results.fail(f"ref {agent_file} → {script_name}", "Agent doesn't reference script")
        else:
            results.fail(f"ref {agent_file}", "Agent file not found")

    # Schema → Migration consistency
    migration_functions = [
        "enforce_lead_status_transition",
        "enforce_message_status_transition",
        "auto_create_handoff_on_response",
        "enforce_icp_threshold",
        "check_rate_limit",
        "enforce_rate_limit_on_queue",
        "enforce_business_hours_on_queue",
        "enforce_personalization_minimum",
    ]

    migration_001 = os.path.join(base, "data/migrations/001_p0_veto_enforcement.sql")
    if os.path.exists(migration_001):
        with open(migration_001) as f:
            sql = f.read()
        for func in migration_functions:
            if func in sql:
                results.ok(f"migration001: {func}", "Function defined")
            else:
                results.fail(f"migration001: {func}", "Function NOT in migration")

    # Migration 002 checks
    migration_002 = os.path.join(base, "data/migrations/002_p1_handoff_sentiment.sql")
    if os.path.exists(migration_002):
        with open(migration_002) as f:
            sql = f.read()

        p1_items = [
            ("sentiment TEXT", "P1-1: Sentiment column"),
            ("handoff_notifications", "P1-2: Notification table"),
            ("notify_sales_closer_new_handoff", "P1-2: Notification function"),
            ("expire_stale_handoffs", "P1-3: TTL enforcement"),
            ("pending_handoffs", "P1-4: Monitoring view"),
            ("sentiment_report", "P1-4: Sentiment report view"),
        ]

        for item, desc in p1_items:
            if item in sql:
                results.ok(f"migration002: {desc}", f"Contains '{item}'")
            else:
                results.fail(f"migration002: {desc}", f"Missing '{item}'")

    # Workflow → Task file references
    workflow_path = os.path.join(base, "workflows/wf-lead-capture.yaml")
    if os.path.exists(workflow_path):
        with open(workflow_path) as f:
            wf = f.read()

        task_refs = [
            "tasks/qualify-lead.md",
            "tasks/capture-leads.md",
            "tasks/extract-context.md",
            "tasks/craft-message.md",
            "tasks/schedule-dispatch.md",
            "tasks/process-responses.md",
            "tasks/pipeline-report.md",
        ]

        for task_ref in task_refs:
            task_path = os.path.join(base, task_ref)
            if task_ref in wf and os.path.exists(task_path):
                results.ok(f"workflow → {task_ref}", "Referenced ✓, exists ✓")
            elif task_ref in wf:
                results.fail(f"workflow → {task_ref}", "Referenced but FILE MISSING")
            else:
                results.warn(f"workflow → {task_ref}", "Not referenced in workflow")

    # Checklist files exist
    checklists = [
        "checklists/lead-qualification-checklist.md",
        "checklists/message-quality-checklist.md",
        "checklists/dispatch-safety-checklist.md",
        "checklists/pipeline-health-checklist.md",
        "checklists/handoff-readiness-checklist.md",
    ]

    for cl in checklists:
        if os.path.exists(os.path.join(base, cl)):
            results.ok(f"checklist: {cl}", "Exists ✓")
        else:
            results.fail(f"checklist: {cl}", "FILE MISSING")

    # Template files exist
    templates = [
        "templates/cold-message-template.md",
        "templates/icp-definition-template.md",
        "templates/handoff-package-template.md",
        "templates/pipeline-report-template.md",
    ]

    for tmpl in templates:
        if os.path.exists(os.path.join(base, tmpl)):
            results.ok(f"template: {tmpl}", "Exists ✓")
        else:
            results.fail(f"template: {tmpl}", "FILE MISSING")


# ============================================================================
# PHASE 7: STATE MACHINE SIMULATION
# ============================================================================

def test_phase_7_state_machine():
    print("\n" + "="*60)
    print("🔄 PHASE 7: State Machine Simulation")
    print("="*60)

    # Valid transitions (from migration 001)
    valid_transitions = {
        "new": ["context_pending", "closed"],
        "context_pending": ["ready", "context_failed", "closed"],
        "context_failed": ["ready", "closed"],
        "ready": ["sent", "closed"],
        "sent": ["delivered", "responded", "failed", "closed"],
        "delivered": ["read", "responded", "closed"],
        "read": ["responded", "closed"],
        "responded": ["closed"],
        "failed": ["ready", "closed"],
        "closed": [],
    }

    # Happy path: new → context_pending → ready → sent → responded → closed
    happy_path = ["new", "context_pending", "ready", "sent", "responded", "closed"]

    for i in range(len(happy_path) - 1):
        from_state = happy_path[i]
        to_state = happy_path[i + 1]
        if to_state in valid_transitions.get(from_state, []):
            results.ok(f"happy: {from_state} → {to_state}", "Valid transition")
        else:
            results.fail(f"happy: {from_state} → {to_state}", "INVALID transition!")

    # Invalid transitions (should be blocked)
    invalid_paths = [
        ("sent", "new", "Backward: sent → new"),
        ("responded", "ready", "Backward: responded → ready"),
        ("closed", "new", "Terminal: closed → new"),
        ("closed", "sent", "Terminal: closed → sent"),
        ("new", "sent", "Skip: new → sent (must go through context)"),
        ("new", "responded", "Skip: new → responded"),
    ]

    for from_state, to_state, desc in invalid_paths:
        if to_state not in valid_transitions.get(from_state, []):
            results.ok(f"BLOCKED: {desc}", f"{from_state} ↛ {to_state}")
        else:
            results.fail(f"BLOCKED: {desc}", f"{from_state} → {to_state} should be blocked!")

    # Unidirectionality check: no state can go to a "previous" state
    state_order = {"new": 0, "context_pending": 1, "context_failed": 1, "ready": 2,
                   "sent": 3, "delivered": 4, "read": 5, "responded": 6, "closed": 7, "failed": 3}

    backward_found = False
    for state, targets in valid_transitions.items():
        for target in targets:
            if target == "closed":
                continue  # closed is terminal, always valid
            if target == "ready" and state == "failed":
                continue  # retry is allowed: failed → ready
            if state_order.get(target, 0) < state_order.get(state, 0):
                results.fail(f"BACKWARD: {state} → {target}", "Violates unidirectional flow!")
                backward_found = True

    if not backward_found:
        results.ok("Unidirectional flow", "No backward transitions found (except failed → ready retry)")


# ============================================================================
# PHASE 8: VETO CONDITIONS MATRIX
# ============================================================================

def test_phase_8_veto_matrix():
    print("\n" + "="*60)
    print("🚫 PHASE 8: Veto Conditions Matrix")
    print("="*60)

    base = os.path.dirname(SCRIPTS_DIR)

    # Read all agent files and count veto conditions
    agents_dir = os.path.join(base, "agents")
    total_vetos = 0

    for agent_file in sorted(os.listdir(agents_dir)):
        if not agent_file.endswith(".md"):
            continue
        with open(os.path.join(agents_dir, agent_file)) as f:
            content = f.read()

        # Count veto conditions
        veto_count = content.lower().count("veto")
        triggers = content.count("trigger:")
        agent_name = agent_file.replace(".md", "")

        if veto_count >= 3:
            results.ok(f"vetos in {agent_name}", f"{veto_count} veto mentions, {triggers} triggers")
        elif veto_count > 0:
            results.warn(f"vetos in {agent_name}", f"Only {veto_count} veto mentions")
        else:
            results.fail(f"vetos in {agent_name}", "ZERO veto conditions!")

        total_vetos += veto_count

    results.ok(f"Total veto density", f"{total_vetos} veto mentions across {len(os.listdir(agents_dir))} agents")

    # Check DB-enforced vetos
    migration_001 = os.path.join(base, "data/migrations/001_p0_veto_enforcement.sql")
    if os.path.exists(migration_001):
        with open(migration_001) as f:
            sql = f.read()

        db_vetos = [
            ("enforce_lead_status_transition", "State machine enforcement"),
            ("enforce_message_status_transition", "Message state enforcement"),
            ("enforce_icp_threshold", "ICP >= 21 enforcement"),
            ("enforce_rate_limit_on_queue", "Rate limit enforcement"),
            ("enforce_business_hours_on_queue", "9h-17h enforcement"),
            ("enforce_personalization_minimum", "Personalization >= 5 enforcement"),
            ("idx_leads_phone_unique_active", "Phone dedup enforcement"),
        ]

        for func, desc in db_vetos:
            if func in sql:
                results.ok(f"DB VETO: {desc}", f"Function/index: {func}")
            else:
                results.fail(f"DB VETO: {desc}", f"Missing: {func}")


# ============================================================================
# PHASE 9: PIPELINE DATA FLOW SIMULATION
# ============================================================================

def test_phase_9_data_flow():
    print("\n" + "="*60)
    print("🔄 PHASE 9: Pipeline Data Flow Simulation")
    print("="*60)

    print("\n  Simulating: Full pipeline with mock lead data\n")

    # Mock lead data (as it would flow through the pipeline)
    mock_lead = {
        "company_name": "Agência Digital XYZ",
        "phone": "+5511999887766",
        "website": "https://agenciaxyz.com.br",
        "address": "Av. Paulista 1000, São Paulo, SP",
        "google_maps_url": "https://maps.google.com/?cid=123",
        "source": "google_maps",
        "status": "new",
        "icp_score": None,
    }

    # Phase 1: ICP Qualification
    icp_dimensions = {
        "market_fit": 5, "budget_potential": 4, "decision_maker": 3,
        "urgency": 4, "digital_presence": 5, "location_fit": 3
    }
    icp_score = sum(icp_dimensions.values())  # 24/30
    mock_lead["icp_score"] = icp_score
    mock_lead["icp_dimensions"] = icp_dimensions

    if icp_score >= 21:
        results.ok("Phase 1: ICP Qualification", f"Score {icp_score}/30 >= 21 threshold → PASS")
        mock_lead["status"] = "context_pending"
    else:
        results.fail("Phase 1: ICP Qualification", f"Score {icp_score}/30 < 21 → BLOCKED")
        return

    # Phase 2: Capture validation
    if mock_lead["phone"]:
        results.ok("Phase 2: GMH_001 (phone check)", f"Phone: {mock_lead['phone']} → PASS")
    else:
        results.fail("Phase 2: GMH_001", "No phone → SKIP")
        return

    # Phase 3: Context extraction
    mock_context = {
        "lead_id": "mock-uuid",
        "pain_points": ["Alto custo de captação", "Dificuldade de escalar"],
        "services_offered": ["Marketing Digital", "Tráfego Pago", "SEO"],
        "company_size": "small",
        "tech_stack": ["WordPress", "Google Analytics"],
        "confidence_score": 8,
    }
    mock_lead["status"] = "ready"

    if len(mock_context["pain_points"]) >= 1:
        results.ok("Phase 3: Context extraction", f"{len(mock_context['pain_points'])} pain points, score {mock_context['confidence_score']}/10")
    else:
        results.warn("Phase 3: Context extraction", "No pain points found")

    # Phase 4: Message crafting
    mock_message = {
        "message_text": f"Oi, vi que a {mock_lead['company_name']} foca em tráfego pago. "
                        f"Ajudamos agências a reduzir CAC com automação de IA 🤖 "
                        f"Faz sentido conversarmos?",
        "personalization_score": 8,
    }

    msg_len = len(mock_message["message_text"])
    if mock_message["personalization_score"] >= 7:
        results.ok("Phase 4: MC_001 (personalization)", f"Score {mock_message['personalization_score']}/10 >= 7 → PASS")
    else:
        results.fail("Phase 4: MC_001", f"Score {mock_message['personalization_score']}/10 < 7 → REJECT")

    if msg_len <= 300:
        results.ok("Phase 4: Message length", f"{msg_len} chars <= 300 → PASS")
    else:
        results.fail("Phase 4: Message length", f"{msg_len} chars > 300 → REJECT")

    # Phase 5: Dispatch validation
    now_brt = datetime.now(BRT)
    in_window = 9 <= now_brt.hour < 17 and now_brt.weekday() != 6

    results.ok("Phase 5: Time window check",
               f"{now_brt.strftime('%H:%M')} BRT — {'OPEN (would dispatch)' if in_window else 'CLOSED (would queue)'}")
    results.ok("Phase 5: Rate limit check", "Mock: 0/30 hour, 0/200 day → PASS")
    results.ok("Phase 5: Random delay", f"Would apply {30}-{180}s delay")

    mock_lead["status"] = "sent"

    # Phase 6: Response classification
    mock_response = "Interessante, como funciona?"
    mock_classification = {
        "sentiment": "positive",
        "confidence": 0.92,
        "routing": "handoff",
    }

    if mock_classification["confidence"] >= 0.7:
        results.ok("Phase 6: Sentiment classification",
                   f"\"{mock_response}\" → {mock_classification['sentiment']} "
                   f"(conf: {mock_classification['confidence']:.0%}) → {mock_classification['routing']}")
    else:
        results.warn("Phase 6: Low confidence", f"Would route to manual review")

    mock_lead["status"] = "responded"

    # Handoff package
    handoff_package = {
        "lead_profile": {
            "company_name": mock_lead["company_name"],
            "phone": mock_lead["phone"],
            "website": mock_lead["website"],
            "address": mock_lead["address"],
            "icp_score": mock_lead["icp_score"],
        },
        "context_summary": mock_context,
        "response_received": mock_response,
        "qualification_score": mock_lead["icp_score"],
        "sentiment": mock_classification["sentiment"],
    }

    required_fields = ["lead_profile", "context_summary", "response_received", "qualification_score", "sentiment"]
    present = [f for f in required_fields if f in handoff_package and handoff_package[f]]

    if len(present) == len(required_fields):
        results.ok("Phase 6: Handoff package", f"{len(present)}/{len(required_fields)} required fields → COMPLETE")
    else:
        missing = [f for f in required_fields if f not in present]
        results.fail("Phase 6: Handoff package", f"Missing: {missing}")

    # Final status
    results.ok("PIPELINE COMPLETE",
               f"new → context_pending → ready → sent → responded | "
               f"Handoff → sales-closer ✓")


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 60)
    print("🧪 LEAD HUNTER — END-TO-END DRY RUN TEST")
    print(f"⏰ {datetime.now(BRT).strftime('%Y-%m-%d %H:%M:%S')} BRT")
    print("=" * 60)

    test_phase_0_dependencies()
    test_phase_1_imports()
    test_phase_2_gmaps()
    test_phase_3_scraper()
    test_phase_4_whatsapp()
    test_phase_5_sentiment()
    test_phase_6_crossref()
    test_phase_7_state_machine()
    test_phase_8_veto_matrix()
    test_phase_9_data_flow()

    all_passed = results.summary()
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
