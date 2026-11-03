# Concept units

This folder holds concept units: HTML pages that each teach one idea. Every unit lists the units a reader
may need first, down to units that start from scratch. A colleague or an intern can start at any unit and follow
those links back until the material is familiar. Explanations, such as a part of a report, link to units for the
background they assume.

`units.json` is the manifest. It lists every unit, its level and its prerequisites, and the explanations that use
units. `scripts/build_units.py` fills the generated parts of each page and writes `index.html`. It also checks
that every page has its required parts and that every link works.

This README gives the mechanics. How to write a good unit, and how to check, review and fix one, is in the agent
skill [`skills/explainer-units/SKILL.md`](../skills/explainer-units/SKILL.md) and its reference files, and in the
guide for people, [`docs/guide.md`](../docs/guide.md).

## What a unit is, and what it is not

A unit teaches one general concept that many explanations can reuse: vectors, gradient descent, KD-trees. The
concept sets the page's length: the unit explains it as simply as it can be explained at its level, with every step,
condition and warning box a reader needs, and then stops. A reader should never have to work through a large
curriculum to understand one idea.

A unit explains only its own concept. [`about.html`](about.html) explains the site to readers: what a unit is,
what the levels mean, how the lists of units to read first work, and what the code is for. A page links a section of
it, such as `about.html#levels`, instead of explaining these things itself.

A unit is not about one project. It never names a project that is not public, and never quotes or describes one
project's code, data, people or results, even without naming them. That material stays in the explanation, which links
to the unit. Public attribution is fine, such as the author or site of a "Go further" item. A unit links back only to
explanations published in this repo, and only through its generated "Where this shows up" block. Explanations kept
elsewhere link to the units, but the units never link to them.

## Two kinds of unit

Each manifest entry has a `kind`:

- `concept`, the default: one idea, at the length it needs.
- `hub`: a short overview that ties several focused units together. For example, a training-loop hub links the
  units on minibatches, data loaders and checkpoints, and lists them as its prerequisites. A hub needs no figure
  or worked example, and its pages show an "overview" tag.

`build_units.py --check` warns, without failing, when a concept unit's title joins two ideas with "and". Treat the
warning as a prompt to split the unit or to make it a hub.

## The three levels

