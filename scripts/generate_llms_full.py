#!/usr/bin/env python3
"""Generate llms-full.txt: the full visible text of every indexable page as
markdown, per the llms.txt convention (https://llmstxt.org/). Runs from
build.sh after partial expansion, so it always reflects the built pages.
Deterministic: output depends only on page content, so a rebuild with no
source changes leaves a clean tree.
"""
import html
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

SITE = 'https://londonchoralservice.com'


def sitemap_pages():
    sm = open('sitemap.xml', encoding='utf-8').read()
    for url in re.findall(r'<loc>([^<]+)</loc>', sm):
        path = url.replace(SITE + '/', '') or 'index.html'
        if path.endswith('/'):
            path += 'index.html'
        yield url, path


def page_markdown(url, path):
    c = open(path, encoding='utf-8').read()
    head, body = c.split('</head>', 1)
    m = re.search(r'name="description" content="([^"]*)"', head)
    desc = html.unescape(m.group(1)) if m else ''
    body = re.sub(r'<script.*?</script>', '', body, flags=re.S)
    body = re.sub(r'<style.*?</style>', '', body, flags=re.S)
    body = re.sub(r'<(nav|footer)\b.*?</\1>', '', body, flags=re.S)
    out = []
    pat = re.compile(r'<(h1|h2|h3|p|li)\b[^>]*>(.*?)</\1>', re.S)
    for tag, inner in pat.findall(body):
        text = re.sub(r'<[^>]+>', ' ', inner)
        text = html.unescape(text)
        text = re.sub(r'[\s  ]+', ' ', text).strip()
        if not text or len(text) < 3:
            continue
        if tag == 'h1':
            out.append(f'\n## {text}\n')
        elif tag == 'h2':
            out.append(f'\n### {text}\n')
        elif tag == 'h3':
            out.append(f'\n#### {text}\n')
        elif tag == 'li':
            out.append(f'- {text}')
        else:
            out.append(f'{text}\n')
    header = f'\n---\n\nSource: {url}\n'
    if desc:
        header += f'Summary: {desc}\n'
    return header + '\n'.join(out) + '\n'


def main():
    parts = [
        '# The London Choral Service — full site text\n',
        '> Professional singers, choirs, and instrumentalists for funerals, '
        'weddings, memorials, Christmas carol services, and corporate events '
        'across the United Kingdom. Operating name of Alma Consort Ltd. '
        'Structured index: https://londonchoralservice.com/llms.txt\n',
    ]
    n = 0
    for url, path in sitemap_pages():
        if not os.path.exists(path):
            print(f'generate_llms_full: missing file for {url}', file=sys.stderr)
            return 1
        parts.append(page_markdown(url, path))
        n += 1
    content = '\n'.join(parts)
    open('llms-full.txt', 'w', encoding='utf-8').write(content)
    print(f'Generated llms-full.txt ({len(content)} bytes, {n} pages)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
