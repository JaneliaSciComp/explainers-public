#!/usr/bin/env python3
"""Check that every code block of an HTML page quotes its source exactly (Python 3 standard library only).

Each <pre><code ...> block must carry a data-src attribute in one of three forms:
    data-src="git:<repo>@<rev>:<path>"      <path> at commit <rev>, read with git -C <repos>/<repo> show <rev>:<path>
    data-src="file:<path>@<sha256 prefix>"   a file under --root, whose SHA-256 hash must start with the prefix
    data-src="none"                          a block that quotes no file; it is listed, not checked
After HTML unescaping, the block's text must equal lines N, N+1, ... of the source, where N is the block's
data-start attribute (default 1). A block without data-src fails, so that no quote goes unchecked by accident.
Write the block as plain, HTML-escaped text: unit.js adds line numbers and highlighting when the page loads.
It assumes pages written like units/_template.html, with lowercase tags and double-quoted attributes, and it drops
blank lines at the end of a block.

Usage, from anywhere:
    python3 -I -B scripts/check_code_blocks.py [--repos DIR] [--root DIR] PAGE [PAGE ...]
  --repos  the folder that holds the quoted clones, one folder per <repo> (default: the current directory)
  --root   the folder that file: paths start from (default: the current directory)
It only reads: git show never changes a clone. Exit status: 0 every quoting block matches, 1 at least one block
fails, 2 bad arguments.
"""
import argparse
import hashlib
import html
import os
import re
import subprocess
import sys

BLOCK = re.compile(r'<pre[^>]*>\s*<code([^>]*)>(.*?)</code>\s*</pre>', re.S)
ATTR = re.compile(r'([\w-]+)="([^"]*)"')
GIT = re.compile(r'^([^@:]+)@([^:]+):(.+)$')


def read_source(src, repos, root):
    """Return (text, None) for a data-src value, or (None, reason) when the source cannot be read."""
    kind, _, spec = src.partition(':')
    if kind == 'git':
        m = GIT.match(spec)
        if not m:
            return None, f'malformed data-src {src!r}; expected git:<repo>@<rev>:<path>'
        repo, rev, path = m.groups()
        r = subprocess.run(['git', '-C', os.path.join(repos, repo), 'show', f'{rev}:{path}'],
                           capture_output=True, text=True)
        if r.returncode != 0:
            first = (r.stderr.strip().splitlines() or ['git show failed'])[0]
            return None, f'cannot read {rev}:{path} from {os.path.join(repos, repo)}: {first}'
        return r.stdout, None
    if kind == 'file':
        path, at, prefix = spec.rpartition('@')
        if not at or not prefix:
            return None, f'malformed data-src {src!r}; expected file:<path>@<sha256 prefix>'
        try:
            raw = open(os.path.join(root, path), 'rb').read()
        except OSError as e:
            return None, f'cannot read {path}: {e.strerror}'
        digest = hashlib.sha256(raw).hexdigest()
        if not digest.startswith(prefix.lower()):
            return None, f'{path} has sha256 {digest[:16]}, expected a hash that starts with {prefix}'
        return raw.decode('utf-8'), None
    return None, f'unknown data-src {src!r}; use git:, file: or none'


def check_page(page, repos, root):
    """Check every code block of one page. Return (number of blocks, number failing)."""
    text = open(page, encoding='utf-8').read()
    n = bad = 0
    for m in BLOCK.finditer(text):
        n += 1
        where = f'{page} line {text.count(chr(10), 0, m.start()) + 1}'
        attrs = dict(ATTR.findall(m.group(1)))
        lines = html.unescape(m.group(2)).rstrip('\n').split('\n')
        src = attrs.get('data-src')
        if src is None:
            print(f'{where}: no data-src')
            bad += 1
            continue
        if src == 'none':
            print(f'{where}: quotes no file ({len(lines)} lines), not checked')
            continue
        try:
            start = int(attrs.get('data-start', '1'))
        except ValueError:
            start = 0
        if start < 1:
            print(f'{where}: data-start {attrs["data-start"]!r} is not a line number of 1 or more')
            bad += 1
            continue
        body, reason = read_source(src, repos, root)
        if body is None:
            print(f'{where}: {reason}')
            bad += 1
            continue
        want = body.split('\n')[start - 1:start - 1 + len(lines)]
        diff = next((k for k, (x, y) in enumerate(zip(lines, want)) if x != y), None)
        if diff is None and len(want) == len(lines):
            print(f'{where}: {src} lines {start}-{start + len(lines) - 1}: identical')
            continue
        k = diff if diff is not None else min(len(lines), len(want))
        print(f'{where}: {src} line {start + k} differs:\n'
              f'  page: {lines[k] if k < len(lines) else "(end)"!r}\n'
              f'  file: {want[k] if k < len(want) else "(end)"!r}')
        bad += 1
    return n, bad


def main():
    ap = argparse.ArgumentParser(description='Check that each code block of an HTML page quotes its source exactly.')
    ap.add_argument('pages', nargs='+', metavar='PAGE', help='HTML pages to check')
    ap.add_argument('--repos', default='.', metavar='DIR',
                    help='the folder that holds the quoted clones, one folder per repo (default: .)')
    ap.add_argument('--root', default='.', metavar='DIR', help='the folder that file: paths start from (default: .)')
    args = ap.parse_args()
    total = failing = 0
    for page in args.pages:
        try:
            n, bad = check_page(page, args.repos, args.root)
        except OSError as e:
            print(f'{page}: cannot read the page: {e.strerror}')
            n, bad = 0, 1
        total += n
        failing += bad
    print(f'{total} code blocks in {len(args.pages)} pages, {failing} failing')
    return 1 if failing else 0


if __name__ == '__main__':
    sys.exit(main())
