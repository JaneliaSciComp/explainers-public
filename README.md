# Explainers

This repo holds concept units: short web pages that each teach one general idea, such as vectors, KD-trees or
flow matching. Every unit lists the units to read first, down to high-school level. A reader can start at any
unit and follow those links back until the material is familiar.

Read the pages at https://janeliascicomp.github.io/explainers-public/. GitHub Pages publishes them from `main`.
The site mirrors the repo's paths, so `units/vectors.html` here is
https://janeliascicomp.github.io/explainers-public/units/vectors.html.

## What is where

| Path | What it holds |
|---|---|
| `units/` | the unit pages, the manifest `units.json`, `unit.css`, `unit.js`, `_template.html`, the generated `index.html`, and a `README.md` on the mechanics of a unit page |
| `units/media/` | the flow-matching video and its captions, narration script and poster; `src/` holds the Manim scene that renders them |
| `scripts/` | the build and checks: `build_units.py`, `render_check_units.mjs`, `check_links.py`, `run_snippets.py`, `figshots.mjs`, `check_code_blocks.py`, `scan_public.py`, `install-hooks.sh` |
| `docs/` | `guide.md`, the guide for people: what makes a good unit, the workflow, the common errors, and how to use the skill |
| `skills/` | `explainer-units/`, the agent skill for writing, checking, reviewing and fixing units: `SKILL.md`, its `references/` and its test cases in `evals/` |
| `.github/workflows/` | `check.yml` runs the checks on every push and pull request; `pages.yml` publishes the site |

## Clone the repo with its video

The video is stored with Git LFS. Install Git LFS once on your machine, then clone:

```sh
git lfs install
git clone https://github.com/JaneliaSciComp/explainers-public.git
```

Without Git LFS, `units/media/flow-matching.mp4` is a small text pointer instead of the video.

## Build and check

Run these from the repo root. The build scripts need only Python 3. The render check needs Node.js and
Google Chrome.

```sh
# Fill the generated blocks, write units/index.html, then check everything. Exit status 1 means an error.
python3 -I -B scripts/build_units.py

# Check only, and write nothing. --require-all also requires a page for every unit.
python3 -I -B scripts/build_units.py --check --require-all

# Render every page in headless Chrome at 1280 px and 390 px, and save screenshots in tmp/.
node scripts/render_check_units.mjs tmp/units-shots
```

`units/README.md` gives the mechanics of a unit page and lists the other checks. `docs/guide.md` and the skill in
`skills/explainer-units/` say how to write a good unit.

## Install the pre-push hook before you push

Everything pushed here is public at once. So a leak scan runs on your machine before each push, in a git
pre-push hook. Install the hook once in each clone:

```sh
sh scripts/install-hooks.sh
```

The hook runs `scripts/scan_public.py --pre-push`. The scan checks every file, path and commit message that the
push sends. It refuses the push if it finds a string from the private forbidden list, a session URL, or an
absolute home folder. Then the hook runs `git lfs pre-push`, which uploads the video.

The forbidden list is not in this repo. The scan looks for it at `../explainers-private/forbidden-strings.txt`
beside this clone, or at the path in `$EXPLAINERS_FORBIDDEN_LIST`. Without the list, the hook refuses the push.
To scan the whole history by hand, run `python3 -I -B scripts/scan_public.py --all`.

CI has no list. It runs the build check, which then skips the private-name check, and the scan with
`--builtin-only`.

## Licences

- Pages, media and documentation: CC BY 4.0. See `LICENSE-CONTENT.md`.
- Scripts, workflows and skills: the BSD 3-Clause licence in `LICENSE`. The skills are the folders in `skills/`,
  with their reference files and test cases. The Python snippets and widget scripts inside the pages are also under
  BSD-3-Clause.

Copyright (c) 2026, Howard Hughes Medical Institute.
