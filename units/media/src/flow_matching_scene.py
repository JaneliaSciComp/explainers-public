"""Flow matching: turning noise into shapes.

A Manim Community Edition scene for the `flow-matching` concept unit. It renders a
silent animation and writes, next to the video in `media/`, the WebVTT captions and
the narration script with start times. Both come from the same cue list below, so
they stay in sync with the animation. See README.md in this folder for how to render.

The math is the standard flow-matching setup with straight (rectified) paths:
    x_t = (1 - t) x0 + t y,   x0 ~ N(0, I),   y drawn from the target point set,
    training target velocity = y - x0.
For a finite target set {y_j}, the best possible velocity field (the one that
minimizes the squared error) is known exactly:
    v(x, t) = (E[y | x_t = x] - x) / (1 - t),
    weight_j(x, t) proportional to exp(-|x - t y_j|^2 / (2 (1 - t)^2)).
The generation part follows this exact field with Euler steps. The last step starts
at t = 1 - 1/K < 1, so the division by (1 - t) is always safe.
"""

from __future__ import annotations

import os
import textwrap
from pathlib import Path

import numpy as np
from manim import (
    DOWN,
    LEFT,
    ORIGIN,
    RIGHT,
    UP,
    Arrow,
    Create,
    Dot,
    FadeIn,
    FadeOut,
    Line,
    MarkupText,
    RoundedRectangle,
    Scene,
    Text,
    Triangle,
    ValueTracker,
    VGroup,
    always_redraw,
    config,
    interpolate_color,
    linear,
    smooth,
    ManimColor,
)

# ---------------------------------------------------------------- look and feel
config.background_color = "#0E1116"
FONT = "DejaVu Sans"
BLUE = ManimColor("#58C4DD")  # noise
GOLD = ManimColor("#F4C542")  # shape / data
WHITE = ManimColor("#ECEFF4")
GREY = ManimColor("#8A93A3")
RED = ManimColor("#FC6255")
GREEN = ManimColor("#83C167")

CENTER = np.array([0.0, -0.15, 0.0])  # screen position of the data-space origin (moved in place)
SCALE = 0.95  # screen units per data unit
DOT_R = 0.032

# Words per second used to reserve time for each spoken cue. ElevenLabs voices
# speak at roughly 150 to 165 words per minute (2.5 to 2.75 words per second).
WORDS_PER_SECOND = 2.75
CUE_PAD = 0.35

MEDIA_DIR = Path(os.environ.get("FM_MEDIA_DIR", Path(__file__).resolve().parent.parent))
# Optional: a folder of recorded narration clips, one per cue, named cue-01.mp3,
# cue-02.mp3, ... When it is set, each cue's slot is sized to its clip instead of to
# the word-count estimate, so the captions are re-timed to the real audio.
AUDIO_DIR = os.environ.get("FM_AUDIO_DIR")


def clip_paths(audio_dir) -> list[Path]:
    return sorted(Path(audio_dir).glob("cue-[0-9][0-9].*"))


def clip_durations(audio_dir) -> list[float]:
    import subprocess

    out = []
    for p in clip_paths(audio_dir):
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
            capture_output=True, text=True, check=True,
        )
        out.append(float(r.stdout.strip()))
    return out


# ---------------------------------------------------------------- data
def _bezier(p0, p1, p2, n):
    s = np.linspace(0.0, 1.0, n)[:, None]
    return (1 - s) ** 2 * p0 + 2 * (1 - s) * s * p1 + s**2 * p2


