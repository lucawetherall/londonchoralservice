#!/usr/bin/env python3
"""Apply the owner's standing approvals from the Monday review (owner decision D1, approved 31 Oct 2026).

The five classes and their rules are in data/standing-approvals.yml:
  (a) campaign negatives for NOT A BUYER search terms, never blocking a HIRING term;
  (b) dismissing open Google recommendations of the types the owner ruled out;
  (c) the dated "Weekly review" line at the end of section 12 of docs/MANUAL-ACTIONS-ARCHIVE.md;
  (d) a sitemap resubmission when section 7 of the saved Monday report says STALE;
  (e) llms.txt's "Content last updated" date, from the newest <lastmod> in sitemap.xml.

BUDGETS ARE NEVER A STANDING CLASS. The owner restated on 31 Oct 2026 that any rise in ad spend needs his
approval, and no budget, bid, pause, keyword status, ad copy or site copy change may be applied by this script.
It has no code for any of them: its only Google Ads writes are campaign negative keywords (create) and
recommendation dismissals.

Input: a JSON file the Monday dispatcher writes,
    {"date": "YYYY-MM-DD", "negatives": [{"campaign_id": int, "text": str, "match": "BROAD|PHRASE|EXACT",
     "blocks": "<the search term>"}], "hiring_terms": [str, ...], "manual_line": str|null}

Default run: shows what each class would do and has Google validate (a) (validate_only=True). Google has no
validate-only mode for a dismissal, so (b) lists exactly the recommendations --apply would dismiss. Changes
nothing, writes no files and runs no git.

--apply: refuses unless the default checks pass, then
  1. re-validates (a), applies (a) and (b) through the Ads API and (d) through Search Console;
  2. git fetch origin, and a temporary worktree from origin/main on claude/standing-<date> under the main
     checkout's .claude/worktrees/ (the main checkout's working tree is never touched);
  3. there: one row per applied Ads change in logs/ads-changes.md (ads_log.py, newest first), (d) in
     logs/gsc-changes.md, and the (c) and (e) edits;
  4. commits, 5. pushes, opens a PR with gh and asks for auto-merge (or waits up to 10 minutes for the checks,
     then merges), 6. removes the worktree, 7. prints one line per change and the PR URL.
If an API step fails it applies nothing further (and makes no file edits), still logs and commits what was
applied, and exits 1 with the reason. git and gh run through subprocess with argument lists, never a shell.

    source .venv/bin/activate
    python scripts/ads/standing_approvals.py --input /path/to/standing.json            # validate only
    python scripts/ads/standing_approvals.py --input /path/to/standing.json --apply    # the Monday run
    (--report PATH reads section 7 from that saved report instead of ~/lcs-private/reports/<date>.txt)
"""

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for p in (HERE, ROOT / "scripts" / "gsc", ROOT / "scripts" / "reports"):
    sys.path.insert(0, str(p))
import ads_log  # noqa: E402
import budget_cap  # noqa: E402
import negative_match  # noqa: E402
import report_sections  # noqa: E402
import submit_sitemap  # noqa: E402
import lcs_money as lm  # noqa: E402  (report_sections puts scripts/bookings on the path)

CUSTOMER_ID = "8733881378"
SCRIPT = "scripts/ads/standing_approvals.py"
RULES = ROOT / "data" / "standing-approvals.yml"
CLASSES = ("negatives", "dismiss_recommendations", "manual_actions_line", "sitemap_resubmit", "llms_date")
HARD_MAX_NEGATIVES = 10
LONDON = ZoneInfo("Europe/London")
TEXT_RE = re.compile(r"[a-z0-9][a-z0-9 '&.+-]{0,79}")
COAUTHOR = "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
PR_FOOTER = "🤖 Generated with [Claude Code](https://claude.com/claude-code)"
MERGE_WAIT_S = 600


class Refused(SystemExit):
    pass


# ---------------------------------------------------------------- rules and input

def load_rules(path=RULES):
    rules = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if tuple(rules.get("classes", {})) != CLASSES:
        raise Refused(f"{path} must name exactly the classes {', '.join(CLASSES)}; nothing done")
    if "BUDGETS ARE NEVER A STANDING CLASS" not in rules.get("never", ""):
        raise Refused(f"{path} has lost its 'never' rule; nothing done")
    return rules


