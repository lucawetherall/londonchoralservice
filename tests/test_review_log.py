#!/usr/bin/env python3
"""Tests for scripts/reports/review_log.py: the Monday review's record of proposals and watch items.
Stdlib only, a temp private dir, no network. .venv/bin/python tests/test_review_log.py"""
import contextlib, datetime, io, json, os, stat, sys, tempfile

TMP = tempfile.mkdtemp(prefix="lcs-review-log-test-")
os.environ["LCS_PRIVATE_DIR"] = TMP
os.environ["LCS_BOOKINGS_CSV"] = os.path.join(TMP, "bookings.csv")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "reports"))
import review_log as rl  # noqa: E402

D = datetime.date
REVIEW = """# Monday review, 26 October 2026

Some brief text with 1. a number in it.

## Decisions

1. [ads] Christmas campaign → negative "lyrics" (phrase): none → added — not a hiring search
2. **[site]** /weddings.html → title: "Wedding choir" → "Wedding choir hire in London" — 8–20 query
3. Ask the venue list → planners page: none → one line — untagged
   a continuation line that is not an item

## Watch

- Funeral campaign clicks after the bid change (due 2026-11-09)
- GoatCounter page views back above 300
1. Christmas enquiries graded B

## Question

1. not a decision
"""


def reset():
    for name in os.listdir(TMP):
        os.remove(os.path.join(TMP, name))


