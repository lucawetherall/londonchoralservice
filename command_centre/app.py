"""The Command Centre web app: routes, templates and middleware.

    create_app()  ->  Starlette app (python -m command_centre serves it on 127.0.0.1:8765, or on a Unix socket)

Phase 1: Today, Money and Passkeys pages, the passkey endpoints and /healthz. Phase 2: the read-only data
pages (Bookings, Enquiries, Singers, Marketing, Calendar, Search, Reports, Health, To-do, Exports, More) and
one local write, POST /todo/tick (actions.REGISTRY["todo-tick"], no passkey: see actions.py). Phase 3: the
actions (POST /actions/<name>/preview, then POST /actions/<name>/run with a passkey assertion bound to the
server-built summary; see actions.py) and the Activity page. Phase 4: the chat with Claude Code (chat.py): /chat, its
POST routes for messages, stop and approval cards (approve needs a passkey bound to the card's exact tool call), and
GET /chat/<id>/stream (Server-Sent Events, no side effects). No GET route has a side effect. See
docs/superpowers/specs/2026-09-28-command-centre-design.md and docs/superpowers/plans/2026-09-28-command-centre.md.
"""

import csv
import datetime
import io
import json
import logging
import os
import urllib.parse
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import (HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse, Response,
                                 StreamingResponse)
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from . import actions, auth, chat, data, models

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
LOOPBACK = "127.0.0.1"
log = logging.getLogger("command_centre")

NAV = [("Today", "/"), ("Bookings", "/bookings"), ("Enquiries", "/enquiries"), ("Money", "/money"),
       ("Singers", "/singers"), ("Marketing", "/marketing"), ("Calendar", "/calendar"), ("Search", "/search"),
       ("Reports", "/reports"), ("Health", "/health"), ("To-do", "/todo"), ("Exports", "/exports"),
       ("Activity", "/activity"), ("Chat", "/chat")]
HAND_CHOICES = [(k, v[0]) for k, v in actions.HAND_CHOICES.items()]
ACTIVITY_RESULTS = ("ok", "failed", "refused", "started", "denied", "timed out", "expired", "stopped")
JSON_MAX = 16384  # bytes of an action request (a passkey assertion is about 1 KB)
TABS = [("Today", "/"), ("Bookings", "/bookings"), ("Money", "/money"), ("Chat", "/chat")]
SOON = []  # every page up to phase 2 is live; chat, drafts and the quote calculator come later
FORM_MAX = 4096  # bytes of a urlencoded POST body
HTMX_CONFIG = json.dumps({"includeIndicatorStyles": False, "allowEval": False, "allowScriptTags": False,
                          "selfRequestsOnly": True, "historyCacheSize": 0}, separators=(",", ":"))


def gbp(value):
    try:
        return f"£{float(value):,.2f}"
    except (TypeError, ValueError):
        return "£?"


def day(iso):
    try:
        d = datetime.date.fromisoformat(str(iso)[:10])
    except ValueError:
        return str(iso)
    return f"{d:%a} {d.day} {d:%b %Y}"


def last4(value):
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())[-4:]
    return f"••••{digits}" if digits else "-"


def state_words(state):
    return data.STATES.get(state, (str(state), ""))[0]


def state_tone(state):
    return data.STATES.get(state, ("", ""))[1]


def checkout_branch(repo=REPO):
    """The branch checked out at `repo` (read from .git/HEAD, no subprocess), or None if detached/unknown."""
    git = Path(repo) / ".git"
    try:
        if git.is_file():  # a worktree: ".git" names the real git dir
            line = git.read_text(encoding="utf-8").strip()
            if not line.startswith("gitdir:"):
                return None
            gitdir = Path(line.split(":", 1)[1].strip())
            git = gitdir if gitdir.is_absolute() else (Path(repo) / gitdir)
        head = (git / "HEAD").read_text(encoding="utf-8").strip()
    except OSError:
        return None
    prefix = "ref: refs/heads/"
    return head[len(prefix):] if head.startswith(prefix) else None


def checkout_warning(branch):
    """The LaunchAgent runs the main checkout, so it serves whatever that checkout has checked out: warn when
    that isn't main (a review branch left checked out would be live)."""
    if branch == "main":
        return None
    return f"The service's checkout is not on main (it is on {branch or 'a detached HEAD'})."


