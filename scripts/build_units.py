#!/usr/bin/env python3
"""Build and check the concept units (Python 3 standard library only).

Usage, from anywhere:
    python3 -I -B scripts/build_units.py            # fill generated blocks, write index.html, then check
    python3 -I -B scripts/build_units.py --check    # check only; writes nothing
    python3 -I -B scripts/build_units.py --check --require-all   # also require a page for every unit
    python3 -I -B scripts/build_units.py --check-links PAGE...   # check the local links of any pages; writes nothing
    python3 -I -B scripts/build_units.py --check-private DIR     # check DIR/explanations.json and its pages

The units are in units/ beside this script's folder, and units/units.json is the manifest.
The check fails a unit page, index.html, _template.html or units.json that contains a string from the forbidden
list. The list is found as scripts/scan_public.py finds it: --forbidden PATH, then $EXPLAINERS_FORBIDDEN_LIST,
then ../explainers-private/forbidden-strings.txt beside this repo. With none of them, the build prints a
notice and skips that check. A local href or src in a public page must stay inside this repo.
The build fills three generated blocks in every existing unit page, between these markers:
    <!-- unit-meta:start --> ... <!-- unit-meta:end -->   level badge and reading minutes, in the header
    <!-- prereqs:start -->   ... <!-- prereqs:end -->     links to the units to read first
    <!-- used-by:start -->   ... <!-- used-by:end -->     units and explanation sections that build on this one
and writes index.html. It writes a file only when its content changes, so running it twice changes nothing.
Exit status 1 means at least one error.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # -I leaves the script's folder off sys.path
from scan_public import LIST_ENV, Scanner, find_list, load_list  # noqa: E402  (one loader for the forbidden list)

REPO = Path(__file__).resolve().parent.parent
ROOT = REPO / "units"
MANIFEST = ROOT / "units.json"
INDEX = ROOT / "index.html"
TEMPLATE = ROOT / "_template.html"
GENERATED = ("unit-meta", "prereqs", "used-by")
DEFAULT_STATUSES = ["planned", "draft", "reviewed"]
ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
UNIT_KEYS = {"id", "title", "level", "minutes", "prereqs", "summary", "owner", "status", "media"}
OPTIONAL_KEYS = {"kind"}
KINDS = ("concept", "hub")          # "concept" is the default: one idea; "hub" ties focused units together
EXTERNAL = ("http://", "https://", "//", "mailto:", "data:", "blob:", "javascript:", "tel:")
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
FIG_MEDIA = {"svg", "canvas", "img", "video"}
IDEA_H2 = "The idea in one paragraph"
CHECK_H2 = "Check yourself"
FURTHER_H2 = "Go further"


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, where: str, msg: str) -> None:
        self.errors.append(f"ERROR {where}: {msg}")

    def warn(self, where: str, msg: str) -> None:
        self.warnings.append(f"WARN  {where}: {msg}")


def rel(p: Path) -> str:
    return os.path.relpath(p.resolve(), REPO)


def inside(p: Path, folder: Path) -> bool:
    return p.resolve().is_relative_to(folder.resolve())


# ---------------------------------------------------------------------------------------------- HTML parsing

class PageParser(HTMLParser):
    """Collects what the checks need: parts (elements with data-part), metas, the page title, ids,
    local references, and comment positions."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, str | None]] = []
        self.parts: dict[str, dict] = {}
        self.metas: dict[str, str] = {}
        self.title: str | None = None
        self._title_buf: list[str] | None = None
        self.ids: Counter = Counter()
        self.refs: list[tuple[str, str, int]] = []  # (attribute, value, line)
        self.comments: list[tuple[str, tuple[int, int]]] = []
        self._heading: tuple[str, list[str], list[str]] | None = None

    def _part(self, name: str) -> dict:
        return self.parts.setdefault(name, {"pos": None, "count": 0, "tags": Counter(), "classes": Counter(),
                                            "h1": [], "h2": [], "hrefs": [], "fig_media": 0})

    def handle_starttag(self, tag, attrs):
        self._start(tag, attrs, push=tag not in VOID)

    def handle_startendtag(self, tag, attrs):
        self._start(tag, attrs, push=False)

    def _start(self, tag, attrs, push):
        a = {k: (v if v is not None else "") for k, v in attrs}
        line = self.getpos()[0]
        if a.get("id"):
            self.ids[a["id"]] += 1
        if tag == "a" and a.get("name"):
            self.ids[a["name"]] += 1
        for attr in ("href", "src", "poster", "xlink:href"):
            if attr in a:
                self.refs.append((attr, a[attr].strip(), line))
        if tag == "meta" and a.get("name"):
            self.metas[a["name"]] = a.get("content", "")
        tags_open = [t for t, _ in self.stack]
        if tag == "title" and "svg" not in tags_open and self.title is None:
            self._title_buf = []
        part = a.get("data-part") or None
        if part:
            info = self._part(part)
            info["count"] += 1
            if info["pos"] is None:
                info["pos"] = self.getpos()
        active = [p for _, p in self.stack if p] + ([part] if part else [])
        classes = a.get("class", "").split()
        for p in active:
            info = self._part(p)
            info["tags"][tag] += 1
            for c in classes:
                info["classes"][c] += 1
            if tag == "a":
                info["hrefs"].append(a.get("href", ""))
            if tag in FIG_MEDIA and "figure" in tags_open:
                info["fig_media"] += 1
        if tag in ("h1", "h2") and self._heading is None:
            self._heading = (tag, active, [])
        if push:
            self.stack.append((tag, part))

    def handle_endtag(self, tag):
        if self._heading and tag == self._heading[0]:
            text = " ".join("".join(self._heading[2]).split())
            for p in self._heading[1]:
                self._part(p)[tag].append(text)
            self._heading = None
        if tag == "title" and self._title_buf is not None:
            self.title = " ".join("".join(self._title_buf).split())
            self._title_buf = None
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        if self._title_buf is not None:
            self._title_buf.append(data)
        if self._heading:
            self._heading[2].append(data)

    def handle_comment(self, data):
        self.comments.append((data.strip(), self.getpos()))


