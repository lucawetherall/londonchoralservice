#!/usr/bin/env python3
"""Tests for scripts/ads/standing_approvals.py and data/standing-approvals.yml (owner decision D1, 31 Oct 2026).
The Google Ads client, Search Console, git and gh are all fakes; nothing contacts Google or GitHub, and every
file the script reads or writes is a temp copy."""
import contextlib, datetime, io, json, os, re, shutil, sys, tempfile
from pathlib import Path
from types import SimpleNamespace as NS
from zoneinfo import ZoneInfo

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "ads"))
import ads_log  # noqa: E402
import standing_approvals as sa  # noqa: E402

XMAS, FUNERAL, WEDDING = 24295921372, 23735776277, 23739971001
NOW = datetime.datetime(2026, 11, 2, 9, 0, tzinfo=ZoneInfo("Europe/London"))
OWNER_TYPES = {"CAMPAIGN_BUDGET", "SEARCH_PARTNERS_OPT_IN", "MAXIMIZE_CONVERSIONS_OPT_IN", "MAXIMIZE_CLICKS_OPT_IN",
               "LEAD_FORM_ASSET", "DYNAMIC_IMAGE_EXTENSION_OPT_IN", "USE_BROAD_MATCH_KEYWORD"}
TABLE = "| Date (Europe/London) | Resource | Field | Current → New | Reason | Script |\n|---|---|---|---|---|---|\n"
FILES = {
    "logs/ads-changes.md": "# Google Ads change log\n\n" + TABLE + "| 2026-10-26 10:00 | old | x | a → b | r | `s` |\n",
    "logs/gsc-changes.md": "# Search Console change log\n\n" + TABLE + "| 2026-10-31 | old | x | a → b | r | s |\n",
    "docs/MANUAL-ACTIONS-ARCHIVE.md": ("# Archive\n\n## 12. SERP baseline\n\nIntro.\n\n"
                                       "**Weekly review, 2026-10-26 (Search Console):** 55 clicks.\n\n---\n\n"
                                       "## 13. Next\n\nBody.\n"),
    "llms.txt": "# The London Choral Service\n\n> Content last updated: 26 October 2026. 60 music guides available.\n",
    "sitemap.xml": "<urlset><url><lastmod>2026-10-01</lastmod></url><url><lastmod>2026-10-31</lastmod></url></urlset>\n",
    "scripts/ads/ads_log.py": "",
}
REPORT = ("== 6. Search Console\n   x\n\n== 7. Search Console coverage\n"
          "   https://londonchoralservice.com/sitemap_index.xml · submitted 2026-10-24 · last read by Google 2026-10-26\n"
          "   https://londonchoralservice.com/sitemap.xml · submitted 2026-09-27 · last read by Google 2026-10-10"
          "  !STALE: resubmit\n   live sitemap.xml lists 177 URLs\n\n== 8. Next\n   y\n")


def fixture_repo():
    d = Path(tempfile.mkdtemp())
    for rel, text in FILES.items():
        (d / rel).parent.mkdir(parents=True, exist_ok=True)
        (d / rel).write_text(text, encoding="utf-8")
    (d / ".git").mkdir()
    ads_log.TEST_LOG_ROOTS.append(d)
    return d


def snapshot(d):
    return {str(p.relative_to(d)): p.read_text() for p in d.rglob("*") if p.is_file()}


class GoogleAdsException(Exception):
    def __init__(self, msg):
        super().__init__(msg)
        self.failure = NS(errors=[NS(error_code="error", message=msg)])


