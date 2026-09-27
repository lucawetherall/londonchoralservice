#!/usr/bin/env python3
"""Fails the build on claims this site has decided it does not make.

Each pattern here was removed from the site once and came back later, either in a
new page or through a merge. A convention in CLAUDE.md did not hold; a build gate
does. If a pattern below fires on copy that is genuinely fine, change the pattern
in this file with a comment saying why, rather than working around it.
"""
import glob
import re
import sys

# (compiled pattern, why it is banned, what to write instead[, scope])
# A "london" scope limits the rule to London pages, or to a match within a few
# hundred characters of a London cathedral's name.
BANNED = [
    (
        re.compile(
            r'\b(?:over|more than)\s+150\b'
            r'|\b150[\s\-]?(?:plus|\+)'
            r'|\b150\s+(?:auditioned|singers|musicians|professionals)\b'
            r'|roster of (?:over |more than )?\d+',
            re.IGNORECASE),
        "roster-scale claim",
        "The site positions on a small hand-picked team auditioned by the Artistic Director. "
        "A large-roster claim is also near-verbatim what a competitor advertises. "
        "Write the selection claim instead, e.g. 'hand-picked by our Artistic Director'.",
    ),
    (
        re.compile(r'\bwe are VAT[\s‑\-]?registered|,\s*VAT[\s‑\-]?registered\s*,', re.IGNORECASE),
        "VAT-registration claim",
        "Alma Consort Ltd is NOT VAT-registered. A finance team reading this expects a VAT "
        "number on the invoice. Either say nothing, or state that no VAT is added.",
    ),
    (
        re.compile(
            r"\b(?:supplement|augment|bolster)\w*\s+(?:(?:its|the|their)\s+(?:own\s+|resident\s+)?"
            r"|(?:the\s+)?(?:cathedral|abbey|minster)(?:&rsquo;|\u2019|')?s?\s+)(?:choir|choral foundation)"
            r"|\bsupplement\w*\s+it\s+with\s+(?:additional|extra)\s+voices"
            r"|\b(?:additional|extra)\s+voices\s+(?:to|for|in)\s+(?:its|the|their)\s+(?:own\s+|resident\s+)?choir"
            r"|\balongside\s+(?:the|its)\s+(?:cathedral|abbey|minster)(?:&rsquo;|\u2019|')?s?\s+(?:own\s+)?(?:choir|choral foundation)",
            re.IGNORECASE),
        "London cathedral-choir supplement claim",
        "In London we never add voices to, or sing as part of, a cathedral's or Westminster "
        "Abbey's own choir (owner, 2026-09-27). We sing there as a separate ensemble, with the "
        "church's permission; say that instead. Outside London we may join a cathedral choir "
        "with the church's permission, so this rule only fires on London pages or next to a "
        "London cathedral's name.",
        "london",
    ),
    (
        re.compile(r'\bfive[\s\-]star\b|\b5[\s\-]star\b|\brated 5\b', re.IGNORECASE),
        "self-reported rating claim",
        "Unverifiable rating claims were removed site-wide (ROADMAP R1). Use a checkable "
        "trust line instead, e.g. musicians' conservatoires.",
    ),
    (
        re.compile(r'AggregateRating|"@type":\s*"Review"'),
        "self-serving review schema",
        "Review markup on your own organisation violates Google's structured-data policy "
        "and risks a manual action. Never add it, even on request.",
    ),
]

LONDON_CATHEDRALS = re.compile(
    r"St(?:\.|&nbsp;|\s)+Paul(?:&rsquo;|\u2019|')?s\s+Cathedral|Southwark\s+Cathedral"
    r"|Westminster\s+(?:Abbey|Cathedral)|St(?:\.|&nbsp;|\s)+George(?:&rsquo;|\u2019|')?s\s+Cathedral",
    re.IGNORECASE)


def in_scope(scope, filepath, content, match):
    if scope != 'london':
        return True
    path = filepath.replace('\\', '/')
    if path.startswith('areas/london/') or path == 'areas/london.html':
        return True
    window = content[max(0, match.start() - 400):match.end() + 200]
    return bool(LONDON_CATHEDRALS.search(window))


FILES = (
    glob.glob('*.html')
    + glob.glob('areas/*.html')
    + glob.glob('areas/**/*.html')
    + glob.glob('music-guides/*.html')
    + glob.glob('compare/*.html')
    + glob.glob('destinations/*.html')
    + glob.glob('destinations/**/*.html')
    + glob.glob('barbershop-grams/*.html')
    + ['llms.txt']
)


def main():
    errors = 0
    for filepath in sorted(set(FILES)):
        try:
            content = open(filepath, encoding='utf-8').read()
        except FileNotFoundError:
            continue
        for pattern, label, remedy, *scope in BANNED:
            for match in pattern.finditer(content):
                if not in_scope(scope[0] if scope else None, filepath, content, match):
                    continue
                line = content.count('\n', 0, match.start()) + 1
                print(f'{filepath}:{line}: {label} — "{match.group(0)}"')
                print(f'    {remedy}')
                errors += 1

    if errors:
        print(f'\n{errors} banned claim(s) found. These are deliberate site-wide decisions; '
              f'see the remedy on each line.')
        return 1
    print(f'House claims clean across {len(set(FILES))} files checked.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