def parse(text: str) -> PageParser:
    p = PageParser()
    p.feed(text)
    p.close()
    return p


_ids_cache: dict[Path, set[str]] = {}


def ids_of(path: Path) -> set[str]:
    path = path.resolve()
    if path not in _ids_cache:
        _ids_cache[path] = set(parse(path.read_text(encoding="utf-8", errors="replace")).ids)
    return _ids_cache[path]


# ---------------------------------------------------------------------------------------------- manifest

def load_manifest(rep: Report) -> dict | None:
    where = rel(MANIFEST)
    try:
        m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except FileNotFoundError:
        rep.error(where, "the manifest is missing")
        return None
    except json.JSONDecodeError as e:
        rep.error(where, f"not valid JSON: {e}")
        return None
    if not isinstance(m, dict):
        rep.error(where, "the top level must be an object")
        return None
    if not isinstance(m.get("version"), int):
        rep.error(where, '"version" must be an integer')
    levels = m.get("levels")
    if not isinstance(levels, dict) or not levels or not all(isinstance(v, str) for v in levels.values()):
        rep.error(where, '"levels" must map each level id to its name, for example {"hs": "High school"}')
        return None
    statuses = m.get("statuses", DEFAULT_STATUSES)
    if not isinstance(statuses, list) or "planned" not in statuses:
        rep.error(where, '"statuses" must be a list that includes "planned"')
        statuses = DEFAULT_STATUSES
    units = m.get("units")
    if not isinstance(units, list) or not units:
        rep.error(where, '"units" must be a non-empty list')
        return None
    ok = True
    seen: dict[str, dict] = {}
    for i, u in enumerate(units):
        w = f"{where} units[{i}]"
        if not isinstance(u, dict):
            rep.error(w, "each unit must be an object")
            ok = False
            continue
        uid = u.get("id")
        if not isinstance(uid, str) or not ID_RE.match(uid):
            rep.error(w, f'"id" must be lowercase words joined by hyphens, got {uid!r}')
            ok = False
            continue
        w = f"{where} unit {uid}"
        if uid in seen:
            rep.error(w, "the id appears twice")
            ok = False
        seen[uid] = u
        missing = UNIT_KEYS - set(u)
        if missing:
            rep.error(w, f"missing keys: {', '.join(sorted(missing))}")
            ok = False
        extra = set(u) - UNIT_KEYS - OPTIONAL_KEYS
        if extra:
            rep.warn(w, f"unknown keys (ignored): {', '.join(sorted(extra))}")
        for key in ("title", "summary", "owner"):
            if key in u and (not isinstance(u[key], str) or not u[key].strip()):
                rep.error(w, f'"{key}" must be a non-empty string')
        if "level" in u and u["level"] not in levels:
            rep.error(w, f'"level" is {u["level"]!r}; it must be one of {", ".join(levels)}')
            ok = False
        if "minutes" in u and (not isinstance(u["minutes"], int) or isinstance(u["minutes"], bool)
                               or not 1 <= u["minutes"] <= 90):
            rep.error(w, '"minutes" must be a whole number from 1 to 90')
        if "status" in u and u["status"] not in statuses:
            rep.error(w, f'"status" is {u["status"]!r}; it must be one of {", ".join(statuses)}')
        if u.get("kind", "concept") not in KINDS:
            rep.error(w, f'"kind" is {u["kind"]!r}; it must be one of {", ".join(KINDS)}')
        elif kind_of(u) == "concept":
            if isinstance(u.get("title"), str) and re.search(r"\band\b", u["title"], re.I):
                rep.warn(w, f'the title {u["title"]!r} joins ideas with "and"; one concept per unit')
        if "prereqs" in u and (not isinstance(u["prereqs"], list) or not all(isinstance(p, str) for p in u["prereqs"])):
            rep.error(w, '"prereqs" must be a list of unit ids')
            ok = False
        if "media" in u:
            if not isinstance(u["media"], list) or not all(isinstance(p, str) for p in u["media"]):
                rep.error(w, '"media" must be a list of paths relative to the units folder')
            else:
                for p in u["media"]:
                    if p.startswith(EXTERNAL) or not (ROOT / p).is_file():
                        rep.error(w, f"media file {p!r} does not exist under {ROOT.name}/")
    if not ok:
        return None
    # prerequisites: they exist, no self or duplicate, no cycle, every chain ends at the lowest level
    lowest = next(iter(levels))
    rank = {lv: i for i, lv in enumerate(levels)}
    for uid, u in seen.items():
        w = f"{where} unit {uid}"
        if len(set(u["prereqs"])) != len(u["prereqs"]):
            rep.error(w, "a prerequisite is listed twice")
        for p in u["prereqs"]:
            if p == uid:
                rep.error(w, "a unit cannot be its own prerequisite")
            elif p not in seen:
                rep.error(w, f"prerequisite {p!r} is not a unit in the manifest")
                ok = False
            elif rank[seen[p]["level"]] > rank[u["level"]]:
                rep.warn(w, f"prerequisite {p!r} is at a higher level ({seen[p]['level']}) than this unit ({u['level']})")
        if not u["prereqs"] and u["level"] != lowest:
            rep.error(w, f'a {u["level"]} unit needs at least one prerequisite, so that every chain ends at {lowest} units')
    if not ok:
        return None
    state: dict[str, int] = {}

    def visit(uid: str, path: list[str]) -> bool:
        if state.get(uid) == 2:
            return True
        if state.get(uid) == 1:
            cyc = path[path.index(uid):] + [uid]
            rep.error(where, "prerequisite cycle: " + " -> ".join(cyc))
            return False
        state[uid] = 1
        good = all(visit(p, path + [uid]) for p in seen[uid]["prereqs"] if p != uid)
        state[uid] = 2
        return good

    if not all(visit(uid, []) for uid in seen):
        return None
    # explanations: {id, title, page, sections: [{anchor, title, uses}]}
    exps = m.get("explanations", [])
    if not isinstance(exps, list):
        rep.error(where, '"explanations" must be a list')
        return None
    for i, e in enumerate(exps):
        w = f"{where} explanations[{i}]"
        if not isinstance(e, dict):
            rep.error(w, "each explanation must be an object")
            return None
        for key in ("id", "title", "page"):
            if not isinstance(e.get(key), str) or not e.get(key, "").strip():
                rep.error(w, f'"{key}" must be a non-empty string')
                return None
        if e["page"].startswith(EXTERNAL) or "#" in e["page"]:
            rep.error(w, '"page" must be a local path relative to the units folder, without an #anchor')
            return None
        secs = e.get("sections")
        if not isinstance(secs, list):
            rep.error(w, '"sections" must be a list')
            return None
        anchors = set()
        for j, s in enumerate(secs):
            ws = f"{w} sections[{j}]"
            if not isinstance(s, dict) or not isinstance(s.get("anchor"), str) or not isinstance(s.get("title"), str) \
                    or not isinstance(s.get("uses"), list):
                rep.error(ws, 'each section needs "anchor" (string), "title" (string) and "uses" (list of unit ids)')
                return None
            if s["anchor"] in anchors:
                rep.error(ws, f'anchor {s["anchor"]!r} appears twice')
            anchors.add(s["anchor"])
            for uid in s["uses"]:
                if uid not in seen:
                    rep.error(ws, f"uses {uid!r}, which is not a unit in the manifest")
    m["_by_id"] = seen
    m["_statuses"] = statuses
    return m


