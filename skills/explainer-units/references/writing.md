# Writing the text of a concept unit

This file holds the practices for the text of a unit. `units/README.md` gives the mechanics: the manifest, the page
parts and their markers. [figures-and-code.md](figures-and-code.md) covers figures, widgets and snippets. Most rules
here come from errors that review found in the first 73 units, which [error-patterns.md](error-patterns.md) counts.

Contents: one concept; levels; prerequisites; conditions and warning boxes; facts with sources; worked examples;
"Check yourself"; notation; wording; "Go further"; the evidence behind the page parts.

## A unit teaches one concept

- Teach one concept that many explanations can reuse. Readers arrive from an explanation to look up one idea, and a
  unit that holds several makes them work through a course instead.
- Let the concept set the page's length. Explain it as simply as it can be explained at the unit's level, with every
  step, condition and warning box a reader needs, then stop. Don't cut a needed part to shorten the page, and don't
  pad a simple concept. The manifest's `minutes` tells readers what to expect; it is not a target.
- Write "The idea in one paragraph" first, in at most six short sentences. If you cannot state the concept that
  briefly, the unit holds more than one concept: split it.
- Link a prerequisite rather than teach it again. A one-sentence reminder with a link is fine.
- Explain only the concept. For anything about the site, such as what the levels mean or how the lists of units to
  read first work, link a section of `units/about.html`, for example `about.html#levels`. A copy on the page goes
  out of date when the site changes.
- Put broad external courses only in "Go further", as optional background. The unit itself must stand alone.
- If the page starts teaching a second concept, move that concept to its own unit and link it. The build warns when a
  title joins two ideas with "and"; treat the warning as a prompt to check. A `hub` is the exception: it ties several
  focused units together, lists them as its prerequisites, and needs no figure or worked example.

## Set the level by what the page needs

`units/about.html#levels` defines the three levels, `starting`, `intermediate` and `advanced`. A level describes the
background that a unit assumes in its own field, not the reader's school year. To choose one:

- Set the level by what the page assumes, not by how advanced the topic sounds. Review moved one unit from
  `advanced` to `intermediate`, because its content and its only prerequisite were `intermediate`.