The manifest's `levels` map gives the three level ids and their names, in order: `starting` (Starting),
`intermediate` (Intermediate) and `advanced` (Advanced). [`about.html#levels`](about.html#levels) defines them, and
each unit's header badge links there.

Every chain of prerequisites ends at `starting` units. So an `intermediate` or `advanced` unit lists at least one
prerequisite, and only `starting` units may list none. A prerequisite is never at a higher level than the unit that
needs it.

## The manifest

`units.json` holds `version`, `levels`, `statuses`, `kinds`, `units` and `explanations`. Each entry in `units` has
these keys:

| Key | What it holds |
|---|---|
| `id` | lowercase words joined by hyphens; the page is `<id>.html` in this folder |
| `title` | the page's `<title>` and `<h1>`, exactly |
| `level` | `starting`, `intermediate` or `advanced` |
| `kind` | `concept` or `hub`; it may be left out, and defaults to `concept` |
| `minutes` | the reading time, a whole number |
| `prereqs` | the ids of the units to read first |
| `summary` | one plain sentence, shown on the index |
| `owner` | who maintains the page |
| `status` | `planned` (no page yet), `draft` (written) or `reviewed` (checked by a second reader) |
| `media` | the unit's files in `media/`, as paths relative to this folder |

## The parts of a unit page, in order

Start from `_template.html`. The checker looks for each part by its marker.

| Part | Marker | Who writes it |
|---|---|---|
| Header: title, level badge, reading minutes | `<header class="unit-head" data-part="header">` with one `<h1>`; the badge and minutes go between `<!-- unit-meta:start -->` and `<!-- unit-meta:end -->` | you write the `<h1>`; the build fills the badge, which links to `about.html#levels`, and the minutes |
| Prerequisites | `<!-- prereqs:start -->` … `<!-- prereqs:end -->` | the build |
| The idea in one paragraph | `<section id="idea" class="idea" data-part="idea">` with `<h2>The idea in one paragraph</h2>` | you |
| Body | `<div class="unit-body" data-part="body">`, holding at least one worked example (`class="example"`) and one `<figure>` with an `<svg>`, `<canvas>`, `<img>` or `<video>` and a `<figcaption>` (a hub needs neither) | you |
| Check yourself | `<section id="check" class="check" data-part="check">` with `<h2>Check yourself</h2>` and two to four questions, each answered in `<details><summary>Answer</summary>…</details>` | you |
| Go further (optional) | `<section id="further" class="further" data-part="further">` with `<h2>Go further</h2>` and a `<ul class="further-list">` | you |
| Where this shows up | `<!-- used-by:start -->` … `<!-- used-by:end -->` | the build |
| Footer | `<footer class="unit-foot" data-part="footer">` with a link to `index.html` | you |

Leave the generated markers in place and empty. The build replaces whatever is between them. The ids `prereqs`,
`prereqs-h`, `used-by` and `used-by-h` belong to the generated blocks, so do not use them elsewhere.

The page's `<meta name="unit-id">`, `<meta name="unit-level">`, `<title>` and `<h1>` must match `units.json`
exactly. The page file is `<id>.html` in this folder.

## The markup that unit.css and unit.js read

| For | Write |
|---|---|
| a warning box that names a simplification | `<div class="callout warn">` with a `<span class="callout-title">`; a plain note is `<div class="callout">` |
| a worked example | `<div class="example">` with a `<span class="example-title">` |
| a figure | `<figure>` holding a `<div class="fig-title">`, the drawing, and a `<figcaption>` |
| a widget's controls and numbers | `<div class="controls">` for the controls, `<output>` for each number, `<div class="readout-box">` for a readout |
| anything wider than a phone | `<div class="table-wrap">` or `<div class="scroll-x">` around it |
| colours that follow the theme | the classes `f-s1` … `f-s4` (fills), `st-s1` … `st-s4` (strokes), `muted` and `ink2` (text), or `var(--s1)` and the other tokens |
| a displayed formula | `<p class="math">`, with `<span class="vec">` for a vector, `<var>` for a variable |
| a defined term | `<dfn>` at its first use |
| a Python snippet | `<p class="code-cap">` with the file name, then `<pre><code class="py">…</code></pre>`; `data-start="N"` numbers from N, and `data-hl="3,4"` highlights lines 3 and 4 |
| a snippet's output | `<pre class="out">` right after the snippet |
| the page's own script | one `<script>` at the end of `<body>`, which runs without the network |

### Video captions

Put a video in a `<figure>` with `<video controls>` and a `<figcaption>`. Keep the files under `media/`, and list
them in the unit's `media` entry in `units.json`.

Chrome refuses `<track src="captions.vtt">` on a page opened from disk (`file://`). Put the WebVTT text in the
page instead, and point the video at it. `unit.js` turns it into a caption track:

```html
<video controls src="media/flow-matching.mp4" data-vtt="cap-flow"></video>
<script type="text/vtt" id="cap-flow">
WEBVTT

00:00.000 --> 00:04.000
Start with random noise.
</script>
```

### Go further items

The optional "Go further" part lists one to four external pages, videos or courses on the concept. Each item gives
the title as a link, the author or site, the format, the level, and one line on why it is worth the reader's time:

```html
<li>
  <div class="fl-head">
    <a href="https://…">Title</a>
    <span class="fl-src">Author or site</span>
    <span class="fl-format">Interactive page</span>
    <span class="level-badge level-intermediate">Intermediate</span>
  </div>
  <p class="fl-why">Why it is worth the reader's time, in one line.</p>
</li>
```

Formats are short words in sentence case: Interactive page, Article, Video, Course, Book. The checker does not
follow external links, so open each one before you add it. `scripts/check_links.py` fetches them in bulk.

## Add a unit

1. Add an entry to `units.json` with `id`, `title`, `level`, `kind`, `minutes`, `prereqs`, `summary` (one plain
   sentence), `owner`, `status` and `media`. Set `status` to `"planned"`. `kind` may be left out; it defaults
   to `"concept"`.
2. Copy `_template.html` to `<id>.html`. Set the two `<meta>` tags, the `<title>` and the `<h1>`.
3. Write the parts. Delete the template's sample text and the "Go further" section if you have nothing good.
4. Set `status` to `"draft"` in `units.json`. The index links a unit only when its status is not `"planned"`.
5. Run the build, then the render check, and fix every error.

## Register an explanation

An explanation published in this repo lists its sections in `units.json` under `explanations`. The build then
adds each section to the "Where this shows up" block of every unit it uses, and lists the explanation on the
index. None is registered yet.

```json
"explanations": [
  {
    "id": "short-id",
    "title": "The explanation's title",
    "page": "../some-folder/page.html",
    "sections": [
      { "anchor": "section-id", "title": "The section's heading", "uses": ["vectors", "distance"] }
    ]
  }
]
```

`page` is a path relative to this folder, and it must stay inside this repo. Each `anchor` must be an `id` in
that page. If the page is built from a template, rebuild it before you run the checker. In the explanation, link
to a unit with a plain relative link, such as `../units/vectors.html`.

An explanation kept in another repo is never listed here. It links to the units by relative paths from a clone
beside this one, such as `../../explainers-public/units/vectors.html`, and keeps its own `explanations.json`.
`build_units.py --check-private DIR` checks that file against this manifest, and checks every link on its pages.

## Keep units public-safe

This repo is public, and a push is public at once. A list of forbidden strings, which name projects, people and
code bases that are not public, lives outside this repo, in the private `explainers-private` repo, so the list
itself stays private. Two scripts read it:

- `build_units.py` fails any unit page, `index.html`, `about.html`, `_template.html` or `units.json` that contains a
  listed string, ignoring case and inside words. It checks whole pages, generated blocks included.
- `scripts/scan_public.py` checks every file, every path and every commit message that a push sends. The
  pre-push hook runs it (see the repo's README). It also fails a session URL or an absolute home folder.

Both find the list in this order: `--forbidden PATH`, then `$EXPLAINERS_FORBIDDEN_LIST`, then
`../explainers-private/forbidden-strings.txt` beside this repo. Without a list, the build prints a notice and
skips the check, as it does in CI; the scan refuses to run unless you pass `--builtin-only`.

Matching works inside words, so an entry can also block an ordinary word that contains it. Rephrase the unit.

## Commands

Run these from the repo root. [`checks.md`](../skills/explainer-units/references/checks.md) gives the order to run
them in, and what each one catches and misses.

```sh
# Fill the generated blocks, write index.html, then check everything. Exit status 1 means an error.
python3 -I -B scripts/build_units.py

# Check only, and write nothing. Add --require-all to require a page for every unit.
python3 -I -B scripts/build_units.py --check

# Render every page in headless Chrome at 1280 px and 390 px, and save screenshots.
# Use your own port when several checks run at once; --only limits the run to some pages.
node scripts/render_check_units.mjs tmp/units-shots --port 9334
node scripts/render_check_units.mjs tmp/units-shots --port 9335 --only vectors,distance

# Check the local links and #anchors of any pages, here or elsewhere; writes nothing:
python3 -I -B scripts/build_units.py --check-links units/*.html

# Review helpers. Fetch every external link and report its status and whether its #anchor exists:
python3 -I scripts/check_links.py tmp/units-links.tsv units/*.html
# Run every Python snippet and compare its output with the page's output block (needs NumPy and PyTorch):
python3 -I scripts/run_snippets.py <python> tmp/units-snippets units/*.html
# Screenshot each figure on its own, light and dark, to read it at full size:
node scripts/figshots.mjs tmp/units-figs --port 9336 --only vectors
# For a page that quotes code: check each code block against the commit it cites:
python3 -I -B scripts/check_code_blocks.py --repos <folder of clones> <page>
```

The build writes a file only when its content changes, so running it twice changes nothing.
[`checks.md`](../skills/explainer-units/references/checks.md) lists what the build check and the render check report.