def norm(text):
    return " ".join(str(text).lower().split())


def load_input(path, today):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise Refused(f"can't read the input {path}: {e}; nothing done") from None
    if not isinstance(data, dict) or set(data) - {"date", "negatives", "hiring_terms", "manual_line"}:
        raise Refused("the input must be an object with date, negatives, hiring_terms and manual_line only")
    try:
        day = datetime.date.fromisoformat(str(data.get("date")))
    except ValueError:
        raise Refused(f"the input's date must be YYYY-MM-DD, not {data.get('date')!r}") from None
    if not (today - datetime.timedelta(days=7) <= day <= today):
        raise Refused(f"the input's date {day} is not within the last week; nothing done")
    negs, terms, line = data.get("negatives") or [], data.get("hiring_terms") or [], data.get("manual_line")
    if not isinstance(negs, list) or not all(isinstance(n, dict) for n in negs):
        raise Refused("negatives must be a list of objects")
    if not isinstance(terms, list) or not all(isinstance(t, str) and t.strip() for t in terms):
        raise Refused("hiring_terms must be a list of search terms")
    if line is not None and not isinstance(line, str):
        raise Refused("manual_line must be a string or null")
    return {"date": day, "negatives": negs, "hiring_terms": [norm(t) for t in terms], "manual_line": line}


# ---------------------------------------------------------------- (a) negatives

def check_negatives(inp, rules):
    """Rule checks that need no API: (accepted [(cid, text, match, blocks)], refused [(entry, why)])."""
    r = rules["classes"]["negatives"]
    limit = min(int(r["max_per_run"]), HARD_MAX_NEGATIVES)
    if len(inp["negatives"]) > limit:
        raise Refused(f"{len(inp['negatives'])} negatives is more than {limit} a run; nothing done")
    guard = inp["hiring_terms"] + [norm(t) for t in r["protected_terms"]]
    ok, refused, seen = [], [], set()
    for n in inp["negatives"]:
        cid, text, match, term = str(n.get("campaign_id", "")), norm(n.get("text", "")), n.get("match"), \
            norm(n.get("blocks", ""))
        label = f'{text or "?"} ({match}) for {cid or "?"}'
        if set(n) - {"campaign_id", "text", "match", "blocks"}:
            refused.append((label, "unknown fields"))
        elif match not in r["match_types"]:
            refused.append((label, f"match type {match!r} is not one of {', '.join(r['match_types'])}"))
        elif cid not in budget_cap.KNOWN_CAMPAIGNS:
            refused.append((label, "not one of the account's known campaigns (budget_cap.KNOWN_CAMPAIGNS)"))
        elif not TEXT_RE.fullmatch(text) or len(text.split()) > 10:
            refused.append((label, "keyword text must be up to 10 plain words (letters, digits, ' & . + -)"))
        elif not term or len(term) > 200 or any(c in term for c in "|@\n"):
            refused.append((label, "its search term is missing or not a plain search"))
        elif not negative_match.blocks(text, match, term):
            refused.append((label, f'does not block its own search term "{term}"'))
        elif any(negative_match.blocks(text, match, h) for h in guard):
            hit = next(h for h in guard if negative_match.blocks(text, match, h))
            refused.append((label, f'would block the hiring search "{hit}"'))
        elif (cid, text, match) in seen:
            refused.append((label, "listed twice"))
        else:
            seen.add((cid, text, match))
            ok.append((cid, text, match, term))
    return ok, refused


def search(client, query):
    return client.get_service("GoogleAdsService").search(customer_id=CUSTOMER_ID, query=query)


