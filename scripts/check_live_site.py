#!/usr/bin/env python3
"""Check what londonchoralservice.com actually serves against the deploy allowlist.

Run after a deploy, and after any change to scripts/stage_site.py or to the
repo's Pages settings:

    git fetch origin && python3 scripts/check_live_site.py

It requests every file on --ref (default origin/main, the deployed branch):
files that scripts/stage_site.py publishes must return 200, every other file
404. Every URL in the live sitemap.xml must return 200, and http:// and the
github.io address must redirect to https://londonchoralservice.com/.

The CDN in front of GitHub Pages caches answers (files for ten minutes, 404s
sometimes longer) and ignores query strings, so no request can bypass it. A
response's Date minus its Age is when the CDN fetched it. A wrong answer
fetched before the latest github-pages deployment finished is reported as
stale rather than failed. Exit status: 0 all good, 1 failures, 2 only stale
answers or a deploy still running (re-run in ten minutes).

To rehearse on a staged copy instead of the live site:

    python3 scripts/stage_site.py --out /tmp/lcs-site
    python3 -m http.server 8000 -d /tmp/lcs-site        (in another terminal)
    python3 scripts/check_live_site.py --base http://localhost:8000 --ref HEAD
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote, unquote, urlsplit

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stage_site  # noqa: E402

LIVE = 'https://londonchoralservice.com'
REPO = 'lucawetherall/londonchoralservice'
REDIRECTS = [  # (URL, where it must redirect)
    ('http://londonchoralservice.com/', 'https://londonchoralservice.com/'),
    ('https://lucawetherall.github.io/londonchoralservice/', 'https://londonchoralservice.com/'),
]
SETTLE = 30  # seconds after a deploy succeeds during which an answer may still predate it


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


_OPENER = urllib.request.build_opener(_NoRedirect)


def _fetched_at(headers):
    """When the CDN fetched this answer from GitHub Pages: Date minus Age."""
    try:
        date = parsedate_to_datetime(headers['Date']).timestamp()
    except (TypeError, ValueError):
        date = time.time()
    try:
        return date - int(headers.get('Age') or 0)
    except ValueError:
        return date


def fetch(url, method='HEAD'):
    """(status, Location, fetched-at time, body) without following redirects.
    The status is a string when the request itself failed three times."""
    request = urllib.request.Request(url, method=method, headers={'User-Agent': 'lcs-deploy-check'})
    for attempt in range(3):
        try:
            with _OPENER.open(request, timeout=30) as r:
                body = r.read() if method == 'GET' else b''
                return r.status, r.headers.get('Location'), _fetched_at(r.headers), body
        except urllib.error.HTTPError as e:
            return e.code, e.headers.get('Location'), _fetched_at(e.headers), b''
        except (urllib.error.URLError, OSError) as e:
            if attempt == 2:
                return f'request failed: {e}', None, time.time(), b''
            time.sleep(2 * (attempt + 1))


def latest_deploy():
    """(state, finished-at Unix time) of the newest github-pages deployment,
    from the public GitHub API, or (None, None) if it cannot be read."""
    def get(url):
        request = urllib.request.Request(url, headers={
            'Accept': 'application/vnd.github+json', 'User-Agent': 'lcs-deploy-check'})
        with urllib.request.urlopen(request, timeout=30) as r:
            return json.load(r)
    try:
        deployment = get(f'https://api.github.com/repos/{REPO}/deployments'
                         f'?environment=github-pages&per_page=1')[0]
        status = get(deployment['statuses_url'] + '?per_page=1')[0]
        when = datetime.strptime(status['created_at'], '%Y-%m-%dT%H:%M:%SZ')
        return status['state'], when.replace(tzinfo=timezone.utc).timestamp()
    except (OSError, ValueError, LookupError) as e:
        print(f'Note: could not read the latest deployment ({e}); stale CDN answers will count as failures.')
        return None, None


def tree(ref):
    try:
        out = subprocess.run(['git', 'ls-tree', '-r', '-z', '--name-only', ref],
                             cwd=stage_site.ROOT, capture_output=True, check=True).stdout
    except subprocess.CalledProcessError as e:
        sys.exit(f'check_live_site.py: cannot list {ref}: {e.stderr.decode().strip()}')
    return [p for p in out.decode('utf-8', errors='surrogateescape').split('\0') if p]


def _when(t):
    return datetime.fromtimestamp(t, timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--base', default=LIVE, help=f'site to check (default {LIVE})')
    ap.add_argument('--ref', default='origin/main', help='git ref that was deployed (default origin/main)')
    args = ap.parse_args()
    base = args.base.rstrip('/')

    since = None
    if base == LIVE:
        state, since = latest_deploy()
        if state and state != 'success':
            print(f'The latest github-pages deployment is "{state}". Re-run once it has succeeded.')
            return 2
        if since:
            print(f'Latest github-pages deployment succeeded at {_when(since)}.')

    files = tree(args.ref)
    public = [p for p in files if stage_site.is_public(p)]
    internal = [p for p in files if not stage_site.is_public(p)]

    status, _, _, body = fetch(f'{base}/sitemap.xml', 'GET')
    if status != 200:
        print(f'{base}/sitemap.xml returned {status}.')
        return 1
    sitemap = [unquote(urlsplit(loc).path) or '/'
               for loc in re.findall(r'<loc>\s*([^<\s]+)\s*</loc>', body.decode('utf-8'))]

    groups = [('published files', 200, public), ('internal files', 404, internal),
              ('sitemap URLs', 200, sitemap)]
    with ThreadPoolExecutor(max_workers=8) as pool:
        answers = [list(pool.map(lambda p: fetch(base + '/' + quote(p.lstrip('/'))), paths))
                   for _, _, paths in groups]

    failures = stale = 0
    for (label, expected, paths), got in zip(groups, answers):
        wrong = [(p, status, at) for p, (status, _, at, _) in zip(paths, got) if status != expected]
        print(f'{len(paths) - len(wrong):4d}/{len(paths):<4d} {label} returned {expected}')
        if label == 'internal files':
            top = lambda p: p.split('/')[0] + '/' if '/' in p else 'root files'
            total, bad = Counter(map(top, paths)), Counter(top(p) for p, _, _ in wrong)
            print('           ' + ' · '.join(f'{d} {total[d] - bad[d]}/{total[d]}' for d in sorted(total)))
        for i, (path, status, at) in enumerate(wrong):
            old = since is not None and at < since + SETTLE
            stale += old
            failures += not old
            if i < 25:
                note = f' (stale: cached at {_when(at)}, before the deploy)' if old else ''
                print(f'           /{path.lstrip("/")} returned {status}{note}')
        if len(wrong) > 25:
            print(f'           … and {len(wrong) - 25} more')

    if base == LIVE:
        for url, target in REDIRECTS:
            status, location, _, _ = fetch(url)
            ok = status in (301, 308) and location == target
            print(f'{"   ok" if ok else " FAIL"}      {url} -> {status} {location or ""}')
            failures += not ok

    where = f'on {base} (files from {args.ref})'
    if failures:
        print(f'\nFAILED: {failures} wrong answer(s) {where}.')
        return 1
    if stale:
        print(f'\nINCONCLUSIVE: {stale} answer(s) came from the CDN cache and predate the deploy. '
              f'Re-run in ten minutes.')
        return 2
    print(f'\nAll checks passed {where}.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
