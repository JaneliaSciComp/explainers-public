# The errors that review found most often

Every mechanical check passed on the first 73 units: the build check, the render check, the links and the
snippets. Four reviewers then read the pages, and raised 125 findings and notes on the units, their manifest and
the video. Of these, 110 were findings on the 73 pages themselves, and 45 of those were substantive. Each of the 125
items falls in one of the 12 patterns below. "Substantive" counts the items whose severity was `error`, `misleading`
or `level`, as [reviewing.md](reviewing.md) defines them.

The first three patterns hold 37 of the 49 substantive items, and no script catches any of them. So read your page
once for each of the first three patterns before you ask for a review.

| # | Pattern | Items | Substantive | What catches it |
|---|---|---|---|---|
| 1 | A page uses a concept it neither teaches nor reaches through its prerequisites, or links a unit that lacks the cited fact | 16 | 15 | listing every concept the page uses, and the prerequisite chain |
| 2 | A claim drops a condition, or a simplification has no warning box | 22 | 14 | testing each claim on its edge cases |
| 3 | A fact, number or name stated from memory, and wrong | 13 | 8 | opening a source for each fact |
| 4 | Code, its output or a table does not show what the text says | 6 | 4 | rerunning the code, and reading the text beside it |
| 5 | A figure or widget misleads: unequal scales, a hidden mark, a start state that shows the answer, a wrong readout | 11 | 3 | the figure screenshots, and the widget's script at its extremes |
| 6 | A "Go further" item names the wrong section, level or claim | 14 | 2 | opening each link at the section named |
| 7 | A worked example skips or asserts a step, or uses a symbol before defining it | 9 | 1 | recomputing each step with only the page |
| 8 | Captions or narration out of step with the render | 2 | 1 | comparing the page's captions with the rendered `.vtt` |
| 9 | A level badge set too high | 1 | 1 | the level table, against what the page needs |
| 10 | Notation or a term drifts within a page or between linked units | 17 | 0 | reading the linked units' notation |
| 11 | Ambiguous wording | 9 | 0 | the plain-English pass |
| 12 | A colour word that is false in dark mode, or names the wrong colour | 5 | 0 | the dark screenshots, and the colour tokens |

## 1. A page uses a concept it neither teaches nor reaches through its prerequisites

16 items, 15 substantive. A page uses a term, a formula, a function or a fact that the reader has not met. It is not
taught on the page, and no unit in the prerequisite chain teaches it. A second form is a link that sends the reader
to a unit for a fact that the unit never states.

**Example, `dot-product.html`.** The page gave the dot product's second form, |**a**| × |**b**| × cos θ. That form
needs a vector's length, which the distance unit teaches, and the cosine, which the sine-waves unit teaches. The
page listed only the vectors unit as a prerequisite, and that unit teaches neither. The fix added `distance` and
`sine-waves` to the unit's prerequisites. The page now links each of them where it first uses it.

