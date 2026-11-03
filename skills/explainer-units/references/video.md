# Videos for a unit

Most units need no video. Add one only when motion teaches what a figure or a widget cannot: a change over time, such
as points that move along a field. The evidence for animation is modest, and it is strongest when the change itself
is the lesson. The only video so far is the flow-matching one; `units/media/src/README.md` gives its exact commands.

## One cue list drives the render, the captions and the narration

Write the scene so that one list of cues produces three files in one render: the silent video, its WebVTT captions,
and the narration script with start times. In the flow-matching scene, each cue is one `self.say(caption, speech)`
call. The first argument is the caption; the second, if given, is the text-to-speech form, with symbols written out
as words. Each cue gets enough time for its words at 2.75 words per second, plus a short pause.

So never edit the `.vtt` file or the narration script by hand. Edit the cue in the scene, and render again. Files
edited by hand drift apart, and then the words run ahead of the picture or behind it.

## Keep each video to one idea, and to 2 minutes or less

- Make each video up to 2 minutes long. Shorter videos hold attention better, and a unit is read in 5 to 10 minutes.
  The flow-matching video runs about 100 seconds.
- Show one idea, not the whole method.
- Keep the file under 8 MB. The repo stores videos with Git LFS.
- Ship it silent first, with captions and a narration script. Narration can come later from the script, through any
  text-to-speech service. Send the service only text that is already public.

## Re-render all three files together, then copy the captions into the page

A page opened from disk cannot load a separate caption file: Chrome refuses `<track src="…">` over `file://`. So the
page holds the WebVTT text inline, in `<script type="text/vtt" id="…">`, and `unit.js` turns it into a caption track
for the `<video data-vtt="…">` that names it. That inline copy is the one that drifts.

After every render:

1. Render once. The render writes the video, the `.vtt` file and the narration script.
2. Copy the `.vtt` file into the page's inline `<script type="text/vtt">` block, exactly.
3. Rebuild the page's transcript from the same cues.
4. Confirm that the inline copy equals the file. For the flow-matching unit:

   ```sh
   python3 -I -c '
   import re, sys
   page, vtt, cap = sys.argv[1:4]
   m = re.search(r"<script type=\"text/vtt\" id=\"" + cap + r"\">\n?(.*?)</script>", open(page).read(), re.S)
   print("same" if m and m.group(1).strip() == open(vtt).read().strip() else "DIFFERENT")' \
     units/flow-matching.html units/media/flow-matching.vtt cap-flow-matching
   ```

5. Run the render check on the page. It reports a video or a caption track that fails to load.

Review once found inline captions from an older render. The ninth cue ended about 0.7 seconds early, later
cues also started early, and the drift reached about 1.7 seconds. Two cues had old wording.

## Change a section title when its cue starts

A title that the scene sets before the next cue's `say()` runs inside the previous cue. The screen then shows the
next section's title while the narration still explains the last one. Set each title right after the `say()` of the
cue that introduces it. Then extract a frame at each cue boundary and look at it:
`ffmpeg -ss <seconds> -i <video> -frames:v 1 frame.png`.

## The narration states the same conditions as the page

Narration is a claim like any sentence on the page, and it is harder to fix: a change needs a render. One condition,
"at the same time", was missing from a heading of the flow-matching page and from the narration alike. Before a
render, read each spoken line against the page, and use the page's exact phrase for each condition.

## Captions, transcript and layout

- Ship captions with every video. They help every viewer, not only those who cannot hear.
- Put a full transcript on the page.
- Do not repeat the narration word for word as text on the screen. Captions stay in their own track, which the viewer
  can turn off.
- Put the video in a `<figure>` with `<video controls>` and a `<figcaption>`, keep its files in `units/media/`, and
  list them in the unit's `media` entry in `units/units.json`.