def plan_negatives(client, accepted):
    """Against the account: drops negatives already there and any that block one of the campaign's own keywords.
    Returns (new [(cid, name, text, match, term, existing count)], skipped [(label, why)])."""
    new, skipped = [], []
    for cid in sorted({a[0] for a in accepted}):
        names = [r.campaign.name for r in search(client, f"SELECT campaign.name FROM campaign WHERE campaign.id = {int(cid)}")]
        if len(names) != 1:
            skipped += [(f"{t} ({m}) for {cid}", "campaign not found") for c, t, m, _ in accepted if c == cid]
            continue
        existing = {(norm(r.campaign_criterion.keyword.text), r.campaign_criterion.keyword.match_type.name)
                    for r in search(client, (
                        "SELECT campaign_criterion.keyword.text, campaign_criterion.keyword.match_type "
                        f"FROM campaign_criterion WHERE campaign.id = {int(cid)} AND campaign_criterion.negative = TRUE "
                        "AND campaign_criterion.type = 'KEYWORD'"))}
        own = [(norm(r.ad_group_criterion.keyword.text), r.ad_group_criterion.keyword.match_type.name)
               for r in search(client, (
                   "SELECT ad_group_criterion.keyword.text, ad_group_criterion.keyword.match_type "
                   f"FROM ad_group_criterion WHERE campaign.id = {int(cid)} AND ad_group_criterion.negative = FALSE "
                   "AND ad_group_criterion.type = 'KEYWORD' AND ad_group_criterion.status != 'REMOVED'"))]
        for c, text, match, term in accepted:
            if c != cid:
                continue
            label = f"{text} ({match}) for {names[0]}"
            hits = negative_match.blocked([(text, match)], own)
            if (text, match) in existing:
                skipped.append((label, "already there"))
            elif hits:
                skipped.append((label, f'refused: would block the campaign\'s own keyword "{hits[0][2]}"'))
            else:
                new.append((cid, names[0], text, match, term, len(existing)))
    return new, skipped


def negatives_request(client, new, validate_only):
    ga = client.get_service("GoogleAdsService")
    req = client.get_type("MutateGoogleAdsRequest")
    req.customer_id = CUSTOMER_ID
    for cid, _, text, match, _, _ in new:
        o = client.get_type("MutateOperation")
        cc = o.campaign_criterion_operation.create
        cc.campaign = ga.campaign_path(CUSTOMER_ID, int(cid))
        cc.negative = True
        cc.keyword.text = text
        cc.keyword.match_type = client.enums.KeywordMatchTypeEnum[match]
        req.mutate_operations.append(o)
    req.validate_only = validate_only
    return ga, req


def google_errors(e):
    if type(e).__name__ == "GoogleAdsException" and hasattr(e, "failure"):
        return "; ".join(f"{err.error_code} {err.message}" for err in e.failure.errors) or str(e)
    return None


def send_negatives(client, new, validate_only):
    """None when Google accepted the set, else the reason. validate_only=False only from --apply."""
    ga, req = negatives_request(client, new, validate_only)
    try:
        ga.mutate(request=req)
    except Exception as e:
        why = google_errors(e)
        if why is None:
            raise
        return why
    return None


def negative_rows(new, day):
    """One log line per campaign: (resource, field, current, new, reason)."""
    out = []
    for cid in sorted({n[0] for n in new}):
        mine = [n for n in new if n[0] == cid]
        listed = ", ".join(f'"{t}"' if m == "PHRASE" else (f"[{t}]" if m == "EXACT" else t) for _, _, t, m, _, _ in mine)
        terms = "; ".join(f"'{n[4]}'" for n in mine)
        out.append((f'campaign "{mine[0][1]}" ({cid})', "negative keywords", f"{mine[0][5]} negatives",
                    f"+{len(mine)}: {listed}",
                    f"NOT A BUYER search terms {terms}; standing approval (a), Monday review {day}"))
    return out


# ---------------------------------------------------------------- (b) recommendations

def ruled_out(kind, rules):
    """The reason a recommendation type is ruled out, or None (never dismissed)."""
    r = rules["classes"]["dismiss_recommendations"]
    if kind in r["types"]:
        return r["types"][kind]
    prefix = r.get("ai_max_prefix")
    if prefix and kind.startswith(prefix):
        return r["ai_max_reason"]
    return None


def plan_dismissals(client, rules):
    """Open recommendations of ruled-out types, on the account or a known campaign: [(label, type, resource)]."""
    found = []
    for row in search(client, ("SELECT recommendation.resource_name, recommendation.type, recommendation.campaign, "
                               "recommendation.dismissed FROM recommendation")):
        rec = row.recommendation
        kind = rec.type_.name
        if rec.dismissed or not ruled_out(kind, rules):
            continue
        camp = rec.campaign.split("/")[-1] if rec.campaign else ""
        if camp and camp not in budget_cap.KNOWN_CAMPAIGNS:
            continue
        found.append((f'campaign "{budget_cap.KNOWN_CAMPAIGNS[camp]}"' if camp else "account", kind, rec.resource_name))
    return sorted(found)


