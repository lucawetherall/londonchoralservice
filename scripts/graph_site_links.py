#!/usr/bin/env python3
"""Write the site's page-to-page links into graphify-out/graph.json, with no LLM.

The knowledge graph's page nodes and links used to come only from LLM extraction,
so each refresh named nodes a little differently and "what links to X" queries
missed edges. This layer is deterministic:

- every published page (scripts/stage_site.py's PUBLIC allowlist) gets a node
  `{stem}_page`, where stem is the path without `.html`, each segment lowercased
  with anything outside [a-z0-9] turned into `_` (areas/london/camden.html →
  `areas_london_camden_page`, index.html → `index_page`). The /graphify
  extraction agents are told to use the same ids, so their concepts attach here;
- every link written in a page's own body (not the nav, footer or other
  `@include` regions, which repeat on every page) becomes a `links_to` edge to the
  page it resolves to, as GitHub Pages would resolve it;
- a `<meta http-equiv="refresh">` redirect becomes a `redirects_to` edge.

Every edge carries source_file `scripts/graph_site_links.py`, so a rerun replaces
the whole layer. A page node that the LLM extraction already made keeps its other
attributes (rationale, community), but its label, source_file and url come from
the page. Run by scripts/refresh_graph.py; on its own: `python3 scripts/graph_site_links.py [--graph graphify-out/graph.json]`.
"""
import argparse
import html as htmllib
import json
import os
import re
import sys
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import stage_site  # noqa: E402

LAYER = 'scripts/graph_site_links.py'
INCLUDE = re.compile(r'<!-- @include-start .*?<!-- @include-end[^>]*-->', re.S)
STYLE = re.compile(r'<style\b.*?</style>', re.S | re.I)
REFRESH = re.compile(
    r'<meta[^>]+http-equiv=["\']refresh["\'][^>]*content=["\'][^"\']*url=([^"\'>\s]+)', re.I)
TITLE = re.compile(r'<title>(.*?)</title>', re.S | re.I)


def page_id(path):
    stem = path[:-5] if path.endswith('.html') else path
    return '_'.join(re.sub(r'[^a-z0-9]', '_', seg.lower()) for seg in stem.split('/')) + '_page'


class _Anchors(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            href = dict(attrs).get('href')
            if href:
                self.hrefs.append(href)


def resolve(ref, source, pages):
    """The published page a link from `source` reaches, or None."""
    path = stage_site.url_path(ref, source)
    if path is None:
        return None
    for cand in stage_site.candidates(path):
        if cand in pages:
            return cand
    return None


def published_pages():
    return sorted(p for p in stage_site.repo_files()
                  if p.endswith('.html') and stage_site.is_public(p))


def layer(pages):
    """(nodes, edges) for the page-link layer."""
    page_set = set(pages)
    nodes, edges = [], []
    for page in pages:
        with open(os.path.join(ROOT, page), encoding='utf-8', errors='replace') as f:
            html = f.read()
        title = TITLE.search(html)
        label = htmllib.unescape(re.sub(r'\s+', ' ', title.group(1)).strip()) if title else page
        nodes.append({
            'id': page_id(page), 'label': label, 'file_type': 'document',
            'source_file': page, 'source_location': None, 'url_path': '/' + page,
            'section': page.split('/')[0] if '/' in page else 'root',
        })
        refresh = REFRESH.search(html)
        if refresh:
            target = resolve(refresh.group(1), page, page_set)
            if target and target != page:
                edges.append(_edge(page, target, 'redirects_to'))
        body = STYLE.sub('', INCLUDE.sub('', html))
        parser = _Anchors()
        parser.feed(body)
        seen = set()
        for href in parser.hrefs:
            target = resolve(href, page, page_set)
            if target and target != page and target not in seen:
                seen.add(target)
                edges.append(_edge(page, target, 'links_to'))
    return nodes, edges


def _edge(src, dst, relation):
    return {
        'relation': relation, 'confidence': 'EXTRACTED', 'confidence_score': 1.0,
        'source_file': LAYER, 'source_location': src, 'weight': 1.0, '_origin': 'site_links',
        'source': page_id(src), 'target': page_id(dst),
    }


def apply(graph_path):
    with open(graph_path, encoding='utf-8') as f:
        graph = json.load(f)
    nodes, edges = layer(published_pages())
    links = [e for e in graph['links'] if e.get('source_file') != LAYER]
    have = {n['id'] for n in graph['nodes']}
    added = [n for n in nodes if n['id'] not in have]
    # A page node belongs to its page: an LLM chunk that met the page as a link
    # target elsewhere may have made it first, with that other file as source.
    by_id = {m['id']: m for m in nodes}
    for n in graph['nodes']:
        match = by_id.get(n['id'])
        if match:
            for key in ('label', 'source_file', 'url_path', 'section'):
                n[key] = match[key]
    graph['nodes'].extend(added)
    graph['links'] = links + edges
    tmp = graph_path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)
    os.replace(tmp, graph_path)
    redirects = sum(e['relation'] == 'redirects_to' for e in edges)
    print(f'site links: {len(nodes)} pages ({len(added)} new nodes), '
          f'{len(edges) - redirects} links_to + {redirects} redirects_to edges')


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--graph', default=os.path.join(ROOT, 'graphify-out', 'graph.json'))
    apply(ap.parse_args().graph)


if __name__ == '__main__':
    main()
