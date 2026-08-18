#!/usr/bin/env python3
"""Tests for validate_competitor_claims.py. Stdlib only — run with: python3 tests/test_competitor_claims.py"""
import os, subprocess, sys, tempfile, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

YAML = """
vat_rate: 0.20
providers:
  test-provider:
    name: "Test Provider"
    pricing_url: "https://example.com/pricing"
    checked_date: "{date}"
    packages:
      soloist:
        price_ex_vat: 275
        source_quote: "Soloist: From £275 + VAT"
lcs_prices:
  soloist: 250
"""

def run_in_sandbox(yaml_text, page_html):
    """Copy the validator into a temp repo, run it, return (exit_code, output)."""
    tmp = tempfile.mkdtemp()
    try:
        os.makedirs(os.path.join(tmp, "data"))
        os.makedirs(os.path.join(tmp, "compare"))
        with open(os.path.join(tmp, "data", "competitor-pricing.yml"), "w") as f:
            f.write(yaml_text)
        with open(os.path.join(tmp, "compare", "x.html"), "w") as f:
            f.write(page_html)
        shutil.copy(os.path.join(ROOT, "validate_competitor_claims.py"), tmp)
        p = subprocess.run([sys.executable, "validate_competitor_claims.py"],
                           cwd=tmp, capture_output=True, text=True)
        return p.returncode, p.stdout + p.stderr
    finally:
        shutil.rmtree(tmp)

def test_sourced_figures_pass():
    code, out = run_in_sandbox(
        YAML.format(date="2026-08-18"),
        "<p>They charge &pound;275 plus VAT, or &pound;330. We charge &pound;250.</p>")
    assert code == 0, f"expected pass, got {code}: {out}"

def test_unsourced_figure_fails():
    code, out = run_in_sandbox(
        YAML.format(date="2026-08-18"),
        "<p>They charge &pound;999 plus VAT.</p>")
    assert code == 1, f"expected failure for unsourced £999, got {code}: {out}"
    assert "999" in out, f"error should name the offending figure: {out}"

def test_undeclared_sum_fails():
    """£550 is 275+275, but arithmetic alone must not make a figure acceptable."""
    code, out = run_in_sandbox(
        YAML.format(date="2026-08-18"),
        "<p>A soloist with an organist is &pound;550 plus VAT.</p>")
    assert code == 1, f"undeclared sum £550 must fail, got {code}: {out}"

def test_declared_derived_figure_passes():
    yaml_text = YAML.format(date="2026-08-18") + "derived_figures:\n  550: \"soloist + organist\"\n"
    code, out = run_in_sandbox(yaml_text, "<p>&pound;550 plus VAT.</p>")
    assert code == 0, f"declared derived figure should pass: {out}"

def test_stale_data_warns_but_passes():
    code, out = run_in_sandbox(
        YAML.format(date="2020-01-01"),
        "<p>They charge &pound;275 plus VAT.</p>")
    assert code == 0, f"stale data must warn, not fail: {out}"
    assert "STALE" in out, f"expected a staleness warning: {out}"

def test_no_compare_pages_is_fine():
    tmp = tempfile.mkdtemp()
    try:
        os.makedirs(os.path.join(tmp, "data"))
        with open(os.path.join(tmp, "data", "competitor-pricing.yml"), "w") as f:
            f.write(YAML.format(date="2026-08-18"))
        shutil.copy(os.path.join(ROOT, "validate_competitor_claims.py"), tmp)
        p = subprocess.run([sys.executable, "validate_competitor_claims.py"],
                           cwd=tmp, capture_output=True, text=True)
        assert p.returncode == 0, f"no compare/ pages should pass: {p.stdout}{p.stderr}"
    finally:
        shutil.rmtree(tmp)

if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except AssertionError as e:
                print(f"FAIL {name}: {e}")
                failures += 1
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)