- Set the level by the text. Code is extra material for readers who program, so it does not raise the level. See
  [figures-and-code.md](figures-and-code.md#snippets-show-what-the-text-says).
- A prerequisite is never at a higher level than the unit that needs it. The build check fails a cycle or an unknown
  id, and warns about a prerequisite at a higher level.

## Prerequisites cover every concept the text uses

A missing prerequisite was the most common substantive finding: 15 of 49. The build proves only that the chain is
well formed, so do this by hand:

1. List what the text uses: terms, symbols, formulas and facts. Read the captions, the widget readouts and the
   "Check yourself" answers too, not only the prose. Leave out the code: it is extra material, and needs no
   prerequisite (see [figures-and-code.md](figures-and-code.md#snippets-show-what-the-text-says)).
2. Print the unit's prerequisite chain. Run this from the repo root, with the unit's id last:

   ```sh
   python3 -I -c '
   import json, sys
   units = {u["id"]: u for u in json.load(open("units/units.json"))["units"]}
   todo, chain = list(units[sys.argv[1]]["prereqs"]), set()
   while todo:
       p = todo.pop()
       if p not in chain:
           chain.add(p)
           todo += units[p]["prereqs"]
   print(" ".join(sorted(chain)))' dot-product
   ```

3. Find each listed item on the page or in a unit of the chain. For an item that is in neither, do one of three
   things. Add the unit that teaches it to `prereqs`, when the page's main point or its worked example depends on it.
   Teach it in a sentence or two, when it is a side detail. Or rewrite the passage so that it no longer needs it.
4. When you send the reader to a unit for a fact, open that unit and find the sentence that states the fact. Link the
   section's `id` (for example `distance.html#three-d`). If the unit does not state the fact, state it on your page.
   Review found pages that linked a unit for a fact that the unit never stated.
5. List only what the text needs. Each unneeded prerequisite asks the reader to read one more unit.

## Write each claim with its conditions

A claim that drops a condition was the second most common substantive finding.

- Treat every sentence as a claim to test, including the idea paragraph, the headings and the manifest's `summary`.
  A reader who skims sees only the headings and the summary, so each must be true on its own. Review found summaries
  that overstated their own page.
- Look for words that claim everything: "any", "every", "always", "never", "the same", "only", "the main". Test each
  one on edge cases: a negative number, zero, a tie, the other axis, the other order, a quantity that changes with
  time. For example, layer normalization undoes a common offset exactly. It undoes a common scale only when the
  scale is positive, and then only nearly: the small ε added to the variance matters when the values lie close
  together.
- Check each "Check yourself" answer the same way. A zero gradient marks a low point, but also a flat stretch, a
  peak or a saddle point. An answer that listed only the first two was incomplete.
- When a sentence is false without its condition, write the condition into the sentence.
- When the page leaves out a detail on purpose, name it in a `<div class="callout warn">` box. Give the box a title
  that says what kind of detail it is, name the detail, and say where it matters. The box on `distance.html`, "This is
  one kind of distance", is a good model. Every one of the 73 units has at least one such box.
- Write a condition in the same words every time it appears. One condition, "at the same time", was dropped from a
  claim that then spread to two pages and a video; see
  [error-patterns.md](error-patterns.md#one-dropped-condition-spread-to-two-pages-and-the-video).
- Units teach standard textbook material, and the textbook is the standard. A unit simplifies the presentation,
  never the truth.

## Check each fact against a source you opened

A fact from memory was the third most common substantive finding: a cost, a size, a name or a default that was wrong
or true only of another version.

- For each fact that the page does not derive, open a source and find the statement: a textbook, the library's
  documentation, or the paper. Prefer the primary source.
- When two versions of a method differ, say which one you mean. The Hungarian algorithm takes about n⁴ steps in its
  line-covering form, and about n³ in its faster form.
- Give a hardware figure with its model, and say that it is a rating. One unit writes: "An NVIDIA A100 GPU's memory
  is rated at 1,555 GB per second or more." Give a measured number with where it was measured.
- Check facts from other fields as carefully as the main topic. A segmentation unit said that cells have walls; the
  animal cells in its images have membranes.
- If you cannot find a source, cut the claim, or reduce it to what the page itself shows.

## Work one example with real numbers, and show every step

- Include at least one worked example (`<div class="example">`) with small, real numbers. Make each step one
  operation, so that a reader can redo it on paper.
- Make every step checkable from the page and its prerequisites. Do not assert the step that gives the answer:
  show it.
- Introduce a tool before an example uses it. An example that divided natural logarithms before the page defined
  them was fixed by using base 10, the calculator's log key.
- When the example compares two options, compute both. An example that judged a GPU "not worth it" for one step had
  to give the CPU's time for that step, not only the GPU's.
- Recompute every number yourself, and run any code that produced one.
- End with a similar problem for the reader ("Your turn"), with its answer in a `<details>` element.

## "Check yourself" asks for recall and for use

- Ask two to four questions that the page answers, each with its answer hidden in
  `<details><summary>Answer</summary>…</details>`. Answering from memory teaches more than rereading does.
- Mix the kinds: at least one that recalls the idea, and one that applies it to a new case.
- Give the reason in each answer, not only the result.
- Recompute each answer, and test it on edge cases as you would any claim.

## Notation and terms match the linked units

Notation drift drew 17 items. None was substantive, but each one costs a reader time. Before you write, open the
units you will link and the units likely to link yours, and use their conventions:

- Write vectors and matrices in bold: `<b>` in prose, `<span class="vec">` in a `.math` line. Write scalars and
  components in italic (`<var>`). The vectors, dot-product and linear-layer units do this, and the vectors unit
  defines a₁ as the first component of **a**.
- Write × for a product of numbers, or of a number and a vector. Keep · for the dot product of two vectors, as the
  dot-product and chain-rule units do. A few pages still write a number times a vector with ·; do not copy them.
- Use "length" only for a vector's magnitude. Say "entries" for how many numbers a vector holds.
- In a matrix product, the vector is a column, as `matrix-times-vector.html` says.
- Give each symbol one meaning across the linked units. The units use γ for a learned scale, so the Fourier-features
  unit writes its feature list as φ(x).
- Use one term for one thing on the page. Write "standard deviation" throughout, not "spread" in the code comments.
  Write "loss" for the number that training lowers, not "error" in one paragraph and "loss" in the next.
- Define each technical term with `<dfn>` the first time you use it, and do not reuse its word in another sense. One
  unit used "bridges" for ordinary edges in its idea paragraph, then defined a bridge as an edge whose cut splits a
  piece.

## Wording

Follow [plain-english.md](plain-english.md) in every sentence. These points came up most often on units:

- Write headings that state their point: "A KD-tree skips whole boxes of points", not "KD-trees".
- Check each quantifier for a second reading. "The point farthest from every point picked so far" can mean the largest
  total distance; the method takes the point whose nearest pick is farthest away.
- Keep counts and shares apart. Over 6000 rolls, each face's share comes close to one sixth, but its count can miss
  1000 by 30 or more.
- Avoid a word whose technical meaning differs from the one you intend: "spanned" suggests a linear span, and
  "column" means an array's axis 1 on the NumPy pages.
- Give each number its unit, and each table its column units.

## "Go further" describes what the reader will find there

The optional "Go further" part lists one to four of the best outside pages, videos or courses on the concept. Its
items drew 14 findings and notes, most of them claims about the linked page that were not quite true.

- Open each link and read the section you point to. Describe what that section shows, and name it by its heading
  and number as the page gives them.
- Link the section's anchor when the page has one. Run `scripts/check_links.py` to confirm the status and the
  anchor.
- Set the item's level badge by the resource's content. A video that works with second-order differential equations
  does not get the Starting badge.
- Warn when the resource uses another convention than your page. The transformer-block unit says that a linked
  tutorial puts the normalization after each step, the older order, while the unit puts it before.
- Make sure the description agrees with your page. One item described a "non-crossing flow" on a page that explains
  why paths can cross.
- Link only. Copy text, figures or code only when the resource's licence allows it, with credit.

## The page parts follow what helps self-taught readers

The unit layout applies findings from teaching research and from the best interactive explainers:

- **Answering from memory** (retrieval practice) beats rereading: Roediger and Karpicke (2006), and the review of
  Dunlosky et al. (2013). Hence "Check yourself", with answers hidden, and a request to predict before a widget moves.
- **Worked examples** help beginners, and the help fades as skill grows: Atkinson et al. (2000), Kalyuga et al.
  (2003). Hence one fully worked example, then a problem for the reader.
- **Guided discovery** works, and unguided discovery does not: Alfieri et al. (2011), Kirschner, Sweller and Clark
  (2006). So give each widget a goal or a question.
- **Animation helps a little, when the change itself is the lesson**: Höffler and Leutner (2007), Berney and
  Bétrancourt (2016). For interactivity, the survey behind these units found no meta-analysis that isolates it, so
  no learning gain from interactivity is established. Hence, as a design rule, a widget only where moving something
  teaches more than a still picture, with one or two controls.
- **Teach the key terms first, and put words beside the matching picture** (Mayer's multimedia principles). Hence
  prerequisites first, and each figure beside the sentence that uses it.

The explainers with the best evidence share six habits:

- one concrete example, carried through the page;
- an overview before the detail;
- a result within a second of the reader's action;
- one control per idea;
- colours and symbols that keep their meaning;
- steps in the order the data flows.

Most of them lack self-checks and prerequisite links, which units add.
