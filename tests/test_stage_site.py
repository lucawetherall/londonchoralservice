#!/usr/bin/env python3
"""Tests for scripts/stage_site.py. Stdlib only — run with: python3 tests/test_stage_site.py"""
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, 'scripts', 'stage_site.py')

PAGE = '''<!DOCTYPE html><html><head>
<link rel="preload" href="/fonts/serif.woff2" as="font">
<link rel="manifest" href="/site.webmanifest">
<meta property="og:image" content="https://londonchoralservice.com/assets/og.png">
<meta name="description" content="Call us or email office@londonchoralservice.com today.">
<style>@font-face { src: url('/fonts/serif.woff2') format('woff2'); }</style>
<script type="application/ld+json">{"url": "https://londonchoralservice.com/about.html",
 "text": "Rates are on the <a href=\\"/about.html\\">about page</a>."}</script>
</head><body>
<a href="/about.html#team">About</a> <a href="areas/">Areas</a> <a href="?page=2">Next</a>
<a href="mailto:office@londonchoralservice.com">Email</a> <a href="tel:+440000">Call</a>
<a href="https://example.com/elsewhere">Elsewhere</a>
<img src="/assets/logo.png?v=3" srcset="/assets/logo.png 1x, /assets/logo@2x.png 2x" alt="">
<script src="/js/nav.js"></script>
{extra}
</body></html>'''

SITE = {
    'index.html': PAGE,
    'about.html': '<a href="/">Home</a>',
    '404.html': '<h1>Not found</h1>',
    'areas/index.html': '<a href="../about.html">About</a> <a href="london/camden.html">Camden</a>',
    'areas/london/camden.html': '<img src="../../assets/logo.png" alt="">',
    'assets/logo.png': 'png', 'assets/logo@2x.png': 'png', 'assets/og.png': 'png',
    'fonts/serif.woff2': 'woff2',
    'css/style.css': "body { background: url(../assets/logo.png); }",
    'js/nav.js': "var home = '/'; var img = 'https://i.ytimg.com/vi/' + id + '/hqdefault.jpg\" alt=\"';",
    'site.webmanifest': '{"start_url": "/", "icons": [{"src": "/assets/logo.png"}]}',
    'favicon.ico': 'ico',
    'robots.txt': 'Sitemap: https://londonchoralservice.com/sitemap.xml\n',
    'sitemap.xml': ('<urlset><url><loc>https://londonchoralservice.com/</loc></url>'
                    '<url><loc>https://londonchoralservice.com/about.html</loc></url>'
                    '<url><loc>https://londonchoralservice.com/areas/</loc></url>'
                    '<url><loc>https://londonchoralservice.com/areas/london/camden.html</loc></url></urlset>'),
    # Internal files: never published.
    'CLAUDE.md': 'agent notes', 'README.md': 'readme',
    'docs/ROADMAP.md': 'roadmap', 'logs/ads-changes.md': 'ads log',
    'scripts/ads/campaign.py': 'print(1)', 'data/prices.yml': 'a: 1', 'data/page-dates.json': '{}',
    'tests/test_x.py': 'pass', 'partials/nav.html': '<nav></nav>', 'graphify-out/graph.html': '<svg/>',
    '.claude/settings.json': '{}', '.github/workflows/deploy.yml': 'on: push', '.nojekyll': '',
    'build.sh': 'echo', 'validate.py': 'pass',
}

PUBLISHED = {
    'index.html', 'about.html', '404.html', 'areas/index.html', 'areas/london/camden.html',
    'assets/logo.png', 'assets/logo@2x.png', 'assets/og.png', 'fonts/serif.woff2',
    'css/style.css', 'js/nav.js', 'site.webmanifest', 'favicon.ico', 'robots.txt', 'sitemap.xml',
}


def make_repo(changes=None, extra='', public_prefix=''):
    """Build a temp repo from SITE (plus `changes`; a value of None deletes the
    file), install stage_site.py, and return its path."""
    tmp = tempfile.mkdtemp()
    files = dict(SITE, **(changes or {}))
    files['index.html'] = files['index.html'].replace('{extra}', extra)
    for path, content in files.items():
        if content is None:
            continue
        full = os.path.join(tmp, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, 'w', encoding='utf-8') as f:
            f.write(content)
    script = open(SCRIPT, encoding='utf-8').read()
    if public_prefix:
        script = script.replace('PUBLIC = [\n', 'PUBLIC = [\n    ' + public_prefix + '\n', 1)
    os.makedirs(os.path.join(tmp, 'scripts'), exist_ok=True)
    with open(os.path.join(tmp, 'scripts', 'stage_site.py'), 'w', encoding='utf-8') as f:
        f.write(script)
    subprocess.run(['git', 'init', '-q'], cwd=tmp, check=True)
    return tmp


def run(repo, *args):
    p = subprocess.run([sys.executable, 'scripts/stage_site.py', *args],
                       cwd=repo, capture_output=True, text=True, env=dict(os.environ, GITHUB_ACTIONS=''))
    return p.returncode, p.stdout + p.stderr


def staged(out):
    return {os.path.relpath(os.path.join(d, f), out).replace(os.sep, '/')
            for d, _, names in os.walk(out) for f in names}


