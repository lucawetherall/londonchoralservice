#!/usr/bin/env python3
"""Tests for scripts/reports/goatcounter.py (Monday report section 5c). Stdlib only, a fake client, no network,
no Keychain. .venv/bin/python tests/test_goatcounter.py"""
import datetime, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "reports"))
import goatcounter as g  # noqa: E402

g.time.sleep = lambda s: None  # no waiting between requests in tests
D = datetime.date


class Fake:
    """Answers /stats/hits by the requested start date; records every call."""

    def __init__(self, by_start):
        self.by_start, self.calls = by_start, []

    def get(self, path, **params):
        self.calls.append((path, params))
        return {"hits": self.by_start.get(params["start"][:10], []), "more": False}


def hit(path, count, event=False):
    return {"path": path, "title": path, "count": count, "event": event, "path_id": 1}


def test_week_and_week_before_with_events():
    fake = Fake({"2026-11-02": [hit("/weddings.html", 30), hit("/", 20), hit("enquiry-sent-form", 2, True),
                                hit("enquiry-sent-whatsapp", 1, True)],
                 "2026-10-26": [hit("/", 15), hit("enquiry-sent-form", 1, True)]})
    lines = g.section(today=D(2026, 11, 9), client=fake)
    text = "\n".join(lines)
    assert "== 5c." in lines[0]
    assert "2026-11-02 to 2026-11-08 (7 days): 50 page views (the 7 days before: 15)" in text, text
    assert "enquiry forms sent 2 (was 1)" in text and "WhatsApp taps 1 (was 0)" in text, text
    assert "top pages: /weddings.html 30 · / 20" in text, text
    # RFC 3339 times: a bare date answers 404
    assert all(p["start"].endswith("T00:00:00Z") and p["end"].endswith("T23:59:59Z") for _, p in fake.calls)
    assert {path for path, _ in fake.calls} == {"/stats/hits"}


def test_counting_starts_on_23_oct():
    fake = Fake({"2026-10-23": [hit("/", 4)]})
    text = "\n".join(g.section(today=D(2026, 10, 26), client=fake))
    assert "2026-10-23 to 2026-10-25 (3 days): 4 page views" in text, text
    assert "the 7 days before" not in text and "(was" not in text, text
    assert "counting started" in "\n".join(g.section(today=D(2026, 10, 23), client=Fake({})))


def test_missing_key_says_so_and_never_calls_out():
    lines = g.section(today=D(2026, 11, 9), token_reader=lambda: None)
    assert "no read key" in lines[-1] and g.KEYCHAIN_SERVICE in lines[-1], lines


def test_client_is_get_only_and_sends_the_key_only_to_our_host():
    seen = []

    class Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b'{"hits": []}'

    def opener(req, timeout):
        seen.append(req)
        return Resp()

    c = g.GoatCounterReadOnly("secret-test-token", opener=opener)
    c.get("/stats/hits", start="2026-11-02T00:00:00Z")
    req = seen[0]
    assert req.get_method() == "GET"
    assert req.full_url.startswith("https://londonchoralservice.goatcounter.com/api/v0/stats/hits?")
    assert req.unredirected_hdrs.get("Authorization") == "Bearer secret-test-token"
    assert "Authorization" not in req.headers  # never re-sent on a redirect
    public = [n for n in dir(g.GoatCounterReadOnly) if not n.startswith("_")]
    assert public == ["get"], public


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
