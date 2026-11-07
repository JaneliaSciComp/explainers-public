# Figures, widgets, colour words and snippets

A figure, a widget or a snippet is a claim, just like a sentence. Review found pictures that contradicted their
captions and code that did not show what the text said, although every page rendered cleanly and every snippet's
output matched. This file says how to make each one show what the text says. `units/README.md` lists the classes and
attributes that `unit.css` and `unit.js` read.

## Every page works from disk, on a phone, in both themes

- Draw figures as inline `<svg>` or `<canvas>`. Use no libraries and no external files. A reader may open the page
  from disk, offline.
- Put the page's script in a classic `<script>` at the end of `<body>`. A page opened from disk (`file://`) cannot
  load an external ES module, cannot `fetch` a local file, and cannot start a worker from a file. So keep the data in
  the page.
- Give each SVG `width`, `height` and `viewBox`. The CSS then shrinks it to fit a phone.
- Wrap anything wider than a phone in `<div class="scroll-x">` or `<div class="table-wrap">`. The page itself must
  never scroll sideways at 390 px, and the render check fails it if it does.
- On an SVG that the reader drags, set `style="touch-action:none"`, so that a drag on a phone moves the point and not
  the page. Make each handle large enough to hit with a finger.

## A figure shows what its caption says

- Write a figure title (`<div class="fig-title">`) that states what the picture shows, and a caption that says what
  to look at. Give the SVG or canvas a one-sentence `aria-label`.
- Use one scale on both axes whenever shapes, angles or distances matter. A figure that drew y at 26 pixels per unit
  and x at 18 made normalizing seem to change a shape's proportions.
- Keep every mark visible. A "shadow" bar drawn along an arrow, under the arrow, showed only as a thin edge; the fix
  drew it a little to one side.
- Define every symbol that the figure shows before the figure or in its caption.
- Say what the figure fixes on purpose. One widget lets the reader turn a line only about the average point. Its
  caption says so, so that the reader does not take this for a property of every line.
- Keep each colour and symbol to one meaning through the page.
- Look at each figure's screenshot in light and dark at full size, and read the drawing code for its scales.

## A widget has a goal, and its start state does not give the answer

Add a widget only when moving something teaches more than a still picture: a slider that turns a shape, a button
that takes one more step. Guided discovery teaches, and a bare sandbox does not, so:

- Give the widget one or two controls, in `<div class="controls">`, and show its numbers in `<output>` elements.
- State a goal or a question in the caption: "**Try this.** …" or "**Predict first.** …". Ask the reader to predict
  before they move anything.
- Make sure the start state does not show the answer. One widget asked for the smallest frequency with some
  property, and its slider started at that frequency; it now starts at 1. Another asked for the points at distance 5
  from a point A, and its movable point started on one of them; the goal now asks for the other two.
- Make the instructions match what the widget does. "Before you let go, predict which boxes turn gray" did not work,
  because the boxes changed during the drag. The caption now asks for the prediction before the drag.
- Make every state true, the idle one included. A race that had not started labelled its two sides "working…" and
  "copying in…"; it now says "ready".
- Make every readout correct for every input. A distance readout printed "√(−3² + −4²)", and −3² is −9 by the order
  of operations. The fix puts each negative number in brackets before it is squared.
- Move every control to its extremes. Dragging one arrow far enough pushed the handle of another off the drawing,
  where nobody could grab it.
- Press every button, and check that something moves. `scripts/check_buttons.mjs` presses each one; see
  [checks.md](checks.md). A Play button added about 0.004 per frame to a slider with
  `step="0.01"`. A range input rounds each value it is given to its step, so the time never moved. Keep an animated
  value in a variable, and only show it on the slider.
- When the picture cannot show a difference that the question needs, give the numbers in the caption. One line was
  ahead of another by 121 to 120 at step 2, a gap too small to see.
- Test the widget's arithmetic outside the page, for example by running its functions in Node, or drive the page in
  headless Chrome.