def depths(m: dict) -> dict[str, int]:
    by = m["_by_id"]
    memo: dict[str, int] = {}

    def d(uid: str) -> int:
        if uid not in memo:
            memo[uid] = 0 if not by[uid]["prereqs"] else 1 + max(d(p) for p in by[uid]["prereqs"])
        return memo[uid]

    return {uid: d(uid) for uid in by}


def kind_of(u: dict) -> str:
    return u.get("kind", "concept")


def is_linked(u: dict) -> bool:
    return u["status"] != "planned"


# ---------------------------------------------------------------------------------------------- generated blocks

def esc(s: str) -> str:
    return html.escape(s, quote=True)


def badge(m: dict, level: str) -> str:
    return f'<span class="level-badge level-{esc(level)}">{esc(m["levels"][level])}</span>'


def unit_link_item(m: dict, u: dict) -> str:
    name = (f'<a href="{esc(u["id"])}.html">{esc(u["title"])}</a>' if is_linked(u)
            else f'<span>{esc(u["title"])}</span> <span class="tag">planned</span>')
    return f'<li>{name} {badge(m, u["level"])} <span class="minutes">{u["minutes"]} min</span></li>'


def gen_unit_meta(m: dict, u: dict) -> list[str]:
    hub = ' <span class="tag hub">overview</span>' if kind_of(u) == "hub" else ""
    return [f'<p class="unit-meta">{badge(m, u["level"])} <span class="minutes">{u["minutes"]} min read</span>{hub}</p>']


def gen_prereqs(m: dict, u: dict) -> list[str]:
    by = m["_by_id"]
    out = ['<section class="prereqs" id="prereqs" aria-labelledby="prereqs-h">']
    if u["prereqs"]:
        out.append('  <h2 id="prereqs-h">Read these first if they are new to you</h2>')
        out.append('  <ul class="unit-links">')
        out += ["    " + unit_link_item(m, by[p]) for p in u["prereqs"]]
        out.append("  </ul>")
    else:
        out.append('  <h2 id="prereqs-h">Before you start</h2>')
        out.append("  <p>You need nothing else first. This unit starts from scratch.</p>")
    out.append("</section>")
    return out


