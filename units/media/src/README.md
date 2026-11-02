# Source for the flow-matching video

`flow_matching_scene.py` renders the video for the `flow-matching` concept unit. One render
produces three files in `media/`: the silent video, its WebVTT captions, and the narration
script with start times. All three come from one cue list in the scene, so they stay in sync.

| File in `media/` | What it is |
|---|---|
| `flow-matching.mp4` | H.264, 1280x720, 30 fps, silent, about 100 s |
| `flow-matching.vtt` | captions, one cue per spoken line |
| `flow-matching-narration.md` | the narration script, with start times and pronunciation notes |
| `flow-matching-poster.png` | a still from the generation part, used as the player's poster |

The video is honest about its math. The paths, the target velocity and the generation all use
the standard flow-matching formulas. The generation follows the exact best velocity field for
the scene's finite set of shape points; a trained network learns an approximation of that field.
The module docstring gives the formulas.

## Set up the environment

Keep the environment outside this repo, in a folder of your choice. Set `MANIM_ENV` to that
folder's absolute path; the commands below use it. The environment uses pixi and conda-forge's
`manim` package, which brings cairo, pango and ffmpeg. No LaTeX is needed: the scene uses only
`Text` and `MarkupText`.

1. Create `$MANIM_ENV/pixi.toml` with this content:

   ```toml
   [workspace]
   name = "explainers-manim"
   channels = ["conda-forge"]
   platforms = ["linux-64"]

   [dependencies]
   python = "3.12.*"
   manim = "*"
   numpy = "*"
   ffmpeg = "*"
   ```

2. Install it:

   ```bash
   cd "$MANIM_ENV" && pixi install
   ```

The first video was made with Manim Community 0.22.1, Python 3.12 and ffmpeg 9.0.2. The labels
use the font "DejaVu Sans". If that font is missing, Pango picks another one and the layout
shifts slightly.

## Render the video

Run these commands from the repo root. The render takes about 3 minutes on one core.

```bash
ENV=$MANIM_ENV/.pixi/envs/default/bin
MEDIA=units/media
OUT=$MANIM_ENV/out/hq

# 1. Render. This also writes flow-matching.vtt and flow-matching-narration.md into $MEDIA.
$ENV/python -B -W ignore -m manim render -r 1280,720 --fps 30 --media_dir $OUT/media \
  $MEDIA/src/flow_matching_scene.py FlowMatching

# 2. Copy the video into media/, with its index at the front so browsers start playing sooner.
$ENV/ffmpeg -y -i $OUT/media/videos/flow_matching_scene/720p30/FlowMatching.mp4 \
  -c copy -movflags +faststart $MEDIA/flow-matching.mp4

# 3. Take the poster frame from the generation part.
$ENV/ffmpeg -y -ss 69.08 -i $MEDIA/flow-matching.mp4 -frames:v 1 $MEDIA/flow-matching-poster.png
```

For a quick draft, replace `-r 1280,720 --fps 30` with `-ql` and set `FM_MEDIA_DIR` to a
scratch folder, so the draft captions do not overwrite the real ones:

```bash
FM_MEDIA_DIR=$MANIM_ENV/out/draft $ENV/python -B -W ignore -m manim render -ql \
  --media_dir $MANIM_ENV/out/draft/media $MEDIA/src/flow_matching_scene.py FlowMatching
```

To change a spoken line, edit its `self.say(caption, speech)` call in the scene and render
again. The first argument is the caption. The second, if given, is the text-to-speech form,
with symbols written out as words. Each cue gets enough time for its words at 2.75 words per
second (`WORDS_PER_SECOND`), plus a short pause (`CUE_PAD`).

## Add narration later

The script in `flow-matching-narration.md` is ready for ElevenLabs or any other
text-to-speech service. Record one clip per cue, so that each clip can start at its cue.

1. Generate one clip per line of the script's "Plain text" section, in order.
2. Save them in one folder as `cue-01.mp3`, `cue-02.mp3`, and so on. The scene expects
   exactly one clip per caption cue (18 now).
3. Render again with `FM_AUDIO_DIR` set to that folder. Each cue's slot then fits its real
   clip, so the animation, the captions and the script are re-timed to the audio:

   ```bash
   PATH=$ENV:$PATH FM_AUDIO_DIR=path/to/clips $ENV/python -B -W ignore -m manim render \
     -r 1280,720 --fps 30 --media_dir $OUT/media $MEDIA/src/flow_matching_scene.py FlowMatching
   ```

   Then repeat steps 2 and 3 of "Render the video". The poster time may need a small shift.

4. Mux the clips into the video. This places each clip at its cue's start time in
   `flow-matching.vtt` and writes `media/flow-matching-narrated.mp4`:

   ```bash
   PATH=$ENV:$PATH $ENV/python -B -I $MEDIA/src/flow_matching_scene.py path/to/clips
   ```

5. Check the result, then replace `flow-matching.mp4` with it. The page's `<video>` tag needs
   no change. With 128 kb/s AAC audio, the file stays near 6.5 MB, under the 8 MB limit.

Both steps were tested on 2026-11-01 with 18 generated test tones.

## Check the output

```bash
$ENV/ffprobe -v error -show_entries format=duration,size:stream=codec_name,width,height,r_frame_rate \
  -of compact $MEDIA/flow-matching.mp4
```

Expect `h264`, `1280` by `720`, `30/1`, a size under 8 MB, and a duration a little past the last
caption's end. Then open a few frames with `ffmpeg -ss <seconds> -i ... -frames:v 1 frame.png` and
look at them.
