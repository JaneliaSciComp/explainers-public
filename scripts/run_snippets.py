"""Run every Python snippet in the concept units and compare its output with the page's <pre class="out"> block.

Usage, from the repo root:
    python3 -I scripts/run_snippets.py <python with NumPy and PyTorch> <out dir> <html files...>
Each <pre><code class="py"> block runs on its own in a temporary folder; its output is compared with the next
<pre class="out"> block before the following snippet.
Writes <out dir>/snippets.tsv (one row per snippet) and <out dir>/diffs/<page>-<n>.txt for each mismatch or error.
"""
import difflib
import html
import os
import re
import subprocess
import sys
import tempfile

SNIP = re.compile(r'<pre[^>]*>\s*<code class="py"[^>]*>(.*?)</code>\s*</pre>', re.S)
OUT = re.compile(r'<pre class="out"[^>]*>(.*?)</pre>', re.S)
TAG = re.compile(r"<[^>]+>")


def text(s):
    return html.unescape(TAG.sub("", s))


def norm(s):
    lines = [ln.rstrip() for ln in s.strip("\n").splitlines()]
    return "\n".join(lines).strip()


def main():
    py, out_dir, files = sys.argv[1], sys.argv[2], sys.argv[3:]
    os.makedirs(os.path.join(out_dir, "diffs"), exist_ok=True)
    rows = []
    for f in files:
        page = os.path.basename(f)[:-5]
        src = open(f, encoding="utf-8").read()
        snips = list(SNIP.finditer(src))
        for i, m in enumerate(snips, 1):
            code = text(m.group(1))
            end = snips[i].start() if i < len(snips) else len(src)
            om = OUT.search(src, m.end(), end)
            expected = norm(text(om.group(1))) if om else None
            with tempfile.TemporaryDirectory() as td:
                p = os.path.join(td, "snippet.py")
                open(p, "w", encoding="utf-8").write(code)
                try:
                    r = subprocess.run([py, "-I", "-B", p], cwd=td, capture_output=True, text=True, timeout=120)
                    got, err, rc = norm(r.stdout), r.stderr.strip(), r.returncode
                except subprocess.TimeoutExpired:
                    got, err, rc = "", "TIMEOUT after 120 s", -1
            if rc != 0:
                state = "ERROR"
            elif expected is None:
                state = "no-out-block" if got else "ran-no-output"
            elif got == expected:
                state = "match"
            elif " ".join(got.split()) == " ".join(expected.split()):
                state = "match-ws"
            else:
                state = "MISMATCH"
            rows.append((page, str(i), state))
            if state in ("ERROR", "MISMATCH"):
                with open(os.path.join(out_dir, "diffs", f"{page}-{i}.txt"), "w", encoding="utf-8") as fh:
                    fh.write(f"# {page} snippet {i}: {state} (exit {rc})\n\n## code\n{code}\n\n## stderr\n{err[-3000:]}\n\n")
                    if expected is not None:
                        fh.write("## diff (page -> actual)\n")
                        fh.write("\n".join(difflib.unified_diff(expected.splitlines(), got.splitlines(), "page", "actual", lineterm="")))
                    else:
                        fh.write("## actual stdout\n" + got)
    with open(os.path.join(out_dir, "snippets.tsv"), "w", encoding="utf-8") as fh:
        fh.write("page\tsnippet\tstate\n")
        for r in rows:
            fh.write("\t".join(r) + "\n")
    from collections import Counter
    print(Counter(r[2] for r in rows))
    for r in rows:
        if r[2] not in ("match", "match-ws"):
            print("\t".join(r))


main()