class FakeAds:
    def __init__(self, existing=None, own=None, recs=None, refuse_types=(), refuse_negatives=False):
        self.existing = existing or {}           # cid -> [(text, match)]
        self.own = own or {}                     # cid -> [(text, match)]
        self.recs = recs or []                   # [(type, campaign id or "", dismissed)]
        self.refuse_types, self.refuse_negatives = set(refuse_types), refuse_negatives
        self.mutations, self.dismissals, self.searches = [], [], []
        self.enums = NS(KeywordMatchTypeEnum={"BROAD": "BROAD", "PHRASE": "PHRASE", "EXACT": "EXACT"})

    def search(self, customer_id, query):
        self.searches.append(query)
        cid = int(m.group(1)) if (m := re.search(r"campaign\.id = (\d+)", query)) else None
        kw = lambda t, mt: NS(keyword=NS(text=t, match_type=NS(name=mt)))
        if "FROM campaign_criterion" in query:
            return [NS(campaign_criterion=kw(t, mt)) for t, mt in self.existing.get(cid, [])]
        if "FROM ad_group_criterion" in query:
            return [NS(ad_group_criterion=kw(t, mt)) for t, mt in self.own.get(cid, [])]
        if "FROM campaign" in query:
            return [NS(campaign=NS(name=sa.budget_cap.KNOWN_CAMPAIGNS[str(cid)]))]
        if "FROM recommendation" in query:
            return [NS(recommendation=NS(type_=NS(name=t), dismissed=dis,
                                         campaign=f"customers/1/campaigns/{c}" if c else "",
                                         resource_name=f"customers/1/recommendations/{t}-{c}"))
                    for t, c, dis in self.recs]
        raise AssertionError(query)

    def mutate(self, request):
        self.mutations.append(request)
        if self.refuse_negatives and not request.validate_only:
            raise GoogleAdsException("refused")

    def dismiss_recommendation(self, request):
        kinds = {op.resource_name.split("/")[-1].split("-")[0] for op in request.operations}
        assert len(kinds) == 1, f"a request mixing types: {kinds}"
        if kinds & self.refuse_types:
            raise GoogleAdsException("refused")
        self.dismissals.append(request)

    def get_service(self, name):
        if name == "GoogleAdsService":
            return NS(search=self.search, mutate=self.mutate, campaign_path=lambda c, i: f"customers/{c}/campaigns/{i}")
        assert name == "RecommendationService", f"the script must not use {name}"
        return NS(dismiss_recommendation=self.dismiss_recommendation)

    def get_type(self, name):
        if name == "MutateGoogleAdsRequest":
            return NS(customer_id=None, mutate_operations=[], validate_only=None)
        if name == "MutateOperation":
            return NS(campaign_criterion_operation=NS(create=NS(campaign=None, negative=None,
                                                                keyword=NS(text=None, match_type=None))))
        if name == "DismissRecommendationRequest":
            return NS(customer_id=None, operations=[], DismissRecommendationOperation=lambda: NS(resource_name=None))
        raise AssertionError(f"the script must not build a {name}")


class FakeGit:
    """git and gh: records each call; `worktree add` copies the fixture repo, as origin/main would be."""

    def __init__(self, origin, auto_merge=True, checks=(0,)):
        self.origin, self.calls, self.auto_merge, self.checks = origin, [], auto_merge, list(checks)
        self.home = Path(tempfile.mkdtemp())
        ads_log.TEST_LOG_ROOTS.append(self.home)

    def __call__(self, args, cwd=None):
        assert isinstance(args, list) and args[0] in ("git", "gh"), args
        self.calls.append(args)
        a = " ".join(args)
        if "--git-common-dir" in a:
            return 0, str(self.home / ".git")
        if "rev-parse --verify" in a:
            return 1, ""
        if "ls-remote" in a:
            return 0, ""
        if "worktree add" in a:
            shutil.copytree(self.origin, args[args.index("-b") + 2])
            return 0, ""
        if a.startswith("gh pr create"):
            return 0, "https://github.com/lucawetherall/londonchoralservice/pull/999"
        if a.startswith("gh pr merge") and "--auto" in a:
            return (0, "") if self.auto_merge else (1, "auto-merge is not allowed")
        if a.startswith("gh pr checks"):
            return self.checks.pop(0), "pending" if self.checks else "pass"
        return 0, ""

    def wt(self):
        add = next(c for c in self.calls if c[1:4] == ["-C", str(self.home), "worktree"] and c[4] == "add")
        return Path(add[add.index("-b") + 2])


