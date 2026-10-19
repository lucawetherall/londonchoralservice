"""Recluster graphify-out/graph.json and rewrite the report, keeping community names.

Run by scripts/refresh_graph.py under graphify's own interpreter (it imports
graphify), after the code and page-link layers have been refreshed:

    <graphify python> scripts/graph_cluster.py <previous-names.json>

graphify renames any community whose membership changed after its
highest-degree node ("areas/birmingham.html"), so hand-chosen names such as
"City Area Pages" would be lost on every refresh. Here a new community keeps a
previous name when at least half of its nodes carried that name before; the
rest get graphify's hub name. Writes graph.json, GRAPH_REPORT.md,
.graphify_labels.json and its .sig; graph.html is exported afterwards.
"""
import json
import sys
from collections import Counter
from pathlib import Path

from graphify.analyze import god_nodes, suggest_questions, surprising_connections
from graphify.build import build_from_json
from graphify.cluster import cluster, community_member_sigs, label_communities_by_hub, score_all
from graphify.detect import detect_incremental
from graphify.export import to_json
from graphify.report import generate

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'graphify-out'
KEEP_SHARE = 0.5


def carried_labels(G, communities, previous):
    hub = label_communities_by_hub(G, communities)
    labels, used = {}, set()
    for cid, members in sorted(communities.items(), key=lambda kv: -len(kv[1])):
        names = Counter(previous[n] for n in members if previous.get(n))
        name, count = names.most_common(1)[0] if names else (None, 0)
        if name and name not in used and count >= KEEP_SHARE * len(members):
            labels[cid] = name
            used.add(name)
        else:
            labels[cid] = hub[cid]
    return labels


def main():
    previous = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    raw = json.loads((OUT / 'graph.json').read_text(encoding='utf-8'))
    drop = {'community', 'community_name'}
    extraction = {
        'nodes': [{k: v for k, v in n.items() if k not in drop} for n in raw['nodes']],
        'edges': raw['links'],
        'hyperedges': raw.get('hyperedges', []),
    }
    G = build_from_json(extraction, root=str(ROOT), directed=bool(raw.get('directed')))
    communities = cluster(G)
    cohesion = score_all(G, communities)
    labels = carried_labels(G, communities, previous)
    gods = god_nodes(G)
    surprises = surprising_connections(G, communities)
    questions = suggest_questions(G, communities, labels)
    scan = detect_incremental(ROOT)
    detection = {'files': scan.get('files', {}), 'total_words': scan.get('total_words', 0),
                 'total_files': sum(len(v) for v in scan.get('files', {}).values())}
    report = generate(G, communities, cohesion, labels, gods, surprises, detection,
                      {'input': 0, 'output': 0}, 'londonchoralservice', suggested_questions=questions)
    # force: this is the authoritative rebuild, so a graph that legitimately lost
    # nodes (deleted code, fuzzy dedup) must still be written.
    to_json(G, communities, str(OUT / 'graph.json'), community_labels=labels, force=True)
    (OUT / 'GRAPH_REPORT.md').write_text(report, encoding='utf-8')
    (OUT / '.graphify_labels.json').write_text(
        json.dumps({str(k): v for k, v in sorted(labels.items())}, ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8')
    (OUT / '.graphify_labels.json.sig').write_text(
        json.dumps({str(k): v for k, v in sorted(community_member_sigs(communities).items())}) + '\n',
        encoding='utf-8')
    kept = sum(1 for cid in communities if labels[cid] in set(previous.values()))
    print(f'graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges, '
          f'{len(communities)} communities ({kept} kept their name)')


if __name__ == '__main__':
    main()
