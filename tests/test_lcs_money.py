#!/usr/bin/env python3
"""Tests for scripts/bookings/lcs_money.py. Stdlib only: .venv/bin/python tests/test_lcs_money.py"""
import csv, datetime, inspect, io, json, os, sys, tempfile

os.environ["LCS_PRIVATE_DIR"] = tempfile.mkdtemp()  # the fingerprint key goes here, never in ~/lcs-private
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


def test_fingerprint_is_keyed_and_the_key_is_private():
    home = os.environ["LCS_PRIVATE_DIR"]
    a = m.bank_fingerprint("60-83-71", "24972792")
    assert a == m.bank_fingerprint("608371", "24972792")
    key = os.path.join(home, "fingerprint.key")
    assert oct(os.stat(key).st_mode)[-3:] == "600" and len(open(key, "rb").read()) == 32
    other = os.path.join(tempfile.mkdtemp(), "priv")
    os.environ["LCS_PRIVATE_DIR"] = other
    try:
        b = m.bank_fingerprint("60-83-71", "24972792")
        assert b and b != a and len(b) == 16
        assert oct(os.stat(other).st_mode)[-3:] == "700"
        assert oct(os.stat(os.path.join(other, "fingerprint.key")).st_mode)[-3:] == "600"
    finally:
        os.environ["LCS_PRIVATE_DIR"] = home
    assert m.bank_fingerprint("60-83-71", "24972792") == a


def test_fingerprint_is_not_a_plain_hash():
    import hashlib
    assert m.bank_fingerprint("608371", "24972792") != hashlib.sha256(b"608371:24972792").hexdigest()[:16]


def test_fingerprint_coerces_non_string_input():
    assert m.bank_fingerprint("12-34-56", 12345678) == m.bank_fingerprint("12-34-56", "12345678")
    assert m.bank_fingerprint(123456, "12345678") == m.bank_fingerprint("123456", "12345678")
    assert m.bank_fingerprint(None, "12345678") is None
    assert m.bank_fingerprint("12-34-56", None) is None
    item = {"counterPartySubEntityIdentifier": "12-34-56", "counterPartySubEntitySubIdentifier": 12345678}
    assert m.feed_item_fingerprint(item) == m.bank_fingerprint("12-34-56", "12345678")