def gen_used_by(m: dict, u: dict) -> list[str]:
    dependents = [v for v in m["units"] if u["id"] in v["prereqs"]]
    uses = [(e, s) for e in m.get("explanations", []) for s in e["sections"] if u["id"] in s["uses"]]
    out = ['<section class="used-by" id="used-by" aria-labelledby="used-by-h">',
           '  <h2 id="used-by-h">Where this shows up</h2>']
    if not dependents and not uses:
        out.append("  <p>No unit or explanation builds on this one yet.</p>")
    if dependents:
        out.append("  <h3>Units that build on this one</h3>")
        out.append('  <ul class="unit-links">')
        out += ["    " + unit_link_item(m, v) for v in dependents]
        out.append("  </ul>")
    if uses:
        out.append("  <h3>Explanations that use it</h3>")
        out.append('  <ul class="unit-links">')
        for e, s in uses:
            out.append(f'    <li><a href="{esc(e["page"])}#{esc(s["anchor"])}">{esc(s["title"])}</a> '
                       f'<span class="small">in {esc(e["title"])}</span></li>')
        out.append("  </ul>")
    out.append("</section>")
    return out


def block_re(name: str) -> re.Pattern:
    return re.compile(r"(?P<indent>[ \t]*)<!-- " + re.escape(name) + r":start -->.*?<!-- "
                      + re.escape(name) + r":end -->", re.S)


def fill_block(text: str, name: str, lines: list[str]) -> str:
    def repl(mt: re.Match) -> str:
        ind = mt.group("indent")
        body = "".join(f"{ind}{ln}\n" for ln in lines)
        return f"{ind}<!-- {name}:start -->\n{body}{ind}<!-- {name}:end -->"
    return block_re(name).sub(repl, text, count=1)


def fill_page(m: dict, u: dict, text: str) -> str:
    text = fill_block(text, "unit-meta", gen_unit_meta(m, u))
    text = fill_block(text, "prereqs", gen_prereqs(m, u))
    return fill_block(text, "used-by", gen_used_by(m, u))


# ---------------------------------------------------------------------------------------------- index page

def wrap_label(uid: str, width: int = 15) -> list[str]:
    lines: list[str] = []
    for word in uid.split("-"):
        if lines and len(lines[-1]) + 1 + len(word) <= width:
            lines[-1] += " " + word
        else:
            lines.append(word)
    return lines


def graph_svg(m: dict) -> list[str]:
    by, order = m["_by_id"], {u["id"]: i for i, u in enumerate(m["units"])}
    dep = depths(m)
    nlayers = max(dep.values()) + 1
    layers = [[u["id"] for u in m["units"] if dep[u["id"]] == d] for d in range(nlayers)]
    children = {uid: [v["id"] for v in m["units"] if uid in v["prereqs"]] for uid in by}
    # order nodes within each layer by the average position of their neighbors, a few sweeps each way
    pos = {uid: i / max(1, len(layer) - 1) for layer in layers for i, uid in enumerate(layer)}

    def reorder(layer: list[str], nbrs) -> list[str]:
        def key(uid: str):
            xs = [pos[n] for n in nbrs(uid)]
            return (sum(xs) / len(xs) if xs else pos[uid], order[uid])
        new = sorted(layer, key=key)
        for i, uid in enumerate(new):
            pos[uid] = i / max(1, len(new) - 1)
        return new

    for _ in range(4):
        for d in range(1, nlayers):
            layers[d] = reorder(layers[d], lambda uid: by[uid]["prereqs"])
        for d in range(nlayers - 2, -1, -1):
            layers[d] = reorder(layers[d], lambda uid: children[uid])
    W, H, G, VG, PAD = 110, 52, 12, 44, 8
    widest = max(len(layer) for layer in layers)
    width = widest * W + (widest - 1) * G + 2 * PAD
    height = nlayers * H + (nlayers - 1) * VG + 2 * PAD
    xy: dict[str, tuple[float, float]] = {}
    for d, layer in enumerate(layers):
        x0 = (width - (len(layer) * W + (len(layer) - 1) * G)) / 2
        for i, uid in enumerate(layer):
            xy[uid] = (x0 + i * (W + G), PAD + d * (H + VG))
    out = [f'<svg class="prereq-graph" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
           f'style="--graph-w: {width}px" role="group" '
           f'aria-label="Prerequisite graph: each arrow points from a unit to a unit that builds on it">',
           '  <defs><marker id="arrowhead" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" '
           'orient="auto-start-reverse"><path class="arrowhead" d="M0,0 L8,4 L0,8 z"/></marker></defs>']
    for u in m["units"]:
        x2, y2 = xy[u["id"]]
        for p in u["prereqs"]:
            x1, y1 = xy[p]
            ax, ay, bx, by_ = x1 + W / 2, y1 + H, x2 + W / 2, y2 - 1
            dy = (by_ - ay) / 2
            out.append(f'  <path class="edge" data-from="{p}" data-to="{u["id"]}" marker-end="url(#arrowhead)" '
                       f'd="M{ax:.1f},{ay:.1f} C{ax:.1f},{ay + dy:.1f} {bx:.1f},{by_ - dy:.1f} {bx:.1f},{by_:.1f}"/>')
    for layer in layers:
        for uid in layer:
            u, (x, y) = by[uid], xy[uid]
            lines = wrap_label(uid)
            cls = f'node lv-{esc(u["level"])}' + ("" if is_linked(u) else " planned") + (" hub" if kind_of(u) == "hub" else "")
            tip = f'{u["title"]} ({m["levels"][u["level"]]}' + (")" if is_linked(u) else ", planned)")
            ty = y + H / 2 - (len(lines) - 1) * 7 + 4
            tspans = "".join(f'<tspan x="{x + W / 2:.1f}" y="{ty + k * 14:.1f}">{esc(t)}</tspan>'
                             for k, t in enumerate(lines))
            g = (f'<g class="{cls}" data-id="{uid}"{"" if is_linked(u) else " tabindex=" + chr(34) + "0" + chr(34)}>'
                 f'<title>{esc(tip)}</title><rect x="{x:.1f}" y="{y:.1f}" width="{W}" height="{H}" rx="6"/>'
                 f'<text text-anchor="middle">{tspans}</text></g>')
            out.append(f'  <a href="{uid}.html">{g}</a>' if is_linked(u) else "  " + g)
    out.append("</svg>")
    return out


