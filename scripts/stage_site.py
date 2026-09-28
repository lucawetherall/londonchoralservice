#!/usr/bin/env python3
"""Select the files londonchoralservice.com publishes, check them, and stage them.

The repo is public and keeps internal files next to the site (docs/, logs/,
scripts/, data/, tests/, partials/, graphify-out/, .claude/, Markdown notes).
The deploy workflow (.github/workflows/deploy-pages.yml) publishes only the
files selected here: files that match PUBLIC and nothing in PRIVATE. They are
copied byte for byte; this script never builds or edits a page. build.sh does
the building, locally, and its output is committed.

    python3 scripts/stage_site.py                      check only (build.sh runs this)
    python3 scripts/stage_site.py --list               check, and print every published file
    python3 scripts/stage_site.py --out /tmp/lcs-site  check, then copy the site there

Any failure exits 1 and stages nothing:
  1. Every file is published or internal: never both, never neither. Hidden
     files and names with control characters count as internal, and a
     published file may not be a symlink.
  2. Every sitemap.xml URL has a published file behind it.
  3. Every same-site page or asset a published file references is published:
     an allowlist gap if the file exists, a broken link if it does not.
  4. The files browsers and crawlers fetch by name are published.
"""
import argparse
import os
import posixpath
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from html.parser import HTMLParser
from urllib.parse import unquote, urljoin, urlsplit

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = 'https://londonchoralservice.com/'
HOSTS = {'londonchoralservice.com', 'www.londonchoralservice.com'}

# What the site publishes. '*' matches within one directory, '**' across any
# number, '{a,b}' either. A new directory of pages, a new asset type, or a new
# root file the site must serve needs a line here: build.sh fails until then.
PUBLIC = [
    # Pages
    '*.html',                  # root pages, including 404.html
    'areas/**/*.html',
    'compare/**/*.html',
    'destinations/**/*.html',
    'music-guides/**/*.html',
    # What the pages load, by type
    'assets/**/*.{png,jpg,jpeg,webp,avif,gif,svg,ico}',
    'css/**/*.css',
    'fonts/**/*.{woff2,woff}',
    'js/**/*.js',
    # Fetched by name by browsers, crawlers and search engines
    'favicon.ico',
    'robots.txt',
    'sitemap.xml',
    'site.webmanifest',
    'llms.txt',
    'llms-full.txt',
    '4751d098385ed7e02df93e8b2f957673.txt',  # IndexNow key, see scripts/indexnow-ping.py
    'CNAME',
]

# Internal: never published, whatever PUBLIC says. Matched ignoring case.
# A new internal file that matches neither list fails the build until it is
# added here (or to PUBLIC, if the site should serve it).
PRIVATE = [
    'logs/**', 'docs/**', 'scripts/**', 'data/**', 'tests/**', 'partials/**', 'graphify-out/**',
    'command_centre/**',  # the owner's private web app: code and templates, never served by Pages
    '**/*.md', '**/*.py', '**/*.sh', '**/*.yml', '**/*.yaml', '**/*.json', '**/*.csv',
]

# Requested by name, never linked: the home page, GitHub Pages' not-found page,
# robots.txt and the browser's default favicon. The IndexNow key file is added
# by indexnow_keys().
REQUIRED = ['index.html', '404.html', 'robots.txt', 'favicon.ico']


def _compile(pattern, flags=0):
    """Glob to regex: '*' and '?' stay within one path segment, '**/' spans
    zero or more directories, a trailing '**' matches everything below, and
    '{a,b}' matches either alternative."""
    out, i, in_braces = [], 0, False
    while i < len(pattern):
        c = pattern[i]
        if pattern.startswith('**/', i):
            out.append('(?:.*/)?')
            i += 3
            continue
        if pattern.startswith('**', i):
            out.append('.*')
            i += 2
            continue
        if c == '*':
            out.append('[^/]*')
        elif c == '?':
            out.append('[^/]')
        elif c == '{':
            out.append('(?:')
            in_braces = True
        elif c == '}' and in_braces:
            out.append(')')
            in_braces = False
        elif c == ',' and in_braces:
            out.append('|')
        else:
            out.append(re.escape(c))
        i += 1
    return re.compile(''.join(out) + r'\Z', flags | re.DOTALL)


_PUBLIC = [(p, _compile(p)) for p in PUBLIC]
_PRIVATE = [(p, _compile(p, re.IGNORECASE)) for p in PRIVATE]


def _first_match(path, compiled):
    return next((pattern for pattern, rx in compiled if rx.match(path)), None)


def refusal(path):
    """Why `path` is internal, or None."""
    if re.search(r'[\x00-\x1f\x7f]', path):
        return 'its name contains a control character'
    if any(part.startswith('.') for part in path.split('/')):
        return 'it is a hidden file'
    pattern = _first_match(path, _PRIVATE)
    return f"it matches PRIVATE '{pattern}'" if pattern else None