def refuse_git(args, cwd=None):
    raise AssertionError(f"the default run ran {args}")


class FakeGsc:
    def __init__(self):
        self.puts = []

    def get(self, url):
        return NS(status_code=200, ok=True, json=lambda: {"lastSubmitted": "2026-09-27T10:00:00Z",
                                                           "lastDownloaded": "2026-10-10T10:00:00Z"})

    def put(self, url):
        self.puts.append(url)
        return NS(ok=True, status_code=204, content=b"")


def write_input(**kw):
    data = {"date": "2026-11-02", "negatives": [], "hiring_terms": ["carol singers london"], "manual_line": None}
    data.update(kw)
    f = Path(tempfile.mkdtemp()) / "standing.json"
    f.write_text(json.dumps(data))
    return str(f)


def write_report(text=REPORT):
    f = Path(tempfile.mkdtemp()) / "2026-11-02.txt"
    f.write_text(text)
    return str(f)


def run(argv, ads, git=refuse_git, gsc=None, repo=None):
    saved = sa.ROOT
    sa.ROOT = repo or fixture_repo()
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out):
            code = sa.main(argv, client=ads, run=git, gsc=gsc, now=NOW, sleep=lambda s: None)
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else (print(e.code, file=out) or 1)
    finally:
        sa.ROOT = saved
    return code, out.getvalue()


NEG = {"campaign_id": XMAS, "text": "jingle belles", "match": "PHRASE", "blocks": "the jingle belles"}


# ---------------------------------------------------------------- the rules file

def test_the_yml_names_exactly_the_five_classes_and_no_budget_class():
    rules = yaml.safe_load((ROOT / "data" / "standing-approvals.yml").read_text())
    assert list(rules["classes"]) == ["negatives", "dismiss_recommendations", "manual_actions_line",
                                      "sitemap_resubmit", "llms_date"]
    assert [c["id"] for c in rules["classes"].values()] == list("abcde")
    for name, c in rules["classes"].items():
        assert c["rule"].strip(), name
        assert not re.search(r"budget|bid|pause|status|ad copy|site copy", name, re.I), name
    never = " ".join(rules["never"].split())
    assert never.startswith("BUDGETS ARE NEVER A STANDING CLASS.") and "any rise in ad spend needs his approval" in never
    for word in ("budget", "bid", "pause", "keyword status", "ad copy", "site copy"):
        assert word in never, word
    assert sa.load_rules()["classes"].keys() == rules["classes"].keys()


def test_the_ruled_out_types_are_the_owners_and_cover_26_october():
    rules = sa.load_rules()
    types = set(rules["classes"]["dismiss_recommendations"]["types"])
    assert types == OWNER_TYPES, types
    log = (ROOT / "logs" / "ads-changes.md").read_text()
    oct26 = set(re.findall(r"^\| 2026-10-26 [^|]*\| [^|]*recommendation ([A-Z_]+) \| status \| open → dismissed",
                           log, re.M))
    assert oct26, "the 26 Oct dismissals are no longer in the log"
    # RESPONSIVE_SEARCH_AD was a one-off (that week's second ad already existed), not a type the owner rules out
    assert oct26 - {"RESPONSIVE_SEARCH_AD"} <= types and "RESPONSIVE_SEARCH_AD" not in types, oct26


def test_the_script_has_no_budget_bid_status_or_ad_code():
    src = (ROOT / "scripts" / "ads" / "standing_approvals.py").read_text()
    doc = " ".join(sa.__doc__.split())
    assert "BUDGETS ARE NEVER A STANDING CLASS" in doc and "any rise in ad spend needs his approval" in doc
    code = src.split('"""', 2)[2]
    for banned in ("CampaignBudget", "mutate_campaigns", "CampaignService", "AdGroupCriterionService",
                   "AdGroupAdService", "cpc_bid", "amount_micros", "set_budget", "set_campaign_status",
                   "ApplyRecommendation", "ad_group_criterion_operation", "campaign_operation"):
        assert banned not in code, banned


