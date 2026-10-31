#!/usr/bin/env python3
"""Run the tests that need only the checkout: the pull-request check in .github/workflows/deploy-pages.yml.

Each file below passed in a clean venv with PyYAML alone and HOME pointed at an empty folder (no
credentials, network, Keychain or ~/lcs-private), in under 30 s. The workflow installs PyYAML and runs
this file; run it locally the same way before a pull request:

    python3 tests/run_ci_tests.py            # or .venv/bin/python

Left out on purpose (26 Oct 2026):
  - tests that need packages beyond PyYAML (pypdf for booking documents and singer invoices) or the repo's
    .venv: test_calendar_guard, test_cancel_contract, test_dashboard, test_events_cli, test_imap_draft,
    test_lcs_mcp, test_make_booking_docs, test_singer_invoices, test_singer_links, test_state_twins and
    test_weekly_proposals;
  - test_zoho_books_guard (passes, but takes over a minute).
Run those locally with the repo's .venv. A new test that needs only the checkout belongs in TESTS.
"""

import os
import subprocess
import sys
import time

TESTS = [
    "test_ad_attribution.py",
    "test_assistant_io.py",
    "test_brief.py",
    "test_check_history_names.py",
    "test_check_payments.py",
    "test_christmas_pages.py",
    "test_competitor_claims.py",
    "test_cwv.py",
    "test_design_markup.py",
    "test_economics.py",
    "test_enquiry_sources.py",
    "test_events_migrate.py",
    "test_goatcounter.py",
    "test_graph_site_links.py",
    "test_house_claims.py",
    "test_index_coverage.py",
    "test_lcs_events.py",
    "test_lcs_money.py",
    "test_lcs_owner.py",
    "test_lookup_ref.py",
    "test_mcp_bypass_guard.py",
    "test_money_report.py",
    "test_negative_match.py",
    "test_owner_confirm_guard.py",
    "test_pipeline.py",
    "test_prompt_allowlist.py",
    "test_register_generators.py",
    "test_review_log.py",
    "test_set_budget.py",
    "test_stage_site.py",
    "test_upload_bookings.py",
    "test_visit_counter.py",
    "test_weekly_review_archive.py",
    "test_weekly_review_snapshot.py",
    "test_zoho_guard.py",
]

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def main():
    start = time.time()
    for name in TESTS:
        t = time.time()
        r = subprocess.run([sys.executable, os.path.join(HERE, name)], cwd=ROOT)
        if r.returncode != 0:
            print(f"\nFAILED: tests/{name} (exit {r.returncode}); "
                  f"{TESTS.index(name)} of {len(TESTS)} passed before it", flush=True)
            return 1
        print(f"--- ok tests/{name} ({time.time() - t:.1f}s)", flush=True)
    print(f"\nall {len(TESTS)} test files passed in {time.time() - start:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