def is_public(path):
    return _first_match(path, _PUBLIC) is not None and refusal(path) is None


def _show(path):
    return path if path.isprintable() else repr(path)


def _git(*args):
    return subprocess.run(['git', *args], cwd=ROOT, capture_output=True, check=True).stdout


def repo_files():
    """Tracked files plus new files not yet added, so a page made before
    `git add` is checked too. CI checks out a clean tree, where this is
    exactly the committed files. A copy of the repo without its .git (as
    tests/test_register_generators.py makes) is checked file by file on disk,
    never against the file list of some enclosing repo."""
    try:
        top = _git('rev-parse', '--show-toplevel').decode().strip()
        in_git = os.path.realpath(top) == os.path.realpath(ROOT)
    except (OSError, subprocess.CalledProcessError):
        in_git = False
    if in_git:
        out = _git('ls-files', '-z', '--cached', '--others', '--exclude-standard')
        paths = {p for p in out.decode('utf-8', errors='surrogateescape').split('\0') if p}
    else:
        paths = set()
        for folder, dirs, names in os.walk(ROOT):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('__pycache__', 'node_modules')]
            rel = os.path.relpath(folder, ROOT).replace(os.sep, '/')
            paths.update(n if rel == '.' else f'{rel}/{n}' for n in names if not n.startswith('.'))
    return sorted(p for p in paths if os.path.lexists(os.path.join(ROOT, p)))


def indexnow_keys(files):
    """Root-level key files, found by the same rule as scripts/indexnow-ping.py."""
    keys = []
    for path in files:
        stem, ext = os.path.splitext(path)
        if '/' in path or ext != '.txt' or not re.fullmatch(r'[0-9a-fA-F-]{32,36}', stem):
            continue
        with open(os.path.join(ROOT, path), encoding='utf-8', errors='replace') as f:
            if f.read().strip() == stem:
                keys.append(path)
    return keys


# ── references ──────────────────────────────────────────────────────────────

ABS_URL = re.compile(r'https?://(?:www\.)?londonchoralservice\.com(?![\w.-])[^\s"\'<>()\[\]\\,]*')
QUOTED_PATH = re.compile(r'\\?(["\'])(/[^"\'\s<>\\]*)\\?\1')  # also \"/x.html\" inside JSON-LD
CSS_URL = re.compile(r'url\(\s*["\']?([^"\')]+?)["\']?\s*\)')
CSS_IMPORT = re.compile(r'@import\s+["\']([^"\']+)["\']')
URL_ATTRS = {'href', 'src', 'poster', 'data', 'action', 'formaction', 'background',
             'manifest', 'xlink:href', 'cite', 'longdesc'}
SRCSET_ATTRS = {'srcset', 'imagesrcset'}
# A data-* value is followed as a link when it looks like one, e.g. the form
# pages' data-redirect="thank-you.html?from=wedding" that js/form.js navigates to.
DATA_LINK = re.compile(r'(?:/|\.\.?/|https?://)\S*\Z'
                       r'|[\w%./-]+\.(?:html?|png|jpe?g|webp|avif|gif|svg|ico|pdf|css|js|'
                       r'woff2?|xml|txt|webmanifest|mp3|mp4|webm)(?:[?#]\S*)?\Z')