def neuron_shape(rng: np.random.Generator, n_total: int = 280) -> np.ndarray:
    """A branching, neuron-like curve in 2D, as a point cloud (data units)."""
    P = np.array
    # Each branch is a quadratic Bezier curve: start, control, end.
    branches = [
        (P([-1.55, -0.55]), P([0.0, -0.45]), P([2.05, 0.55])),  # main trunk
        (P([-0.55, -0.42]), P([-0.65, 0.6]), P([-0.05, 1.55])),  # upper branch
        (P([-0.40, 0.55]), P([-1.1, 1.0]), P([-1.55, 1.35])),  # twig off upper branch
        (P([0.75, -0.08]), P([1.05, -0.7]), P([1.25, -1.55])),  # lower branch
        (P([2.05, 0.55]), P([2.2, 0.95]), P([2.45, 1.25])),  # end fork, up
        (P([2.05, 0.55]), P([2.35, 0.45]), P([2.55, 0.05])),  # end fork, down
        (P([-1.55, -0.55]), P([-2.0, -0.9]), P([-2.35, -1.55])),  # dendrite, down-left
        (P([-1.55, -0.55]), P([-2.2, -0.35]), P([-2.5, 0.25])),  # dendrite, left
    ]
    lengths = []
    for b in branches:
        pts = _bezier(*b, 50)
        lengths.append(np.linalg.norm(np.diff(pts, axis=0), axis=1).sum())
    lengths = np.array(lengths)
    n_soma = 30
    counts = np.maximum(6, np.round((n_total - n_soma) * lengths / lengths.sum())).astype(int)
    parts = [_bezier(*b, c) for b, c in zip(branches, counts)]
    # Soma: a small filled blob at the root of the trunk.
    ang = rng.uniform(0, 2 * np.pi, n_soma)
    rad = 0.24 * np.sqrt(rng.uniform(0, 1, n_soma))
    parts.append(np.c_[-1.55 + rad * np.cos(ang), -0.55 + rad * np.sin(ang)])
    pts = np.concatenate(parts)
    pts = pts + rng.normal(0.0, 0.025, pts.shape)
    return pts


def neuron_shape_3d(rng: np.random.Generator, n_total: int = 320) -> np.ndarray:
    """The same kind of branching curve, bent into 3D."""
    p2 = neuron_shape(rng, n_total)
    x, y = p2[:, 0], p2[:, 1]
    z = 0.75 * np.sin(1.2 * x + 0.4) + 0.45 * y * np.cos(0.9 * x)
    return np.c_[x, y, z]


def exact_velocity(x: np.ndarray, t: float, targets: np.ndarray) -> np.ndarray:
    """Exact flow-matching velocity for a finite target set; x is (n, d), t < 1."""
    d2 = ((x[:, None, :] - t * targets[None, :, :]) ** 2).sum(-1)
    logits = -d2 / (2.0 * (1.0 - t) ** 2)
    logits -= logits.max(axis=1, keepdims=True)
    w = np.exp(logits)
    w /= w.sum(axis=1, keepdims=True)
    mean_y = w @ targets
    return (mean_y - x) / (1.0 - t)


def euler_path(x0: np.ndarray, targets: np.ndarray, steps: int) -> np.ndarray:
    """Euler steps from t = 0 to t = 1; returns positions after each step, (steps+1, n, d)."""
    h = 1.0 / steps
    out = [x0.copy()]
    x = x0.copy()
    for k in range(steps):
        x = x + h * exact_velocity(x, k * h, targets)
        out.append(x.copy())
    return np.stack(out)


# ---------------------------------------------------------------- helpers
def to_screen(p: np.ndarray, center=CENTER, scale=SCALE) -> np.ndarray:
    p = np.atleast_2d(p)
    out = np.zeros((p.shape[0], 3))
    out[:, :2] = p[:, :2] * scale
    return out + center


def dots(points_screen: np.ndarray, color, radius=DOT_R, opacity=1.0) -> VGroup:
    return VGroup(*[Dot(p, radius=radius, color=color, fill_opacity=opacity) for p in points_screen])


def set_positions(group: VGroup, points_screen: np.ndarray) -> None:
    for d, p in zip(group, points_screen):
        d.move_to(p)


def label(text: str, size: float = 26, color=WHITE, markup: bool = False):
    if markup:
        return MarkupText(text, font=FONT, font_size=size, color=color)
    return Text(text, font=FONT, font_size=size, color=color)