def london_day(value):
    if isinstance(value, datetime.datetime) and value.tzinfo is not None:
        value = value.astimezone(data.LONDON)
    return day(value.isoformat() if hasattr(value, "isoformat") else value)


def gbp_or_dash(value):
    return "–" if value is None else gbp(value)


def when(value):
    """A datetime as "Mon 28 Sep 2026, 09:30" (London), or "never"."""
    if not isinstance(value, datetime.datetime):
        return "never" if value is None else str(value)
    if value.tzinfo is not None:
        value = value.astimezone(data.LONDON)
    return f"{day(value.date().isoformat())}, {value:%H:%M}"


def current(href, path):
    """Whether the nav item `href` is the section `path` is in."""
    return path == "/" if href == "/" else (path == href or path.startswith(href + "/"))


def make_env():
    env = Environment(loader=FileSystemLoader(HERE / "templates"), autoescape=select_autoescape(default=True),
                      trim_blocks=True, lstrip_blocks=True)
    env.filters.update(gbp=gbp, day=day, london_day=london_day, last4=last4, state_words=state_words,
                       state_tone=state_tone, gbp_or_dash=gbp_or_dash, when=when, pct=models.rate)
    env.filters.update(masked=lambda v: actions.DIGITS_RE.sub("••••••", str(v)))
    env.globals.update(NAV=NAV, TABS=TABS, SOON=SOON, HTMX_CONFIG=HTMX_CONFIG, current=current,
                       HAND_CHOICES=HAND_CHOICES)
    return env


class CommandCentre(Starlette):
    """Starlette with the security headers outside everything, so even a 500 from ServerErrorMiddleware has them."""

    def build_middleware_stack(self):
        return auth.SecurityHeadersMiddleware(super().build_middleware_stack())


