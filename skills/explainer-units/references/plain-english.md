These rules are copied word for word from Bill Katz's plain-English skill on 2026-11-03.
They are under the skills' licence, BSD-3-Clause (see [`LICENSE`](../../../LICENSE)).

# Plain English

Write so that the reader understands the text on the first read and can act on
it. Accuracy comes first: never trade a correct statement for a shorter one.

## 1. Start from the reader

- Decide who reads the text and what they must know, decide or do. Leave out
  what they don't need.
- Put the answer, decision or main point first. Give background after it, and
  only as much as the reader needs.
- Write headings that state the point of the section: "The cache cuts read time
  in half," not "Background."
- End with the next step, decision or question, if there is one.

## 2. Make each sentence clear on the first read

- Put one idea in each sentence. Keep instructions to 20 words or fewer and
  descriptions to 25 words or fewer.
- Use the active voice: "DSG checks the token," not "The token is checked."
  Use the passive only when the actor is unknown.
- Write each step as a command with one action, unless two actions happen at
  the same time. Put a condition before its action: "If DVID rejects the
  token, sign in again."
- Use familiar words. Keep a technical term when it is the precise one, and
  define it the first time you use it.
- Use one term for one thing. Do not switch to a synonym for variety. If a
  glossary exists, use its terms.
- Keep noun clusters to three words or fewer. Break longer ones with a
  preposition or a clause. For example, write "the token that DSG gives the
  viewer," not "DSG viewer token issuance flow." Write a longer official name
  in full the first time, then use a short form.
- Keep the small words: articles, "that," and pronouns that point clearly to
  one thing. Do not compress text into telegraph style.
- Keep the subject close to its verb, and put the action in the verb: "decide,"
  not "make a decision."
- State things in positive form when that is equally true. Write "keep the old
  token," not "do not discard the old token."

## 3. Give each paragraph one topic

- Give each paragraph one topic and at most six sentences. Start it with its
  point.
- In each sentence, put familiar information first and the new or important
  part last.
- Give parallel items the same grammatical form.
- Cut every word, sentence and paragraph that does no work. Say each thing once.
- Use a numbered list for steps and a bulleted list for three or more parallel
  items. Use a table for comparisons and prose for reasoning.

## 4. Habits to remove

People have flagged these patterns in Claude's output. Replace each one with the
literal statement, or cut it.

| Habit | Instead of | Write |
|---|---|---|
| Invented metaphor or coinage | "both surface in the first consumer" | "both appear in the first program that reads them" |
| Stock image | "this moves the needle on latency" | "this cuts latency from 80 ms to 20 ms" |
| Hype or corporate words | "robust", "seamless", "leverage", "key insight" | a specific claim, or nothing |
| Stacked hedges | "this may potentially suggest" | the claim once, with one qualifier if needed |
| Filler at the start or end | "Great question", "In summary", "Let me know if…" | nothing |
| Contrast formula | "It's not X, it's Y" | "It is Y." |
| Chained asides | long parentheses, dash asides, semicolon chains | separate sentences |
| Label fragments | "The fix: …" | a full sentence |
| Echo | restating the question or the last message | the answer |
| A menu instead of advice | five options when the reader asked for one | one recommendation and its reason |
| Emphasis everywhere | bold on many phrases, headings on a short answer | bold only on what the reader must not miss |

## 5. Keep these exact

Keep code, commands, file paths, identifiers, hostnames, ports, numbers and
units, error messages, quotations and names exactly as they are. Do not round or
paraphrase them. When a style rule and accuracy conflict, accuracy wins.

## 6. Make each slide and section state one point

- Give each slide or section a title that is a full sentence and states its
  point.
- Put one idea on a slide or in a section. Move detail to an appendix, speaker
  notes or a linked report.
- Use the same terms in diagrams, labels and text.
- Start a report with a summary of three to five sentences: the finding, the
  evidence, and what to do.
- Say what is live and what is only planned, and date each claim about the
  current state.

## 7. Check before you send

1. Does the first sentence give the answer or the point?
2. Does any sentence hold two ideas or more than 25 words? Split it.
3. Does any term have two meanings, or any thing two names? Fix it.
4. Is there a metaphor, coinage, hype word or filler phrase? Use the literal
   statement, or cut it.
5. Could a third of the words go without losing meaning? Cut them.
6. Are all code, paths, numbers and names exact?

## Restate an earlier answer in the reader's terms

When the reader asks for a plainer version of an earlier answer:

1. Start with one line on what you think they want to know.
2. Give only the context they need.
3. State the point in short sentences, in the reader's own terms.
4. End with the next step, decision or question.

Do not defend the old wording, and do not only shorten it.
