#!/usr/bin/env python3
"""Tests for scripts/ads/set_budget.py and scripts/ads/ads_log.py. A fake Google Ads client; never contacts Google.
The change log is a temp copy (LCS_ADS_LOG)."""
import contextlib, datetime, io, os, subprocess, sys, tempfile
from pathlib import Path
from types import SimpleNamespace as NS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "ads"))
import ads_log  # noqa: E402
import set_budget as sb  # noqa: E402

LOG_HEAD = ("# Google Ads change log\n\n| Date (Europe/London) | Resource | Field | Current → New | Reason | Script |\n"
            "|---|---|---|---|---|---|\n| 2026-09-01 10:00 | old | x | a → b | r | `s` |\n")


class Req(NS):
    def __init__(self):
        super().__init__(operations=[], customer_id=None, validate_only=None)


class FakeClient:
    def __init__(self, rows, fail=None):
        self.rows, self.fail, self.searches, self.mutations = rows, fail, [], []

    def get_service(self, name):
        if name == "GoogleAdsService":
            return NS(search=lambda customer_id, query: self.searches.append(query) or list(self.rows))
        assert name == "CampaignBudgetService", name
        return NS(mutate_campaign_budgets=self.mutate)

    def get_type(self, name):
        if name == "CampaignBudgetOperation":
            return NS(update=NS(resource_name=None, amount_micros=None), update_mask=NS(paths=[]))
        assert name == "MutateCampaignBudgetsRequest", name
        return Req()

    def mutate(self, request):
        if self.fail:
            raise self.fail
        self.mutations.append(request)


def campaign(amount=3_000_000, shared=False, cid=111, name="funeral expert campaign"):
    return NS(campaign=NS(id=cid, name=name),
              campaign_budget=NS(resource_name=f"customers/1/campaignBudgets/{cid}", amount_micros=amount,
                                 explicitly_shared=shared))


def temp_log():
    d = tempfile.mkdtemp()
    path = Path(d) / "ads-changes.md"
    path.write_text(LOG_HEAD)
    os.environ["LCS_ADS_LOG"] = str(path)
    return path


def run(argv, client):
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out):
            code = sb.main(argv, client=client, now=datetime.datetime(2026, 10, 1, 9, 30))
    except SystemExit as e:
        return e.code, out.getvalue()
    return code, out.getvalue()


def test_the_cap_is_checked_before_google_is_called():
    temp_log()
    for bad in ("5.01", "6", "100", "0", "0.00", "-1", "4.505", "£4", "4,50", "", "1e3"):
        client = FakeClient([campaign()])
        code, _ = run(["111", bad], client)
        assert code not in (0, None), bad
        assert client.searches == [] and client.mutations == [], bad


def test_validate_only_is_the_default_and_explicit():
    log = temp_log()
    for extra in ([], ["--validate-only"]):
        client = FakeClient([campaign()])
        code, out = run(["111", "4.50", *extra], client)
        assert code == 0 and "VALIDATE ONLY" in out and "£3.00 → £4.50" in out, out
        req = client.mutations[0]
        assert req.validate_only is True and req.operations[0].update.amount_micros == 4_500_000
        assert req.operations[0].update_mask.paths == ["amount_micros"]
    assert log.read_text() == LOG_HEAD


def test_apply_changes_and_logs_to_the_override():
    log = temp_log()
    client = FakeClient([campaign()])
    code, out = run(["111", "5", "--apply", "--reason", "Christmas push"], client)
    assert code == 0 and "APPLYING" in out, out
    assert client.mutations[0].validate_only is False
    lines = log.read_text().splitlines()
    assert lines[4] == ('| 2026-10-01 09:30 | campaign "funeral expert campaign" (111) budget | daily budget | '
                        '£3.00 → £5.00 | Christmas push | `scripts/ads/set_budget.py` |'), lines[4]
    assert lines[5].startswith("| 2026-09-01")  # newest first


def test_both_modes_together_are_refused():
    temp_log()
    client = FakeClient([campaign()])
    code, _ = run(["111", "4", "--apply", "--validate-only"], client)
    assert code == 2 and client.searches == []


def test_shared_budget_missing_or_ambiguous_campaign_refused():
    temp_log()
    for rows in ([campaign(shared=True)], [], [campaign(), campaign(cid=222)]):
        client = FakeClient(rows)
        code, _ = run(["111", "4", "--apply"], client)
        assert code not in (0, None) and client.mutations == [], rows


def test_apply_needs_a_readable_log_before_anything_changes():
    d = tempfile.mkdtemp()
    os.environ["LCS_ADS_LOG"] = os.path.join(d, "missing.md")
    client = FakeClient([campaign()])
    code, _ = run(["111", "4", "--apply"], client)
    assert code not in (0, None) and client.searches == [] and client.mutations == []


def test_a_rejection_is_reported_and_nothing_logged():
    log = temp_log()

    class GoogleAdsException(Exception):
        failure = NS(errors=[NS(error_code="budget_error", message="too low")])
    client = FakeClient([campaign()], fail=GoogleAdsException())
    code, out = run(["111", "1", "--apply"], client)
    assert code == 1 and "REJECTED" in out and log.read_text() == LOG_HEAD


def test_campaign_by_name_is_quoted_and_odd_names_refused():
    temp_log()
    client = FakeClient([campaign()])
    code, _ = run(["funeral expert campaign", "4"], client)
    assert code == 0 and "campaign.name = 'funeral expert campaign'" in client.searches[0]
    for bad in ("x' OR '1'='1", "-x", "a;b", "a\nb"):
        client = FakeClient([campaign()])
        code, _ = run([bad, "4"], client)
        assert code == 2 and client.searches == [], bad


def test_log_path_default_and_override():
    saved = os.environ.pop("LCS_ADS_LOG", None)
    try:
        assert ads_log.log_path() == Path(ROOT) / "logs" / "ads-changes.md"
        os.environ["LCS_ADS_LOG"] = "/tmp/elsewhere.md"
        assert ads_log.log_path() == Path("/tmp/elsewhere.md")
    finally:
        os.environ.pop("LCS_ADS_LOG", None)
        if saved:
            os.environ["LCS_ADS_LOG"] = saved


def test_old_scripts_refuse_the_validate_only_flag():
    """The natural allowlist: a script that doesn't know --validate-only fails at argparse, before Google."""
    old = Path(ROOT) / "scripts" / "ads" / "add_negatives_2026_09_28.py"
    src = old.read_text()
    assert "--validate-only" not in src and "--apply" in src
    probe = ("import argparse, sys; p = argparse.ArgumentParser(); p.add_argument('--apply', action='store_true'); "
             "p.parse_args(['--validate-only'])")
    r = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True)
    assert r.returncode == 2 and "unrecognized arguments: --validate-only" in r.stderr


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted((n, f) for n, f in globals().items() if n.startswith("test_") and callable(f)):
        try:
            fn()
            print(f"PASS {name}")
        except Exception as ex:
            failures += 1
            import traceback
            traceback.print_exc()
            print(f"FAIL {name}: {type(ex).__name__}: {ex}")
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)
