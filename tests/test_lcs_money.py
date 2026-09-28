#!/usr/bin/env python3
"""Tests for scripts/bookings/lcs_money.py. Stdlib only: .venv/bin/python tests/test_lcs_money.py"""
import datetime, io, json, os, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "bookings"))
import lcs_money as m


class FakeOpener:
    """Stands in for urllib.request.urlopen and records every request."""
    def __init__(self, payload):
        self.payload, self.requests = payload, []

    def __call__(self, req, timeout=30):
        self.requests.append(req)
        body = self.payload(req.full_url) if callable(self.payload) else self.payload
        return io.BytesIO(json.dumps(body).encode())


ACCOUNTS = {"accounts": [{"accountUid": "a1", "defaultCategory": "c1"}]}


def test_fingerprint_ignores_formatting():
    a = m.bank_fingerprint("60-83-71", "24972792")
    assert a == m.bank_fingerprint("608371", "2497 2792")
    assert len(a) == 16


def test_fingerprint_pads_seven_digit_accounts():
    assert m.bank_fingerprint("60-83-71", "1234567") == m.bank_fingerprint("608371", "01234567")


def test_fingerprint_rejects_bad_input():
    assert m.bank_fingerprint("6083", "24972792") is None
    assert m.bank_fingerprint("60-83-71", "12") is None
    assert m.bank_fingerprint("", "") is None


def test_last4():
    assert m.last4("2497 2792") == "2792"
    assert m.last4("") == ""


def test_money_parses_pounds():
    assert m.money("£1,150.00") == 1150.0
    assert m.money("") == 0.0
    assert m.money(None) == 0.0
    assert m.money("n/a") == 0.0


def test_client_only_sends_get_with_bearer():
    fake = FakeOpener(ACCOUNTS)
    m.StarlingReadOnly("tok", opener=fake).account()
    assert fake.requests and all(r.get_method() == "GET" for r in fake.requests)
    assert fake.requests[0].headers["Authorization"] == "Bearer tok"


def test_client_has_no_write_methods():
    public = {n for n in dir(m.StarlingReadOnly) if not n.startswith("_")}
    assert public == {"get", "account", "feed", "payees"}, public


def test_feed_filters_direction_and_status():
    items = [{"direction": "IN", "status": "SETTLED"}, {"direction": "OUT", "status": "SETTLED"},
             {"direction": "IN", "status": "DECLINED"}]
    fake = FakeOpener(lambda url: ACCOUNTS if url.endswith("/accounts") else {"feedItems": items})
    got = m.StarlingReadOnly("tok", opener=fake).feed(datetime.date(2026, 9, 1), datetime.date(2026, 9, 2), "IN")
    assert got == [items[0]]
    assert "minTransactionTimestamp=2026-09-01T00:00:00.000Z" in fake.requests[-1].full_url


def test_payee_fingerprints():
    payees = [{"payeeName": "Laura T", "accounts": [{"bankIdentifier": "608371", "accountIdentifier": "24972792"}]},
              {"payeeName": "No UK account", "accounts": [{"bankIdentifier": "", "accountIdentifier": "GB00XX"}]}]
    fps = m.payee_fingerprints(payees)
    assert fps == {m.bank_fingerprint("60-83-71", "24972792"): "Laura T"}


def test_csv_round_trip_is_private():
    path = os.path.join(tempfile.mkdtemp(), "sub", "f.csv")
    m.write_csv(path, [{"a": "1", "b": "x"}], ["a", "b"])
    assert oct(os.stat(path).st_mode)[-3:] == "600"
    assert m.read_csv(path) == [{"a": "1", "b": "x"}]
    assert m.read_csv(path + ".missing") == []


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