def gen_index(m: dict) -> str:
    by = m["_by_id"]
    written = sum(1 for u in m["units"] if is_linked(u))
    L = ['<!doctype html>', '<html lang="en">', '<head>', '<meta charset="utf-8">',
         '<meta name="viewport" content="width=device-width, initial-scale=1">',
         '<!-- Generated by scripts/build_units.py from units.json. Edit those, not this file. -->',
         '<title>Concept units</title>',
         '<link rel="preconnect" href="https://fonts.googleapis.com">',
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>',
         '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Code+Pro:wght@400;600&amp;'
         'family=Source+Sans+3:ital,wght@0,400;0,600;0,700;1,400&amp;family=Source+Serif+4:opsz,wght@8..60,600;'
         '8..60,700&amp;display=swap">',
         '<link rel="stylesheet" href="unit.css">', '<script src="unit.js" defer></script>', '</head>', '<body>',
         '<main class="unit-index">', '<header class="unit-head">', '  <p class="eyebrow">Concept units</p>',
         '  <h1>Concept units</h1>',
         '  <p class="idea-lede">Each unit is a short page that teaches one idea. Each page lists the units to read '
         'first, so you can start anywhere and work back to high-school level.</p>',
         f'  <p class="small">{written} of {len(m["units"])} units are written. The rest are planned and listed '
         'without links.</p>',
         '  <p class="unit-meta">' + " ".join(badge(m, lv) for lv in m["levels"]) + '</p>',
         '</header>', '',
         '<section id="graph">', '  <h2>How the units build on each other</h2>', '  <figure class="plain">',
         '    <div class="graph-box">']
    L += ["      " + ln for ln in graph_svg(m)]
    L += ['    </div>',
          '    <figcaption>Each arrow points from a unit to a unit that builds on it, so the foundations are at the top. '
          'Box outlines show the level. Dashed boxes are planned units. Hover over a unit, or tab to it, to light '
          'its links. On a narrow screen, scroll sideways to see the whole graph.</figcaption>',
          '  </figure>', '</section>']
    for lv, name in m["levels"].items():
        units = [u for u in m["units"] if u["level"] == lv]
        if not units:
            continue
        L += ['', f'<section id="level-{esc(lv)}" class="index-level">', f'  <h2>{esc(name)}</h2>',
              '  <ul class="unit-cards">']
        for u in units:
            title = (f'<a href="{esc(u["id"])}.html">{esc(u["title"])}</a>' if is_linked(u) else esc(u["title"]))
            tag = ("" if is_linked(u) else ' <span class="tag">planned</span>') + \
                (' <span class="tag hub">overview</span>' if kind_of(u) == "hub" else "")
            needs = (", ".join(f'<a href="#u-{p}">{esc(by[p]["title"])}</a>' for p in u["prereqs"])
                     if u["prereqs"] else "nothing first")
            L += [f'    <li id="u-{esc(u["id"])}"{"" if is_linked(u) else " class=" + chr(34) + "planned" + chr(34)}>',
                  f'      <div class="uc-head"><span class="uc-title">{title}</span> '
                  f'<span class="minutes">{u["minutes"]} min</span>{tag}</div>',
                  f'      <p class="uc-summary">{esc(u["summary"])}</p>',
                  f'      <p class="uc-needs">Needs: {needs}</p>',
                  '    </li>']
        L += ['  </ul>', '</section>']
    exps = m.get("explanations", [])
    if exps:
        L += ['', '<section id="explanations" class="index-level">', '  <h2>Explanations that use these units</h2>']
        for e in exps:
            L += [f'  <h3><a href="{esc(e["page"])}">{esc(e["title"])}</a></h3>', '  <ul class="unit-links">']
            for s in e["sections"]:
                used = ", ".join(f'<a href="#u-{uid}">{esc(by[uid]["title"])}</a>' for uid in s["uses"])
                L.append(f'    <li><a href="{esc(e["page"])}#{esc(s["anchor"])}">{esc(s["title"])}</a>'
                         + (f' <span class="small">uses {used}</span>' if used else "") + '</li>')
            L.append('  </ul>')
        L.append('</section>')
    L += ['', '<footer class="unit-foot">',
          '  <span>Built from units.json by scripts/build_units.py. The README in this folder explains how to add a '
          'unit.</span>', '</footer>', '</main>', '</body>', '</html>']
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------------------------------------- checks