# ---------------------------------------------------------------- (a) negatives

def test_a_negative_that_blocks_a_hiring_term_is_refused():
    rules = sa.load_rules()
    inp = sa.load_input(write_input(negatives=[
        {"campaign_id": XMAS, "text": "london", "match": "BROAD", "blocks": "london jingle belles"},
        {"campaign_id": XMAS, "text": "carol", "match": "PHRASE", "blocks": "carol of the bells lyrics"},  # protected
        NEG]), NOW.date())
    ok, refused = sa.check_negatives(inp, rules)
    assert [o[1] for o in ok] == ["jingle belles"], ok
    assert len(refused) == 2 and all("would block the hiring search" in why for _, why in refused), refused
    ads = FakeAds()
    code, out = run(["--input", write_input(negatives=inp["negatives"]), "--report", write_report()], ads)
    assert code == 0 and 'would block the hiring search "carol singers london"' in out, out
    texts = [op.campaign_criterion_operation.create.keyword.text for r in ads.mutations for op in r.mutate_operations]
    assert texts == ["jingle belles"], texts


def test_other_refusals():
    rules = sa.load_rules()
    bad = [dict(NEG, match="BROAD_MATCH"), dict(NEG, campaign_id=111), dict(NEG, blocks="jingle bells"),
           dict(NEG, text="a|b"), dict(NEG, extra=1), dict(NEG, text="one two three four five six seven eight nine ten eleven")]
    ok, refused = sa.check_negatives(sa.load_input(write_input(negatives=bad), NOW.date()), rules)
    assert ok == [] and len(refused) == len(bad), refused
    whys = " ".join(w for _, w in refused)
    for bit in ("match type", "known campaigns", "does not block its own search term", "unknown fields"):
        assert bit in whys, bit
    too_many = [dict(NEG, text=f"act {i}", blocks=f"act {i}") for i in range(11)]
    code, out = run(["--input", write_input(negatives=too_many)], FakeAds())
    assert code != 0 and "more than 10" in out, out
    code, out = run(["--input", write_input(date="2026-10-01")], FakeAds())
    assert code != 0 and "within the last week" in out, out


def test_existing_negatives_and_ones_blocking_the_campaigns_keywords_are_skipped():
    ads = FakeAds(existing={XMAS: [("jingle belles", "PHRASE")]}, own={FUNERAL: [("funeral ikos choir", "PHRASE")]})
    negs = [NEG, {"campaign_id": FUNERAL, "text": "ikos", "match": "BROAD", "blocks": "ikos tavener"}]
    code, out = run(["--input", write_input(negatives=negs, hiring_terms=["hire a choir"]), "--report", write_report()],
                    ads)
    assert code == 0 and "already there" in out and 'own keyword "funeral ikos choir"' in out, out
    assert ads.mutations == [], "nothing new, so nothing sent"


# ---------------------------------------------------------------- (b) recommendations

