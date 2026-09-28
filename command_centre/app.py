"""The Command Centre web app: routes, templates and middleware.

    create_app()  ->  Starlette app (python -m command_centre serves it on 127.0.0.1:8765, or on a Unix socket)

Phase 1 is read-only: Today, Money and Passkeys pages, the passkey endpoints and /healthz. See
docs/superpowers/specs/2026-09-28-command-centre-design.md and docs/superpowers/plans/2026-09-28-command-centre.md.
"""

import datetime
import json
import logging
import os
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, PlainTextResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from . import auth, data

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
LOOPBACK = "127.0.0.1"
log = logging.getLogger("command_centre")

NAV = [("Today", "/"), ("Money", "/money")]
SOON = ["Bookings", "Enquiries", "Singers", "Marketing", "Calendar", "Search", "Reports", "Health", "To-do"]
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


def make_env():
    env = Environment(loader=FileSystemLoader(HERE / "templates"), autoescape=select_autoescape(default=True),
                      trim_blocks=True, lstrip_blocks=True)
    env.filters.update(gbp=gbp, day=day, london_day=london_day, last4=last4, state_words=state_words,
                       state_tone=state_tone)
    env.globals.update(NAV=NAV, SOON=SOON, HTMX_CONFIG=HTMX_CONFIG)
    return env


class CommandCentre(Starlette):
    """Starlette with the security headers outside everything, so even a 500 from ServerErrorMiddleware has them."""

    def build_middleware_stack(self):
        return auth.SecurityHeadersMiddleware(super().build_middleware_stack())


def create_app(client_factory=data.default_client, now=None, clock=None, passkeys=None, bind_host=None, port=None,
               uds=None, checkout=None):
    """The app. `bind_host`, `port` and `uds` say how __main__ serves it. CC_DEV_LOGIN is honoured only on
    127.0.0.1, on a port other than the service's 8765, and never on the Unix socket. `checkout` returns the
    serving checkout's branch (default: read from .git)."""
    env = make_env()
    reader = data.Data(client_factory, now=now, **({"clock": clock} if clock else {}))
    keys = passkeys or auth.Passkeys()
    dev_login = os.environ.get("CC_DEV_LOGIN", "").strip() or None
    if bind_host != LOOPBACK or uds or port is None or int(port) == auth.SERVICE_PORT:
        dev_login = None
    if dev_login:
        log.warning("CC_DEV_LOGIN is set: requests are treated as %s (local check only)", dev_login)
    warning = checkout_warning((checkout or checkout_branch)())

    def passkey_info():
        try:
            return auth.passkey_summary(auth.load_config())
        except (OSError, ValueError):
            return auth.passkey_summary({})

    def render(request, name, **ctx):
        page = env.get_template(name).render(request=request, path=request.url.path, **ctx)
        return HTMLResponse(page)

    async def healthz(request):
        return PlainTextResponse("ok")

    async def today(request):
        return render(request, "today.html", title="Today", passkey_info=passkey_info(), checkout_warning=warning,
                      **reader.today_page())

    async def money(request):
        return render(request, "money.html", title="Money", **reader.money_page())

    async def passkeys_page(request):
        info = passkey_info()
        return render(request, "passkeys.html", title="Passkeys", count=info["count"], passkey_info=info,
                      register_action=auth.REGISTER.name, check_action=auth.CHECK.name, stamp=data.stamp(reader.now()))

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
        Route("/auth/passkey/register/options", register_options, methods=["POST"]),
        Route("/auth/passkey/register", register, methods=["POST"]),
        Route("/auth/passkey/assert/options", assert_options, methods=["POST"]),
        Route("/auth/passkey/assert", assert_check, methods=["POST"]),
        Mount("/static", app=StaticFiles(directory=HERE / "static"), name="static"),
    ]
    app = CommandCentre(
        routes=routes,
        middleware=[Middleware(auth.IdentityMiddleware, dev_login=dev_login, dev_port=port, uds=bool(uds))],
        exception_handlers={auth.PasskeyError: passkey_error, 404: not_found})
    app.state.dev_login = dev_login
    app.state.passkeys = keys
    app.state.checkout_warning = warning
    return app