def marker_positions(p: PageParser, where: str, rep: Report) -> dict[str, tuple[int, int]]:
    found: dict[str, list] = {}
    for text, pos in p.comments:
        mt = re.fullmatch(r"([a-z-]+):(start|end)", text)
        if mt and mt.group(1) in GENERATED:
            found.setdefault(f"{mt.group(1)}:{mt.group(2)}", []).append(pos)
    out = {}
    for name in GENERATED:
        for edge in ("start", "end"):
            key = f"{name}:{edge}"
            n = len(found.get(key, []))
            if n != 1:
                rep.error(where, f"needs exactly one <!-- {key} --> marker, found {n}")
            else:
                out[key] = found[key][0]
    return out


def check_structure(p: PageParser, where: str, rep: Report, hub: bool = False) -> None:
    """The required parts, in order, each with its required contents."""
    marks = marker_positions(p, where, rep)
    for part in ("header", "idea", "body", "check", "footer"):
        n = p.parts.get(part, {}).get("count", 0)
        if n != 1:
            rep.error(where, f'needs exactly one element with data-part="{part}", found {n}')
    if p.parts.get("further", {}).get("count", 0) > 1:
        rep.error(where, 'has more than one data-part="further"')
    seq = [("header", p.parts.get("header", {}).get("pos")), ("unit-meta markers", marks.get("unit-meta:start")),
           ("prereqs:start marker", marks.get("prereqs:start")), ("prereqs:end marker", marks.get("prereqs:end")),
           ("idea", p.parts.get("idea", {}).get("pos")), ("body", p.parts.get("body", {}).get("pos")),
           ("check", p.parts.get("check", {}).get("pos")), ("further", p.parts.get("further", {}).get("pos")),
           ("used-by:start marker", marks.get("used-by:start")), ("used-by:end marker", marks.get("used-by:end")),
           ("footer", p.parts.get("footer", {}).get("pos"))]
    seq = [(n, pos) for n, pos in seq if pos is not None]
    for (n1, a), (n2, b) in zip(seq, seq[1:]):
        if a >= b:
            rep.error(where, f"parts are out of order: {n1} (line {a[0]}) must come before {n2} (line {b[0]})")
    if "unit-meta:start" in marks and "idea" in p.parts and p.parts["idea"]["pos"] and \
            marks["unit-meta:start"] > p.parts["idea"]["pos"]:
        rep.error(where, "the unit-meta markers belong inside the header")
    hdr = p.parts.get("header")
    if hdr and len(hdr["h1"]) != 1:
        rep.error(where, f"the header needs exactly one <h1>, found {len(hdr['h1'])}")
    idea = p.parts.get("idea")
    if idea:
        if IDEA_H2 not in idea["h2"]:
            rep.error(where, f'the idea part needs the heading <h2>{IDEA_H2}</h2>')
        if not idea["tags"]["p"]:
            rep.error(where, "the idea part needs a paragraph")
    body = p.parts.get("body")
    if body and not hub:
        if not body["tags"]["figure"] or not body["fig_media"]:
            rep.error(where, "the body needs at least one <figure> holding an <svg>, <canvas>, <img> or <video>")
        elif not body["tags"]["figcaption"]:
            rep.error(where, "each figure in the body needs a <figcaption>; found none")
        if not body["classes"]["example"]:
            rep.error(where, 'the body needs at least one worked example (an element with class="example")')
    chk = p.parts.get("check")
    if chk:
        if CHECK_H2 not in chk["h2"]:
            rep.error(where, f'the check part needs the heading <h2>{CHECK_H2}</h2>')
        n = chk["tags"]["details"]
        if not 2 <= n <= 4:
            rep.error(where, f"Check yourself needs two to four questions with <details> answers, found {n}")
        if chk["tags"]["summary"] < n:
            rep.error(where, "each <details> answer needs a <summary>")
    fur = p.parts.get("further")
    if fur:
        if FURTHER_H2 not in fur["h2"]:
            rep.error(where, f'the further part needs the heading <h2>{FURTHER_H2}</h2>')
        if not fur["classes"]["further-list"] or not fur["tags"]["li"]:
            rep.error(where, 'Go further needs a <ul class="further-list"> with at least one item')
    foot = p.parts.get("footer")
    if foot and "index.html" not in foot["hrefs"]:
        rep.error(where, 'the footer needs a link to index.html')


def check_refs(path: Path, p: PageParser, rep: Report, public: bool = True) -> None:
    """Each local href or src points to an existing file and #id. On a public page it must also stay in the repo."""
    where = rel(path)
    for attr, val, line in p.refs:
        if not val or val == "#" or val.lower().startswith(EXTERNAL):
            continue
        target, _, frag = val.partition("#")
        target = unquote(target.split("?", 1)[0])
        dest = (path.parent / target) if target else path
        if public and not inside(dest, REPO):
            rep.error(where, f'line {line}: {attr}="{val}" points outside the repo; a public page must not')
            continue
        if not dest.exists():
            rep.error(where, f'line {line}: {attr}="{val}" points to a missing file ({rel(dest)})')
            continue
        if frag:
            frag = unquote(frag)
            if dest.suffix.lower() not in (".html", ".htm"):
                continue
            ids = set(p.ids) if dest.resolve() == path.resolve() else ids_of(dest)
            if frag not in ids:
                rep.error(where, f'line {line}: {attr}="{val}": no element with id "{frag}" in {rel(dest)}')