def test_an_unknown_recommendation_type_is_never_dismissed():
    rules = sa.load_rules()
    for kind in ("KEYWORD", "RESPONSIVE_SEARCH_AD", "UNKNOWN", "TARGET_CPA_OPT_IN", "SITELINK_ASSET",
                 "MOVE_UNUSED_BUDGET", "CAMPAIGN_BUDGETS", "RAISE_TARGET_CPA"):
        assert sa.ruled_out(kind, rules) is None, kind
    assert sa.ruled_out("AI_MAX_OPT_IN", rules)  # a future AI Max type
    recs = [("KEYWORD", XMAS, False), ("RESPONSIVE_SEARCH_AD", WEDDING, False), ("CAMPAIGN_BUDGET", XMAS, False),
            ("SEARCH_PARTNERS_OPT_IN", FUNERAL, True), ("SEARCH_PARTNERS_OPT_IN", 999, False),
            ("DYNAMIC_IMAGE_EXTENSION_OPT_IN", "", False), ("TARGET_CPA_OPT_IN", FUNERAL, False)]
    ads = FakeAds(recs=recs)
    assert [k for _, k, _ in sa.plan_dismissals(ads, rules)] == ["DYNAMIC_IMAGE_EXTENSION_OPT_IN", "CAMPAIGN_BUDGET"]
    git = FakeGit(fixture_repo())
    code, out = run(["--input", write_input(), "--report", write_report(), "--apply"], ads, git=git, gsc=FakeGsc())
    assert code == 0, out
    sent = sorted(op.resource_name.split("/")[-1].split("-")[0] for r in ads.dismissals for op in r.operations)
    assert sent == ["CAMPAIGN_BUDGET", "DYNAMIC_IMAGE_EXTENSION_OPT_IN"], sent
    assert len(ads.dismissals) == 2  # one request per type


# ---------------------------------------------------------------- the default run

def test_the_default_run_changes_nothing_and_runs_no_git():
    repo = fixture_repo()
    before = snapshot(repo)
    ads = FakeAds(recs=[("CAMPAIGN_BUDGET", XMAS, False)])
    code, out = run(["--input", write_input(negatives=[NEG], manual_line="61 clicks."), "--report", write_report()],
                    ads, git=refuse_git, repo=repo)
    assert code == 0, out
    assert ads.mutations and all(r.validate_only is True for r in ads.mutations)
    assert ads.dismissals == []
    assert snapshot(repo) == before
    for bit in ("VALIDATE ONLY", '+1: "jingle belles"', "CAMPAIGN_BUDGET", "append to §12: **Weekly review, 2026-11-02:** 61 clicks.",
                "resubmit sitemap.xml", "26 October 2026 → 31 October 2026", "Nothing was changed"):
        assert bit in out, (bit, out)
    assert "sitemap_index.xml: section 7" not in out


def test_a_tilde_in_the_report_and_input_paths_is_expanded():
    """The Monday prompt passes ~/lcs-private/... paths; a quoted ~ must not silently skip section 7 (31 Oct 2026)."""
    home = Path(tempfile.mkdtemp())
    (home / "r").mkdir()
    (home / "r" / "2026-11-02.txt").write_text(REPORT)
    inp = Path(write_input())
    (home / "in.json").write_text(inp.read_text())
    saved = os.environ.get("HOME")
    os.environ["HOME"] = str(home)
    try:
        code, out = run(["--input", "~/in.json", "--report", "~/r/2026-11-02.txt"], FakeAds(), git=refuse_git)
    finally:
        os.environ["HOME"] = saved
    assert code == 0, out
    assert "no saved report" not in out, out
    assert "resubmit sitemap.xml" in out, out


def test_a_google_refusal_in_validation_stops_the_run():
    ads = FakeAds()
    ads.mutate = lambda request: (_ for _ in ()).throw(GoogleAdsException("bad keyword"))
    code, out = run(["--input", write_input(negatives=[NEG]), "--report", write_report(), "--apply"], ads,
                    git=refuse_git)
    assert code == 1 and "Google refused the negatives as written" in out, out


# ---------------------------------------------------------------- --apply

