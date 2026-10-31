#!/usr/bin/env python3
"""Tests for scripts/ads/validate_proposal.py: the cap is refused before Google is called, "enabled" and --apply
are refused, and every mutate request it sends carries validate_only=True. A fake Google Ads client; never
contacts Google, never writes the change log."""
import contextlib, datetime, io, os, subprocess, sys
from types import SimpleNamespace as NS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "ads"))
import validate_proposal as vp  # noqa: E402

XMAS = "24295921372"
WHEN = datetime.datetime(2026, 11, 2, 9, 0)


class Req(NS):
    def __init__(self):
        super().__init__(operations=[], customer_id=None, validate_only=None)


class FakeClient:
    """Answers both scripts' searches; records every mutate request."""

    def __init__(self, amount=5_000_000, status="ENABLED"):
        self.amount, self.status, self.searches, self.mutations = amount, status, [], []
        self.enums = NS(CampaignStatusEnum={"PAUSED": "PAUSED", "ENABLED": "ENABLED"})

    def row(self):
        return NS(campaign=NS(id=int(XMAS), name="Christmas carol singers – events 2026", status=NS(name=self.status)),
                  campaign_budget=NS(resource_name="customers/1/campaignBudgets/9", amount_micros=self.amount,
                                     explicitly_shared=False))

    def get_service(self, name):
        if name == "GoogleAdsService":
            return NS(search=lambda customer_id, query: self.searches.append(query) or [self.row()])
        if name == "CampaignBudgetService":
            return NS(mutate_campaign_budgets=lambda request: self.mutations.append(request))
        if name == "CampaignService":
            return NS(mutate_campaigns=lambda request: self.mutations.append(request),
                      campaign_path=lambda c, i: f"customers/{c}/campaigns/{i}")
        raise AssertionError(f"unexpected service {name}")

    def get_type(self, name):
        if name in ("CampaignBudgetOperation", "CampaignOperation"):
            return NS(update=NS(resource_name=None, amount_micros=None, status=None), update_mask=NS(paths=[]))
        assert name in ("MutateCampaignBudgetsRequest", "MutateCampaignsRequest"), name
        return Req()


def run(argv, client):
    out, err = io.StringIO(), io.StringIO()
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = vp.main(argv, client=client, now=WHEN)
    except SystemExit as e:
        code = e.code
    return code, out.getvalue() + err.getvalue()


def test_a_budget_above_the_cap_is_refused_before_google():
    for argv in (["budget", XMAS, "8.01", "--reason", "x"],          # the Christmas cap is £8 to 13 Dec
                 ["budget", "23735776277", "5.01", "--reason", "x"],  # £5 for everyone else
                 ["budget", XMAS, "0", "--reason", "x"]):
        client = FakeClient()
        code, out = run(argv, client)
        assert code not in (0, None), (argv, out)
        assert client.searches == [] and client.mutations == [], argv


def test_enabled_and_apply_are_refused():
    for argv in (["status", XMAS, "enabled", "--reason", "x"],
                 ["budget", XMAS, "4.50", "--reason", "x", "--apply"],
                 ["status", XMAS, "paused", "--reason", "x", "--apply"],
                 ["budget", XMAS, "4.50", "--apply", "--reason", "x"],
                 ["budget", "wedding-leads", "4.50", "--reason", "x"],   # ids only
                 ["budget", XMAS, "4.50", "--reason", "a|b"]):
        client = FakeClient()
        code, _ = run(argv, client)
        assert code == 2 and client.searches == [] and client.mutations == [], argv


def test_the_script_itself_refuses_apply_as_an_unknown_argument():
    r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "ads", "validate_proposal.py"),
                        "budget", XMAS, "4.50", "--reason", "x", "--apply"], capture_output=True, text=True)
    assert r.returncode == 2 and "unrecognized arguments: --apply" in r.stderr, r.stderr
    src = open(os.path.join(ROOT, "scripts", "ads", "validate_proposal.py"), encoding="utf-8").read()
    assert "apply=True" not in src and 'add_argument("--apply"' not in src


def test_validate_only_is_always_set():
    cases = [(["budget", XMAS, "4.50", "--reason", "quiet week"], FakeClient(), "£5.00 → £4.50"),
             (["budget", XMAS, "8", "--reason", "x"], FakeClient(), "£5.00 → £8.00"),
             (["budget", XMAS, "4.50", "--reason=--apply"], FakeClient(), "£5.00 → £4.50"),
             (["status", XMAS, "paused", "--reason", "spend guard"], FakeClient(), "status: enabled → paused")]
    for argv, client, line in cases:
        code, out = run(argv, client)
        assert code == 0 and "VALIDATE ONLY" in out and line in out and "APPLYING" not in out, (argv, out)
        assert client.mutations and all(r.validate_only is True for r in client.mutations), argv


def test_nothing_to_change_sends_nothing():
    for argv, client in ((["budget", XMAS, "5.00", "--reason", "x"], FakeClient()),
                         (["status", XMAS, "paused", "--reason", "x"], FakeClient(status="PAUSED"))):
        code, out = run(argv, client)
        assert code == 0 and client.mutations == [], (argv, out)


def test_a_rejection_exits_non_zero():
    class GoogleAdsException(Exception):
        failure = NS(errors=[NS(error_code="budget_error", message="too low")])

    client = FakeClient()

    def refuse(request):
        assert request.validate_only is True
        raise GoogleAdsException()
    client.get_service = (lambda orig: lambda name: NS(mutate_campaign_budgets=refuse)
                          if name == "CampaignBudgetService" else orig(name))(client.get_service)
    code, out = run(["budget", XMAS, "0.01", "--reason", "x"], client)
    assert code == 1 and "REJECTED" in out, out


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