def check_forbidden(m: dict, path: Path, text: str, rep: Report) -> None:
    """The whole file, generated blocks included: no public page may name a private explanation."""
    low = text.lower()
    for k, s in enumerate(m["_forbidden"], 1):
        lines = sorted({low.count("\n", 0, mt.start()) + 1 for mt in re.finditer(re.escape(s.lower()), low)})
        if lines:  # name the entry by number and mask the file name, so the log names no private project
            rep.error(Scanner(m["_forbidden"]).mask(rel(path)),
                      f"contains forbidden-list entry {k} on line {', '.join(map(str, lines[:5]))}; "
                                 "units must stay general and public-safe")


def check_unit_page(m: dict, u: dict, path: Path, rep: Report) -> None:
    where = rel(path)
    text = path.read_text(encoding="utf-8")
    p = parse(text)
    check_structure(p, where, rep, hub=kind_of(u) == "hub")
    if not text.lstrip().lower().startswith("<!doctype html>"):
        rep.error(where, "the page must start with <!doctype html>")
    if "viewport" not in p.metas:
        rep.error(where, 'needs <meta name="viewport" content="width=device-width, initial-scale=1">')
    if p.metas.get("unit-id") != u["id"]:
        rep.error(where, f'<meta name="unit-id"> is {p.metas.get("unit-id")!r}; the manifest id is {u["id"]!r}')
    if p.metas.get("unit-level") != u["level"]:
        rep.error(where, f'<meta name="unit-level"> is {p.metas.get("unit-level")!r}; the manifest level is {u["level"]!r}')
    if p.title != u["title"]:
        rep.error(where, f'<title> is {p.title!r}; the manifest title is {u["title"]!r}')
    hdr = p.parts.get("header")
    if hdr and hdr["h1"] and hdr["h1"][0] != u["title"]:
        rep.error(where, f'<h1> is {hdr["h1"][0]!r}; the manifest title is {u["title"]!r}')
    hrefs = {v for a, v, _ in p.refs}
    for need in ("unit.css", "unit.js"):
        if need not in hrefs:
            rep.error(where, f"must load {need}")
    for attr, val, line in p.refs:
        if attr == "src" and val.lower().startswith(EXTERNAL):
            rep.error(where, f"line {line}: external script or media {val!r}; pages must be self-contained")
    dups = [i for i, n in p.ids.items() if n > 1]
    if dups:
        rep.error(where, f"ids used more than once: {', '.join(sorted(dups))}")
    check_forbidden(m, path, text, rep)
    for name in GENERATED:
        mt = block_re(name).search(text)
        if mt and fill_block(mt.group(0), name, {"unit-meta": gen_unit_meta, "prereqs": gen_prereqs,
                                                 "used-by": gen_used_by}[name](m, u)) != mt.group(0):
            rep.warn(where, f"the generated {name} block is out of date; run build_units.py without --check")
    check_refs(path, p, rep)


def check_all(m: dict, rep: Report, require_all: bool) -> None:
    for e in m.get("explanations", []):
        page = ROOT / e["page"]
        w = f'{rel(MANIFEST)} explanation {e["id"]}'
        if not page.is_file():
            rep.error(w, f'page {e["page"]!r} does not exist')
            continue
        ids = ids_of(page)
        for s in e["sections"]:
            if s["anchor"] not in ids:
                rep.error(w, f'no element with id "{s["anchor"]}" in {e["page"]} (rebuild that page if you just added it)')
    known = {f'{u["id"]}.html' for u in m["units"]} | {"index.html", "_template.html"}
    for f in sorted(ROOT.glob("*.html")):
        if f.name not in known:
            rep.error(rel(f), "an HTML page with no unit in units.json; add the unit or remove the page")
    for u in m["units"]:
        path = ROOT / f'{u["id"]}.html'
        if not path.exists():
            if u["status"] != "planned":
                rep.error(f'unit {u["id"]}', f'status is {u["status"]!r} but {path.name} does not exist')
            elif require_all:
                rep.error(f'unit {u["id"]}', f"{path.name} does not exist (--require-all)")
            continue
        if u["status"] == "planned":
            rep.warn(rel(path), 'the page exists but the unit is "planned", so nothing links to it; set its status '
                                'in units.json to "draft"')
        check_unit_page(m, u, path, rep)
    if TEMPLATE.exists():
        tpl = TEMPLATE.read_text(encoding="utf-8")
        check_structure(parse(tpl), rel(TEMPLATE), rep)
        check_forbidden(m, TEMPLATE, tpl, rep)
    else:
        rep.error(rel(TEMPLATE), "the template is missing")
    if INDEX.exists():
        cur = INDEX.read_text(encoding="utf-8")
        if cur != gen_index(m):
            rep.warn(rel(INDEX), "out of date; run build_units.py without --check")
        check_refs(INDEX, parse(cur), rep)
        check_forbidden(m, INDEX, cur, rep)
    else:
        rep.warn(rel(INDEX), "missing; run build_units.py without --check")
    check_forbidden(m, MANIFEST, MANIFEST.read_text(encoding="utf-8"), rep)