def dismiss(client, found):
    """One request per type (Google refuses a request mixing types). Stops at the first refusal.
    Returns (dismissed [(label, type, resource)], reason or None)."""
    svc = client.get_service("RecommendationService")
    done = []
    for kind in sorted({k for _, k, _ in found}):
        batch = [f for f in found if f[1] == kind]
        req = client.get_type("DismissRecommendationRequest")
        req.customer_id = CUSTOMER_ID
        for _, _, res in batch:
            op = client.get_type("DismissRecommendationRequest").DismissRecommendationOperation()
            op.resource_name = res
            req.operations.append(op)
        try:
            svc.dismiss_recommendation(request=req)
        except Exception as e:
            why = google_errors(e)
            if why is None:
                raise
            return done, f"dismissing {kind}: {why}"
        done.extend(batch)
    return done, None


def dismissal_rows(done, rules):
    return [(f"{label} recommendation {kind}", "status", "open", "dismissed",
             f"{ruled_out(kind, rules)}; standing approval (b)") for label, kind, _ in done]


# ---------------------------------------------------------------- (c), (d), (e): files

def manual_entry(line, day):
    """The archive entry for the review's line, or a Refused."""
    line = " ".join((line or "").split())
    if not line or len(line) > 3000 or "@" in line or "|" in line:
        raise Refused("manual_line must be one plain line of at most 3,000 characters without '@' or '|'")
    head = f"**Weekly review, {day}"
    if line.startswith("**Weekly review, "):
        if not line.startswith(head):
            raise Refused(f"manual_line is dated otherwise than {day}")
        return line
    return f"{head}:** {line}"


def with_manual_line(text, section, entry, day):
    """The archive with the entry added at the end of its section, or None when that date's entry is there."""
    start = text.find("\n" + section)
    if start < 0:
        raise Refused(f"the archive has no '{section}' section")
    after = start + 1 + len(section)
    nxt = re.search(r"\n(---\n|## )", text[after:])
    end = after + nxt.start() if nxt else len(text)
    body = text[start:end]
    if f"**Weekly review, {day}" in body:
        return None
    return text[:start] + body.rstrip("\n") + "\n\n" + entry + "\n\n" + text[end:].lstrip("\n")


def stale_sitemaps(report_text, rules):
    """Sitemap names section 7 marks stale (only names submit_sitemap.py knows)."""
    r = rules["classes"]["sitemap_resubmit"]
    sec = report_sections.split(report_text).get(r["report_section"], "")
    out = []
    for ln in sec.splitlines():
        m = re.search(r"https://londonchoralservice\.com/(\S+?\.xml)\b", ln)
        if r["marker"] in ln and m and m.group(1) in submit_sitemap.SITEMAPS and m.group(1) not in out:
            out.append(m.group(1))
    return out


def llms_update(llms_text, sitemap_text, rules):
    """(new llms text or None, old date text, new date text)."""
    prefix = rules["classes"]["llms_date"]["prefix"]
    m = re.search(re.escape(prefix) + r"(\d{1,2} [A-Z][a-z]+ \d{4})\.", llms_text)
    if not m:
        raise Refused(f"llms.txt has no '{prefix}<d Month yyyy>.' line")
    old = datetime.datetime.strptime(m.group(1), "%d %B %Y").date()
    dates = [datetime.date.fromisoformat(d) for d in re.findall(r"<lastmod>(\d{4}-\d{2}-\d{2})", sitemap_text)]
    if not dates:
        raise Refused("sitemap.xml has no <lastmod> dates")
    newest = max(dates)
    new_text = f"{newest.day} {newest:%B %Y}"
    if newest <= old:
        return None, m.group(1), new_text
    return llms_text[:m.start(1)] + new_text + llms_text[m.end(1):], m.group(1), new_text


# ---------------------------------------------------------------- git and gh

def run_cmd(args, cwd=None):
    """Run git or gh with an argument list (no shell). Returns (exit code, combined output)."""
    assert isinstance(args, list) and args[0] in ("git", "gh"), args
    r = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip()


def must(run, args, cwd=None):
    code, out = run(args, cwd=cwd)
    if code != 0:
        raise RuntimeError(f"{' '.join(args[:3])} failed: {out[:300]}")
    return out


