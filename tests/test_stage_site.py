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
<form data-redirect="thank-you.html?from=wedding" data-occasion="wedding" data-domain="example.com"></form>
<script src="/js/nav.js"></script>
{extra}
</body></html>'''

SITE = {
    'index.html': PAGE,
    'about.html': '<a href="/">Home</a>',
    'thank-you.html': '<p>Thank you</p>',
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
    'index.html', 'about.html', 'thank-you.html', '404.html', 'areas/index.html',
    'areas/london/camden.html', 'assets/logo.png', 'assets/logo@2x.png', 'assets/og.png',
    'fonts/serif.woff2', 'css/style.css', 'js/nav.js', 'site.webmanifest', 'favicon.ico',
    'robots.txt', 'sitemap.xml',
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


def check(changes=None, extra='', public_prefix=''):
    repo = make_repo(changes, extra, public_prefix)
    try:
        return run(repo)
    finally:
        shutil.rmtree(repo)


# ── the site passes and stages exactly the allowlist ────────────────────────

def test_clean_site_passes():
    code, out = check()
    assert code == 0, out
    assert f'Deploy allowlist OK: {len(PUBLISHED)} of' in out, out

def test_out_copies_only_published_files_byte_for_byte():
    repo, out_dir = make_repo(), tempfile.mkdtemp()
    try:
        code, out = run(repo, '--out', out_dir)
        assert code == 0, out
        assert staged(out_dir) == PUBLISHED, sorted(staged(out_dir) ^ PUBLISHED)
        for path in PUBLISHED:
            with open(os.path.join(repo, path), 'rb') as a, open(os.path.join(out_dir, path), 'rb') as b:
                assert a.read() == b.read(), path
    finally:
        shutil.rmtree(repo)
        shutil.rmtree(out_dir)

def test_repo_checkout_passes():
    """The committed site itself must pass (this is what CI deploys)."""
    p = subprocess.run([sys.executable, SCRIPT], cwd=ROOT, capture_output=True, text=True,
                       env=dict(os.environ, GITHUB_ACTIONS=''))
    assert p.returncode == 0, p.stdout + p.stderr


# ── internal files are never published ─────────────────────────────────────

def test_widening_public_cannot_publish_internal_files():
    repo, out_dir = make_repo(public_prefix="'**',"), tempfile.mkdtemp()
    try:
        code, out = run(repo, '--out', out_dir)
        assert code == 1, out
        for path in ('CLAUDE.md', 'docs/ROADMAP.md', 'logs/ads-changes.md', 'scripts/ads/campaign.py',
                     'data/prices.yml', 'partials/nav.html', 'graphify-out/graph.html', 'build.sh'):
            assert f'{path}: PUBLIC selects it' in out, (path, out)
        assert '.claude/settings.json: PUBLIC selects it, but it is a hidden file' in out, out
        assert staged(out_dir) == set(), 'staged despite errors'
    finally:
        shutil.rmtree(repo)
        shutil.rmtree(out_dir)

def test_private_ignores_case():
    code, out = check({'assets/Notes.MD': 'notes', 'js/tool.PY': 'x'}, public_prefix="'assets/**', 'js/**',")
    assert code == 1, out
    assert "assets/Notes.MD: PUBLIC selects it, but it matches PRIVATE '**/*.md'" in out, out
    assert "js/tool.PY: PUBLIC selects it, but it matches PRIVATE '**/*.py'" in out, out

def test_control_character_in_name_is_refused():
    code, out = check({'assets/odd\nname.png': 'png'})
    assert code == 1, out
    assert "'assets/odd\\nname.png': PUBLIC selects it, but its name contains a control character" in out, out

def test_newline_cannot_slip_past_private():
    code, out = check({'logs/ads\nchanges.html': 'ads'}, public_prefix="'**/*.html',")
    assert code == 1, out
    assert "'logs/ads\\nchanges.html': PUBLIC selects it" in out, out

def test_symlink_is_refused():
    repo = make_repo()
    try:
        os.symlink('../docs/ROADMAP.md', os.path.join(repo, 'assets', 'notes.png'))
        code, out = run(repo)
        assert code == 1, out
        assert 'assets/notes.png: is a symlink' in out, out
    finally:
        shutil.rmtree(repo)


# ── every file is classified ────────────────────────────────────────────────

def test_unclassified_root_file_fails():
    """A verification file dropped at the root must not silently go unserved."""
    code, out = check({'BingSiteAuth.xml': '<users/>'})
    assert code == 1, out
    assert 'BingSiteAuth.xml: is neither published nor internal' in out, out

def test_unlisted_asset_type_fails():
    code, out = check({'assets/brochure.pdf': 'pdf'})
    assert code == 1, out
    assert 'assets/brochure.pdf: is neither published nor internal' in out, out


# ── gaps in the allowlist and broken links fail ─────────────────────────────

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

def test_data_redirect_is_followed():
    """js/form.js navigates to data-redirect after a lead, so its target must be served."""
    code, out = check({'thanks/wedding.html': '<p>Thanks</p>'},
                      extra='<form data-redirect="thanks/wedding.html?from=wedding"></form>')
    assert code == 1, out
    assert '/thanks/wedding.html is referenced by index.html and exists in the repo' in out, out

def test_missing_data_redirect_target_fails():
    code, out = check({'thank-you.html': None})
    assert code == 1, out
    assert '/thank-you.html is referenced by index.html, but no such file exists' in out, out

def test_broken_link_fails():
    code, out = check(extra='<a href="/no-such-page.html">Old</a>')
    assert code == 1, out
    assert '/no-such-page.html is referenced by index.html, but no such file exists' in out, out


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


# ── staging never deletes and never writes into the repo ────────────────────

def test_out_refuses_directory_inside_repo():
    repo = make_repo()
    try:
        code, out = run(repo, '--out', '_site')
        assert code != 0, out
        assert 'is inside the repo' in out, out
        assert not os.path.exists(os.path.join(repo, '_site'))
    finally:
        shutil.rmtree(repo)

def test_out_refuses_non_empty_directory():
    repo, out_dir = make_repo(), tempfile.mkdtemp()
    try:
        keep = os.path.join(out_dir, 'keep.txt')
        with open(keep, 'w', encoding='utf-8') as f:
            f.write('keep')
        code, out = run(repo, '--out', out_dir)
        assert code != 0, out
        assert 'is not empty' in out, out
        assert staged(out_dir) == {'keep.txt'} and open(keep, encoding='utf-8').read() == 'keep'
    finally:
        shutil.rmtree(repo)
        shutil.rmtree(out_dir)


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
