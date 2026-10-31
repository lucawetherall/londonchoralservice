#!/usr/bin/env python3
"""Tests for scripts/graph_site_links.py. Stdlib only — run with: python3 tests/test_graph_site_links.py"""
import json
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import graph_site_links as g  # noqa: E402


def test_page_ids():
    assert g.page_id('index.html') == 'index_page'
    assert g.page_id('areas/london/camden.html') == 'areas_london_camden_page'
    assert g.page_id('christmas-carol-services.html') == 'christmas_carol_services_page'
    assert g.page_id('music-guides/index.html') == 'music_guides_index_page'


def test_layer_on_the_live_pages():
    pages = g.published_pages()
    assert 'christmas-carol-services.html' in pages
    assert not any(p.startswith('partials/') for p in pages)
    nodes, edges = g.layer(pages)
    assert len({n['id'] for n in nodes}) == len(pages)
    pairs = {(e['source'], e['target'], e['relation']) for e in edges}
    assert ('carol_singers_page', 'christmas_page', 'redirects_to') in pairs
    assert all(e['source_file'] == g.LAYER for e in edges)
    # The nav and footer repeat on every page; their links must not count, so no
    # page links to every other page.
    targets = {}
    for e in edges:
        targets.setdefault(e['source'], set()).add(e['target'])
    assert max(len(t) for t in targets.values()) < len(pages) // 2


def test_apply_replaces_the_layer_and_keeps_existing_nodes():
    tmp = tempfile.mkdtemp()
    try:
        path = os.path.join(tmp, 'graph.json')
        graph = {'directed': False, 'multigraph': False, 'graph': {},
                 'nodes': [{'id': 'index_page', 'label': 'index.html', 'file_type': 'document',
                            'source_file': 'areas/bath.html', 'rationale': 'kept'}],
                 'links': [{'source': 'index_page', 'target': 'gone_page', 'relation': 'links_to',
                            'source_file': g.LAYER},
                           {'source': 'index_page', 'target': 'index_page', 'relation': 'calls',
                            'source_file': 'index.html'}]}
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(graph, f)
        g.apply(path)
        g.apply(path)
        with open(path, encoding='utf-8') as f:
            out = json.load(f)
        ids = [n['id'] for n in out['nodes']]
        assert ids.count('index_page') == 1
        home = next(n for n in out['nodes'] if n['id'] == 'index_page')
        assert home['rationale'] == 'kept' and home['source_file'] == 'index.html'
        assert home['label'] != 'index.html'
        assert not any(e['target'] == 'gone_page' for e in out['links'])
        assert any(e['relation'] == 'calls' for e in out['links'])
        layer = [e for e in out['links'] if e['source_file'] == g.LAYER]
        assert len(layer) == len({(e['source'], e['target'], e['relation']) for e in layer})
    finally:
        shutil.rmtree(tmp)


if __name__ == '__main__':
    for name, fn in sorted(globals().items()):
        if name.startswith('test_') and callable(fn):
            fn()
            print(f'ok {name}')
