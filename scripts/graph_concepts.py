#!/usr/bin/env python3
"""Refresh the knowledge graph's concept layer (the LLM part of /graphify --update).

    python3 scripts/graph_concepts.py prep [--dry-run]   # what changed; write one prompt per agent
    (dispatch the agents it prints, all in one message)
    python3 scripts/graph_concepts.py finish [--tokens N] # merge, recluster keeping names, report

The code and page-link layers need no LLM: scripts/refresh_graph.py does them.
Pages and docs need one extraction agent per chunk of about 21 files. This script
is graphify 0.9.97's own incremental runbook (the skill's Steps 2-9 and
references/update.md) with three changes for this repo:

- Pages are read without their generated blocks. About 650 of a page's ~900
  lines are the critical CSS and the shared partials (nav, footer, analytics),
  identical on every page; each partial is extracted on its own as a file in
  partials/. prep writes a stripped copy of each changed page under
  graphify-out/.graphify_text/, the agent reads that, and its coverage is checked
  against the copy. This cuts what the agents read by about two thirds.
- Each agent gets a prompt file (the skill's extraction prompt with its file
  list, the page-node id rule and the repo notes substituted), so the
  orchestrator's message is one line per agent instead of 3,000 tokens.
- finish keeps the community names (scripts/graph_cluster.py) and rebuilds the
  page-link layer (scripts/graph_site_links.py), which re-extracting a page drops.

Commit graphify-out/ in its own PR (`chore(graph): refresh the knowledge graph`).
"""
import glob
import json
import os
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'graphify-out'
SPEC = Path.home() / '.claude' / 'skills' / 'graphify' / 'references' / 'extraction-spec.md'
TEXT = OUT / '.graphify_text'
STATE = OUT / '.graphify_concepts.json'
# The skill's chunk bounds: 20-25 files and about 6,000 lines; a file past the
# Read tool's 2,000-line cap gets a chunk to itself.
CHUNK_FILES = 22
CHUNK_LINES = 6000
LONG_FILE = 2000
GENERATED = re.compile(r'<!-- @(css|include)-start(?: (?!generated)([^\s:]+))?')
SEMANTIC = ('document', 'paper', 'image')
TEMP = ['.graphify_detect.json', '.graphify_incremental.json', '.graphify_ast.json',
        '.graphify_cached.json', '.graphify_uncached.txt', '.graphify_semantic.json',
        '.graphify_extract.json', '.graphify_partial.txt', '.graphify_old.json',
        '.graphify_previous_names.json', '.graphify_concepts.json']

REPO_NOTES = '''
Repository notes (from the orchestrator): this is the website repo of The London
Choral Service. Pages (.html) were stripped of their generated CSS and shared
partials (nav, footer, analytics), which are extracted on their own. Where a
FILE_LIST entry has a "read:" copy below, Read that copy instead of the original,
report the copy's line count in coverage, and still set source_file to the
FILE_LIST path. Extract each page's own content: headings, body copy, FAQ and
JSON-LD facts (services, prices, repertoire, places, venues, policies, people).
Page-to-page links are already in the graph from another extractor, so add no
edge just because one page links to another; do add concept edges (a page
describes a service, quotes a price, names a hymn).

Page node ids: each published .html page's OWN document node has the id
`{stem}_page`, where stem is the repo-relative path without `.html`, segments
joined with `_` and anything outside [a-z0-9] turned into `_`
(areas/london/camden.html -> `areas_london_camden_page`, index.html ->
`index_page`). Attach the page's concepts to that node. Concept nodes keep the
usual `{stem}_{entity}` ids; .md and .txt files are unaffected.

Existing ids: the graph already holds nodes from earlier runs (`concept_*`,
`rep_*`, `venue_*`, `lcs_price_*` and so on). Before writing, list the nodes
whose source_file is one of your files (`grep -n '"source_file": "<repo-relative
path>"' graphify-out/graph.json`; never Read graph.json whole, it is 9 MB) and
re-emit those ids for the same entities, relabelling any that are out of date
(a changed price), so edges from other files still resolve. An edge may point
at an existing node from another file without re-emitting it.

Do not edit any file in the repository: the only file you write is the chunk
JSON above. When done, reply with one line: the chunk path, node count and edge
count.
'''


def graphify_python():
    sys.path.insert(0, str(ROOT / 'scripts'))
    from refresh_graph import graphify_python as find
    return find()


def rel(path):
    return os.path.relpath(path, ROOT)


def strip_generated(text):
    """The page without its @css and @include blocks, one marker line in place of each."""
    out, skip = [], None
    for line in text.splitlines():
        if skip:
            if f'@{skip}-end' in line:
                skip = None
            continue
        m = GENERATED.search(line)
        if m:
            kind, name = m.group(1), m.group(2) or 'critical CSS'
            out.append(f'<!-- [generated {kind} block removed: {name}] -->')
            if f'@{kind}-end' not in line[m.end():]:
                skip = kind
            continue
        out.append(line)
    return '\n'.join(out) + '\n'


