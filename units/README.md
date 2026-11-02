# Concept units

This folder holds concept units: short HTML pages that each teach one idea. Every unit lists the units a reader
may need first, down to high-school level. A colleague or an intern can start at any unit and follow those links
back until the material is familiar. Explanations, such as a part of a report, link to units for the background
they assume.

`units.json` is the manifest. It lists every unit, its level and its prerequisites, and the explanations that use
units. `scripts/build_units.py` fills the generated parts of each page and writes `index.html`. It also checks
that every page has its required parts and that every link works.

## What a unit is, and what it is not

A unit teaches one general concept that many explanations can reuse: vectors, gradient descent, KD-trees. A
reader should never have to work through a large curriculum to understand one idea.

A unit is not about one project. It never quotes a project's code or names its data, people or results. That
material stays in the explanation, which links to the unit. A unit links back only to explanations published in
this repo, and only through its generated "Where this shows up" block. Explanations kept elsewhere link to the
units, but the units never link to them.

## One concept per unit

- Teach one concept in each unit. A concept unit takes about 5 to 10 minutes to read.
- Link to a prerequisite rather than teach it again.
- If the idea needs more than one paragraph to state, split the unit into focused units.
- Put broad external courses only in "Go further", as optional background.

Each manifest entry has a `kind`:

- `concept`, the default: one idea, about 5 to 10 minutes.
- `hub`: a short overview that ties several focused units together. For example, a training-loop hub links the
  units on minibatches, data loaders and checkpoints, and lists them as its prerequisites. A hub needs no figure
  or worked example, and its pages show an "overview" tag.

`build_units.py --check` warns, without failing, when a concept unit takes more than 12 minutes or its title
joins two ideas with "and". Treat each warning as a prompt to split the unit or to make it a hub.

## The three levels

| Id | Level | The reader knows |
|---|---|---|
| `hs` | High school | algebra, coordinates, a little geometry; no programming is assumed |
| `u1` | Intro undergraduate | some Python; the `hs` units it lists |
| `u2` | Upper undergraduate | the `u1` units it lists |

Every chain of prerequisites ends at `hs` units. So a `u1` or `u2` unit lists at least one prerequisite, and only
`hs` units may list none. A prerequisite is never at a higher level than the unit that needs it.

## The parts of a unit page, in order

Start from `_template.html`. The checker looks for each part by its marker.

| Part | Marker | Who writes it |
|---|---|---|
| Header: title, level badge, reading minutes | `<header class="unit-head" data-part="header">` with one `<h1>`; the badge and minutes go between `<!-- unit-meta:start -->` and `<!-- unit-meta:end -->` | you write the `<h1>`; the build fills the badge and minutes |
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

## How to write

Write in plain English:

- Put one idea in each sentence, and keep sentences short.
- Use familiar words. Define each technical term the first time you use it, with `<dfn>`.
- Use one term for one thing throughout the page.
- Write headings that state their point: "A KD-tree skips whole boxes of points," not "KD-trees."
- Use the active voice, and give each paragraph one topic.

Be accurate first. Units teach standard textbook material. When the text simplifies, say so in a
`<div class="callout warn">` box that names the hidden detail, rather than stating the simplification as fact.

## Figures and widgets

- Draw figures as inline `<svg>` or `<canvas>`. Use no libraries and no external files.
- Give an SVG `width`, `height` and `viewBox`. The CSS shrinks it to fit a phone.
- Color SVG with the classes in `unit.css` (`f-s1` … `f-s4` for fills, `st-s1` … `st-s4` for strokes, `muted`
  and `ink2` for text) or with `var(--s1)` and the other tokens. Then dark mode works without extra code.
- A canvas draws with colors read from CSS: `getComputedStyle(document.documentElement).getPropertyValue('--s1')`.
  Redraw when `matchMedia('(prefers-color-scheme: dark)')` changes.
- Add a widget when moving something teaches more than a still picture: a slider that rotates a shape, a button
  that takes one more step. Put controls in `<div class="controls">` and numbers in `<output>`.
- Put the page's own script in a `<script>` at the end of `<body>`. It must run without errors and without the
  network.
- Wrap anything wider than a phone (a wide table, a wide drawing) in `<div class="table-wrap">` or
  `<div class="scroll-x">`, so it scrolls inside its own box. The page itself must never scroll sideways at 390 px.

## Python snippets

- Use plain Python, NumPy or PyTorch, and nothing else.
- Keep each snippet short and runnable as it stands. Show the output in a comment or in `<pre class="out">`.
- Write `<pre><code class="py">…</code></pre>`. `unit.js` adds line numbers and highlighting.
  `data-start="N"` numbers from N, and `data-hl="3,4"` highlights lines 3 and 4.
- Put the file name or a short label above it in `<p class="code-cap">`.

## Video and captions

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

## Keep units public-safe

This repo is public, and a push is public at once. A list of forbidden strings, which name projects, people and
code bases that are not public, lives outside this repo, in the private `explainers-private` repo, so the list
itself stays private. Two scripts read it:

- `build_units.py` fails any unit page, `index.html`, `_template.html` or `units.json` that contains a listed
  string, ignoring case and inside words. It checks whole pages, generated blocks included.
- `scripts/scan_public.py` checks every file, every path and every commit message that a push sends. The
  pre-push hook runs it (see the repo's README). It also fails a session URL or an absolute home folder.

Both find the list in this order: `--forbidden PATH`, then `$EXPLAINERS_FORBIDDEN_LIST`, then
`../explainers-private/forbidden-strings.txt` beside this repo. Without a list, the build prints a notice and
skips the check, as it does in CI; the scan refuses to run unless you pass `--builtin-only`.

Matching works inside words, so an entry can also block an ordinary word that contains it. Rephrase the unit.

## Go further: the best outside material

The optional "Go further" part lists one to four external pages, videos or courses on the concept. Each item gives
the title as a link, the author or site, the format, the level, and one line on why it is worth the reader's time:

```html
<li>
  <div class="fl-head">
    <a href="https://…">Title</a>
    <span class="fl-src">Author or site</span>
    <span class="fl-format">Interactive page</span>
    <span class="level-badge level-u1">Intro undergraduate</span>
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

The statuses are `planned` (no page yet), `draft` (written) and `reviewed` (checked by a second reader).

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

## Commands

Run these from the repo root.

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
```

The build writes a file only when its content changes, so running it twice changes nothing. The checker reports:

- a manifest error: a missing key, an unknown prerequisite, a cycle, or a chain that does not end at `hs`;
- as a warning only, a concept unit over 12 minutes or with "and" in its title;
- a missing page for a unit that is not `planned`, or a page with no unit;
- a missing or out-of-order part, or a `<meta>`, `<title>` or `<h1>` that does not match the manifest;
- a local `href` or `src` that points to a missing file or a missing `#id`, or outside this repo;
- a string from the forbidden list in a page or in `units.json` (see "Keep units public-safe").

The render check reports console errors and exceptions, sideways scrolling, and images, videos or caption
tracks that fail to load. It saves three screenshots of each page: light at 1280 px with the answers open, dark at
1280 px, and light at 390 px.
