#!/usr/bin/env python3
"""R13: give each London borough page its own section order, headings and FAQ.

Reads data/r13-borough-plan.json (spec: docs/superpowers/specs/
2026-09-27-borough-template-variants-design.md) and, for each of the 33
areas/london/*.html pages:

- reorders the existing H2 blocks of the body section into the page's variant
  order, moving the testimonial figure with them (its text never changes);
- rewrites the H2 headings from the plan;
- drops the blocks the plan names (the "For more guidance" guides paragraph,
  the standalone crematorium-guide paragraph, thin generic ensemble blocks);
- rebuilds the FAQ from the kept question/answer pairs, copied byte for byte,
  plus one new borough-specific pair, and rebuilds the FAQPage JSON-LD in the
  same order so the visible FAQ and the schema stay identical;
- on variant B (wedding-led) pages, swaps the H1 and title to
  "Wedding and funeral choirs in X" (owner-approved 2026-09-27).

Everything outside <main> except the JSON-LD block and the title tags is
asserted unchanged. A page whose structure does not match its plan is left
untouched and reported.

    python3 scripts/r13_borough_variants.py --check   # dry run, writes nothing
    python3 scripts/r13_borough_variants.py           # apply, then ./build.sh
"""
import html
import json
import re
import sys

PLAN = 'data/r13-borough-plan.json'
CHECK = '--check' in sys.argv


def norm(s):
    s = html.unescape(re.sub(r'<[^>]+>', '', s))
    s = s.replace('\xa0', ' ').replace(' ', ' ').replace(' ', ' ')
    s = s.replace('’', "'").replace('‘', "'")
    return ' '.join(s.split())


def key_of(h2_text):
    k = norm(h2_text).lower()
    if 'ensemble' in k: return 'ensembles'
    if k.startswith('funeral music'): return 'funeral'
    if k.startswith('wedding'): return 'wedding'
    if k.startswith('christmas'): return 'christmas'
    if k.startswith('memorial'): return 'memorial'
    if 'neighbour' in k: return 'neighbours'
    if 'logistic' in k: return 'logistics'
    if k.startswith('crematorium'): return 'crematoria'
    if k == 'frequently asked questions': return 'faq'
    raise ValueError(f'unknown section heading: {h2_text!r}')


def encode(text):
    """Plain Unicode copy -> the pages' entity conventions."""
    t = html.escape(text, quote=False)
    t = t.replace('’', '&rsquo;').replace('‘', '&lsquo;').replace('£', '&pound;')
    t = re.sub(r'\bSt (?=[A-Z])', 'St&nbsp;', t)
    return t


def split_body(inner):
    """Body div.prose inner HTML -> ordered list of (key, [blocks])."""
    blocks = [b for b in inner.split('\n\n') if b.strip()]
    chunks, faq_pairs, tail = [], [], {}
    current = None
    for b in blocks:
        s = b.strip()
        if s.startswith('<h2'):
            key = key_of(re.search(r'<h2[^>]*>(.*?)</h2>', s, re.S).group(1))
            current = [key, [b]]
            chunks.append(current)
        elif s.startswith('<figure class="pull-quote"'):
            chunks.append(['quote', [b]])
            current = None
        elif s.startswith('<p>For more guidance, explore our'):
            tail['guides'] = b
        elif 'class="btn-link"' in s and s.startswith('<p><a'):
            tail['cta'] = b
        elif current and current[0] == 'faq' and s.startswith('<h3>'):
            faq_pairs.append(b)
        elif current is not None and current[0] != 'faq':
            current[1].append(b)
        else:
            raise ValueError(f'unplaced block: {s[:80]!r}')
    return chunks, faq_pairs, tail