def test_lost_key_guard_refuses_to_recreate_when_fingerprints_are_on_record():
    home = tempfile.mkdtemp()
    with open(os.path.join(home, "singer-invoices.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["message_id", "bank_fp"])
        w.writeheader()
        w.writerow({"message_id": "m1", "bank_fp": "abc123"})
    saved = os.environ["LCS_PRIVATE_DIR"]
    os.environ["LCS_PRIVATE_DIR"] = home
    try:
        try:
            m.bank_fingerprint("60-83-71", "24972792")
            assert False, "should have refused to create a new key"
        except ValueError as e:
            assert "restore the key from a backup" in str(e) and "fingerprint.key is missing" in str(e)
        assert not os.path.exists(os.path.join(home, "fingerprint.key"))
    finally:
        os.environ["LCS_PRIVATE_DIR"] = saved


def test_lost_key_guard_allows_a_fresh_key_when_no_fingerprints_are_on_record():
    home = tempfile.mkdtemp()
    with open(os.path.join(home, "singer-invoices.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["message_id", "bank_fp"])
        w.writeheader()
        w.writerow({"message_id": "m1", "bank_fp": ""})
    saved = os.environ["LCS_PRIVATE_DIR"]
    os.environ["LCS_PRIVATE_DIR"] = home
    try:
        assert m.bank_fingerprint("60-83-71", "24972792") is not None
        assert os.path.exists(os.path.join(home, "fingerprint.key"))
    finally:
        os.environ["LCS_PRIVATE_DIR"] = saved


def test_feed_item_fingerprint():
    item = {"counterPartySubEntityIdentifier": "608371", "counterPartySubEntitySubIdentifier": "24972792"}
    assert m.feed_item_fingerprint(item) == m.bank_fingerprint("60-83-71", "24972792")
    assert m.feed_item_fingerprint({"counterPartyName": "X"}) is None
    assert m.feed_item_fingerprint({"counterPartySubEntityIdentifier": "", "counterPartySubEntitySubIdentifier": "1"}) is None


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
    assert fake.requests[0].get_header("Authorization") == "Bearer tok"


def test_token_is_never_sent_on_after_a_redirect():
    fake = FakeOpener(ACCOUNTS)
    m.StarlingReadOnly("tok", opener=fake).account()
    req = fake.requests[0]
    assert "Authorization" in req.unredirected_hdrs and "Authorization" not in req.headers


def test_get_takes_only_a_path():
    assert list(inspect.signature(m.StarlingReadOnly.get).parameters) == ["self", "path"]


def test_every_call_is_a_bodiless_get():
    payload = lambda url: ACCOUNTS if url.endswith("/accounts") else {"feedItems": [], "payees": []}
    fake = FakeOpener(payload)
    c = m.StarlingReadOnly("tok", opener=fake)
    c.account()
    c.feed(datetime.date(2026, 9, 1), datetime.date(2026, 9, 2), "IN")
    c.payees()
    assert len(fake.requests) >= 3
    assert all(r.get_method() == "GET" and r.data is None for r in fake.requests)


def test_account_is_fetched_once():
    fake = FakeOpener(lambda url: ACCOUNTS if url.endswith("/accounts") else {"feedItems": []})
    c = m.StarlingReadOnly("tok", opener=fake)
    c.feed(datetime.date(2026, 9, 1), datetime.date(2026, 9, 2), "IN")
    c.feed(datetime.date(2026, 9, 1), datetime.date(2026, 9, 2), "OUT")
    assert sum(r.full_url.endswith("/accounts") for r in fake.requests) == 1


def test_missing_account_raises_starling_error():
    saved = os.environ.get("LCS_STARLING_ACCOUNT_UID")
    os.environ["LCS_STARLING_ACCOUNT_UID"] = "nope"
    try:
        m.StarlingReadOnly("tok", opener=FakeOpener(ACCOUNTS)).account()
        assert False, "no error"
    except m.StarlingError:
        pass
    finally:
        if saved is None:
            del os.environ["LCS_STARLING_ACCOUNT_UID"]
        else:
            os.environ["LCS_STARLING_ACCOUNT_UID"] = saved


def test_local_date_is_london_time():
    assert m.local_date("2026-09-30T23:30:00.000Z") == "2026-10-01"
    assert m.local_date("2026-12-31T23:30:00.000Z") == "2026-12-31"
    assert m.local_date("2026-09-30T10:00:00Z") == "2026-09-30"
    assert m.local_date("") == ""


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


def test_csv_write_is_atomic_and_leaves_no_temp_files():
    d = tempfile.mkdtemp()
    path = os.path.join(d, "f.csv")
    m.write_csv(path, [{"a": "1"}], ["a"])
    m.write_csv(path, [{"a": "2"}], ["a"])
    assert os.listdir(d) == ["f.csv"]
    assert oct(os.stat(path).st_mode)[-3:] == "600"
    assert m.read_csv(path) == [{"a": "2"}]
    try:
        m.write_csv(path, [{"a": "3"}, None], ["a"])  # fails half way through
    except Exception:
        pass
    assert m.read_csv(path) == [{"a": "2"}] and os.listdir(d) == ["f.csv"]


def test_ledger_lock_is_exclusive_and_private():
    import fcntl
    path = os.path.join(tempfile.mkdtemp(), "sub", "bookings.csv")
    with m.ledger_lock(path):
        assert oct(os.stat(path + ".lock").st_mode)[-3:] == "600"
        fd = os.open(path + ".lock", os.O_RDWR)
        try:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                assert False, "second lock taken while the first is held"
            except BlockingIOError:
                pass
        finally:
            os.close(fd)
    fd = os.open(path + ".lock", os.O_RDWR)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)  # released on exit
    finally:
        os.close(fd)


def test_ledger_lock_releases_on_error():
    import fcntl
    path = os.path.join(tempfile.mkdtemp(), "bookings.csv")
    try:
        with m.ledger_lock(path):
            raise KeyError("boom")
    except KeyError:
        pass
    fd = os.open(path + ".lock", os.O_RDWR)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    finally:
        os.close(fd)


# --- one money parser, one London today, one locked read-modify-write ------------------------

def test_parse_gbp_reads_pounds_and_refuses_the_unreadable():
    for raw, want in (("1150", 1150.0), ("£1,150.00", 1150.0), (" £ 575.5 ", 575.5), (325, 325.0), (12.5, 12.5),
                      ("-50", -50.0), ("0", 0.0)):
        assert m.parse_gbp(raw) == want, (raw, m.parse_gbp(raw))
    for raw in (None, "", "  ", "abc", "£", "nan", "NaN", "inf", "-inf", "Infinity", float("nan"), float("inf"), "1,150 GBP?"):
        assert m.parse_gbp(raw) is None, (raw, m.parse_gbp(raw))
    # money() keeps its old contract (0.0 for anything unreadable), now also for nan and inf
    assert m.money("nan") == 0.0 and m.money("inf") == 0.0 and m.money(None) == 0.0 and m.money("£1,150") == 1150.0


def test_today_is_the_london_date():
    late = datetime.datetime(2026, 9, 28, 23, 30, tzinfo=datetime.timezone.utc)  # 00:30 on the 29th, BST
    assert m.today(late) == datetime.date(2026, 9, 29)
    assert m.today(datetime.datetime(2026, 12, 31, 23, 30, tzinfo=datetime.timezone.utc)) == datetime.date(2026, 12, 31)
    assert isinstance(m.today(), datetime.date) and not isinstance(m.today(), datetime.datetime)


def _table(path, cols, rows, extra_line=None):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in rows:
            w.writerow(r)
        if extra_line:
            f.write(extra_line + "\n")


def test_locked_rows_reads_with_the_header_and_writes_back_privately():
    d = tempfile.mkdtemp()
    path = os.path.join(d, "t.csv")
    _table(path, ["a", "b", "own"], [["1", "x", "keep"]])
    os.chmod(path, 0o644)
    with m.locked_rows(path, ["a", "b", "c"]) as t:
        assert t.columns == ["a", "b", "own", "c"], t.columns  # the file's own columns first, ours appended
        assert t.rows == [{"a": "1", "b": "x", "own": "keep"}], t.rows
        t.rows[0]["b"] = "y"
        t.rows.append({"a": "2", "c": "new"})
    with open(path, newline="") as f:
        assert list(csv.reader(f)) == [["a", "b", "own", "c"], ["1", "y", "keep", ""], ["2", "", "", "new"]]
    assert oct(os.stat(path).st_mode & 0o777) == "0o600"
    assert sorted(os.listdir(d)) == ["t.csv", "t.csv.lock"], os.listdir(d)


def test_locked_rows_holds_the_lock_and_skips_an_unchanged_or_failed_write():
    import fcntl
    d = tempfile.mkdtemp()
    path = os.path.join(d, "t.csv")
    _table(path, ["a"], [["1"]])
    before = os.stat(path).st_mtime_ns, os.stat(path).st_ino
    with m.locked_rows(path) as t:
        fd = os.open(path + ".lock", os.O_RDWR)
        try:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                held = False
            except BlockingIOError:
                held = True
        finally:
            os.close(fd)
    assert held, "locked_rows must hold the ledger lock while the caller works"
    assert (os.stat(path).st_mtime_ns, os.stat(path).st_ino) == before  # nothing changed: nothing written
    try:
        with m.locked_rows(path) as t:
            t.rows[0]["a"] = "2"
            raise SystemExit("refused")
    except SystemExit:
        pass
    assert m.read_csv(path) == [{"a": "1"}]  # an error inside: nothing written


def test_locked_rows_refuses_a_row_wider_than_the_header():
    d = tempfile.mkdtemp()
    path = os.path.join(d, "t.csv")
    _table(path, ["a", "b"], [["1", "2"]], extra_line="3,4,5")
    before = open(path).read()
    try:
        with m.locked_rows(path) as t:
            t.rows.append({"a": "x"})
        raise AssertionError("a wider row must be refused")
    except SystemExit as e:
        assert "more fields than its header" in str(e), e
    assert open(path).read() == before


def test_locked_rows_on_a_missing_file_starts_empty_and_creates_it_on_write():
    d = tempfile.mkdtemp()
    path = os.path.join(d, "sub", "t.csv")
    with m.locked_rows(path, ["a", "b"]) as t:
        assert t.rows == [] and t.columns == ["a", "b"]
    assert not os.path.exists(path)
    with m.locked_rows(path, ["a", "b"]) as t:
        t.rows.append({"a": "1"})
    assert m.read_csv(path) == [{"a": "1", "b": ""}] and oct(os.stat(path).st_mode & 0o777) == "0o600"


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