# ---------------------------------------------------------------- the scene
class FlowMatching(Scene):
    # ---- cue bookkeeping: each spoken line becomes a caption and a script line
    def setup(self):
        self.cues: list[dict] = []
        self._open = None
        self.clip_durs = clip_durations(AUDIO_DIR) if AUDIO_DIR else None

    def say(self, caption: str, speech: str | None = None):
        """Start a narration cue now. The previous cue is padded so it can finish."""
        self._close_cue()
        speech = speech or caption
        need = len(speech.split()) / WORDS_PER_SECOND + CUE_PAD
        if self.clip_durs is not None:
            need = self.clip_durs[len(self.cues)] + CUE_PAD
        self._open = {"start": self.renderer.time, "caption": caption, "speech": speech, "need": need}

    def _close_cue(self):
        if self._open is None:
            return
        elapsed = self.renderer.time - self._open["start"]
        if elapsed < self._open["need"]:
            self.wait(self._open["need"] - elapsed)
        self._open["end"] = self.renderer.time
        self.cues.append(self._open)
        self._open = None

    def finish(self, tail: float = 1.0):
        self._close_cue()
        self.wait(tail)
        if not config.dry_run and not config.save_last_frame:
            write_captions(self.cues, self.renderer.time)

    # ---- title in the top-left corner
    def set_title(self, text: str, *extra, run_time: float = 0.6):
        new = label(text, size=28, color=WHITE).to_corner(UP + LEFT, buff=0.45)
        if getattr(self, "title", None) is None:
            self.play(FadeIn(new, shift=0.2 * DOWN), *extra, run_time=run_time)
        else:
            self.play(FadeOut(self.title, shift=0.2 * UP), FadeIn(new, shift=0.2 * UP), *extra, run_time=run_time)
        self.title = new

    # ---- the time indicator in the top-right corner
    def make_clock(self, tracker: ValueTracker) -> VGroup:
        x_a, x_b, y = 4.3, 6.5, 3.35
        bar = Line([x_a, y, 0], [x_b, y, 0], color=GREY, stroke_width=3)
        ticks = VGroup(
            Line([x_a, y - 0.09, 0], [x_a, y + 0.09, 0], color=GREY, stroke_width=3),
            Line([x_b, y - 0.09, 0], [x_b, y + 0.09, 0], color=GREY, stroke_width=3),
        )
        nums = VGroup(
            label("0", 20, GREY).next_to([x_a, y, 0], DOWN, buff=0.16),
            label("1", 20, GREY).next_to([x_b, y, 0], DOWN, buff=0.16),
        )

        def marker():
            t = tracker.get_value()
            x = x_a + (x_b - x_a) * t
            tri = Triangle(color=WHITE, fill_opacity=1, stroke_width=0).scale(0.07).rotate(np.pi)
            tri.move_to([x, y + 0.13, 0])
            return tri

        def readout():
            t = tracker.get_value()
            return label(f"t = {t:.2f}", 24, WHITE).next_to([x_a, y, 0], LEFT, buff=0.3)

        return VGroup(bar, ticks, nums, always_redraw(marker), always_redraw(readout))

    # ------------------------------------------------------------ construct
    def construct(self):
        rng = np.random.default_rng(7)
        Y = neuron_shape(rng)  # target points, data units
        n = len(Y)
        X0 = rng.normal(size=(n, 2))  # training noise
        perm = rng.permutation(n)
        Yp = Y[perm]  # Yp[i] is the shape point paired with noise point X0[i]

        # ======================================================= 1. noise and shape
        title = label("Flow matching", 64, WHITE)
        sub = label("turning noise into shapes", 34, GREY).next_to(title, DOWN, buff=0.3)
        self.say("Flow matching turns random noise into shapes.")
        self.play(FadeIn(title, shift=0.3 * UP), run_time=1.0)
        self.play(FadeIn(sub), run_time=0.8)
        self.wait(0.6)
        self.play(FadeOut(title), FadeOut(sub), run_time=0.7)

        left_c = np.array([-3.6, -0.3, 0.0])
        right_c = np.array([3.6, -0.3, 0.0])
        s_small = 0.62
        noise_dots = dots(to_screen(X0, left_c, s_small), BLUE, radius=0.028)
        shape_dots = dots(to_screen(Y, right_c, s_small), GOLD, radius=0.028)
        noise_lab = label("noise", 30, BLUE).move_to(left_c + np.array([0, 2.75, 0]))
        shape_lab = label("shape", 30, GOLD).move_to(right_c + np.array([0, 2.75, 0]))

        self.say("On the left is noise: random points from a bell-shaped distribution.")
        self.play(FadeIn(noise_lab), Create(noise_dots, lag_ratio=0.01), run_time=2.0)
        self.say("On the right is a branching, neuron-like shape, made of points.")
        self.play(FadeIn(shape_lab), Create(shape_dots, lag_ratio=0.01), run_time=2.0)

        self.say("Both live in the same plane, so we overlay them.")
        axes = VGroup(
            Line(to_screen(np.array([-3.3, 0]))[0], to_screen(np.array([3.3, 0]))[0], color=GREY, stroke_width=1.5, stroke_opacity=0.35),
            Line(to_screen(np.array([0, -3.0]))[0], to_screen(np.array([0, 3.1]))[0], color=GREY, stroke_width=1.5, stroke_opacity=0.35),
        )
        noise_target = to_screen(X0)
        shape_target = to_screen(Y)
        self.play(
            FadeOut(noise_lab),
            FadeOut(shape_lab),
            FadeIn(axes),
            *[d.animate.move_to(p).scale(DOT_R / 0.028) for d, p in zip(noise_dots, noise_target)],
            *[d.animate.move_to(p).scale(DOT_R / 0.028).set_opacity(0.28) for d, p in zip(shape_dots, shape_target)],
            run_time=2.2,
        )

        # ======================================================= 2. pair and move
        lines_idx = rng.choice(n, 70, replace=False)
        path_lines = VGroup(
            *[
                Line(to_screen(X0[i])[0], to_screen(Yp[i])[0], color=WHITE, stroke_width=1.3, stroke_opacity=0.35)
                for i in lines_idx
            ]
        )
        # Each section title changes at the start of the cue that introduces it, after say(),
        # so it never appears under the previous cue's caption.
        self.say("Join each noise point to a random shape point with a straight line.")
        self.set_title("Training: straight paths")
        self.play(Create(path_lines, lag_ratio=0.03), run_time=2.6)

        t_tr = ValueTracker(0.0)
        clock = self.make_clock(t_tr)
        movers = noise_dots  # the noise dots become the moving points

        def update_movers(group):
            t = t_tr.get_value()
            set_positions(group, to_screen((1 - t) * X0 + t * Yp))
            col = interpolate_color(BLUE, GOLD, t)
            for d in group:
                d.set_fill(col, opacity=1.0)

        self.say(
            "As time t runs from 0 to 1, each point slides from noise to the shape.",
            "As time t runs from zero to one, each point slides from noise to the shape.",
        )
        self.play(FadeIn(clock), run_time=0.5)
        movers.add_updater(update_movers)
        self.play(t_tr.animate.set_value(1.0), run_time=3.4, rate_func=smooth)
        self.wait(0.4)

        # ======================================================= 3. freeze at t = 0.5
        self.say(
            "Freeze at t = 0.5. Each point moves at a steady velocity.",
            "Freeze at t equals one half. Each point moves at a steady velocity.",
        )
        self.set_title("The velocity of one pair")
        self.play(t_tr.animate.set_value(0.5), run_time=1.8, rate_func=smooth)
        movers.remove_updater(update_movers)
        xt = 0.5 * X0 + 0.5 * Yp
        vel = Yp - X0
        arrows = VGroup(
            *[
                Arrow(
                    to_screen(xt[i])[0],
                    to_screen(xt[i] + 0.28 * vel[i])[0],
                    buff=0,
                    color=WHITE,
                    stroke_width=2.2,
                    max_tip_length_to_length_ratio=0.3,
                    tip_length=0.1,
                )
                for i in lines_idx
            ]
        )
        self.play(FadeIn(arrows, lag_ratio=0.02), run_time=1.6)

        # choose a long, clear pair: noise on the left-bottom, shape point on the right
        cand = [i for i in range(n) if X0[i, 0] < -1.0 and X0[i, 1] < -0.6 and Yp[i, 0] > 1.4 and Yp[i, 1] > 0.6]
        k = cand[0] if cand else int(np.argmax(np.linalg.norm(vel, axis=1)))

        # Slide the plot left to make room for the formula panel.
        shift = np.array([-2.5, 0.0, 0.0])
        plot = VGroup(axes, path_lines, arrows, movers, shape_dots)
        self.say("Take one pair: noise point x₀ and shape point y.", "Take one pair: noise point x zero, and shape point y.")
        self.play(plot.animate.shift(shift), run_time=1.0)
        CENTER[:] = CENTER + shift
        p0, py, pt = to_screen(X0[k])[0], to_screen(Yp[k])[0], to_screen(xt[k])[0]
        dim = [m.animate.set_opacity(0.12) for m in (path_lines, arrows)]
        self.play(*dim, *[d.animate.set_opacity(0.18) for d in movers], *[d.animate.set_opacity(0.12) for d in shape_dots], run_time=0.8)
        seg = Line(p0, py, color=WHITE, stroke_width=2.5, stroke_opacity=0.8)
        d0 = Dot(p0, radius=0.07, color=BLUE)
        dy = Dot(py, radius=0.07, color=GOLD)
        dt = Dot(pt, radius=0.07, color=interpolate_color(BLUE, GOLD, 0.5))
        along = (py - p0) / np.linalg.norm(py - p0)
        normal = np.array([-along[1], along[0], 0.0])
        if normal[1] < 0:
            normal = -normal
        l0 = label("x<sub>0</sub>", 32, BLUE, markup=True).move_to(p0 - 0.38 * along)
        ly = label("y", 32, GOLD).move_to(py + 0.34 * along)
        lt = label("x<sub>t</sub>", 32, WHITE, markup=True).move_to(pt + 0.38 * normal)
        self.play(Create(seg), FadeIn(d0), FadeIn(dy), FadeIn(l0), FadeIn(ly), run_time=1.0)
        self.play(FadeIn(dt), FadeIn(lt), run_time=0.6)

        panel_x = 3.9
        f1 = label("x<sub>t</sub> = (1 − t) x<sub>0</sub> + t y", 26, WHITE, markup=True)
        f2 = label("velocity = y − x<sub>0</sub>", 26, WHITE, markup=True)
        f3 = label("loss = | net(x<sub>t</sub>, t) − (y − x<sub>0</sub>) |<sup>2</sup>", 22, WHITE, markup=True)
        formulas = VGroup(f1, f2, f3).arrange(DOWN, aligned_edge=LEFT, buff=0.35)
        formulas.move_to([panel_x, 0.9, 0])
        box = RoundedRectangle(
            corner_radius=0.15,
            width=formulas.width + 0.5,
            height=formulas.height + 0.5,
            stroke_color=GREY,
            stroke_width=1.5,
            fill_color="#161B22",
            fill_opacity=0.92,
        ).move_to(formulas)
        f2.set_color(GOLD)

        self.say(
            "It travels from x₀ to y in one unit of time, so its velocity is y − x₀.",
            "It travels from x zero to y in one unit of time, so its velocity is y minus x zero.",
        )
        vec = Arrow(p0, py, buff=0.08, color=GOLD, stroke_width=5, max_tip_length_to_length_ratio=0.08)
        self.play(FadeIn(box), FadeIn(f1), run_time=0.8)
        self.play(Create(vec), FadeIn(f2), run_time=1.4)

        self.say("Training teaches a neural network to predict this velocity from the position and the time.")
        self.play(FadeIn(f3), run_time=1.0)

        self.say(
            "Many paths pass each spot at the same time, so it can only learn their average velocity.",
        )
        self.play(
            FadeOut(vec),
            FadeOut(seg),
            FadeOut(d0),
            FadeOut(dy),
            FadeOut(dt),
            FadeOut(l0),
            FadeOut(ly),
            FadeOut(lt),
            path_lines.animate.set_opacity(0.4),
            arrows.animate.set_opacity(0.8),
            *[d.animate.set_opacity(1.0) for d in movers],
            *[d.animate.set_opacity(0.28) for d in shape_dots],
            run_time=1.2,
        )
        self.wait(0.5)

        # ======================================================= 4. generation
        self.say(
            "Here we can compute that average velocity exactly, at every spot. A real model trains a network to approximate it."
        )
        self.set_title("Generation: follow the velocity field")
        self.play(
            FadeOut(path_lines),
            FadeOut(arrows),
            FadeOut(movers),
            FadeOut(box),
            FadeOut(formulas),
            run_time=1.0,
        )
        self.play(axes.animate.shift(-shift), shape_dots.animate.shift(-shift), t_tr.animate.set_value(0.0), run_time=0.9)
        CENTER[:] = CENTER - shift

        gx = np.arange(-3.4, 3.41, 0.4)
        gy = np.arange(-2.8, 2.81, 0.4)
        grid = np.array([[a, b] for a in gx for b in gy])  # data units
        T_MAX_FIELD = 0.97

        def field():
            t = min(t_tr.get_value(), T_MAX_FIELD)
            v = exact_velocity(grid, t, Y)
            mag = np.linalg.norm(v, axis=1)
            unit = v / np.maximum(mag[:, None], 1e-9)
            length = 0.32 * np.tanh(mag / 2.0) + 0.06
            g = VGroup()
            for p, u, L, m in zip(grid, unit, length, mag):
                a = to_screen(p)[0]
                b = to_screen(p + u * L / SCALE)[0]
                c = interpolate_color(ManimColor("#2E5C8A"), GOLD, float(np.tanh(m / 4.0)))
                g.add(
                    Arrow(a, b, buff=0, color=c, stroke_width=2.0, stroke_opacity=0.55,
                          max_tip_length_to_length_ratio=0.35, tip_length=0.07)
                )
            return g

        field_mob = always_redraw(field)
        self.play(FadeIn(field_mob), run_time=1.2)
        self.play(t_tr.animate.set_value(0.5), run_time=2.0, rate_func=smooth)
        self.play(t_tr.animate.set_value(0.0), run_time=1.5, rate_func=smooth)

        K = 40
        Xg0 = np.random.default_rng(11).normal(size=(300, 2))
        traj = euler_path(Xg0, Y, K)
        gen = dots(to_screen(Xg0), BLUE)
        self.say("To generate, start from fresh noise and take small steps along the field.")
        self.play(FadeIn(gen, lag_ratio=0.005), shape_dots.animate.set_opacity(0.0), run_time=1.0)

        def update_gen(group):
            s = t_tr.get_value() * K
            k0 = min(int(np.floor(s)), K - 1)
            f = s - k0
            pos = (1 - f) * traj[k0] + f * traj[k0 + 1]
            set_positions(group, to_screen(pos))
            col = interpolate_color(BLUE, GOLD, t_tr.get_value())
            for d in group:
                d.set_fill(col, opacity=1.0)

        gen.add_updater(update_gen)
        self.play(t_tr.animate.set_value(1.0), run_time=4.6, rate_func=linear)
        gen.remove_updater(update_gen)
        self.say("After 40 steps, the noise has become the shape.", "After forty steps, the noise has become the shape.")
        self.play(FadeOut(field_mob), run_time=1.0)
        self.wait(0.5)

        self.say(
            "This exact field only rebuilds these points. A trained network's smoother field can make new shapes.",
        )
        self.play(shape_dots.animate.set_opacity(0.5), run_time=1.0)
        self.play(shape_dots.animate.set_opacity(0.0), run_time=1.0)

        # ======================================================= 5. how many steps
        panels = []
        centers = [np.array([-4.4, -0.4, 0]), np.array([0.0, -0.4, 0]), np.array([4.4, -0.4, 0])]
        s_panel = 0.62
        Xc = np.random.default_rng(23).normal(size=(300, 2))
        step_counts = [1, 3, 40]
        names = ["1 step", "3 steps", "40 steps"]
        for c, kk, nm in zip(centers, step_counts, names):
            res = euler_path(Xc, Y, kk)[-1]
            start = dots(to_screen(Xc, c, s_panel), BLUE, radius=0.026)
            end_pos = to_screen(res, c, s_panel)
            cap = VGroup(
                label(nm, 28, WHITE).move_to(c + np.array([0, 2.35, 0])),
                dots(to_screen(Y, c, s_panel), GREY, radius=0.02, opacity=0.3),  # faint target, for reference
            )
            panels.append((start, end_pos, cap))
        self.say(
            "One step lands every point on the average. Three steps blur the shape. Forty make it sharp.",
        )
        self.set_title("More steps, sharper shapes", FadeOut(gen), FadeOut(axes), FadeOut(clock), run_time=0.8)
        self.play(*[FadeIn(st) for st, _, _ in panels], *[FadeIn(cp) for _, _, cp in panels], run_time=1.0)
        for st, end_pos, _ in panels:
            self.play(
                *[d.animate.move_to(p).set_fill(GOLD) for d, p in zip(st, end_pos)],
                run_time=1.3,
            )
        self.wait(0.3)

        # ======================================================= 6. 3D
        rng3 = np.random.default_rng(5)
        Y3 = neuron_shape_3d(rng3, 320)
        X3 = rng3.normal(size=(320, 3))
        traj3 = euler_path(X3, Y3, 40)
        tt = ValueTracker(0.0)
        ang = ValueTracker(-1.0)
        c3 = np.array([0.0, -0.3, 0.0])
        s3 = 1.1

        def cloud3d():
            t = tt.get_value()
            s = t * 40
            k0 = min(int(np.floor(s)), 39)
            f = s - k0
            pos = (1 - f) * traj3[k0] + f * traj3[k0 + 1]
            th = ang.get_value()
            xs = pos[:, 0] * np.cos(th) + pos[:, 2] * np.sin(th)
            depth = -pos[:, 0] * np.sin(th) + pos[:, 2] * np.cos(th)
            order = np.argsort(-depth)  # far points first
            col = interpolate_color(BLUE, GOLD, t)
            g = VGroup()
            for i in order:
                near = float(np.clip(0.5 - depth[i] / 6.0, 0.15, 1.0))
                g.add(
                    Dot(
                        c3 + np.array([xs[i] * s3, pos[i, 1] * s3, 0.0]),
                        radius=0.022 + 0.018 * near,
                        color=col,
                        fill_opacity=0.35 + 0.65 * near,
                    )
                )
            return g

        cloud = always_redraw(cloud3d)
        coords = label("each point: (x, y, z)", 26, GREY).move_to([4.6, 2.3, 0])
        self.say(
            "The same idea works for 3D point clouds, with three coordinates per point.",
            "The same idea works for three-D point clouds, with three coordinates per point.",
        )
        self.set_title("The same idea in 3D", *[FadeOut(VGroup(st, cp)) for st, _, cp in panels], run_time=0.8)
        self.play(FadeIn(cloud), FadeIn(coords), run_time=0.8)
        self.play(tt.animate.set_value(1.0), ang.animate.set_value(0.2), run_time=4.5, rate_func=smooth)
        self.play(ang.animate.set_value(0.8), run_time=1.2, rate_func=linear)

        # ======================================================= close
        self.say(
            "Learn the velocity that carries noise to data. Then follow it in small steps.",
        )
        self.play(FadeOut(cloud), FadeOut(coords), FadeOut(self.title), run_time=1.0)
        end1 = label("Learn the velocity that carries noise to data.", 34, WHITE)
        end2 = label("Then follow it in small steps.", 34, GOLD)
        VGroup(end1, end2).arrange(DOWN, buff=0.35).move_to(ORIGIN + 0.3 * UP)
        self.play(FadeIn(end1, shift=0.2 * UP), run_time=1.0)
        self.play(FadeIn(end2, shift=0.2 * UP), run_time=1.0)
        self.finish(tail=1.5)