def test_apply_does_every_class_logs_and_merges():
    origin = fixture_repo()
    git, gsc = FakeGit(origin), FakeGsc()
    ads = FakeAds(recs=[("CAMPAIGN_BUDGET", XMAS, False), ("SEARCH_PARTNERS_OPT_IN", FUNERAL, False)])
    code, out = run(["--input", write_input(negatives=[NEG], manual_line="61 clicks (was 55)."),
                     "--report", write_report(), "--apply"], ads, git=git, gsc=gsc)
    assert code == 0, out
    assert [r.validate_only for r in ads.mutations] == [True, True, False]  # validate, re-validate, apply
    wt = git.wt()
    assert wt.parent == git.home / ".claude" / "worktrees" and wt.name == "standing-2026-11-02"
    log = (wt / "logs" / "ads-changes.md").read_text().splitlines()
    rows = [ln for ln in log if ln.startswith("| 2026-11-02 09:00")]
    assert len(rows) == 3, rows
    assert rows[0].startswith('| 2026-11-02 09:00 | campaign "Christmas carol singers – events 2026" (24295921372) | '
                              'negative keywords | 0 negatives → +1: "jingle belles" | NOT A BUYER'), rows[0]
    assert "recommendation CAMPAIGN_BUDGET | status | open → dismissed" in rows[1]
    assert log.index(rows[2]) + 1 == log.index("| 2026-10-26 10:00 | old | x | a → b | r | `s` |")  # newest first
    gsc_log = (wt / "logs" / "gsc-changes.md").read_text()
    assert ("| 2026-11-02 09:00 | sitemap https://londonchoralservice.com/sitemap.xml | submission | submitted "
            "2026-09-27, last read 2026-10-10 → resubmitted |") in gsc_log
    assert len(gsc.puts) == 1 and "sitemap.xml" in gsc.puts[0] and "sitemap_index" not in gsc.puts[0]
    archive = (wt / "docs" / "MANUAL-ACTIONS-ARCHIVE.md").read_text()
    assert ("**Weekly review, 2026-10-26 (Search Console):** 55 clicks.\n\n**Weekly review, 2026-11-02:** "
            "61 clicks (was 55).\n\n---\n\n## 13.") in archive
    assert "Content last updated: 31 October 2026." in (wt / "llms.txt").read_text()
    cmds = [" ".join(c[:4]) for c in git.calls]
    commit = next(c for c in git.calls if "commit" in c)
    msg = commit[commit.index("-m") + 1]
    assert msg.startswith("chore(ads): standing approvals from the Monday review 2026-11-02\n")
    assert msg.rstrip().endswith("Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>")
    create = next(c for c in git.calls if c[:3] == ["gh", "pr", "create"])
    assert create[create.index("--body") + 1].rstrip().endswith("🤖 Generated with [Claude Code](https://claude.com/claude-code)")
    assert any(c[:3] == ["gh", "pr", "merge"] and "--auto" in c for c in git.calls)
    assert any(c[3:5] == ["worktree", "remove"] for c in git.calls)
    assert cmds[0].endswith(" fetch") and cmds.index(f"git -C {git.home} worktree") > 0  # fetch comes first
    added = next(c for c in git.calls if c[3:4] == ["add"] and "--" in c)
    assert sorted(added[added.index("--") + 1:]) == ["docs/MANUAL-ACTIONS-ARCHIVE.md", "llms.txt",
                                                     "logs/ads-changes.md", "logs/gsc-changes.md"]
    assert "PR: https://github.com/lucawetherall/londonchoralservice/pull/999" in out
    assert snapshot(origin) == snapshot(fixture_repo()), "the source checkout is never edited"


