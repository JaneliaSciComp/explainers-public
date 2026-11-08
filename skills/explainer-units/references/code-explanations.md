# Pages that quote code

A unit never quotes a project's code. An explanation may: a page that shows how one code base works, or what is
wrong in it, and links to units for the general background. Claims about code are the hardest claims to get right,
because what code does depends on the commit, the inputs and the path it runs. This file holds the practices for
such a page.

## Keep each explanation where its code may be shown

- An explanation of public code may live in this repo. Register its sections under `explanations` in
  `units/units.json`, as `units/README.md` describes, and the units it uses will link back to it.
- An explanation of code that is not public lives in a private repo beside this one. It links to the units by
  relative paths, keeps its own `explanations.json`, and is never listed here. Run
  `python3 -I -B scripts/build_units.py --check-private <its folder>` to check its links against this manifest.
- Keep a project that is not public out of this repo: never name it, and never quote or describe its code, data,
  people or results, even without naming them.

## Assume Intermediate Python, and link the rest

An explanation of a code base is for readers who read its code. So it may assume Intermediate Python, as
`index.html#levels` on the front page defines that level. For anything beyond that, such as a NumPy or PyTorch feature,
link the unit or a good outside tutorial that teaches it, or explain it on the page.

Explain the code, and link a section of the front page, `index.html`, for anything about the site, such as what a unit
or a level is. Copy none of it into the page, because a copy goes out of date when the site changes.

## Pin every quote to a commit, and let a script check it

- Quote code at a fixed commit, never from a working tree. A working tree changes under you, and a reader must be
  able to find the same lines later.
- Mark each code block with its source and its first line number:

  ```html
  <p class="code-cap">parse.py, lines 40 to 52, at commit abc1234</p>
  <pre><code class="py" data-src="git:<repo>@abc1234:src/parse.py" data-start="40">…the lines, HTML-escaped…</code></pre>
  ```

  `data-src` takes one of three forms. `git:<repo>@<rev>:<path>` reads the file at that commit of the clone
  `<repo>`. `file:<path>@<sha256 prefix>` reads a file outside git, whose hash must start with the prefix. `none`
  marks a block that quotes no file, such as a command to run. `data-start` makes `unit.js` number the lines as the
  file does, so a reader can find each one.
- Run the checker on every page that quotes code:

  ```sh
  python3 -I -B scripts/check_code_blocks.py --repos <folder that holds the clones> <page>...
  ```

  It fails a block that differs from its source, and a block without `data-src`, so no quote goes unchecked by
  accident. Use `--root <folder>` when `file:` paths start somewhere other than the current folder. Exit status 1
  means at least one block failed.
- Name the commit in the text wherever a claim depends on it: "At commit `abc1234`, the parser …".
- Read the code only at that commit: `git -C <clone> show <rev>:<path>`, `git -C <clone> grep -n <pattern> <rev>`, or
  `git -C <clone> ls-tree -r --name-only <rev>`. Never check out, reset or stash a clone that someone else uses.

## Claim only what the code shows

- Sort each claim into one of two kinds, and say which kind it is. Some claims the code at a commit shows: what a
  function does with a given input. Others need evidence that the repository does not hold: which commit a running
  job used, what a saved file contains, whether a job failed, what reached a remote service. For the second kind,
  write that the repository cannot show it, and write the question that would settle it.
- Follow the whole path, not one line. A function that returns early instead of failing moves the failure to whoever
  uses its result. Check every step from the input to the output before you write "nothing fails".
- Read the code, not its comment. A handler often catches more cases than its comment names, and a comment can
  describe an older version of the code.
- Make absolute words literally true: "never", "every", "only", "nothing", "reads only". A Python command that imports
  modules can write bytecode caches unless you run it with `-B`. So write what a command does not change, rather than
  promising that it has no side effects.
- Do not take a finished run as proof of its side effect, such as an upload or a written file. Do not take a missing
  record as proof of failure: the run may still be going, or an earlier attempt may have written the same path.
- Check every part of a fix before you say that it is present. A search that finds the new line does not show that
  the function's signature and its callers changed too.
- When a later commit fixes the problem, say which code it reaches. A copy of the code that a long job took when it
  started keeps the old behaviour.
- Give each reproduction as a command that a reader can run, and say what it tests and what it does not.

## State each lesson as a rule with its evidence

If the page draws lessons, state each one as an imperative sentence that applies to other code too. Then give the
evidence on the page that supports it, and the commit that applies it, if one exists. A lesson without evidence on
the page is advice, and belongs elsewhere.

## Have an independent reviewer check the page before anything reaches the code's author

A wrong claim about someone's code costs them time, and it costs the page their trust. So a note to the code's
author waits until all three of these hold:

1. The person who will send it understands the issue completely, from a page that shows the relevant code.
2. The finding holds on the current code, not only on an older commit.
3. An independent reviewer has checked the page: another agent or a person who did not write it.

Give the reviewer the page and read-only access to the pinned code, not your conclusions, so that its review does
not start from yours. Ask it three questions. Does each claim hold at the cited commit? What can the repository not
show? Do the commands run as written? Then apply each correction, or answer it with a reason, and keep a record of
both.

An agent drafts the note, a pull-request body or a comment for the code's author. A person who owns the contact with
the author decides whether and when to send it.

## Checks for a page that quotes code

- `scripts/check_code_blocks.py`, as above.
- `python3 -I -B scripts/build_units.py --check-links <page>...` for the page's local links and anchors.
- `node scripts/render_check_units.mjs <out dir> --port <port> --dir <folder of the page>` for script errors and
  sideways scrolling.
- `python3 -I scripts/check_links.py <out.tsv> <page>...` for its external links.