# ---------------------------------------------------------------- outputs
def _ts(sec: float) -> str:
    ms = int(round(sec * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


PRONUNCIATION = """\
## Pronunciation notes

The script below is already written out in words for text-to-speech. The captions use
symbols. The table shows how to read each symbol:

| On screen | Say |
|---|---|
| `t` | "tee", the time, a number from 0 to 1 |
| `x₀` | "x zero", the noise point |
| `xₜ` | "x sub tee", the point at time t |
| `y` | "why", the shape point |
| `y − x₀` | "y minus x zero" |
| `t = 0.5` | "t equals one half" |
| the `loss` line | not spoken; it stays on screen only |
| `3D` | "three-D" |

Keep a short pause at each full stop. The cue start times below match the silent video.
If the spoken audio runs longer than a cue's slot, re-time the captions as described in
`src/README.md` rather than speeding up the voice.
"""


def write_captions(cues: list[dict], total: float) -> None:
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    vtt = ["WEBVTT", ""]
    for i, c in enumerate(cues, 1):
        text = textwrap.fill(c["caption"], width=56)  # at most two short lines on screen
        vtt += [str(i), f"{_ts(c['start'])} --> {_ts(c['end'])}", text, ""]
    (MEDIA_DIR / "flow-matching.vtt").write_text("\n".join(vtt), encoding="utf-8")

    words = sum(len(c["speech"].split()) for c in cues)
    md = [
        "# Narration script: Flow matching, turning noise into shapes",
        "",
        "This is the voice-over for `flow-matching.mp4`. It is generated by",
        "`src/flow_matching_scene.py` together with the captions, so the two always match.",
        f"The video lasts {total:.1f} s. The script has {len(cues)} lines and {words} words.",
        f"Each line's slot assumes about {WORDS_PER_SECOND} words per second.",
        "",
        PRONUNCIATION,
        "## Script",
        "",
        "| Start | End | Spoken text |",
        "|---|---|---|",
    ]
    for c in cues:
        md.append(f"| {_ts(c['start'])[3:]} | {_ts(c['end'])[3:]} | {c['speech']} |")
    md += [
        "",
        "## Plain text for text-to-speech",
        "",
        "Paste each paragraph as one clip, or the whole block as one clip and re-time the captions.",
        "",
    ]
    md += [c["speech"] + "\n" for c in cues]
    (MEDIA_DIR / "flow-matching-narration.md").write_text("\n".join(md), encoding="utf-8")


# ---------------------------------------------------------------- adding narration later
def mux(audio_dir: str, out: str | None = None) -> None:
    """Place each narration clip at its cue's start time and mux it into the video."""
    import re
    import subprocess

    clips = clip_paths(audio_dir)
    vtt = (MEDIA_DIR / "flow-matching.vtt").read_text(encoding="utf-8")
    starts = [m.group(1) for m in re.finditer(r"^(\d\d:\d\d:\d\d\.\d{3}) -->", vtt, re.M)]
    if len(clips) != len(starts):
        raise SystemExit(f"{len(clips)} clips but {len(starts)} caption cues; they must match one to one")

    def ms(ts: str) -> int:
        h, m, s = ts.split(":")
        return int(round((int(h) * 3600 + int(m) * 60 + float(s)) * 1000))

    cmd = ["ffmpeg", "-y", "-i", str(MEDIA_DIR / "flow-matching.mp4")]
    for c in clips:
        cmd += ["-i", str(c)]
    parts = [f"[{i + 1}:a]adelay={ms(t)}:all=1[a{i}]" for i, t in enumerate(starts)]
    mix = "".join(f"[a{i}]" for i in range(len(clips)))
    parts.append(f"{mix}amix=inputs={len(clips)}:normalize=0[aout]")
    out = out or str(MEDIA_DIR / "flow-matching-narrated.mp4")
    cmd += [
        "-filter_complex", ";".join(parts),
        "-map", "0:v", "-map", "[aout]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart", out,
    ]
    subprocess.run(cmd, check=True)
    print("wrote", out)


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Add recorded narration to the rendered video.")
    ap.add_argument("audio_dir", help="folder with cue-01.mp3, cue-02.mp3, ... (one clip per caption cue)")
    ap.add_argument("--out", help="output file (default: media/flow-matching-narrated.mp4)")
    a = ap.parse_args()
    mux(a.audio_dir, a.out)