def test_apply_logs_only_what_succeeded():
    git = FakeGit(fixture_repo())
    ads = FakeAds(recs=[("CAMPAIGN_BUDGET", XMAS, False), ("SEARCH_PARTNERS_OPT_IN", FUNERAL, False),
                        ("USE_BROAD_MATCH_KEYWORD", WEDDING, False)], refuse_types={"SEARCH_PARTNERS_OPT_IN"})
    gsc = FakeGsc()
    code, out = run(["--input", write_input(negatives=[NEG], manual_line="61 clicks."), "--report", write_report(),
                     "--apply"], ads, git=git, gsc=gsc)
    assert code == 1 and "FAILED: dismissing SEARCH_PARTNERS_OPT_IN" in out, out
    wt = git.wt()
    log = (wt / "logs" / "ads-changes.md").read_text()
    assert '+1: "jingle belles"' in log and "recommendation CAMPAIGN_BUDGET" in log
    assert "SEARCH_PARTNERS_OPT_IN" not in log and "USE_BROAD_MATCH_KEYWORD" not in log
    assert [op.resource_name for r in ads.dismissals for op in r.operations] == [
        f"customers/1/recommendations/CAMPAIGN_BUDGET-{XMAS}"]  # nothing after the refusal
    assert gsc.puts == [] and (wt / "logs" / "gsc-changes.md").read_text() == FILES["logs/gsc-changes.md"]
    assert (wt / "llms.txt").read_text() == FILES["llms.txt"]
    assert (wt / "docs" / "MANUAL-ACTIONS-ARCHIVE.md").read_text() == FILES["docs/MANUAL-ACTIONS-ARCHIVE.md"]
    assert any("commit" in c for c in git.calls)  # what was applied is still committed and logged


def test_a_failure_before_anything_applied_makes_no_worktree():
    git = FakeGit(fixture_repo())
    ads = FakeAds(refuse_negatives=True)
    code, out = run(["--input", write_input(negatives=[NEG]), "--report", write_report(), "--apply"], ads, git=git,
                    gsc=FakeGsc())
    assert code == 1 and "nothing was applied" in out, out
    assert not any("worktree" in c for c in git.calls)


def test_the_merge_waits_for_checks_when_auto_merge_is_refused():
    git = FakeGit(fixture_repo(), auto_merge=False, checks=(8, 8, 0))
    code, out = run(["--input", write_input(manual_line="61 clicks."), "--report", write_report(REPORT.replace("!STALE", "")),
                     "--apply"], FakeAds(), git=git)
    assert code == 0 and "merged (squash)" in out, out
    assert sum(c[:3] == ["gh", "pr", "checks"] for c in git.calls) == 3
    assert git.calls[-2][:3] == ["gh", "pr", "merge"] and "--auto" not in git.calls[-2]


def test_nothing_to_do_opens_no_pr():
    repo = fixture_repo()
    (repo / "llms.txt").write_text(FILES["llms.txt"].replace("26 October", "31 October"))
    git = FakeGit(repo)
    code, out = run(["--input", write_input(manual_line="**Weekly review, 2026-10-26 (x):** old"), "--report",
                     write_report(REPORT.replace("!STALE", "")), "--apply"], FakeAds(), git=git)
    assert code != 0 and "dated otherwise" in out, out  # a line for another date is refused
    code, out = run(["--input", write_input(), "--report", write_report(REPORT.replace("!STALE", "")), "--apply"],
                    FakeAds(), git=git, repo=repo)
    assert code == 0 and "Nothing to apply or log." in out, out
    assert not any(c[:3] == ["gh", "pr", "create"] for c in git.calls)
    assert any(c[3:5] == ["branch", "-D"] for c in git.calls)


def test_pure_helpers():
    rules = sa.load_rules()
    text = FILES["docs/MANUAL-ACTIONS-ARCHIVE.md"]
    assert sa.with_manual_line(text, "## 12.", "**Weekly review, 2026-10-26:** x", datetime.date(2026, 10, 26)) is None
    for bad in ("a@b.com wrote", "a | b", ""):
        try:
            sa.manual_entry(bad, datetime.date(2026, 11, 2))
            raise AssertionError(bad)
        except SystemExit:
            pass
    assert sa.stale_sitemaps(REPORT, rules) == ["sitemap.xml"]
    assert sa.stale_sitemaps(REPORT.replace("== 7.", "== 7b."), rules) == []
    new, old, newest = sa.llms_update(FILES["llms.txt"], FILES["sitemap.xml"], rules)
    assert (old, newest) == ("26 October 2026", "31 October 2026") and "updated: 31 October 2026. 60" in new
    assert sa.llms_update(new, FILES["sitemap.xml"], rules)[0] is None


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
