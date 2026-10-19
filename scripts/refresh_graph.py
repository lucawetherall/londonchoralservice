#!/usr/bin/env python3
"""Keep the committed knowledge graph (graphify-out/) current without LLM agents.

    python3 scripts/refresh_graph.py           # refresh code + page links, recluster, report, html
    python3 scripts/refresh_graph.py --check   # say how far behind the graph is; changes nothing

The graph has three layers:

1. Code (scripts/, tests/, command_centre/, js/, .claude/hooks/): graphify's AST
   extractor, free and deterministic. Refreshed here.
2. Page-to-page links and redirects: scripts/graph_site_links.py, free and
   deterministic. Refreshed here.
3. Concepts from pages and docs (repertoire, policies, specs, plans): LLM
   extraction by `/graphify --update` in Claude Code, one agent per ~21 changed
   files. Not refreshed here; --check says when it is due.

Run the refresh in the same PR as a change that adds, removes or renames pages or
scripts, and commit graphify-out/ with it. Files graphify skips are in
.graphifyignore. Needs graphify (`uv tool install graphifyy`); without it the
script says so and exits 0, so it never blocks other work.
"""
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRAPH = os.path.join(ROOT, 'graphify-out', 'graph.json')
# Concept extraction is due once this many pages/docs have changed since it last ran.
DOCS_DUE = 10


def graphify_python():
    """The interpreter graphify is installed under, or None."""
    exe = shutil.which('graphify')
    if not exe:
        return None
    with open(exe, encoding='utf-8', errors='replace') as f:
        first = f.readline()
    py = first[2:].strip() if first.startswith('#!') else ''
    return py if py and os.path.exists(py) else None


STALENESS = r'''
import json, sys
from pathlib import Path
from graphify.detect import detect_incremental
root = Path(sys.argv[1])
# Code is current when its AST is (refresh_graph.py); pages and docs only once the
# LLM concept extraction has seen them (/graphify --update).
code = detect_incremental(root, kind="ast")
docs = detect_incremental(root, kind="semantic")
new_docs = docs.get("new_files", {})
print(json.dumps({"code": len(code.get("new_files", {}).get("code", [])),
                  "docs": len(new_docs.get("document", [])) + len(new_docs.get("paper", [])),
                  "deleted": len(code.get("deleted_files", []))}))
'''


def staleness(py):
    out = subprocess.run([py, '-c', STALENESS, ROOT], cwd=ROOT, capture_output=True, text=True)
    if out.returncode != 0:
        raise SystemExit(f'graphify detect failed:\n{out.stderr.strip()}')
    return json.loads(out.stdout.strip().splitlines()[-1])


def check(py):
    s = staleness(py)
    if not any(s.values()):
        print('graph: up to date')
        return
    parts = []
    if s['code'] or s['deleted']:
        parts.append(f"{s['code']} code file(s) changed, {s['deleted']} deleted: "
                     'run python3 scripts/refresh_graph.py')
    if s['docs']:
        due = ' (due)' if s['docs'] >= DOCS_DUE else ''
        parts.append(f"{s['docs']} page/doc file(s) changed since concept extraction{due}: "
                     'run /graphify --update in Claude Code')
    print('graph: ' + '; '.join(parts))


def run(*args):
    print('$ ' + ' '.join(args))
    subprocess.run(args, cwd=ROOT, check=True)


def refresh(py):
    graphify = shutil.which('graphify')
    # Community names as they stand, so graph_cluster.py can carry them over:
    # `graphify update --no-cluster` drops them from graph.json.
    with open(GRAPH, encoding='utf-8') as f:
        names = {n['id']: n['community_name'] for n in json.load(f)['nodes']
                 if n.get('community_name')}
    names_path = os.path.join(ROOT, 'graphify-out', '.graphify_previous_names.json')
    with open(names_path, 'w', encoding='utf-8') as f:
        json.dump(names, f)
    try:
        # --force: deleted code legitimately shrinks the graph.
        run(graphify, 'update', '.', '--force', '--no-cluster')
        run(sys.executable, os.path.join(ROOT, 'scripts', 'graph_site_links.py'), '--graph', GRAPH)
        run(py, os.path.join(ROOT, 'scripts', 'graph_cluster.py'), names_path)
        run(graphify, 'export', 'html')
    finally:
        os.remove(names_path)


def main():
    py = graphify_python()
    if py is None:
        print('graph: graphify is not installed (uv tool install graphifyy); skipped')
        return
    if '--check' in sys.argv[1:]:
        check(py)
        return
    refresh(py)
    check(py)


if __name__ == '__main__':
    main()
