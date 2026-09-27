#!/usr/bin/env python3
"""Check what londonchoralservice.com actually serves against the deploy allowlist.

Run after a deploy, and after any change to scripts/stage_site.py or to the
repo's Pages settings. It fails unless:
  - every file the deploy publishes returns 200,
  - every other file in the repo returns 404, and so does each internal
    directory (docs/, logs/, scripts/, ...),
  - every URL in the live sitemap.xml returns 200,
  - http:// and the github.io address redirect to https://londonchoralservice.com/.

    git fetch origin && python3 scripts/check_live_site.py
    python3 scripts/check_live_site.py --base http://localhost:8000 --ref HEAD

The file lists come from --ref (default origin/main, the deployed branch).
Every request carries a unique query string, so the CDN's ten-minute cache
cannot answer for a deploy that has not reached it yet.
"""
import argparse
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote, urlsplit

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stage_site  # noqa: E402

LIVE = 'https://londonchoralservice.com'
REDIRECTS = [  # (URL, where it must redirect)
    ('http://londonchoralservice.com/', 'https://londonchoralservice.com/'),
    ('https://lucawetherall.github.io/londonchoralservice/', 'https://londonchoralservice.com/'),
]


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


_OPENER = urllib.request.build_opener(_NoRedirect)


def fetch(url, method='HEAD'):
    """(status, Location header, body) without following redirects; status is
    a string when the request itself failed after three tries."""
    request = urllib.request.Request(url, method=method, headers={'User-Agent': 'lcs-deploy-check'})
    for attempt in range(3):
        try:
            with _OPENER.open(request, timeout=30) as r:
                return r.status, r.headers.get('Location'), r.read() if method == 'GET' else b''
        except urllib.error.HTTPError as e:
            return e.code, e.headers.get('Location'), b''
        except (urllib.error.URLError, OSError) as e:
            if attempt == 2:
                return f'request failed: {e}', None, b''
            time.sleep(2 * (attempt + 1))


def tree(ref):
    try:
        out = subprocess.run(['git', 'ls-tree', '-r', '-z', '--name-only', ref],
                             cwd=stage_site.ROOT, capture_output=True, check=True).stdout
    except subprocess.CalledProcessError as e:
        sys.exit(f'check_live_site.py: cannot list {ref}: {e.stderr.decode().strip()}')
    return [p for p in out.decode('utf-8').split('\0') if p]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--base', default=LIVE, help=f'site to check (default {LIVE})')
    ap.add_argument('--ref', default='origin/main', help='git ref whose files were deployed (default origin/main)')
    args = ap.parse_args()
    base = args.base.rstrip('/')
    stamp = f'lcs_verify={int(time.time())}'

    files = tree(args.ref)
    public = [p for p in files if stage_site.is_public(p)]
    internal = [p for p in files if not stage_site.is_public(p)]
    internal_dirs = sorted({p.split('/')[0] + '/' for p in internal if '/' in p}
                           - {p.split('/')[0] + '/' for p in public if '/' in p})

    status, _, body = fetch(f'{base}/sitemap.xml?{stamp}', 'GET')
    if status != 200:
        sys.exit(f'check_live_site.py: {base}/sitemap.xml returned {status}')
    sitemap = [urlsplit(loc).path or '/'
               for loc in re.findall(r'<loc>\s*([^<\s]+)\s*</loc>', body.decode('utf-8'))]

    groups = [
        ('published files', 200, ['/' + p for p in public]),
        ('internal files', 404, ['/' + p for p in internal]),
        ('internal directories', 404, ['/' + d for d in internal_dirs]),
        ('sitemap URLs', 200, sitemap),
    ]
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = [(label, expected, paths,
                    list(pool.map(lambda p: fetch(f'{base}{quote(p)}?{stamp}')[0], paths)))
                   for label, expected, paths in groups]

    failures = 0
    for label, expected, paths, statuses in results:
        wrong = [(p, s) for p, s in zip(paths, statuses) if s != expected]
        print(f'{len(paths) - len(wrong):4d}/{len(paths):<4d} {label} returned {expected}')
        for path, got in wrong[:25]:
            print(f'           {path} returned {got}')
        if len(wrong) > 25:
            print(f'           … and {len(wrong) - 25} more')
        failures += len(wrong)

    if base == LIVE:
        for url, target in REDIRECTS:
            got, location, _ = fetch(url)
            ok = got in (301, 308) and location == target
            print(f'{"   ok" if ok else " FAIL"}      {url} -> {got} {location or ""}')
            failures += not ok

    print(f'\n{"FAILED: " + str(failures) + " unexpected response(s)" if failures else "All checks passed"}'
          f' on {base} (files from {args.ref}).')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
