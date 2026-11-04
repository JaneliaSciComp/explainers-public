# The checks, what each one catches, and the order to run them

Run every command from the repo root. Run the scripts first, then read the page for meaning.

Passing every script does not make a page correct. The first 73 units passed all of them, and review still found 45
substantive problems on 34 of the units. They were 8 errors, 22 misleading statements and 15 level problems. The
scripts settle the mechanical questions, so that your reading time goes to meaning.

## Run them in this order

| Step | Command | What it catches |
|---|---|---|
| 1. Build (writer only) | `python3 -I -B scripts/build_units.py` | fills the generated blocks and writes `units/index.html`, then runs every check of step 2 |
| 2. Strict check | `python3 -I -B scripts/build_units.py --check --require-all` | the manifest, the page parts, the links inside the repo, the forbidden list; writes nothing |
| 3. Render | `node scripts/render_check_units.mjs tmp/units-shots --port 9334 --only <id>` | script errors, sideways scrolling, media that fail to load |
| 4. Snippets | `python3 -I scripts/run_snippets.py <python> tmp/units-snippets units/<id>.html` | a snippet that fails, or whose output differs from its output block |
| 5. External links | `python3 -I scripts/check_links.py tmp/units-links.tsv units/<id>.html` | a link that does not load, or an `#anchor` that does not exist |
| 6. Figures | `node scripts/figshots.mjs tmp/units-figs --port 9336 --only <id>` | nothing by itself: it saves each figure, light and dark, for you to look at |
| 7. Quoted code (explanations only) | `python3 -I -B scripts/check_code_blocks.py --repos <clones dir> <page>` | a code block that differs from the commit it cites |
| 8. Meaning | read the page once per pattern in [error-patterns.md](error-patterns.md), then once by [plain-english.md](plain-english.md) | what no script can see |
| 9. Leak scan | the pre-push hook, or `python3 -I -B scripts/scan_public.py --all` after you commit | a forbidden string, a session URL or a home folder in anything pushed |

`<id>` is the unit's id, and `--only` takes several, separated by commas. `<python>` is an interpreter that has NumPy
and PyTorch. `tmp/` is ignored by git, so the outputs stay out of commits.

The order has reasons:

- The build comes first because it is the cheapest check, and because it writes the blocks that the page shows. A
  page whose prerequisites block is still empty renders differently.
- The render comes before the figure screenshots, because a script error leaves figures blank or half drawn.
- The snippets and links come next. They need NumPy and PyTorch, or the network, and they take longer.
- Reading comes last, once the scripts have passed, so that no reading time goes to what a script would have caught.
- The leak scan reads commits, not the working tree. So it runs after you commit and before you push.

Only the writer runs step 1. A reviewer or a fixer runs `--check` only, because the build rewrites every unit page,
and other agents may be editing pages at the same time.

## What each check reports

**The build check** (steps 1 and 2) exits with status 1 on any error. It reports:

- a manifest error: a missing key, an unknown prerequisite, a cycle, or a chain that does not end at `starting`;
- a missing page for a unit that is not `planned`, or a page with no unit;
- a missing or out-of-order page part, or a `<meta>`, `<title>` or `<h1>` that does not match the manifest;
- a local `href` or `src` that points to a missing file or a missing `#id`, or outside the repo;
- a string from the forbidden list, when the list is present.

It warns, without failing, about a concept unit with "and" in its title, and about a prerequisite at a higher
level than the unit. Treat each warning as an error to fix or to justify. It cannot check
that the prerequisites cover what the page uses.

**The render check** (step 3) opens each page from disk in headless Chrome. It reports console errors and uncaught
exceptions, sideways scrolling at 1280 px and 390 px, and images, videos or caption tracks that fail to load. It
exits with status 1 on any problem. It saves three screenshots of each page: light at 1280 px with the answers open,
dark at 1280 px, and light at 390 px. It needs Node.js and Google Chrome. Give runs at the same time different ports.

**The snippet check** (step 4) runs each `<pre><code class="py">` block alone, in an empty folder, and compares what
it prints with the next `<pre class="out">` block. It prints a count of each state and lists every snippet that did
not match:

| State | Meaning |
|---|---|
| `match` | the output equals the block |
| `match-ws` | they differ only in spaces; make them equal |
| `MISMATCH` | they differ; the diff is in `tmp/units-snippets/diffs/` |
| `ERROR` | the snippet failed or ran over 120 seconds |
| `no-out-block` | the snippet prints, but the page shows no output block |
| `ran-no-output` | the snippet printed nothing, and the page shows no block |

It always exits with status 0, so read its summary line. It does not read comments or the prose about the output.

**The link check** (step 5) fetches every external link once and writes a table. Its columns are the HTTP status, the
state of the `#anchor` (`found`, `MISSING`, `no-body`, `not-an-id` or `-`), the URL, any redirect, and the pages that
use it. It prints how many links "need a look". A page that builds itself with a script may add its anchors only when
the script runs. So open a `MISSING` anchor on such a page in a browser before you change the link. It also exits with
status 0. It cannot tell whether your description of the page is true.

**Local links on other pages.** The build check covers the unit pages. For any other page, such as an explanation,
run `python3 -I -B scripts/build_units.py --check-links <page>...`. It writes nothing.

**The figure screenshots** (step 6) save `<id>-fig<N>-light.png` and `-dark.png` for each `<figure>`. Open each one.
Look for text or lines that vanish in dark mode, scales that differ between axes, and marks hidden under others.

**The code-block check** (step 7) is for pages that quote code; units do not. It needs each block's `data-src`, and
exits with status 1 when a block differs from its source. See [code-explanations.md](code-explanations.md).

**The leak scan** (step 9) checks every file, path and commit message that a push sends. The pre-push hook runs it;
install the hook once per clone with `sh scripts/install-hooks.sh`. It needs the private forbidden list, which is
not in this repo; the repo's `README.md` says where it looks. Without the list, the build check skips the
forbidden-string check and says so.

## What no script checks

The scripts cannot tell whether a claim is true, whether the reader can follow it, or whether a picture shows what
its caption says. The three most common substantive errors are of that kind: a concept used without a prerequisite,
a claim that drops a condition, and a fact stated from memory. Step 8 is where they are caught, before a reviewer
has to. [error-patterns.md](error-patterns.md) gives the check for each pattern.