# ---------------------------------------------------------------------------------------------- main

def write_if_changed(path: Path, text: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.write_text(text, encoding="utf-8")
    return True


def load_forbidden(arg: str | None, rep: Report) -> list[str]:
    path = find_list(arg)
    if path is None:
        print(f"build_units: notice: no forbidden list (--forbidden, ${LIST_ENV}, or a sibling explainers-private "
              "clone), so the private-name check is skipped")
        return []
    try:
        entries = load_list(path)
    except OSError as e:
        rep.error(str(path), f"cannot read the forbidden list: {e.strerror}")
        return []
    if not entries:
        rep.error(str(path), "the forbidden list has no entries")
    return entries


def check_links(pages: list[Path], rep: Report) -> None:
    """Every local link and #anchor on these pages resolves. No containment rule: any page may link anywhere."""
    for page in pages:
        if not page.is_file():
            rep.error(str(page), "no such page")
            continue
        check_refs(page, parse(page.read_text(encoding="utf-8")), rep, public=False)


def check_private(m: dict, folder: Path, rep: Report) -> list[Path]:
    """folder/explanations.json: {"explanations": [{id, title, page, sections: [{anchor, title, uses}]}]}, with
    page relative to folder. Each page and anchor exists, and each used id is a unit of the public manifest.
    Returns the pages, for the link check."""
    path = folder / "explanations.json"
    where = rel(path)
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        rep.error(where, f"cannot read it: {e}")
        return []
    exps = doc.get("explanations") if isinstance(doc, dict) else None
    if not isinstance(exps, list) or not exps:
        rep.error(where, '"explanations" must be a non-empty list')
        return []
    pages = []
    for i, e in enumerate(exps):
        w = f"{where} explanations[{i}]"
        if not isinstance(e, dict) or not all(isinstance(e.get(k), str) and e[k].strip() for k in ("id", "title", "page")) \
                or not isinstance(e.get("sections"), list):
            rep.error(w, 'needs "id", "title" and "page" (strings) and "sections" (a list)')
            continue
        page = folder / e["page"]
        if not page.is_file():
            rep.error(w, f'page {e["page"]!r} does not exist')
            continue
        pages.append(page)
        ids = ids_of(page)
        for j, s in enumerate(e["sections"]):
            ws = f"{w} sections[{j}]"
            if not isinstance(s, dict) or not isinstance(s.get("anchor"), str) or not isinstance(s.get("uses"), list):
                rep.error(ws, 'each section needs "anchor" (string) and "uses" (list of unit ids)')
                continue
            if s["anchor"] not in ids:
                rep.error(ws, f'no element with id "{s["anchor"]}" in {e["page"]}')
            for uid in s["uses"]:
                if uid not in m["_by_id"]:
                    rep.error(ws, f"uses {uid!r}, which is not a unit in the public manifest")
    return pages


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="check only; write nothing")
    ap.add_argument("--require-all", action="store_true", help="require a page for every unit in the manifest")
    ap.add_argument("--forbidden", metavar="PATH", help=f"the forbidden list (else ${LIST_ENV}, else the sibling repo)")
    ap.add_argument("--check-links", nargs="+", metavar="PAGE", type=Path,
                    help="check every local link and #anchor on these pages, wherever they are; write nothing")
    ap.add_argument("--check-private", metavar="DIR", type=Path,
                    help="check DIR/explanations.json against the manifest, and the links on its pages; write nothing")
    args = ap.parse_args()
    rep = Report()
    if args.check_links:
        check_links(args.check_links, rep)
        for line in rep.errors:
            print(line)
        print(f"build_units: links on {len(args.check_links)} pages, {len(rep.errors)} errors"
              + ("" if rep.errors else " - OK"))
        return 1 if rep.errors else 0
    m = load_manifest(rep)
    if args.check_private:
        pages = check_private(m, args.check_private, rep) if m is not None else []
        check_links(pages, rep)
        for line in rep.errors:
            print(line)
        print(f"build_units: {args.check_private}/explanations.json, {len(pages)} pages, {len(rep.errors)} errors"
              + ("" if rep.errors else " - OK"))
        return 1 if rep.errors else 0
    if m is not None:
        m["_forbidden"] = load_forbidden(args.forbidden, rep)
    if m is not None and not args.check and not rep.errors:
        changed = []
        for u in m["units"]:
            path = ROOT / f'{u["id"]}.html'
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            if all(block_re(n).search(text) for n in GENERATED):
                if write_if_changed(path, fill_page(m, u, text)):
                    changed.append(path.name)
            else:
                rep.error(rel(path), "is missing a generated-block marker pair; the page was not updated")
        if write_if_changed(INDEX, gen_index(m)):
            changed.append(INDEX.name)
        print("build_units: updated " + (", ".join(changed) if changed else "nothing (all files current)"))
    if m is not None:
        check_all(m, rep, args.require_all)
    for line in rep.warnings + rep.errors:
        print(line)
    n_pages = sum(1 for u in (m or {}).get("units", []) if (ROOT / f'{u["id"]}.html').exists())
    print(f"build_units: {n_pages} unit pages, {len(rep.errors)} errors, {len(rep.warnings)} warnings"
          + ("" if rep.errors else " - OK"))
    return 1 if rep.errors else 0


if __name__ == "__main__":
    sys.exit(main())