def line_count(path):
    with open(path, encoding='utf-8', errors='replace') as f:
        return sum(1 for _ in f)


def spec_prompt():
    text = SPEC.read_text(encoding='utf-8')
    start = text.index('```\n') + 4
    return text[start:text.rindex('```')]


def chunked(files, lines):
    by_dir = defaultdict(list)
    for f in sorted(files):
        by_dir[str(Path(f).parent)].append(f)
    chunks, cur, cur_lines = [], [], 0
    for f in (f for d in sorted(by_dir) for f in by_dir[d]):
        n = lines[f]
        if n > LONG_FILE:
            chunks.append([f])
            continue
        if cur and (len(cur) >= CHUNK_FILES or cur_lines + n > CHUNK_LINES):
            chunks.append(cur)
            cur, cur_lines = [], 0
        cur.append(f)
        cur_lines += n
    if cur:
        chunks.append(cur)
    return chunks


def prep(dry_run):
    from graphify.cache import check_semantic_cache
    from graphify.detect import detect_incremental
    from graphify.extract import collect_files, extract

    if not dry_run and glob.glob(str(OUT / '.graphify_chunk_*.json')):
        raise SystemExit('chunk files from an earlier run are in graphify-out/: run finish, '
                         'or delete graphify-out/.graphify_chunk_*.json to start again')
    if not SPEC.exists():
        raise SystemExit(f'{SPEC} is missing: run graphify install --platform claude')
    inc = detect_incremental(ROOT)
    changed = inc.get('new_files', {})
    docs = [f for t in SEMANTIC for f in changed.get(t, [])]
    code = changed.get('code', [])
    deleted = inc.get('deleted_files', [])
    print(f'changed: {len(docs)} page/doc file(s), {len(code)} code file(s), {len(deleted)} deleted')
    if not docs and not code and not deleted:
        print('graph: concept layer up to date')
        return
    nodes, edges, hyper, uncached = check_semantic_cache(docs, root=ROOT, prompt_file=SPEC)
    print(f'cache: {len(docs) - len(uncached)} hit, {len(uncached)} to extract')
    texts = {f: strip_generated(Path(f).read_text(encoding='utf-8', errors='replace'))
             for f in uncached if f.endswith('.html')}
    lines = {f: texts[f].count('\n') if f in texts else line_count(f) for f in uncached}
    chunks = chunked(uncached, lines)
    if dry_run:
        for i, c in enumerate(chunks, 1):
            print(f'  chunk {i}: {len(c)} file(s), {sum(lines[f] for f in c)} lines')
        return

    for name in TEMP:
        (OUT / name).unlink(missing_ok=True)
    shutil.rmtree(TEXT, ignore_errors=True)
    (OUT / '.graphify_incremental.json').write_text(json.dumps(inc, ensure_ascii=False), encoding='utf-8')
    (OUT / '.graphify_detect.json').write_text(json.dumps({
        'files': changed, 'all_files': inc.get('files', {}), 'total_files': inc.get('new_total', 0),
        'total_words': inc.get('total_words', 0), 'skipped_sensitive': inc.get('skipped_sensitive', []),
        'needs_graph': True}, ensure_ascii=False), encoding='utf-8')

    code_files = []
    for f in code:
        code_files.extend(collect_files(Path(f)) if Path(f).is_dir() else [Path(f)])
    ast = extract(code_files, cache_root=ROOT, root=ROOT) if code_files else \
        {'nodes': [], 'edges': [], 'input_tokens': 0, 'output_tokens': 0}
    (OUT / '.graphify_ast.json').write_text(json.dumps(ast, ensure_ascii=False), encoding='utf-8')
    print(f'AST: {len(ast["nodes"])} nodes from {len(code_files)} changed code file(s)')

    if nodes or edges or hyper:
        (OUT / '.graphify_cached.json').write_text(json.dumps(
            {'nodes': nodes, 'edges': edges, 'hyperedges': hyper}, ensure_ascii=False), encoding='utf-8')
    (OUT / '.graphify_uncached.txt').write_text('\n'.join(uncached), encoding='utf-8')

    read_path = {}
    for f in uncached:
        read_path[f] = f
        if f in texts:
            copy = TEXT / rel(f)
            copy.parent.mkdir(parents=True, exist_ok=True)
            copy.write_text(texts[f], encoding='utf-8')
            read_path[f] = str(copy)
    template = spec_prompt()
    prompts = []
    for i, chunk in enumerate(chunks, 1):
        chunk_path = OUT / f'.graphify_chunk_{i:02d}.json'
        body = template.replace('chunk CHUNK_NUM of TOTAL_CHUNKS', f'chunk {i} of {len(chunks)}')
        body = body.replace('\nFILE_LIST\n', '\n' + '\n'.join(chunk) + '\n')
        body = body.replace('\nCHUNK_PATH\n', f'\n{chunk_path}\n')
        copies = [f'{f}\n  read: {read_path[f]}' for f in chunk if read_path[f] != f]
        notes = REPO_NOTES + ('\nStripped copies to read:\n' + '\n'.join(copies) + '\n' if copies else '')
        prompt = OUT / f'.graphify_prompt_{i:02d}.md'
        prompt.write_text(body + '\nDEEP_MODE for this run: false.\n' + notes, encoding='utf-8')
        prompts.append(prompt)
    STATE.write_text(json.dumps({'chunks': len(chunks), 'read_path': read_path}, indent=1), encoding='utf-8')
    total = sum(lines.values())
    print(f'{len(uncached)} file(s), {total} lines to read (stripped) in {len(chunks)} chunk(s).')
    print('Dispatch every agent in ONE message, subagent_type "general-purpose" (it must write a file),')
    print('each with the prompt "Read <file> and follow its instructions exactly.":')
    for p in prompts:
        print(f'  {p}')
    print('Then: python3 scripts/graph_concepts.py finish --tokens <total tokens the agents report>')