- On a canvas, read colours from CSS with
  `getComputedStyle(document.documentElement).getPropertyValue('--s1')`, and redraw when
  `matchMedia('(prefers-color-scheme: dark)')` changes.

## Colour words must hold in both themes

Colour SVG with the classes in `unit.css` (`f-s1` … `f-s4` for fills, `st-s1` … `st-s4` for strokes, `muted` and
`ink2` for text) or with `var(--s1)` and the other tokens. Then dark mode works without extra code. The words in the
text must work in both themes too:

| Token | Light | Dark | Call it |
|---|---|---|---|
| `--s1` | blue | blue | blue |
| `--s2` | orange | orange | orange |
| `--s3` | green | green | green |
| `--s4` | yellow | dark yellow | yellow |
| `--bad` | red | light red | red |
| `--ink` | near black | near white | name the mark's shape: "the round dot", "the tick on the axis" |
| `--ink-3` | grey | grey | grey |

- Never call an `--ink` mark black or white, and never call samples "dark" or "light". Use shape or fill: "solid
  dots", "large dots", "faint".
- Check each colour word against the token that the code uses. A page called some points red while it drew them in
  `--s2`, which is orange; the fix drew them in `--bad`.
- To find the words, run `grep -n -i -w -E 'black|white|dark|light|red|blue|orange|green|yellow|grey|gray'
  units/<id>.html`, and read the dark screenshot of each figure.

## Snippets show what the text says

Show code where it helps the reader, and don't avoid it. Code is most useful where a figure or a widget can't show
the idea, and in a unit about coding it is part of the lesson. List `python-basics` or `numpy-arrays` among the
prerequisites only when the lesson depends on the code: in a unit about coding, or where the code carries part of the
idea. Keep all other code easy to read, by the rules below.

Python is the default language, but it can vary depending on the application. In Python, use plain Python, NumPy or
PyTorch. Keep each snippet short and runnable as it stands: `scripts/run_snippets.py` runs each one alone, in its own
empty folder. The script runs only `<code class="py">` blocks. Put code in another language, or an excerpt that
cannot run alone, in a plain `<pre><code>`, and run it yourself if it prints anything.

- Put everything a snippet prints in a `<pre class="out">` block right after it, exactly as printed. The snippet
  check compares only that block. It does not read comments, so a value that you give in a comment is unchecked:
  print it instead, or check it by hand.
- Fix the random seed, for example `rng = np.random.default_rng(0)` or `torch.manual_seed(0)`, so the output is the
  same on every run.
- Make the text match what each line prints, and when. One page said that its output showed `cpu` because the
  computer had no GPU. But the snippet printed the device before it moved the tensor, so it said `cpu` everywhere.
- Produce every number and table that the text credits to the code from that code. A table of search costs in 3D
  came from code that split on all three axes, while the snippet split only on x and y.
- Make every comment true, and true of the page's own figure. A comment beside `b - a` said "the arrow from a's tip
  to b's tip". In the page's figure, b starts at a's tip, so that arrow is b itself. The comment now says "the arrow
  from point a to point b".
- Name the method that the code uses. A caption said that a widget moved particles by Euler's method; its script
  used the midpoint method.
- Check orientation with a small case. In code, tokens are the rows of a matrix, so `X @ Wq` holds each token's query
  only when `Wq` is the transpose of the matrix in the formula. A 2 × 2 matrix and one vector are enough to see it.
- Keep to the Python that `python-basics` teaches. A snippet that used a generator expression became a list
  comprehension, which `python-basics` teaches. For anything beyond it, such as a NumPy or PyTorch call, link the
  unit that teaches it, such as `numpy-arrays`, or a good outside tutorial, or say in a comment what it does.
- Put a file name or a short label above each snippet in `<p class="code-cap">`.

A unit never quotes a project's code. A page that does is an explanation, and
[code-explanations.md](code-explanations.md) covers it.