class _AttrRefs(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.refs = []

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            value = (value or '').strip()
            if not value:
                continue
            if name in URL_ATTRS:
                self.refs.append(value)
            elif name in SRCSET_ATTRS:
                self.refs.extend(c.split()[0] for c in value.split(',') if c.strip())
            elif name == 'content' and value.startswith(('/', 'http://', 'https://')):
                self.refs.append(value)  # og:image, twitter:image, og:url
            elif name == 'style':
                self.refs.extend(CSS_URL.findall(value))
            elif name.startswith('data-') and DATA_LINK.match(value):
                self.refs.append(value)


def references(path):
    """Every URL a published file points at, as written (relative or absolute)."""
    ext = os.path.splitext(path)[1].lower()
    if ext not in {'.html', '.css', '.js', '.webmanifest', '.xml', '.txt'}:
        return set()
    with open(os.path.join(ROOT, path), encoding='utf-8', errors='replace') as f:
        text = f.read()
    refs = {m.rstrip('.:;!?') for m in ABS_URL.findall(text)}
    if ext == '.html':
        parser = _AttrRefs()
        parser.feed(text)
        refs.update(parser.refs)
    if ext in {'.html', '.css'}:
        refs.update(CSS_URL.findall(text))
        refs.update(CSS_IMPORT.findall(text))
    if ext in {'.html', '.js', '.webmanifest'}:
        refs.update(m[1] for m in QUOTED_PATH.findall(text))
    return refs


def url_path(ref, source):
    """The site path a reference from `source` points at, or None if it leaves the site."""
    if not ref or ref.startswith('#'):
        return None
    parts = urlsplit(urljoin(SITE + source, ref))
    if parts.scheme not in ('http', 'https') or parts.hostname not in HOSTS:
        return None
    return parts.path or '/'


def candidates(path):
    """Files GitHub Pages tries for a URL path, in order: the file itself,
    then the extensionless '.html' form, then a directory index."""
    rel = posixpath.normpath('/' + unquote(path).lstrip('/')).lstrip('/')
    if rel in ('', '.'):
        return ['index.html']
    if path.endswith('/'):
        return [rel + '/index.html']
    return [rel, rel + '.html', rel + '/index.html']


# ── checks ──────────────────────────────────────────────────────────────────

def _sources(files):
    files = sorted(files)
    return ', '.join(files[:3]) + (f' and {len(files) - 3} more' if len(files) > 3 else '')


def check(files):
    """Returns (published files, errors)."""
    errors, published = [], []
    for path in files:
        selected, why = _first_match(path, _PUBLIC), refusal(path)
        if selected and why:
            errors.append(f'{_show(path)}: PUBLIC selects it, but {why}. Internal files are never '
                          f'published; narrow the PUBLIC pattern.')
        elif selected and os.path.islink(os.path.join(ROOT, path)):
            errors.append(f'{_show(path)}: is a symlink. Commit the file itself.')
        elif selected:
            published.append(path)
        elif not why:
            errors.append(f'{_show(path)}: is neither published nor internal. Add a PUBLIC pattern '
                          f'if the site should serve it, or a PRIVATE one if not.')
    published_set, repo = set(published), set(files)

    def served(path):
        return any(c in published_set for c in candidates(path))

    # 2. Every sitemap URL is served.
    if 'sitemap.xml' in published_set:
        with open(os.path.join(ROOT, 'sitemap.xml'), encoding='utf-8') as f:
            for loc in re.findall(r'<loc>\s*([^<\s]+)\s*</loc>', f.read()):
                parts = urlsplit(loc)
                if parts.hostname not in HOSTS:
                    errors.append(f'sitemap.xml lists {loc}, which is not on {SITE}')
                elif not served(parts.path or '/'):
                    errors.append(f'sitemap.xml lists {loc}, but no published file serves it. '
                                  f'Add its directory to PUBLIC.')

    # 3. Everything a published file references is published.
    gaps, broken = defaultdict(set), defaultdict(set)
    for source in published:
        for ref in references(source):
            path = url_path(ref, source)
            if path is None or served(path):
                continue
            in_repo = any(c in repo for c in candidates(path))
            (gaps if in_repo else broken)[path].add(source)
    for path, sources in sorted(gaps.items()):
        errors.append(f'{path} is referenced by {_sources(sources)} and exists in the repo, but '
                      f'is not published. Add it to PUBLIC, or drop the reference if it is internal.')
    for path, sources in sorted(broken.items()):
        errors.append(f'{path} is referenced by {_sources(sources)}, but no such file exists. '
                      f'Fix the link, or commit the missing file.')

    # 4. Files fetched by name are published.
    for name in REQUIRED + indexnow_keys(files):
        if name not in published_set:
            errors.append(f'{name} must be published (browsers or crawlers fetch it by name). '
                          f'Add it to PUBLIC.')
    return published, errors


def report(errors):
    in_ci = os.environ.get('GITHUB_ACTIONS') == 'true'
    for message in errors:
        if in_ci:
            print('::error::' + message.replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A'))
        else:
            print(f'ERROR: {message}')


def stage(published, out):
    """Copy the published files into `out`, a directory outside the repo that is
    empty or absent. Never deletes anything, so a mistyped --out cannot wipe a
    directory."""
    out, root = os.path.realpath(out), os.path.realpath(ROOT)
    if out == root or out.startswith(root + os.sep):
        sys.exit(f'stage_site.py: {out} is inside the repo, where build.sh would treat the '
                 f'copies as pages. Stage outside it, e.g. /tmp/lcs-site (nothing was staged).')
    if os.path.isdir(out) and os.listdir(out):
        sys.exit(f'stage_site.py: {out} is not empty. Delete it first (nothing was staged).')
    for path in published:
        dest = os.path.join(out, path)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copyfile(os.path.join(ROOT, path), dest)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', help='copy the published files into this directory, outside the '
                                  'repo (must be empty or absent)')
    ap.add_argument('--list', action='store_true', help='print every published file')
    args = ap.parse_args()

    files = repo_files()
    published, errors = check(files)
    report(errors)
    if args.list:
        print('\n'.join(published))
    if errors:
        print(f'\n{len(errors)} deploy allowlist error(s); nothing staged. '
              f'PUBLIC and PRIVATE are in scripts/stage_site.py.')
        return 1
    size = sum(os.path.getsize(os.path.join(ROOT, p)) for p in published)
    print(f'Deploy allowlist OK: {len(published)} of {len(files)} files are published '
          f'({size / 1e6:.1f} MB); the other {len(files) - len(published)} are internal.')
    if args.out:
        stage(published, args.out)
        print(f'Staged {len(published)} files into {args.out}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