def main_repo(run):
    common = must(run, ["git", "-C", str(ROOT), "rev-parse", "--path-format=absolute", "--git-common-dir"])
    return Path(common).parent


def free_branch(run, repo, day):
    """claude/standing-<date>, or -2 … -9 if a rerun already used it (locally, on origin or as a folder)."""
    for n in range(1, 10):
        name = f"standing-{day}" + (f"-{n}" if n > 1 else "")
        branch, path = f"claude/{name}", repo / ".claude" / "worktrees" / name
        local, _ = run(["git", "-C", str(repo), "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"])
        remote, out = run(["git", "-C", str(repo), "ls-remote", "--heads", "origin", branch])
        if local != 0 and remote == 0 and not out.strip() and not path.exists():
            return branch, path
    raise RuntimeError(f"no free claude/standing-{day} branch name")


def merge(run, url, wt, sleep):
    """Auto-merge, or wait (at most MERGE_WAIT_S) for the checks and merge. Returns a status line."""
    code, out = run(["gh", "pr", "merge", url, "--squash", "--auto"], cwd=wt)
    if code == 0:
        return "auto-merge requested (squash)"
    waited = 0
    while waited <= MERGE_WAIT_S:
        code, out = run(["gh", "pr", "checks", url], cwd=wt)
        if code == 0:
            code, out = run(["gh", "pr", "merge", url, "--squash"], cwd=wt)
            return "merged (squash)" if code == 0 else f"checks passed but merge failed: {out[:200]}"
        if code != 8 and "no checks reported" not in out:  # 8 = checks still pending
            return f"checks failed, left open: {out[:200]}"
        sleep(30)
        waited += 30
    return "checks still pending after 10 minutes, left open"


# ---------------------------------------------------------------- the run

def now_london(now=None):
    return (now or datetime.datetime.now(LONDON)).astimezone(LONDON)


def show(title, lines):
    print(f"\n({title})")
    for ln in lines or ["   nothing to do"]:
        print(ln)


def load_client():
    from google.ads.googleads.client import GoogleAdsClient
    return GoogleAdsClient.load_from_storage(os.environ.get(
        "GOOGLE_ADS_CONFIGURATION_FILE_PATH", os.path.expanduser("~/.config/lcs/google-ads.yaml")))


def parse(argv=None):
    p = argparse.ArgumentParser(description="Apply the owner's standing approvals from the Monday review.")
    p.add_argument("--input", required=True, help="the dispatcher's JSON file")
    p.add_argument("--report", help="the saved Monday report (default ~/lcs-private/reports/<date>.txt)")
    p.add_argument("--apply", action="store_true", help="apply, log, commit and merge (the Monday run)")
    return p.parse_args(argv)