def create_app(client_factory=data.default_client, now=None, clock=None, passkeys=None, bind_host=None, port=None,
               uds=None, checkout=None, chat_client_factory=None):
    """The app. `bind_host`, `port` and `uds` say how __main__ serves it. CC_DEV_LOGIN is honoured only on
    127.0.0.1, on a port other than the service's 8765, and never on the Unix socket. `checkout` returns the
    serving checkout's branch (default: read from .git). `chat_client_factory(options)` makes the chat's SDK client
    (default: claude_agent_sdk.ClaudeSDKClient; the tests pass a fake)."""
    env = make_env()
    reader = data.Data(client_factory, now=now, **({"clock": clock} if clock else {}))
    keys = passkeys or auth.Passkeys()
    chats = chat.ChatManager(keys, client_factory=chat_client_factory)
    dev_login = os.environ.get("CC_DEV_LOGIN", "").strip() or None
    if bind_host != LOOPBACK or uds or port is None or int(port) == auth.SERVICE_PORT:
        dev_login = None
    if dev_login:
        log.warning("CC_DEV_LOGIN is set: requests are treated as %s (local check only)", dev_login)
    checkout_now = checkout or checkout_branch
    warning = checkout_warning(checkout_now())

    def passkey_info():
        try:
            return auth.passkey_summary(auth.load_config())
        except (OSError, ValueError):
            return auth.passkey_summary({})

    def render(request, name, **ctx):
        ctx.setdefault("action_day", data.lm.today(reader.now()).isoformat())  # the date fields' default and max
        page = env.get_template(name).render(request=request, path=request.url.path, **ctx)
        return HTMLResponse(page)

    def proposals():
        try:
            return data.Panel(value=actions.list_proposals())
        except Exception as e:  # the type only
            return data.Panel(error=type(e).__name__)

    async def healthz(request):
        return PlainTextResponse("ok")

    async def today(request):
        props = proposals()
        waiting = [p for p in (props.value or []) if not p["applied"] and not p["problem"]] if props.ok else []
        books = actions.books_status()
        ctx = reader.today_page()
        ctx["attention"] += len(waiting) + (1 if books["dry_run"] and not books["approved_at"] else 0)
        return render(request, "today.html", title="Today", passkey_info=passkey_info(), checkout_warning=warning,
                      proposals=props, waiting=waiting, books=books, **ctx)

    async def money(request):
        return render(request, "money.html", title="Money", **reader.money_page())

    async def passkeys_page(request):
        info = passkey_info()
        return render(request, "passkeys.html", title="Passkeys", count=info["count"], passkey_info=info,
                      register_action=auth.REGISTER.name, check_action=auth.CHECK.name, stamp=data.stamp(reader.now()))

    def page_or_404(request, name, ctx, **extra):
        if ctx is None:
            return PlainTextResponse("Not found", status_code=404)
        return render(request, name, **extra, **ctx)

    async def bookings(request):
        q = request.query_params
        return render(request, "bookings.html", title="Bookings",
                      **reader.bookings_page(q.get("when", "upcoming"), q.get("state", "")))

    async def booking(request):
        ref = request.path_params["ref"]
        return page_or_404(request, "booking.html", reader.booking_page(ref), title=f"Booking {ref}")

    async def enquiries(request):
        return render(request, "enquiries.html", title="Enquiries", **reader.enquiries_page())

    async def enquiry(request):
        eid = request.path_params["eid"]
        return page_or_404(request, "enquiry.html", reader.enquiry_page(eid), title=f"Enquiry {eid}")

    async def singers(request):
        return render(request, "singers.html", title="Singers", **reader.singers_page())

    async def marketing(request):
        return render(request, "marketing.html", title="Marketing", proposals=proposals(), **reader.marketing_page())

    async def calendar(request):
        q = request.query_params
        return render(request, "calendar.html", title="Calendar", **reader.calendar_page(q.get("view", "month"),
                                                                                        q.get("date")))

    async def search(request):
        return render(request, "search.html", title="Search", **reader.search_page(request.query_params.get("q", "")))

    async def reports(request):
        return render(request, "reports.html", title="Reports", **reader.reports_page())

    async def report(request):
        name = request.path_params["name"]
        return page_or_404(request, "report.html", reader.report_page(name), title=f"Report {name[:10]}")

    async def health(request):
        return render(request, "health.html", title="Runs and health", **reader.health_page(checkout_now()))

    async def todo_list(request):
        return render(request, "todo.html", title="To-do", **reader.todo_page())

    async def todo_tick(request):
        if request.headers.get("content-type", "").split(";")[0].strip() != "application/x-www-form-urlencoded":
            return PlainTextResponse("Bad request", status_code=400)
        raw = await request.body()
        if len(raw) > FORM_MAX:
            return PlainTextResponse("Bad request", status_code=400)
        try:
            fields = urllib.parse.parse_qs(raw.decode("utf-8"), max_num_fields=4, strict_parsing=True)
        except (UnicodeDecodeError, ValueError):
            return PlainTextResponse("Bad request", status_code=400)
        form = {k: v[0] for k, v in fields.items() if len(v) == 1}
        try:
            actions.REGISTRY["todo-tick"].execute(form, user(request))
        except actions.ActionError as e:
            return PlainTextResponse(e.reason, status_code=e.status)
        return RedirectResponse("/todo", status_code=303)

    async def exports(request):
        return render(request, "exports.html", title="Exports", stamp=data.stamp(reader.now()),
                      names=reader.EXPORTS)

    async def export(request):
        try:
            found = reader.export(request.path_params["name"])
        except RuntimeError as e:
            return PlainTextResponse(f"couldn't load ({e})", status_code=503)
        if found is None:
            return PlainTextResponse("Not found", status_code=404)
        filename, head, rows = found
        out = io.StringIO()
        w = csv.writer(out, lineterminator="\r\n")
        w.writerow(head)
        for r in rows:
            w.writerow([models.csv_safe(v) for v in r])
        return Response(out.getvalue().encode("utf-8"), media_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition": f'attachment; filename="{filename}"'})

    async def more(request):
        return render(request, "more.html", title="More", stamp=data.stamp(reader.now()))

    async def activity(request):
        q = request.query_params
        name = q.get("action", "")
        name = name if name in actions.REGISTRY or name in chat.AUDIT_NAMES else ""
        result = q.get("result", "")
        result = result if result in ACTIVITY_RESULTS else ""
        text = q.get("q", "").strip()[:80]
        try:
            entries = data.Panel(value=actions.read_audit())
        except Exception as e:  # the type only
            entries = data.Panel(error=type(e).__name__)
        try:
            chain = data.Panel(value=actions.audit_status())
        except Exception as e:  # the type only
            chain = data.Panel(error=type(e).__name__)
        shown = []
        for e in entries.value or []:
            if name and e.get("action") != name:
                continue
            if result and not str(e.get("result", "")).startswith(result):
                continue
            if text and text.casefold() not in json.dumps(e, ensure_ascii=False).casefold():
                continue
            shown.append(e)
        return render(request, "activity.html", title="Activity", stamp=data.stamp(reader.now()), entries=entries,
                      shown=shown, names=sorted([*actions.REGISTRY, *chat.AUDIT_NAMES]), results=ACTIVITY_RESULTS, action_name=name,
                      result=result, text=text, chain=chain)

    def guarded(fn, *args):
        """Refusals pass through; any other failure (an unreadable ledger, say) becomes its type name only."""
        try:
            return fn(*args)
        except (actions.ActionError, auth.PasskeyError):
            raise
        except Exception as e:
            log.warning("action failed: %s", type(e).__name__)
            raise actions.ActionError(f"couldn't run ({type(e).__name__})", status=503) from None

    async def action_payload(request, name):
        if name not in actions.ROUTED:
            raise actions.ActionError("unknown action", status=404)
        if request.headers.get("content-type", "").split(";")[0].strip() != "application/json":
            raise actions.ActionError("malformed request")
        raw = await request.body()
        if len(raw) > JSON_MAX:
            raise actions.ActionError("request too large")
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            raise actions.ActionError("malformed request") from None
        if not isinstance(payload, dict) or not set(payload) <= {"input", "credential"}:
            raise actions.ActionError("malformed request")
        return actions.REGISTRY[name], payload

    async def action_preview(request):
        """The server-built summary (plain English plus the exact command) and, for a passkey action, assertion
        options whose challenge is bound to that summary. Nothing runs."""
        defn, payload = await action_payload(request, request.path_params["name"])
        cleaned = await run_in_threadpool(guarded, defn.validate, payload.get("input"))
        action = auth.Action(defn.name, defn.preview(cleaned))
        body = {"action": defn.name, "title": defn.title, "summary": action.summary, "command": defn.command(cleaned),
                "passkey": defn.passkey}
        if hasattr(defn, "code"):  # an Ads change set: the script's code change, bound to the summary by its sha256
            body["code"] = defn.code(cleaned)
        if defn.passkey:
            body["options"] = keys.assertion_options(action)
        return JSONResponse(body)

    async def action_run(request):
        defn, payload = await action_payload(request, request.path_params["name"])
        result = await run_in_threadpool(guarded, actions.run_action, defn, payload.get("input"), user(request),
                                         payload.get("credential"), keys)
        if getattr(defn, "clears_cache", False):
            reader.clear_caches()
        return JSONResponse(result.as_json())

    async def action_error(request, exc):
        return JSONResponse({"error": exc.reason}, status_code=exc.status)

    # ------------------------------------------------------------ chat (phase 4)

    async def read_form(request, allowed):
        if request.headers.get("content-type", "").split(";")[0].strip() != "application/x-www-form-urlencoded":
            raise chat.ChatError("malformed request")
        raw = await request.body()
        if len(raw) > FORM_MAX:
            raise chat.ChatError("malformed request")
        try:
            fields = urllib.parse.parse_qs(raw.decode("utf-8"), max_num_fields=8, keep_blank_values=True)
        except (UnicodeDecodeError, ValueError):
            raise chat.ChatError("malformed request") from None
        if not set(fields) <= allowed or any(len(v) != 1 for v in fields.values()):
            raise chat.ChatError("malformed request")
        return {k: v[0] for k, v in fields.items()}

    async def read_json(request, allowed):
        if request.headers.get("content-type", "").split(";")[0].strip() != "application/json":
            raise chat.ChatError("malformed request")
        raw = await request.body()
        if len(raw) > JSON_MAX:
            raise chat.ChatError("request too large")
        try:
            payload = json.loads(raw.decode("utf-8")) if raw else {}
        except (UnicodeDecodeError, ValueError):
            raise chat.ChatError("malformed request") from None
        if not isinstance(payload, dict) or not set(payload) <= allowed:
            raise chat.ChatError("malformed request")
        return payload

    def hand_refs():
        try:
            hand = reader.today_page()["hand"]
            rows = hand.value if hand.ok else (hand.stale or [])
            return sorted({str(r.get("ref")) for r in rows if actions.REF_RE.fullmatch(str(r.get("ref", "")))})
        except Exception as e:  # the picker is a convenience; the page still renders
            log.warning("hand refs: %s", type(e).__name__)
            return []

    def chat_common():
        try:
            tasks = chat.scheduled_tasks()
        except OSError:
            tasks = []
        return {"stamp": data.stamp(reader.now()), "conversations": chat.list_conversations(),
                "tasks": tasks, "handoffs": chat.handoffs(), "sdk_ok": chat.sdk is not None,
                "task_note": chat.TASK_DIFFERENCES}

    async def chat_list(request):
        return render(request, "chat_list.html", title="Chat", **chat_common())

    async def chat_page(request):
        conv = chats.get(request.path_params["cid"])
        if conv is None:
            return PlainTextResponse("Not found", status_code=404)
        return render(request, "chat.html", title=conv.meta.get("title") or "Chat", conv=conv, totals=conv.totals(),
                      quick=chat.QUICK_PROMPTS, hand_refs=await run_in_threadpool(hand_refs),
                      hand_prompt=chat.HAND_PROMPT, turn_choices=chat.MAX_TURNS_CHOICES,
                      default_turns=chat.DEFAULT_MAX_TURNS, **chat_common())

    async def chat_new(request):
        form = await read_form(request, {"kind", "task", "item"})
        kind = form.get("kind", "blank")
        u = user(request)
        if kind == "blank":
            conv = chats.create(u)
        elif kind == "task":
            name = form.get("task", "")
            prompt = await run_in_threadpool(chat.task_prompt, name)
            conv = chats.create(u, "task", f"Run now: {name}", prompt)
            chats.send(conv, prompt, u, max_turns=chat.TASK_MAX_TURNS)
        elif kind == "handoff":
            h = next((h for h in chat.handoffs() if h["item"] == form.get("item")), None)
            if h is None:
                raise chat.ChatError("nothing approved to run", status=404)
            if h["started"]:
                raise chat.ChatError("already started", status=409)
            prompt = chat.handoff_prompt(h)
            cid = chat.new_id()
            chat.record_handoff(h["item"], cid, u)
            conv = chats.create(u, "handoff", f"Run approved: {h['label']}", prompt, cid=cid)
            chats.send(conv, prompt, u, max_turns=chat.HANDOFF_MAX_TURNS)
        else:
            raise chat.ChatError("malformed request")
        if wants_json(request):  # chat.js posts the form with fetch(), which sends the real Origin (see chat.js)
            return JSONResponse({"url": f"/chat/{conv.id}"})
        return RedirectResponse(f"/chat/{conv.id}", status_code=303)

    async def chat_message(request):
        conv = chats.require(request.path_params["cid"])
        payload = await read_json(request, {"text", "max_turns"})
        chats.send(conv, payload.get("text"), user(request), payload.get("max_turns", chat.DEFAULT_MAX_TURNS))
        return JSONResponse({"ok": True})

    async def chat_stop(request):
        conv = chats.require(request.path_params["cid"])
        await read_json(request, set())
        chats.stop(conv, user(request))
        return JSONResponse({"ok": True})

    async def chat_stream(request):
        conv = chats.require(request.path_params["cid"])
        after = request.headers.get("last-event-id") or request.query_params.get("after") or "0"
        after = int(after) if after.isdigit() and len(after) < 10 else 0
        return StreamingResponse(chats.stream(conv, after), media_type="text/event-stream",
                                 headers={"X-Accel-Buffering": "no"})

    async def card_options(request):
        conv = chats.require(request.path_params["cid"])
        payload = await read_json(request, {"digest"})
        return JSONResponse(chats.card_options(conv, request.path_params["card"], payload.get("digest")))

    async def card_approve(request):
        conv = chats.require(request.path_params["cid"])
        payload = await read_json(request, {"digest", "credential"})
        u = user(request)
        card, action = chats.card_check(conv, request.path_params["card"], payload.get("digest"), u)
        if payload.get("credential") is None:
            chats.refuse_passkey(conv, card, action, "no passkey", u)
            raise chat.ChatError("approving needs a passkey", status=403)
        try:
            passkey_id = await run_in_threadpool(keys.require_fresh_assertion, payload["credential"], action)
        except auth.PasskeyError as e:
            chats.refuse_passkey(conv, card, action, e.reason, u)
            raise
        chats.approve_verified(conv, card, action, passkey_id, u)
        return JSONResponse({"ok": True})

    async def card_deny(request):
        conv = chats.require(request.path_params["cid"])
        await read_json(request, set())
        chats.deny(conv, request.path_params["card"], user(request))
        return JSONResponse({"ok": True})

    def wants_json(request):
        return request.headers.get("accept", "").split(",")[0].strip() == "application/json"

    async def chat_error(request, exc):
        if request.url.path == "/chat/new" and not wants_json(request):
            return PlainTextResponse(exc.reason, status_code=exc.status)
        return JSONResponse({"error": exc.reason}, status_code=exc.status)

    async def body(request):
        try:
            payload = await request.json()
        except ValueError:
            raise auth.PasskeyError("malformed request", status=400) from None
        if not isinstance(payload, dict):
            raise auth.PasskeyError("malformed request", status=400)
        return payload

    def user(request):
        return request.state.user

    async def register_options(request):
        payload = await body(request)
        u = user(request)
        return JSONResponse(keys.registration_options(u["login"], u["name"], payload.get("assertion"),
                                                      payload.get("bootstrap")))

    async def register(request):
        payload = await body(request)
        keys.finish_registration(payload.get("credential"), user(request)["login"], payload.get("label", ""),
                                 payload.get("bootstrap"))
        return JSONResponse({"ok": True})

    async def assert_options(request):
        payload = await body(request)
        # the request names the action; its summary is the server's (auth.Action), never the client's text
        return JSONResponse(keys.assertion_options(auth.action_named(payload.get("action"))))

    async def assert_check(request):
        payload = await body(request)
        keys.require_fresh_assertion(payload.get("credential"), auth.action_named(payload.get("action")))
        return JSONResponse({"ok": True})

    async def passkey_error(request, exc):
        return JSONResponse({"error": exc.reason}, status_code=exc.status)

    async def not_found(request, exc):
        return PlainTextResponse("Not found", status_code=404)

    routes = [
        Route("/healthz", healthz),
        Route("/", today),
        Route("/money", money),
        Route("/passkeys", passkeys_page),
        Route("/bookings", bookings),
        Route("/bookings/{ref}", booking),
        Route("/enquiries", enquiries),
        Route("/enquiries/{eid}", enquiry),
        Route("/singers", singers),
        Route("/marketing", marketing),
        Route("/calendar", calendar),
        Route("/search", search),
        Route("/reports", reports),
        Route("/reports/{name}", report),
        Route("/health", health),
        Route("/todo", todo_list),
        Route("/todo/tick", todo_tick, methods=["POST"]),
        Route("/exports", exports),
        Route("/exports/{name}.csv", export),
        Route("/more", more),
        Route("/activity", activity),
        Route("/actions/{name}/preview", action_preview, methods=["POST"]),
        Route("/actions/{name}/run", action_run, methods=["POST"]),
        Route("/chat", chat_list),
        Route("/chat/new", chat_new, methods=["POST"]),
        Route("/chat/{cid}", chat_page),
        Route("/chat/{cid}/message", chat_message, methods=["POST"]),
        Route("/chat/{cid}/stop", chat_stop, methods=["POST"]),
        Route("/chat/{cid}/stream", chat_stream),
        Route("/chat/{cid}/cards/{card}/options", card_options, methods=["POST"]),
        Route("/chat/{cid}/cards/{card}/approve", card_approve, methods=["POST"]),
        Route("/chat/{cid}/cards/{card}/deny", card_deny, methods=["POST"]),
        Route("/auth/passkey/register/options", register_options, methods=["POST"]),
        Route("/auth/passkey/register", register, methods=["POST"]),
        Route("/auth/passkey/assert/options", assert_options, methods=["POST"]),
        Route("/auth/passkey/assert", assert_check, methods=["POST"]),
        Mount("/static", app=StaticFiles(directory=HERE / "static"), name="static"),
    ]
    app = CommandCentre(
        routes=routes,
        middleware=[Middleware(auth.IdentityMiddleware, dev_login=dev_login, dev_port=port, uds=bool(uds))],
        exception_handlers={auth.PasskeyError: passkey_error, actions.ActionError: action_error,
                            chat.ChatError: chat_error, 404: not_found})
    app.state.dev_login = dev_login
    app.state.passkeys = keys
    app.state.chat = chats
    app.state.checkout_warning = warning
    return app