def restructure(path, plan):
    src = open(path, encoding='utf-8').read()
    m = re.search(r'(<main id="main">)(.*?)(</main>)', src, re.S)
    main = m.group(2)
    sections = list(re.finditer(r'(    <section class="section">\n      <div class="prose">\n)(.*?)(\n      </div>\n    </section>)', main, re.S))
    body = [s for s in sections if '<h2' in s.group(2)]
    if len(body) != 1:
        raise ValueError('expected exactly one body section with H2s')
    body = body[0]
    chunks, pairs, tail = split_body(body.group(2))

    present = {k for k, _ in chunks} | set(tail)
    drops = set(plan['drop_blocks'])
    order = plan['section_order']
    if set(order) != (present - drops) or len(order) != len(set(order)):
        raise ValueError(f'section keys {sorted(present)} minus drops {sorted(drops)} != plan {order}')
    if len([k for k, _ in chunks if k not in ('quote',)]) != len({k for k, _ in chunks if k != 'quote'}):
        raise ValueError('duplicate section key')

    rewrites = {norm(k): v for k, v in plan['heading_rewrites'].items()}
    by_key = {}
    for key, blks in chunks:
        if key in drops:
            continue
        blks = list(blks)
        if blks[0].strip().startswith('<h2'):
            old = re.search(r'<h2[^>]*>(.*?)</h2>', blks[0], re.S).group(1)
            new = rewrites.get(norm(old))  # absent: the plan keeps this heading as it is
            if new is not None:
                blks[0] = blks[0].replace(f'>{old}</h2>', f'>{encode(new)}</h2>', 1)
        if 'crem_link' in drops:
            kept = []
            for b in blks:
                b2 = '\n'.join(ln for ln in b.split('\n')
                               if not ln.strip().startswith('<p>For practical guidance on music at crematorium services'))
                kept.append(b2)
            blks = kept
        by_key[key] = blks

    # FAQ: keep listed pairs (byte for byte), add the new one where marked.
    pair_by_q = {norm(re.search(r'<h3>(.*?)</h3>', p, re.S).group(1)): p for p in pairs}
    new_q = plan['new_faq']['question']; new_a = plan['new_faq']['answer']
    indent = re.match(r'\s*', pairs[0]).group(0) if pairs else '        '
    faq_blocks = []
    for q in plan['faq_keep']:
        if q == 'NEW':
            faq_blocks.append(f'{indent}<h3>{encode(new_q)}</h3>\n{indent}<p>{encode(new_a)}</p>')
        else:
            if norm(q) not in pair_by_q:
                raise ValueError(f'FAQ not on page: {q!r}')
            faq_blocks.append(pair_by_q[norm(q)])
    by_key['faq'] = by_key['faq'][:1] + faq_blocks

    if 'guides' in tail and 'guides' not in drops: by_key['guides'] = [tail['guides']]
    by_key['cta'] = [tail['cta']]

    new_inner = '\n\n'.join(b for key in order for b in by_key[key])
    if not new_inner.endswith('\n') and body.group(2).endswith('\n'):
        new_inner += '\n'
    new_main = main[:body.start(2)] + new_inner + main[body.end(2):]
    out = src[:m.start(2)] + new_main + src[m.end(2):]

    # JSON-LD: rebuild FAQPage.mainEntity in the visible order.
    jm = re.search(r'(<script type="application/ld\+json">\n)(.*?)(\n  </script>)', out, re.S)
    raw = jm.group(2)
    data = json.loads(raw)
    reser = '\n'.join('  ' + ln for ln in json.dumps(data, indent=2, ensure_ascii=False).split('\n'))
    if reser != raw:
        raise ValueError('JSON-LD does not round-trip; refusing to rewrite it')
    faq_node = next(n for n in data['@graph'] if n.get('@type') == 'FAQPage')
    q_by_name = {norm(q['name']): q for q in faq_node['mainEntity']}
    entities = []
    for q in plan['faq_keep']:
        if q == 'NEW':
            entities.append({'@type': 'Question', 'name': new_q,
                             'acceptedAnswer': {'@type': 'Answer', 'text': new_a}})
        else:
            entities.append(q_by_name[norm(q)])
    faq_node['mainEntity'] = entities

    # Variant B: wedding-led pages lead with weddings in the H1 and title too.
    if plan['variant'] == 'B':
        place = re.search(r'<h1>Funeral and wedding choirs in (.*?)</h1>', out).group(1)
        old_t, new_t = f'Funeral and wedding choirs in {place}', f'Wedding and funeral choirs in {place}'
        head_end = out.index('</head>')
        head = out[:head_end].replace(f'<title>{old_t} |', f'<title>{new_t} |')
        head = head.replace(f'content="{old_t} |', f'content="{new_t} |')
        out = head + out[head_end:]
        out = out.replace(f'<h1>{old_t}</h1>', f'<h1>{new_t}</h1>', 1)
        for node in data['@graph']:
            if node.get('name') == html.unescape(old_t):
                node['name'] = html.unescape(new_t)

    new_raw = '\n'.join('  ' + ln for ln in json.dumps(data, indent=2, ensure_ascii=False).split('\n'))
    jm = re.search(r'(<script type="application/ld\+json">\n)(.*?)(\n  </script>)', out, re.S)
    out = out[:jm.start(2)] + new_raw + out[jm.end(2):]

    # Guard: nothing outside <main>, the JSON-LD and the title tags changed.
    def outside(t):
        t = re.sub(r'<main id="main">.*?</main>', '', t, flags=re.S)
        t = re.sub(r'<script type="application/ld\+json">.*?</script>', '', t, flags=re.S)
        t = re.sub(r'<title>[^<]*</title>|content="(Funeral and wedding|Wedding and funeral) choirs in [^"]*"', '', t)
        return t
    if outside(src) != outside(out):
        raise ValueError('change leaked outside <main>/JSON-LD/title')
    # Guard: the hero and nearby sections are untouched.
    for s in sections:
        if s is not body and s.group(0).replace(
                'Funeral and wedding choirs in', 'Wedding and funeral choirs in') not in out and s.group(0) not in out:
            raise ValueError('hero or nearby section changed')
    return src, out


def main():
    plan = json.load(open(PLAN, encoding='utf-8'))
    changed, failed = 0, []
    for p in plan['pages']:
        try:
            src, out = restructure(p['file'], p)
        except (ValueError, KeyError, StopIteration, AttributeError) as e:
            failed.append((p['file'], str(e)))
            continue
        h2 = [norm(x) for x in re.findall(r'<h2[^>]*>(.*?)</h2>', re.search(r'<main id="main">(.*?)</main>', out, re.S).group(1))]
        print(f"{p['file']:40} {p['variant']}  {len(p['faq_keep'])} FAQs  | " + ' / '.join(h2[:3]) + ' …')
        if out != src:
            changed += 1
            if not CHECK:
                open(p['file'], 'w', encoding='utf-8').write(out)
    for f, e in failed:
        print(f'FAILED {f}: {e}')
    print(f"{'Would change' if CHECK else 'Changed'} {changed} pages; {len(failed)} failed.")
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