def finish(tokens):
    from graphify.build import build_merge
    from graphify.cache import save_semantic_cache
    from graphify.cli import _stamped_manifest_files
    from graphify.detect import save_manifest
    from graphify.diagnostics import diagnose_extraction, format_diagnostic_report
    from graphify.export import to_json
    sys.path.insert(0, str(ROOT / 'scripts'))
    import graph_site_links

    if not STATE.exists():
        raise SystemExit('nothing to finish: run prep first')
    state = json.loads(STATE.read_text(encoding='utf-8'))
    read_path = state['read_path']
    uncached = [line for line in (OUT / '.graphify_uncached.txt').read_text(encoding='utf-8').splitlines() if line]
    inc = json.loads((OUT / '.graphify_incremental.json').read_text(encoding='utf-8'))
    ast = json.loads((OUT / '.graphify_ast.json').read_text(encoding='utf-8'))

    # Step B3: collect the chunks.
    new = {'nodes': [], 'edges': [], 'hyperedges': []}
    covered, found = {}, 0
    for i in range(1, state['chunks'] + 1):
        path = OUT / f'.graphify_chunk_{i:02d}.json'
        try:
            d = json.loads(path.read_text(encoding='utf-8'))
            assert isinstance(d.get('nodes'), list) and isinstance(d.get('edges'), list)
        except (OSError, ValueError, AssertionError) as exc:
            print(f'WARNING: chunk {i} missing or invalid ({exc.__class__.__name__}); its files stay due')
            continue
        found += 1
        for key in new:
            new[key] += d.get(key, [])
        for src, n in (d.get('coverage') or {}).items():
            covered[src] = max(covered.get(src, 0), int(n))
    if found * 2 < state['chunks']:
        raise SystemExit(f'only {found} of {state["chunks"]} chunks came back: re-dispatch with '
                         'subagent_type "general-purpose" and run finish again')

    # Step B3.5: coverage against what the agent was asked to read.
    partial = []
    for src in uncached:
        n, total = covered.get(src), line_count(read_path[src])
        if n is not None and n < total:
            partial.append(src)
            print(f'WARNING: {rel(src)} read {n} of {total} lines; cached as partial, retried next run')
    unreported = [s for s in uncached if s not in covered]
    print(f'coverage: {len(covered)} reported, {len(partial)} partial, {len(unreported)} unreported')

    # Page nodes: an agent that named a page's own node without the _page suffix.
    pages = {str(ROOT / p): graph_site_links.page_id(p) for p in graph_site_links.published_pages()}
    renames = {}
    for n in new['nodes']:
        # ROOT / an absolute path is that path, so this takes either form.
        pid = pages.get(str(ROOT / (n.get('source_file') or '')))
        if pid and n['id'] == pid[:-len('_page')]:
            renames[n['id']] = pid
            n['id'] = pid
    for e in new['edges']:
        e['source'] = renames.get(e['source'], e['source'])
        e['target'] = renames.get(e['target'], e['target'])
    for h in new['hyperedges']:
        h['nodes'] = [renames.get(x, x) for x in h.get('nodes', [])]
    if renames:
        print(f'page ids: {len(renames)} page node(s) renamed to {{stem}}_page')

    saved = save_semantic_cache(new['nodes'], new['edges'], new['hyperedges'], root=ROOT,
                                allowed_source_files=uncached, prompt_file=SPEC,
                                partial_source_files=partial)
    print(f'cache: saved {saved} file(s)')

    cached_path = OUT / '.graphify_cached.json'
    cached = json.loads(cached_path.read_text(encoding='utf-8')) if cached_path.exists() else \
        {'nodes': [], 'edges': [], 'hyperedges': []}
    seen, sem_nodes = set(), []
    for n in cached['nodes'] + new['nodes']:
        if n['id'] not in seen:
            seen.add(n['id'])
            sem_nodes.append(n)
    sem_edges = cached['edges'] + new['edges']
    for item in sem_nodes + sem_edges:
        item.setdefault('_origin', 'semantic')

    # Part C: AST + semantic.
    ids = {n['id'] for n in ast['nodes']}
    extraction = {'nodes': ast['nodes'] + [n for n in sem_nodes if n['id'] not in ids],
                  'edges': ast['edges'] + sem_edges,
                  'hyperedges': cached.get('hyperedges', []) + new['hyperedges'],
                  'input_tokens': tokens, 'output_tokens': 0}
    raw = json.loads((OUT / 'graph.json').read_text(encoding='utf-8'))
    directed = bool(raw.get('directed'))
    print(format_diagnostic_report(diagnose_extraction(extraction, directed=directed, root=ROOT)))

    # Merge into the graph, keeping the community names for graph_cluster.py.
    names = {n['id']: n['community_name'] for n in raw['nodes'] if n.get('community_name')}
    names_path = OUT / '.graphify_previous_names.json'
    names_path.write_text(json.dumps(names), encoding='utf-8')
    shutil.copy(OUT / 'graph.json', OUT / '.graphify_old.json')
    deleted = list(inc.get('deleted_files', []))
    G = build_merge([extraction], graph_path=OUT / 'graph.json', prune_sources=deleted or None,
                    root=ROOT, directed=directed, ast_sources=inc.get('new_files', {}).get('code', []))
    to_json(G, {}, str(OUT / 'graph.json'), force=True)
    print(f'merged: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges '
          f'(was {len(raw["nodes"])} / {len(raw["links"])})')

    # Step 9: manifest. A partial or failed file stays unstamped, so the next run retries it.
    stamped = _stamped_manifest_files(inc['files'], extraction, ROOT, partial_source_files=set(partial))
    dispatched = {f for t, fl in inc.get('new_files', {}).items() if t in SEMANTIC for f in fl}
    done = {f for fl in stamped.values() for f in fl}
    save_manifest(stamped, manifest_path=str(OUT / 'manifest.json'), root=ROOT,
                  scan_corpus={f for fl in inc['files'].values() for f in fl},
                  clear_semantic=(dispatched - done) or None)

    py = sys.executable
    subprocess.run([py, str(ROOT / 'scripts' / 'graph_site_links.py'), '--graph', str(OUT / 'graph.json')], check=True)
    subprocess.run([py, str(ROOT / 'scripts' / 'graph_cluster.py'), str(names_path)], check=True)
    subprocess.run([shutil.which('graphify'), 'export', 'html'], cwd=ROOT, check=True)

    cost_path = OUT / 'cost.json'
    cost = json.loads(cost_path.read_text(encoding='utf-8'))
    cost['runs'].append({'date': datetime.now(timezone.utc).isoformat(timespec='seconds'),
                         'input_tokens': tokens, 'output_tokens': 0, 'files': len(uncached),
                         'note': 'scripts/graph_concepts.py: agent total tokens (input+output); '
                                 f'{state["chunks"]} agents, pages read without generated blocks'})
    cost['total_input_tokens'] += tokens
    cost_path.write_text(json.dumps(cost, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    for name in TEMP:
        (OUT / name).unlink(missing_ok=True)
    for path in glob.glob(str(OUT / '.graphify_chunk_*.json')) + glob.glob(str(OUT / '.graphify_prompt_*.md')):
        os.remove(path)
    shutil.rmtree(TEXT, ignore_errors=True)
    subprocess.run([py, str(ROOT / 'scripts' / 'refresh_graph.py'), '--check'], check=False)


def main():
    args = sys.argv[1:]
    if not args or args[0] not in ('prep', 'finish'):
        raise SystemExit(__doc__)
    try:
        import graphify  # noqa: F401
    except ImportError:
        py = graphify_python()
        if py is None:
            raise SystemExit('graphify is not installed')
        os.execv(py, [py, __file__, *args])
    os.chdir(ROOT)
    if args[0] == 'prep':
        prep('--dry-run' in args)
    else:
        tokens = int(args[args.index('--tokens') + 1]) if '--tokens' in args else 0
        finish(tokens)


if __name__ == '__main__':
    main()