def main(argv=None, client=None, run=None, gsc=None, now=None, sleep=time.sleep):
    args = parse(argv)
    run = run or run_cmd
    stamp = now_london(now)
    rules = load_rules()
    inp = load_input(args.input, stamp.date())
    day = inp["date"]
    print(f"STANDING APPROVALS, Monday review {day}: "
          + ("APPLYING" if args.apply else "VALIDATE ONLY (nothing is changed, no files written, no git)"))
    print("Budgets, bids, pauses, keyword status, ad copy and site copy are never standing approvals.")

    # (a) and (b): read and validate
    accepted, refused = check_negatives(inp, rules)
    client = client or load_client()
    new, skipped = plan_negatives(client, accepted) if accepted else ([], [])
    neg_lines = [f"   refused: {lbl}: {why}" for lbl, why in refused] + [f"   skipped: {lbl}: {why}" for lbl, why in skipped]
    for res, field, cur, nw, why in negative_rows(new, day):
        neg_lines.append(f"{res}\n   {field}: {cur} → {nw}\n   reason: {why}")
    neg_error = send_negatives(client, new, validate_only=True) if new else None
    if new:
        neg_lines.append(f"   Google refused the set: {neg_error}" if neg_error else
                         "   Google accepted every operation (validate_only).")
    show("a: campaign negatives", neg_lines)
    found = plan_dismissals(client, rules)
    show("b: dismiss ruled-out recommendations",
         [f"{lbl}: {kind}\n   status: open → dismissed\n   reason: {ruled_out(kind, rules)}\n   {res}"
          for lbl, kind, res in found]
         + (["   Google has no validate-only mode for a dismissal: these are exactly what --apply dismisses."]
            if found else []))

    # (c), (d), (e): what the files say now (this checkout; --apply edits a fresh worktree from origin/main)
    c_rules, e_rules = rules["classes"]["manual_actions_line"], rules["classes"]["llms_date"]
    entry = manual_entry(inp["manual_line"], day) if inp["manual_line"] else None
    if not entry:
        c_line = "   no manual_line given"
    elif with_manual_line((ROOT / c_rules["file"]).read_text(encoding="utf-8"), c_rules["section"], entry, day) is None:
        c_line = f"   skipped: an entry for {day} is already there"
    else:
        c_line = f"   append to §12: {entry[:160]}{'…' if len(entry) > 160 else ''}"
    show("c: MANUAL-ACTIONS archive line", [c_line])
    report = Path(args.report) if args.report else lm.PRIVATE / "reports" / f"{day}.txt"
    stale = stale_sitemaps(report.read_text(encoding="utf-8"), rules) if report.is_file() else None
    show("d: sitemap resubmission", ["   no saved report at " + str(report) + ": nothing resubmitted"] if stale is None
         else [f"   resubmit {s}: section 7 says STALE" for s in stale])
    llms, old, newest = llms_update((ROOT / e_rules["file"]).read_text(encoding="utf-8"),
                                    (ROOT / e_rules["sitemap"]).read_text(encoding="utf-8"), rules)
    show("e: llms.txt date", [f"   Content last updated: {old} → {newest}" if llms else f"   already {old} (newest lastmod {newest})"])

    if neg_error:
        print(f"\nREFUSED: Google refused the negatives as written ({neg_error}); nothing applied.")
        return 1
    if not args.apply:
        print("\nValidate only. Nothing was changed.")
        return 0
    return apply(client, run, gsc, sleep, rules, inp, new, found, entry, stale or [], stamp)


def apply(client, run, gsc, sleep, rules, inp, new, found, entry, stale, stamp):
    day = inp["date"]
    try:  # before touching the account: git must work and the branch name must be free
        must(run, ["git", "-C", str(ROOT), "fetch", "origin"])
        repo = main_repo(run)
        branch, wt = free_branch(run, repo, day)
    except RuntimeError as e:
        print(f"\nFAILED before any change: {e}")
        return 1

    ads_rows, gsc_rows, done, failure = [], [], [], None
    when = stamp.strftime("%Y-%m-%d %H:%M")
    if new:
        failure = send_negatives(client, new, validate_only=True)
        failure = failure and f"re-validating the negatives: {failure}"
        if not failure:
            failure = send_negatives(client, new, validate_only=False)
            failure = failure and f"adding the negatives: {failure}"
        if not failure:
            for res, field, cur, nw, why in negative_rows(new, day):
                ads_rows.append(f"| {when} | {res} | {field} | {cur} → {nw} | {why} | `{SCRIPT}` |")
                done.append(f"(a) {res}: negative keywords {nw}")
    if not failure and found:
        found = plan_dismissals(client, rules)  # re-read: only what is still open
        dismissed, failure = dismiss(client, found)
        for res, field, cur, nw, why in dismissal_rows(dismissed, rules):
            ads_rows.append(f"| {when} | {res} | {field} | {cur} → {nw} | {why} | `{SCRIPT}` |")
            done.append(f"(b) {res}: dismissed")
    if not failure and stale:
        s = gsc or submit_sitemap.session()
        for name in stale:
            try:
                before = submit_sitemap.status(s, name)
                after = submit_sitemap.submit(s, name, before)
            except SystemExit as e:
                failure = f"resubmitting {name}: {e.code if e.code not in (None, 1) else 'Search Console refused it'}"
                break
            gsc_rows.append(submit_sitemap.log_row(
                name, before, after, f"section 7 of the Monday report {day} said STALE; standing approval (d)",
                SCRIPT, now=stamp))
            done.append(f"(d) sitemap {name}: {before} → {after}")

    if failure and not (ads_rows or gsc_rows):
        print(f"\nFAILED: {failure}; nothing was applied.")
        return 1
    # The worktree is made even when nothing was applied, because (c) and (e) are judged on origin/main.
    try:
        must(run, ["git", "-C", str(repo), "worktree", "add", "-b", branch, str(wt), "origin/main"])
    except RuntimeError as e:
        return report_unlogged(f"making the worktree: {e}", ads_rows, gsc_rows, done, failure)
    edits, committed = [], False
    try:
        files = write_files(wt, rules, ads_rows, gsc_rows, None if failure else entry, day, edit_llms=not failure)
        edits = files["done"]
        if not files["paths"]:
            print("\nNothing to apply or log.")
            return 0
        title = f"chore(ads): standing approvals from the Monday review {day}"
        body = "\n".join(f"- {ln}" for ln in done + edits) + (f"\n\nStopped early: {failure}" if failure else "")
        must(run, ["git", "-C", str(wt), "add", "--", *files["paths"]])
        must(run, ["git", "-C", str(wt), "commit", "-m", f"{title}\n\n{body}\n\n{COAUTHOR}"])
        committed = True
        must(run, ["git", "-C", str(wt), "push", "-u", "origin", branch])
        out = must(run, ["gh", "pr", "create", "--base", "main", "--head", branch, "--title", title, "--body",
                         f"Standing approvals (data/standing-approvals.yml), applied by `{SCRIPT}`:\n\n"
                         f"{body}\n\n{PR_FOOTER}"], cwd=str(wt))
        url = out.splitlines()[-1].strip() if out else "(no URL printed)"
        merged = merge(run, url, str(wt), sleep)
    except (RuntimeError, OSError, SystemExit) as e:
        where = f" (committed on branch {branch}, not pushed or not merged)" if committed else ""
        return report_unlogged(f"{e}{where}", [] if committed else ads_rows, [] if committed else gsc_rows,
                               done + edits, failure)
    finally:
        run(["git", "-C", str(repo), "worktree", "remove", "--force", str(wt)])
        if not committed:
            run(["git", "-C", str(repo), "branch", "-D", branch])
    print()
    for ln in done + edits:
        print(f"done: {ln}")
    print(f"PR: {url} ({merged})")
    if failure:
        print(f"FAILED: {failure}; nothing further was applied.")
        return 1
    return 0


