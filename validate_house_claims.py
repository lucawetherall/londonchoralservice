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

# (compiled pattern, why it is banned, what to write instead)
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

FILES = (
    glob.glob('*.html')
    + glob.glob('areas/*.html')
    + glob.glob('areas/**/*.html')
    + glob.glob('music-guides/*.html')
    + glob.glob('compare/*.html')
    + ['llms.txt']
)


def main():
    errors = 0
    for filepath in sorted(set(FILES)):
        try:
            content = open(filepath, encoding='utf-8').read()
        except FileNotFoundError:
            continue
        for pattern, label, remedy in BANNED:
            for match in pattern.finditer(content):
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
