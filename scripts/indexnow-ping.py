#!/usr/bin/env python3
"""Notify IndexNow (Bing/Yandex — and via them the LLM crawlers that use Bing's
index) that pages have changed. See MANUAL-ACTIONS-REQUIRED.md §7.

Prerequisite (human, one-off): generate a 32-character key at
https://www.indexnow.org/ and commit it as <key>.txt in the repo root.
This script refuses to run until that file exists.

Usage, after a deploy to production (a merge to main):
    python3 scripts/indexnow-ping.py                 # ping every sitemap URL
    python3 scripts/indexnow-ping.py URL [URL ...]   # ping specific URLs

Run it after the pages are live on londonchoralservice.com, not before —
IndexNow verifies the key file at the domain root, so a ping from an
undeployed tree fails verification.
"""
import glob
import json
import re
import sys
import urllib.request

HOST = 'londonchoralservice.com'
ENDPOINT = 'https://api.indexnow.org/indexnow'


def find_key():
    for path in glob.glob('*.txt'):
        if path in ('robots.txt', 'llms.txt'):
            continue
        stem = path[:-4]
        content = open(path, encoding='utf-8').read().strip()
        if re.fullmatch(r'[0-9a-fA-F-]{32,36}', stem) and content == stem:
            return stem
    return None


def main():
    key = find_key()
    if not key:
        sys.exit(
            'No IndexNow key file found in the repo root.\n'
            'Generate a key at https://www.indexnow.org/ and commit it as '
            '<key>.txt (file content = the key itself), then rerun. '
            'See MANUAL-ACTIONS-REQUIRED.md §7.'
        )

    if len(sys.argv) > 1:
        urls = sys.argv[1:]
    else:
        sitemap = open('sitemap.xml', encoding='utf-8').read()
        urls = re.findall(r'<loc>([^<]+)</loc>', sitemap)
    if not urls:
        sys.exit('No URLs to submit.')

    body = json.dumps({
        'host': HOST,
        'key': key,
        'keyLocation': f'https://{HOST}/{key}.txt',
        'urlList': urls,
    }).encode()
    req = urllib.request.Request(
        ENDPOINT, data=body, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        print(f'IndexNow: HTTP {resp.status} for {len(urls)} URL(s)')


if __name__ == '__main__':
    main()