def write_files(wt, rules, ads_rows, gsc_rows, entry, day, edit_llms=True):
    """The worktree edits. Returns {"paths": changed repo paths, "done": one line per (c)/(e) edit}."""
    paths, done = [], []
    if ads_rows:
        os.environ["LCS_ADS_LOG"] = str(wt / "logs" / "ads-changes.md")
        try:
            ads_log.check_log()
            for row in reversed(ads_rows):  # newest first, the batch in its own order
                ads_log.append_row(row)
        finally:
            os.environ.pop("LCS_ADS_LOG", None)
        paths.append("logs/ads-changes.md")
    if gsc_rows:
        for row in reversed(gsc_rows):
            submit_sitemap.append_log(row, wt / "logs" / "gsc-changes.md")
        paths.append("logs/gsc-changes.md")
    c = rules["classes"]["manual_actions_line"]
    if entry:
        f = wt / c["file"]
        text = with_manual_line(f.read_text(encoding="utf-8"), c["section"], entry, day)
        if text is not None:
            f.write_text(text, encoding="utf-8")
            paths.append(c["file"])
            done.append(f"(c) {c['file']} §12: Weekly review, {day} entry added")
    e = rules["classes"]["llms_date"]
    if edit_llms:
        text, old, new = llms_update((wt / e["file"]).read_text(encoding="utf-8"),
                                     (wt / e["sitemap"]).read_text(encoding="utf-8"), rules)
        if text is not None:
            (wt / e["file"]).write_text(text, encoding="utf-8")
            paths.append(e["file"])
            done.append(f"(e) llms.txt Content last updated: {old} → {new}")
    return {"paths": paths, "done": done}


def report_unlogged(why, ads_rows, gsc_rows, done, failure):
    print(f"\nFAILED: {why}")
    if failure:
        print(f"(and earlier: {failure})")
    for ln in done:
        print(f"applied: {ln}")
    rows = ads_rows + gsc_rows
    if rows:
        print("These applied changes are NOT in the repo's logs yet; add them by hand:")
        for r in rows:
            print(r.rstrip("\n"))
    return 1


if __name__ == "__main__":
    sys.exit(main())
