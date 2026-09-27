#!/usr/bin/env python3
"""Select the files londonchoralservice.com publishes, check them, and stage them.

The repo is public and keeps internal files next to the site (docs/, logs/,
scripts/, data/, tests/, partials/, graphify-out/, .claude/, Markdown notes).
The deploy workflow (.github/workflows/deploy-pages.yml) publishes only the
files selected here: files that match PUBLIC and nothing in PRIVATE. They are
copied byte for byte; this script never builds or edits a page. build.sh does
the building, locally, and its output is committed.

    python3 scripts/stage_site.py              check only (build.sh runs this)
    python3 scripts/stage_site.py --list       check, and print every published file
    python3 scripts/stage_site.py --out _site  check, then copy the site into _site/

Any failure exits 1 and stages nothing:
  1. A selected file matches PRIVATE, is hidden, or is a symlink.
  2. A sitemap.xml URL has no published file behind it.
  3. A published file references a page or asset that exists in the repo but
     is not published: PUBLIC is missing it.
  4. A file that browsers and crawlers fetch by name is not published.
A reference to a file that exists nowhere is a broken link, not an allowlist
gap, so it is only a warning.
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
# number. A new directory of pages, or a new file the site must serve from
# outside these, needs a line here: build.sh fails until it has one.
PUBLIC = [
    # Pages
    '*.html',                  # root pages, including 404.html
    'areas/**/*.html',
    'compare/**/*.html',
    'destinations/**/*.html',
    'music-guides/**/*.html',
    # What the pages load
    'assets/**',
    'css/**',
    'fonts/**',
    'js/**',
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

# Never published, whatever PUBLIC says. Hidden files and directories
# (.github/, .claude/, .gitignore) and symlinks are refused as well.
PRIVATE = [
    'logs/**', 'docs/**', 'scripts/**', 'data/**', 'tests/**', 'partials/**', 'graphify-out/**',
    '**/*.md', '**/*.py', '**/*.sh', '**/*.yml', '**/*.yaml', '**/*.json', '**/*.csv',
]

# Requested by name, never linked: the home page, GitHub Pages' not-found page,
# robots.txt and the browser's default favicon. The IndexNow key file is added
# by indexnow_keys().
REQUIRED = ['index.html', '404.html', 'robots.txt', 'favicon.ico']


def _compile(pattern):
    """Glob to regex: '*' and '?' stay within one path segment, '**/' spans
    zero or more directories, a trailing '**' matches everything below."""
    out, i = [], 0
    while i < len(pattern):
        if pattern.startswith('**/', i):
            out.append('(?:.*/)?')
            i += 3
        elif pattern.startswith('**', i):
            out.append('.*')
            i += 2
        elif pattern[i] == '*':
            out.append('[^/]*')
            i += 1
        elif pattern[i] == '?':
            out.append('[^/]')
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile(''.join(out) + r'\Z')


_PUBLIC = [(p, _compile(p)) for p in PUBLIC]
_PRIVATE = [(p, _compile(p)) for p in PRIVATE]


def _first_match(path, compiled):
    return next((pattern for pattern, rx in compiled if rx.match(path)), None)


def refusal(path):
    """Why `path` may never be published, or None."""
    if any(part.startswith('.') for part in path.split('/')):
        return 'it is a hidden file'
    pattern = _first_match(path, _PRIVATE)
    return f"it matches PRIVATE '{pattern}'" if pattern else None


def is_public(path):
    return _first_match(path, _PUBLIC) is not None and refusal(path) is None


def repo_files():
    """Tracked files plus new files not yet added, so a page made before
    `git add` is checked too. CI checks out a clean tree, where this is
    exactly the committed files."""
    try:
        out = subprocess.run(
            ['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'],
            cwd=ROOT, capture_output=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError) as e:
        sys.exit(f'stage_site.py: git ls-files failed ({e}); run this inside the repo checkout.')
    paths = {p for p in out.decode('utf-8').split('\0') if p}
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
    """Returns (published files, errors, warnings)."""
    errors, warnings = [], []
    selected = [p for p in files if _first_match(p, _PUBLIC)]
    published = []
    for path in selected:
        why = refusal(path)
        if why:
            errors.append(f'{path}: PUBLIC selects it, but {why}. Internal files are never '
                          f'published; narrow the PUBLIC pattern.')
        elif os.path.islink(os.path.join(ROOT, path)):
            errors.append(f'{path}: is a symlink. Commit the file itself.')
        else:
            published.append(path)
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
        warnings.append(f'{path} is referenced by {_sources(sources)}, but no such file exists '
                        f'(broken link).')

    # 4. Files fetched by name are published.
    for name in REQUIRED + indexnow_keys(files):
        if name not in published_set:
            errors.append(f'{name} must be published (browsers or crawlers fetch it by name). '
                          f'Add it to PUBLIC.')
    return published, errors, warnings


def report(errors, warnings):
    in_ci = os.environ.get('GITHUB_ACTIONS') == 'true'
    for level, messages in (('warning', warnings), ('error', errors)):
        for message in messages:
            if in_ci:
                print(f'::{level}::' + message.replace('%', '%25'))
            else:
                print(f'{level.upper()}: {message}')


def stage(published, out):
    """Copy the published files into `out`, which must be empty or absent.
    Never deletes anything, so a mistyped --out cannot wipe a directory."""
    if os.path.isdir(out) and os.listdir(out):
        sys.exit(f'stage_site.py: {out} is not empty. Delete it first (nothing was staged).')
    for path in published:
        dest = os.path.join(out, path)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copyfile(os.path.join(ROOT, path), dest)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', help='copy the published files into this directory (must be empty or absent)')
    ap.add_argument('--list', action='store_true', help='print every published file')
    args = ap.parse_args()

    files = repo_files()
    published, errors, warnings = check(files)
    report(errors, warnings)
    if args.list:
        print('\n'.join(published))
    if errors:
        print(f'\n{len(errors)} deploy allowlist error(s); nothing staged. '
              f'The allowlist is PUBLIC in scripts/stage_site.py.')
        return 1
    size = sum(os.path.getsize(os.path.join(ROOT, p)) for p in published)
    print(f'Deploy allowlist OK: {len(published)} of {len(files)} files are published '
          f'({size / 1e6:.1f} MB); the other {len(files) - len(published)} stay in the repo only.')
    if args.out:
        stage(published, args.out)
        print(f'Staged {len(published)} files into {args.out}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