Code counts here when the lesson depends on it: in a unit about coding, or where the code carries part of the idea
([figures-and-code.md](figures-and-code.md#snippets-show-what-the-text-says)). Other code needs only a link or a
comment for what goes beyond `python-basics`.

**Check.** List every concept the page uses: in the prose, the captions, the widget readouts, the "Check yourself"
answers, and the code when the lesson depends on it. Find each one on the page or in a unit of the prerequisite chain.
When you cite a unit for a fact, open that unit and find the sentence that states it.
[writing.md](writing.md#prerequisites-cover-every-concept-the-page-uses) has a command that prints the chain. The
build check proves only that the chain is well formed. It cannot tell what a page uses.

## 2. A claim drops a condition, or a simplification has no warning box

22 items, 14 substantive. A sentence states something that holds only under a condition, and leaves the condition
out. Or the page simplifies, and no `callout warn` box names what it hides.

**Example, `rotation-matrices.html`.** The page showed the matrix that turns points around the z-axis. It then said
that the matrices for the x- and y-axes look the same, with the 1 in a different place. For the y-axis that is false:
its two sines swap signs. A reader who only moved the 1 would build a turn in the wrong direction. The fix says that
the two matrices have the same shape, says that for the y-axis the sines swap signs, and shows the y-axis matrix in
full.

**Check.** Look for words that claim everything: "any", "every", "always", "never", "the same", "only", "the main".
Test each such claim on its edge cases: a negative number, zero, a tie, the other axis, the other order, a step that
changes with time. Then write the condition into the sentence, or name the hidden detail in a warning box.

### One dropped condition spread to two pages and the video

Six findings, on the `flow-matching` and `velocity-field` pages and in the video's narration, came from one claim. In
flow matching, a network learns a velocity from a point's place and the time. The pages said that the straight
training paths cross in many places, so the network must learn their average there. But two paths usually pass a
crossing point at different times, and the network tells them apart by the time. Only paths that are at the same place
at the same time force an average. The claim without "at the same time" sat in a heading, in the idea paragraph, in a
figure's answer, in a "Go further" description and in the narration. On the `velocity-field` page, it became the claim
that the learned paths bend wherever the straight training paths would cross, as if learned paths never cross. They
can cross in a still picture, at different times. What never happens, in a smooth field, is that two particles are at
the same place at the same time. The fixers rewrote every copy with the same phrase, "at the same place at the same
time", and re-rendered the video.

The lesson has two parts:

- Write a condition in the same words every time: in headings, captions, summaries and narration as well as in the
  body. A heading or a summary is read as a fact on its own.
- When a review finds a dropped condition, search every page and the media for the claim's key words, for example
  `grep -n -i "cross" units/*.html units/media/*.md`, and fix each copy in the same pass.

## 3. A fact, number or name stated from memory, and wrong

13 items, 8 substantive. A number, a name, a date or a cost came from memory and was wrong, or true only of another
version of the thing.

**Example, `assignment-problem.html`.** The page said that the Hungarian algorithm finds the best pairing in about
n³ steps. Its warning box then described the version that covers zeros with lines. That version, the one the linked
encyclopedia article walks through, takes about n⁴ steps. Only a later, faster form takes n³. The fix says "in its
faster modern form" beside n³, and says that the line-covering version in the box takes about n⁴ steps.

**Check.** For each fact that the page does not derive, open a source and find the statement: a textbook, the
library's documentation or the paper. When versions differ, name the one you mean. Give a measured number with
where it was measured, and a hardware figure with the model it belongs to.

## 4. Code, its output or a table does not show what the text says

6 items, 4 substantive. The code runs and its output matches, but the text around it claims something the code does
not show.

**Example, `kd-tree.html`.** A table counted the distances that "the code above" measured in 2, 3 and 10
dimensions. But the code chose its splitting axis with `depth % 2`, so in 3D it never split on z, and its counts
would have been higher. The table's numbers came from code that cycles through every axis. The fix changed the
line to `axis = depth % pts.shape[1]`. The 2D output did not change, and the table now matches the code on the page.

**Check.** Rerun every snippet with `scripts/run_snippets.py`. Then read the code against each sentence and table
that describes it, and regenerate any number that the text attributes to the code. The snippet check compares only
the output block. It does not read comments, prose or tables.

## 5. A figure or widget misleads

11 items, 3 substantive. The picture contradicts the text: unequal scales, a mark hidden under another, a start state
that already shows the answer, or a readout that is wrong for some positions.

**Example, `normalizing-data.html`.** The figure showed two shapes before and after normalizing. The "before" panel
drew x at 18 pixels per unit and y at 26, so both shapes looked 1.44 times as tall, for their width, as they are. The
"after" panel used one scale. So the figure suggested that normalizing changes a shape's proportions, which it never
does. The fix uses 18 pixels per unit on both axes of the "before" panel.

**Check.** Look at each figure's screenshot in light and dark (`scripts/figshots.mjs`). Read the drawing code for its
scales. Move each control to its extremes and to negative values, and read every readout. See
[figures-and-code.md](figures-and-code.md).

## 6. A "Go further" item names the wrong section, level or claim

14 items, 2 substantive. The description says what the linked page shows, and the linked page shows something else.

**Example, `learning-rate-schedule.html`.** An item said that a book's warm-up section trains the same network with
and without warm-up, and plots the difference. The section trains it only with warm-up. The run without warm-up is
in the section before it, and no plot compares the two. The fix says that the section trains a network with a
straight-line warm-up, and asks the reader to compare its first epochs with the run in the section before.

**Check.** Open each link at the section you name, and read it. Then compare each claim of your description with
what is there: the section's name and number, what it plots or compares, and its level.
`scripts/check_links.py` confirms that the page and the anchor exist. It cannot read the description.

## 7. A worked example skips or asserts a step, or uses a symbol before defining it

9 items, 1 substantive. A step that the reader cannot check from the page, a tool used before it is introduced, or a
symbol in a figure that the text defines only later.

**Example, `sine-waves.html`.** To find sin 30°, the example said that the triangle "is half of an equilateral
triangle". A reader at the Basic level would not see why, and that step gives the answer. The fix shows the step:
reflect the triangle in the x-axis. Together, the triangle and its mirror image have a 60° angle at the origin between
two sides of length 1. So their other two angles are also 60°, and they form an equilateral triangle.

**Check.** Recompute every step with only the page and its prerequisites in front of you. Wherever you need a fact
that neither gives, write the step out or link the unit that holds it.

## 8. Captions or narration out of step with the render

2 items, 1 substantive. A page's copy of the captions comes from an older render, or a title changes before its cue.

**Example, `flow-matching.html`.** The page holds the video's captions inline, because a page opened from disk cannot
load a separate caption file. Those inline captions came from an older render. The ninth cue ended about 0.7 seconds
early, later cues also started early, and the drift reached about 1.7 seconds. Two cues had old wording. So the words
ran ahead of the picture. The fix re-rendered the video and copied the new `.vtt` file into the page exactly. The
transcript was rebuilt from the same cues.

**Check.** After every render, compare the page's inline captions with the `.vtt` file byte for byte. See
[video.md](video.md).

## 9. A level badge set too high

1 item, substantive. The page sits at a higher level than its content needs.

**Example, `conditional-generation.html`.** The unit was marked `advanced`. Its content was two bell curves, an
average and one formula read in words, and its only prerequisite was an `intermediate` unit. The fix set the unit to
`intermediate` in the manifest and on the page.

**Check.** Compare what the page assumes with the level table in `index.html#levels` on the front page, and with
[writing.md](writing.md#set-the-level-by-what-the-page-needs). Set the level by what the page needs, not by how
advanced the topic sounds.

## 10. Notation or a term drifts within a page or between linked units

17 items, none substantive, but they cost readers time. One symbol or word means two things, or two linked units
write one thing two ways.

**Example, `fourier-features.html`.** The page named its list of sine and cosine features γ(x). But the units on layer
normalization and time conditioning use γ for a learned scale. The time-conditioning unit links this page, and it
wrote γ(t) for a scale right after it sent readers here. The fix renamed the feature list φ(x), so γ means only the
learned scale across the linked units.

**Check.** Open each unit you link and each unit that will link yours, and use their symbols and terms. Then read your
page for any word used in two senses. [writing.md](writing.md#notation-and-terms-match-the-linked-units) lists the
conventions the units share.

## 11. Ambiguous wording

9 items, none substantive. A sentence has two readings, and the reader may take the wrong one.

**Example, `farthest-point-sampling.html`.** The idea paragraph said that the method picks "the point that is
farthest from every point picked so far". That can mean the largest total distance. The method takes the point whose
nearest pick is farthest away. The fix says exactly that.

**Check.** Read each sentence that holds a quantifier ("every", "each", "all") or a comparison, and ask what else it
could mean. Follow [plain-english.md](plain-english.md).

## 12. A colour word that is false in dark mode, or names the wrong colour

5 items, none substantive. The text names a colour that the reader does not see.

**Example, `matrix-times-vector.html`.** A readout said that a point "lands on the black dot". The dot is drawn in the
ink colour, which is near white in dark mode. The fix says "the round dot".

**Check.** Name marks by shape or by a hue that holds in both themes. Look at the dark screenshot of each figure. See
[figures-and-code.md](figures-and-code.md#colour-words-must-hold-in-both-themes).
