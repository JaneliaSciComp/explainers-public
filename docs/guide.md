# A guide to writing concept units

This guide says what makes a good concept unit, and how to write, check, review and fix one. It also says how to have
an AI agent do the work with the repo's skill. `units/README.md` gives the mechanics: the manifest, the page parts and
the commands. The skill in `skills/explainer-units/` holds the detailed rules, and this guide links to them.

## A good unit teaches one idea, accurately, to a stated reader

A concept unit is a short web page that teaches one general idea in 5 to 10 minutes. A good unit has these
qualities:

- **One concept.** Its idea fits in one paragraph of at most six short sentences. A reader comes to look up one
  idea, so a unit that holds two ideas becomes two units, or a hub that links them.
- **A stated reader.** Its level, `hs`, `u1` or `u2`, says what the reader knows. Its prerequisites reach every
  concept the page uses, and every chain of prerequisites ends at high-school units.
- **True claims, with their conditions.** Each sentence holds as written. Where the page simplifies, a warning box
  names the detail it leaves out. Each fact comes from a source that the writer opened.
- **A worked example with every step.** A reader at the unit's level can redo it on paper, then try a similar
  problem.
- **A figure that shows what the text says.** A widget appears only where moving something teaches more than a
  still picture, and it comes with a goal.
- **Questions that make the reader recall and apply the idea,** with the answers hidden until asked for.
- **The same notation and terms as the units it links.**
- **Plain English,** by the rules in
  [`skills/explainer-units/references/plain-english.md`](../skills/explainer-units/references/plain-english.md).
- **A page that works anywhere:** opened from disk, on a 390 px phone, and in dark mode.
- **Public safety.** A unit never names a project that is not public, and never quotes or describes one project's
  code, data, people or results, even without naming them. Public attribution is fine, such as the author or site of
  a "Go further" item.

## The workflow has four steps: write, check, review, fix

1. **Write.** Scope one concept, list what the page will use, and set the prerequisites. Read the units you link,
   then write the page from `units/_template.html`. The skill's
   [`SKILL.md`](../skills/explainer-units/SKILL.md) gives the steps, and
   [`writing.md`](../skills/explainer-units/references/writing.md) and
   [`figures-and-code.md`](../skills/explainer-units/references/figures-and-code.md) give the rules.
2. **Check.** Run the build check, the render check, the snippet check, the link check and the figure screenshots,
   in that order. Then read the page once for each of the most common errors.
   [`checks.md`](../skills/explainer-units/references/checks.md) gives the commands and what each one catches.
3. **Review.** A second reader, a person or an agent that did not write the page, checks it with
   [`reviewing.md`](../skills/explainer-units/references/reviewing.md). The reviewer edits nothing. It writes each
   finding as a quote, a problem, the evidence and a fix, at one of five severities.
4. **Fix.** The owner of the page verifies each finding, then fixes it or rejects it with a reason, using
   [`fixing.md`](../skills/explainer-units/references/fixing.md). After every finding has a disposition,
   whoever integrates the fixes sets the unit's status to `reviewed`, runs the build, and reruns the checks.

The severities are these:

| Severity | Meaning |
|---|---|
| `error` | a false statement; a wrong number, formula, code comment, figure or widget; a wrong answer to a check question |
| `misleading` | defensible, but a reader would come away believing something false; or a simplification without a warning box |
| `level` | the page needs knowledge it neither teaches nor links, or it sits above or below its level |
| `clarity` | a reader would likely stumble |
| `nit` | small |

The first three are the substantive ones. Before you push, install the pre-push hook once with
`sh scripts/install-hooks.sh`. It scans everything a push sends for names that must stay private.

## Scripts catch the mechanical errors, and reading catches the rest

The first 73 units passed every script. Four reviewers then raised 110 findings on the pages, 45 of them substantive,
on 34 of the 73 units. The substantive ones were 8 errors, 22 misleading statements and 15 level problems. With the
reviewers' notes and the findings on the manifest and the video, there were 125 items, and they fall into 12 patterns:

| Pattern | Items | Substantive |
|---|---|---|
| A page uses a concept it neither teaches nor reaches through its prerequisites, or links a unit that lacks the cited fact | 16 | 15 |
| A claim drops a condition, or a simplification has no warning box | 22 | 14 |
| A fact, number or name stated from memory, and wrong | 13 | 8 |
| Code, its output or a table does not show what the text says | 6 | 4 |
| A figure or widget misleads: unequal scales, a hidden mark, a start state that shows the answer, a wrong readout | 11 | 3 |
| A "Go further" item names the wrong section, level or claim | 14 | 2 |
| A worked example skips or asserts a step, or uses a symbol before defining it | 9 | 1 |
| Captions or narration out of step with the render | 2 | 1 |
| A level badge set too high | 1 | 1 |
| Notation or a term drifts within a page or between linked units | 17 | 0 |
| Ambiguous wording | 9 | 0 |
| A colour word that is false in dark mode, or names the wrong colour | 5 | 0 |

The first three patterns hold 37 of the 49 substantive items, and no script catches them. A writer prevents them by
listing every concept the page uses, by testing each claim on its edge cases, and by checking each fact against a
source. [`error-patterns.md`](../skills/explainer-units/references/error-patterns.md) gives an example of each
pattern from a unit page, and the check that catches it.

One error shows why a dropped condition matters. The flow-matching pages said that crossing paths force a network to
average them, and left out "at the same time". The same claim then appeared in a heading, a figure's answer, a
"Go further" description, a second unit and the video's narration. Write a condition in the same words every time,
and when review finds one dropped, search every page and the media for the same claim.

## Use the skill with an agent

The skill is the folder `skills/explainer-units/`. `SKILL.md` gives the steps of each task: write, check, review and
fix. The files in `references/` hold the rules, which an agent reads when a task needs them. `evals/` holds four
test cases. An agent needs only a clone of this repo, Python 3, and for some checks Node.js, Google Chrome, NumPy and
PyTorch.

**Claude Code.** Claude Code loads a project's skills from `.claude/skills/`. Link the skill there once in your
clone, and keep the link out of commits:

```sh
mkdir -p .claude/skills
ln -s ../../skills/explainer-units .claude/skills/explainer-units
echo .claude/ >> .git/info/exclude
```

Claude Code then lists `explainer-units` among its skills, and loads it when a task matches its description. To
use the skill from a folder outside the clone, make the same link with a relative path to the clone's
`skills/explainer-units`.

**Codex.** Codex reads `AGENTS.md`, which tells it to read `skills/explainer-units/SKILL.md` before it writes, checks,
reviews or fixes a unit.

**Any other agent.** Tell it to read `skills/explainer-units/SKILL.md` first, and the reference files that the task
names.

A request can be short, because the skill holds the rules:

- "Add a concept unit `<id>` at level `u1` on `<topic>`, add its manifest entry, and run the checks."
- "Review `units/<id>.html` with `skills/explainer-units/references/reviewing.md`, and write the findings to
  `tmp/review/R1.json`."
- "Fix the findings in `tmp/review/R1.json` with `skills/explainer-units/references/fixing.md`."

**Testing the skill.** Each folder in `evals/` holds a prompt, the expected outcome and five checks, in the format
that the skill-creator skill and `claude plugin eval` read. A test runs each prompt with the skill and without it,
and compares the results. Each run is a real model run, and it costs money.

## Licences

This guide is documentation, under CC BY 4.0. The skill, its reference files and the scripts are code, under the
BSD 3-Clause licence. See [`LICENSE-CONTENT.md`](../LICENSE-CONTENT.md) and [`LICENSE`](../LICENSE).
