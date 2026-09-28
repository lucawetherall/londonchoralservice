"""The Command Centre web app: routes, templates and middleware.

    create_app()  ->  Starlette app (python -m command_centre serves it on 127.0.0.1:8765)

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


def make_env():
    env = Environment(loader=FileSystemLoader(HERE / "templates"), autoescape=select_autoescape(default=True),
                      trim_blocks=True, lstrip_blocks=True)
    env.filters.update(gbp=gbp, day=day, last4=last4, state_words=state_words, state_tone=state_tone)
    env.globals.update(NAV=NAV, SOON=SOON, HTMX_CONFIG=HTMX_CONFIG)
    return env


class CommandCentre(Starlette):
    """Starlette with the security headers outside everything, so even a 500 from ServerErrorMiddleware has them."""

    def build_middleware_stack(self):
        return auth.SecurityHeadersMiddleware(super().build_middleware_stack())


def create_app(client_factory=data.default_client, now=None, clock=None, passkeys=None, bind_host=None):
    """The app. `bind_host` is what __main__ binds to; CC_DEV_LOGIN is honoured only when it is 127.0.0.1."""
    env = make_env()
    reader = data.Data(client_factory, now=now, **({"clock": clock} if clock else {}))
    keys = passkeys or auth.Passkeys()
    dev_login = os.environ.get("CC_DEV_LOGIN", "").strip() or None
    if bind_host != LOOPBACK:
        dev_login = None
    if dev_login:
        log.warning("CC_DEV_LOGIN is set: requests are treated as %s (local check only)", dev_login)

    def render(request, name, **ctx):
        page = env.get_template(name).render(request=request, path=request.url.path, **ctx)
        return HTMLResponse(page)

    async def healthz(request):
        return PlainTextResponse("ok")

    async def today(request):
        return render(request, "today.html", title="Today", **reader.today_page())

    async def money(request):
        return render(request, "money.html", title="Money", **reader.money_page())

    async def passkeys_page(request):
        try:
            cfg = auth.load_config()
            count = len(cfg.get("passkeys") or [])
        except (OSError, ValueError):
            count = 0
        now = reader.now()
        return render(request, "passkeys.html", title="Passkeys", count=count, stamp=data.stamp(now))

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
        return JSONResponse(keys.registration_options(u["login"], u["name"], payload.get("assertion")))

    async def register(request):
        payload = await body(request)
        keys.finish_registration(payload.get("credential"), user(request)["login"], payload.get("label", ""))
        return JSONResponse({"ok": True})

    async def assert_options(request):
        payload = await body(request)
        return JSONResponse(keys.assertion_options(payload.get("action")))

    async def assert_check(request):
        payload = await body(request)
        keys.require_fresh_assertion(payload.get("credential"), payload.get("action"))
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
        middleware=[Middleware(auth.IdentityMiddleware, dev_login=dev_login)],
        exception_handlers={auth.PasskeyError: passkey_error, 404: not_found})
    app.state.dev_login = dev_login
    app.state.passkeys = keys
    return app