def write_review(text=REVIEW, name="2026-10-26.md"):
    path = os.path.join(TMP, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    code = 0
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = rl.main(list(argv))
        except SystemExit as e:
            code = e.code
    return code, out.getvalue(), err.getvalue()


def items():
    return {i["id"]: i for i in rl.read_items()}


def test_record_numbers_decisions_then_watch_items_from_01():
    reset()
    code, out, _ = run("record", write_review())
    assert code == 0, out
    lines = out.splitlines()
    assert lines[0] == ('2026-10-26-01 Christmas campaign → negative "lyrics" (phrase): none → added — not a '
                        'hiring search'), lines
    assert lines[1].startswith("2026-10-26-02 /weddings.html → title:"), lines
    assert lines[3] == "2026-10-26-04 watch, due 2026-11-09 · Funeral campaign clicks after the bid change", lines
    assert len(lines) == 6, lines
    got = items()
    assert [got[k]["kind"] for k in sorted(got)] == ["ads", "site", "other", "watch", "watch", "watch"], got
    assert got["2026-10-26-02"]["text"].startswith("/weddings.html"), got["2026-10-26-02"]
    assert all(i["status"] == "open" and i["date"] == "2026-10-26" for i in got.values())
    # no due date: the Monday after the review
    assert got["2026-10-26-05"]["due"] == "2026-11-02" and got["2026-10-26-06"]["due"] == "2026-11-02", got
    assert "due" not in got["2026-10-26-01"]


def test_the_file_is_created_mode_600():
    reset()
    run("record", write_review())
    assert stat.S_IMODE(os.stat(rl.STORE).st_mode) == 0o600
    with open(rl.STORE, encoding="utf-8") as f:
        assert all(isinstance(json.loads(ln), dict) for ln in f if ln.strip())


def test_a_second_record_that_day_replaces_only_the_open_items():
    reset()
    run("record", write_review())
    assert run("decide", "2026-10-26-02", "approved", "--today", "2026-10-26")[0] == 0
    changed = REVIEW.replace("3. Ask the venue list", "3. Ask the planner list")
    code, out, _ = run("record", write_review(changed))
    assert code == 0, out
    got = items()
    assert got["2026-10-26-02"]["status"] == "approved", got  # decided: kept, same id
    texts = sorted(i["text"] for i in got.values())
    assert any("planner list" in t for t in texts) and not any("venue list" in t for t in texts), texts
    assert len(got) == 6, got  # the decided item is not recorded twice
    assert "2026-10-26-02 (already decided)" in out, out


def test_a_carried_item_keeps_its_id_and_is_not_recorded_again():
    reset()
    run("record", write_review())
    nxt = "## Decisions\n\n1. 2026-10-26-03 · Ask the venue list → planners page\n2. [growth] New item → x: a → b\n"
    code, out, _ = run("record", write_review(nxt, "2026-11-02.md"))
    assert code == 0
    assert out.splitlines()[0].startswith("2026-10-26-03 (carried)"), out
    assert out.splitlines()[1].startswith("2026-11-02-01 New item"), out
    assert items()["2026-11-02-01"]["kind"] == "growth"
    assert len(items()) == 7


def test_decide_done_and_note():
    reset()
    run("record", write_review())
    assert run("decide", "2026-10-26-01,2026-10-26-03", "dropped", "--note", "owner: no", "--today", "2026-10-27")[0] == 0
    assert run("done", "2026-10-26-02", "--note", "PR #420", "--today", "2026-10-28")[0] == 0
    assert run("note", "2026-10-26-04", "clicks", "flat", "so", "far")[0] == 0
    assert run("note", "2026-10-26-04", "still flat")[0] == 0
    got = items()
    assert got["2026-10-26-01"]["status"] == "dropped" and got["2026-10-26-01"]["decided"] == "2026-10-27"
    assert got["2026-10-26-01"]["note"] == "owner: no"
    assert got["2026-10-26-02"]["status"] == "done" and got["2026-10-26-02"]["note"] == "PR #420"
    assert got["2026-10-26-04"]["note"] == "clicks flat so far; still flat", got["2026-10-26-04"]
    assert got["2026-10-26-04"]["status"] == "open"


def test_decide_on_an_unknown_id_exits_2_and_changes_nothing():
    reset()
    run("record", write_review())
    before = open(rl.STORE, encoding="utf-8").read()
    code, _, err = run("decide", "2026-10-26-01,2026-10-26-99", "approved")
    assert code == 2 and "2026-10-26-99" in err, (code, err)
    assert run("note", "2026-01-01-01", "x")[0] == 2
    assert run("done", "nope", "--note", "x")[0] == 2
    assert open(rl.STORE, encoding="utf-8").read() == before


def test_open_lists_oldest_first_and_expires_old_items():
    reset()
    run("record", write_review(REVIEW, "2026-09-21.md"))  # its watch items 05 and 06 are due 28 Sep, 04 on 9 Nov
    run("record", write_review())
    code, out, _ = run("open", "--today", "2026-10-12")
    lines = out.splitlines()
    assert code == 0 and lines[0].startswith("2026-09-21-01 · ads · Christmas campaign"), lines
    assert "2026-10-26-04 · watch · due 2026-11-09 · Funeral campaign clicks after the bid change" in lines, lines
    assert len(lines) == 12, lines  # 12 Oct: the 28 Sep watch items are 14 days past due, not more
    code, out, _ = run("open", "--today", "2026-10-13")
    got = items()
    assert got["2026-09-21-05"]["status"] == "expired" and got["2026-09-21-05"]["decided"] == "2026-10-13", got
    assert got["2026-09-21-01"]["status"] == "open", got  # 22 days old
    assert len(out.splitlines()) == 10, out
    code, out, _ = run("open", "--today", "2026-10-20")  # 29 days: the 21 Sep proposals expire
    got = items()
    assert got["2026-09-21-01"]["status"] == "expired" and "expired 2026-10-20" in got["2026-09-21-01"]["note"], got
    assert got["2026-09-21-04"]["status"] == "open", got["2026-09-21-04"]  # due 9 Nov
    assert not any(l.startswith("2026-09-21-01") for l in out.splitlines()), out
    code, out, _ = run("open", "--before", "2026-10-26", "--today", "2026-10-20")
    assert out.splitlines() == ["2026-09-21-04 · watch · due 2026-11-09 · Funeral campaign clicks after the bid change"], out


def test_a_watch_item_expires_14_days_after_it_falls_due_not_28():
    its = [{"id": "2026-10-26-01", "date": "2026-10-26", "kind": "watch", "text": "x", "status": "open",
            "decided": "", "note": "", "due": "2026-11-02"},
           {"id": "2026-10-26-02", "date": "2026-10-26", "kind": "ads", "text": "y", "status": "open",
            "decided": "", "note": ""}]
    assert [i["id"] for i in rl.open_items(its, D(2026, 11, 16))] == ["2026-10-26-01", "2026-10-26-02"]
    assert [i["id"] for i in rl.open_items(its, D(2026, 11, 17))] == ["2026-10-26-02"]
    assert rl.open_items(its, D(2026, 11, 24)) == []
    assert its[0]["status"] == "open"  # open_items works on copies


def test_contact_details_are_refused_and_nothing_is_recorded():
    reset()
    for bad in ("1. [ads] Reply to someone@example.com → x", "1. Ring 020 7946 0958 → x",
                "1. Ring 07700 900123 → x", "1. Ring +44 7700 900123 → x"):
        code, out, err = run("record", write_review("## Decisions\n\n" + bad + "\n"))
        assert code == 2 and "refused" in err, (bad, code, err)
        assert "example.com" not in err + out and "7946" not in err + out
        assert not os.path.exists(rl.STORE), bad
    code, _, err = run("record", write_review("## Watch\n\n- call 01632 960123 (due 2026-11-09)\n"))
    assert code == 2, err
    run("record", write_review())
    assert run("note", "2026-10-26-01", "emailed x@y.com")[0] == 2
    assert run("decide", "2026-10-26-01", "approved", "--note", "rang 07700 900123")[0] == 2
    assert items()["2026-10-26-01"]["note"] == ""
    # figures, dates, booking refs and prices are fine
    assert not rl.has_contact("Small Choir £1,150 on 2026-12-12, ref 121226, 4 of 28 days")


def test_record_without_a_date_is_refused():
    reset()
    code, _, _ = run("record", write_review(REVIEW, "review.md"))
    assert code not in (0, None)
    code, out, _ = run("record", write_review(REVIEW, "review.md"), "--date", "2026-10-26")
    assert code == 0 and out.startswith("2026-10-26-01"), out


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted((n, f) for n, f in globals().items() if n.startswith("test_") and callable(f)):
        try:
            fn()
            print(f"PASS {name}")
        except Exception as ex:
            failures += 1
            print(f"FAIL {name}: {type(ex).__name__}: {ex}")
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)
