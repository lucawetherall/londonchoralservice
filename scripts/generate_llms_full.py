#!/usr/bin/env python3
"""Generate llms-full.txt: the site's text as markdown, per the llms.txt
convention (https://llmstxt.org/). Runs from build.sh after partial
expansion, so it always reflects the built pages.

Many AI fetchers stop reading after a few hundred kilobytes, so the file
puts the pages that answer "what does it cost and how do I book" first, in
full (MONEY_PAGES), then the other main pages in full, then every remaining
sitemap page trimmed to its answer block: the summary, the h1, the text
above the first h2 (the lede and the bold-question answer) and its h2/h3
headings. The target is under 300 KB (TARGET_BYTES); the build prints a
warning, not a failure, above it.

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
TARGET_BYTES = 300_000
ANSWER_PARAS = 2
# In this order, in full.
MONEY_PAGES = [
    'facts.html', 'pricing.html', 'christmas-pricing.html', 'funerals.html', 'weddings.html',
    'christmas.html', 'christmas-carol-services.html', 'contact.html', 'services.html', 'faq.html',
]
# Pages under these prefixes are trimmed (the trade landing pages, the private register, the film and
# policy pages, the long terms and the about page too; facts.html carries the company and booking facts in
# full); every other page stays in full.
TRIMMED = ('music-guides/', 'areas/', 'destinations/', 'compare/', 'for-', 'private-events.html',
           'planners-and-venues.html', 'professionals.html', 'listen.html', 'christmas-listen.html',
           'privacy.html', 'accessibility.html', 'corporate.html', 'luca-wetherall.html', 'terms.html', 'about.html')
BLOCK = re.compile(r'<(h1|h2|h3|p|li)\b([^>]*)>(.*?)</\1>', re.S)


def sitemap_pages():
    sm = open('sitemap.xml', encoding='utf-8').read()
    for url in re.findall(r'<loc>([^<]+)</loc>', sm):
        path = url.replace(SITE + '/', '') or 'index.html'
        if path.endswith('/'):
            path += 'index.html'
        yield url, path


def page_markdown(url, path, trim=False):
    c = open(path, encoding='utf-8').read()
    head, body = c.split('</head>', 1)
    m = re.search(r'name="description" content="([^"]*)"', head)
    desc = html.unescape(m.group(1)) if m else ''
    body = re.sub(r'<script.*?</script>', '', body, flags=re.S)
    body = re.sub(r'<style.*?</style>', '', body, flags=re.S)
    body = re.sub(r'<(nav|footer)\b.*?</\1>', '', body, flags=re.S)
    out = []
    past_first_h2 = False
    kept_paras = 0
    for tag, attrs, inner in BLOCK.findall(body):
        if tag == 'h2':
            past_first_h2 = True
        # A trimmed page keeps its answer (the lede and the bold-question paragraph: the first
        # ANSWER_PARAS paragraphs), not the small print around it (date lines, hiring lines, captions).
        small = re.search(r'class="[^"]*\b(guide-meta|text-sm|video-caption)\b', attrs)
        # Its outline is the h2s: the h3s under them, mostly FAQ questions, stay on the page.
        if trim and (past_first_h2 and tag in ('p', 'li', 'h3') or small
                     or tag in ('p', 'li') and kept_paras >= ANSWER_PARAS):
            continue
        if tag in ('p', 'li'):
            kept_paras += 1
        text = re.sub(r'<[^>]+>', ' ', inner)
        text = html.unescape(text)
        text = re.sub(r'[\s  ]+', ' ', text).strip()
        if not text or len(text) < 3:
            continue
        if tag == 'h1':
            out.append(f'\n## {text}\n')
        elif tag in ('h2', 'h3'):
            hashes = '###' if tag == 'h2' else '####'
            # A trimmed page is a run of headings: one per line, without the blank lines between them.
            out.append(f'{hashes} {text}' if trim and past_first_h2 else f'\n{hashes} {text}\n')
        elif tag == 'li':
            out.append(f'- {text}')
        else:
            out.append(f'{text}\n')
    header = f'\n---\n\nSource: {url}\n'
    if desc:
        header += f'Summary: {desc}\n'
    if trim:
        header += '(Shortened to its answer and section headings; the page has the full text and its FAQs.)\n'
    return header + '\n'.join(out) + '\n'


def main():
    parts = [
        '# The London Choral Service — full site text\n',
        '> Professional singers, choirs, and instrumentalists for funerals, '
        'weddings, memorials, Christmas carol services, and corporate events '
        'across the United Kingdom. Operating name of Alma Consort Ltd. '
        'Structured index: https://londonchoralservice.com/llms.txt\n',
        '> Order: prices, booking and the main service pages first, in full; then the other main pages; '
        'then the trade pages, music guides, area pages and destination pages, each shortened to its answer '
        'and headings.\n',
    ]
    pages = list(sitemap_pages())
    for url, path in pages:
        if not os.path.exists(path):
            print(f'generate_llms_full: missing file for {url}', file=sys.stderr)
            return 1
    by_path = dict((p, u) for u, p in pages)
    first = [p for p in MONEY_PAGES if p in by_path]
    full = [p for _, p in pages if p not in first and not p.startswith(TRIMMED)]
    trimmed = [p for _, p in pages if p.startswith(TRIMMED)]
    for p in first + full:
        parts.append(page_markdown(by_path[p], p))
    for p in trimmed:
        parts.append(page_markdown(by_path[p], p, trim=True))
    content = '\n'.join(parts)
    open('llms-full.txt', 'w', encoding='utf-8').write(content)
    size = len(content.encode('utf-8'))
    print(f'Generated llms-full.txt ({size} bytes, {len(pages)} pages, {len(trimmed)} shortened)')
    if size > TARGET_BYTES:
        print(f'generate_llms_full: warning: {size} bytes is over the {TARGET_BYTES} target; '
              'shorten a full page or move it into TRIMMED', file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