def check(changes=None, extra="", public_prefix=""):
    repo = make_repo(changes, extra, public_prefix)
    try:
        return run(repo)
    finally:
        shutil.rmtree(repo)


# ── the real site passes and stages exactly the allowlist ───────────────────

def test_clean_site_passes_without_warnings():
    code, out = check()
    assert code == 0, out
    assert 'Deploy allowlist OK: 15 of' in out, out
    assert 'WARNING' not in out, out

def test_out_copies_only_published_files_byte_for_byte():
    repo = make_repo()
    try:
        out_dir = os.path.join(repo, '_site')
        code, out = run(repo, '--out', '_site')
        assert code == 0, out
        assert staged(out_dir) == PUBLISHED, sorted(staged(out_dir) ^ PUBLISHED)
        for path in PUBLISHED:
            with open(os.path.join(repo, path), 'rb') as a, open(os.path.join(out_dir, path), 'rb') as b:
                assert a.read() == b.read(), path
    finally:
        shutil.rmtree(repo)

def test_repo_checkout_passes():
    """The committed site itself must pass (this is what CI deploys)."""
    p = subprocess.run([sys.executable, SCRIPT], cwd=ROOT, capture_output=True, text=True,
                       env=dict(os.environ, GITHUB_ACTIONS=''))
    assert p.returncode == 0, p.stdout + p.stderr


# ── internal files are never published ─────────────────────────────────────

def test_widening_public_cannot_publish_internal_files():
    repo = make_repo(public_prefix="'**',")
    try:
        code, out = run(repo, '--out', '_site')
        assert code == 1, out
        for path in ('CLAUDE.md', 'docs/ROADMAP.md', 'logs/ads-changes.md', 'scripts/ads/campaign.py',
                     'data/prices.yml', 'partials/nav.html', 'graphify-out/graph.html', 'build.sh'):
            assert f'{path}: PUBLIC selects it' in out, (path, out)
        assert '.claude/settings.json: PUBLIC selects it, but it is a hidden file' in out, out
        assert not os.path.exists(os.path.join(repo, '_site')), 'staged despite errors'
    finally:
        shutil.rmtree(repo)

def test_symlink_is_refused():
    repo = make_repo()
    try:
        os.symlink('../docs/ROADMAP.md', os.path.join(repo, 'assets', 'notes.png'))
        code, out = run(repo)
        assert code == 1, out
        assert 'assets/notes.png: is a symlink' in out, out
    finally:
        shutil.rmtree(repo)


# ── gaps in the allowlist fail; broken links only warn ──────────────────────

def test_sitemap_url_outside_allowlist_fails():
    sitemap = SITE['sitemap.xml'].replace(
        '</urlset>', '<url><loc>https://londonchoralservice.com/venues/savoy.html</loc></url></urlset>')
    code, out = check({'sitemap.xml': sitemap, 'venues/savoy.html': '<p>Savoy</p>'})
    assert code == 1, out
    assert 'sitemap.xml lists https://londonchoralservice.com/venues/savoy.html' in out, out

def test_sitemap_url_with_no_file_fails():
    sitemap = SITE['sitemap.xml'].replace(
        '</urlset>', '<url><loc>https://londonchoralservice.com/gone.html</loc></url></urlset>')
    code, out = check({'sitemap.xml': sitemap})
    assert code == 1, out

def test_reference_to_unpublished_repo_file_fails():
    code, out = check(extra='<a href="/docs/ROADMAP.md">Roadmap</a>')
    assert code == 1, out
    assert '/docs/ROADMAP.md is referenced by index.html and exists in the repo' in out, out

def test_asset_in_new_directory_fails():
    code, out = check({'images/choir.jpg': 'jpg'}, extra='<img src="/images/choir.jpg" alt="">')
    assert code == 1, out
    assert '/images/choir.jpg is referenced by index.html' in out, out

def test_relative_css_reference_is_checked():
    code, out = check({'css/style.css': 'body { background: url(../images/bg.png); }',
                       'images/bg.png': 'png'})
    assert code == 1, out
    assert '/images/bg.png is referenced by css/style.css' in out, out

def test_broken_link_only_warns():
    code, out = check(extra='<a href="/no-such-page.html">Old</a>')
    assert code == 0, out
    assert 'WARNING: /no-such-page.html is referenced by index.html' in out, out


# ── files fetched by name ───────────────────────────────────────────────────

def test_missing_favicon_fails():
    code, out = check({'favicon.ico': None})
    assert code == 1, out
    assert 'favicon.ico must be published' in out, out

def test_unlisted_indexnow_key_fails():
    key = '0123456789abcdef0123456789abcdef'
    code, out = check({f'{key}.txt': key})
    assert code == 1, out
    assert f'{key}.txt must be published' in out, out


# ── staging never deletes ───────────────────────────────────────────────────

def test_out_refuses_non_empty_directory():
    repo = make_repo()
    try:
        keep = os.path.join(repo, 'docs', 'ROADMAP.md')
        code, out = run(repo, '--out', 'docs')
        assert code != 0, out
        assert 'is not empty' in out, out
        assert open(keep, encoding='utf-8').read() == 'roadmap'
    finally:
        shutil.rmtree(repo)


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
