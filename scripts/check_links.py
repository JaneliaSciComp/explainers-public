"""Fetch every external link in some HTML pages; report its HTTP status and whether its #anchor exists.

Usage, from the repo root:
    python3 -I scripts/check_links.py <out.tsv> <html files...>
It fetches each page once, keeps it in memory, and writes only the TSV. A fragment that is not an id
(a time such as t=90, or a text fragment) is reported as not-an-id. A page built by script may hold its
anchors only after it runs, so a MISSING anchor there needs a look in a browser.
"""
import concurrent.futures as cf
import html
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0 Safari/537.36")
HREF = re.compile(r'href="(https?://[^"]+)"')
SKIP = {"https://fonts.googleapis.com", "https://fonts.gstatic.com"}  # preconnect hints, not links


def fetch(base):
    req = urllib.request.Request(base, headers={"User-Agent": UA, "Accept": "text/html,*/*"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            ctype = r.headers.get("Content-Type", "")
            body = r.read(6_000_000) if ("html" in ctype or "xml" in ctype or ctype == "") else b""
            return r.status, r.geturl(), ctype, body.decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, base, "", ""
    except Exception as e:  # noqa: BLE001 - report any failure as a row
        return f"ERR {type(e).__name__}: {e}"[:120], base, "", ""


def frag_state(frag, body):
    if not frag:
        return "-"
    if frag.startswith(":~:text=") or frag.startswith("t=") or re.fullmatch(r"\d+(\.\d+)?", frag):
        return "not-an-id"
    if not body:
        return "no-body"
    cands = {frag, urllib.parse.unquote(frag), html.escape(urllib.parse.unquote(frag))}
    for c in cands:
        esc = re.escape(c)
        if re.search(r'(?:id|name)\s*=\s*["\']' + esc + r'["\']', body) or re.search(r'(?:id|name)=' + esc + r'[\s>]', body):
            return "found"
    return "MISSING"


def main():
    out, files = sys.argv[1], sys.argv[2:]
    uses = defaultdict(set)
    for f in files:
        for u in HREF.findall(open(f, encoding="utf-8").read()):
            if u in SKIP:
                continue
            uses[html.unescape(u)].add(f.rsplit("/", 1)[-1])
    bases = sorted({u.split("#", 1)[0] for u in uses})
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        res = dict(zip(bases, ex.map(fetch, bases)))
    rows = []
    for u in sorted(uses):
        base, _, frag = u.partition("#")
        st, final, ctype, body = res[base]
        rows.append((str(st), frag_state(frag, body), u, final if final != base else "", ",".join(sorted(uses[u]))))
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("status\tfragment\turl\tredirected_to\tused_in\n")
        for r in rows:
            fh.write("\t".join(r) + "\n")
    bad = [r for r in rows if not r[0].startswith("2") or r[1] in ("MISSING", "no-body")]
    print(f"{len(rows)} links, {len(bases)} pages fetched, {len(bad)} need a look")
    for r in bad:
        print("\t".join(r))


main()
