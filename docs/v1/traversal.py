#!/usr/bin/env python3
"""Draws the two GIFs in the v1 section of README.md: the order in which multiplyBlock visits one
4 x 4 tile, in v0 (loop order i-j-k) and in v1 (i-k-j).

    python3 docs/v1/traversal.py      # writes traversal_v0.gif and traversal_v1.gif next to this file

Each frame highlights the elements of A and B being read and the elements of C being written,
both in the 4 x 4 grids and in B's and C's row-major memory, where adjacent cells are adjacent
addresses. C's shading shows how many of its 4 multiply-adds each element has received.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import to_rgb  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402
from PIL import Image  # noqa: E402

N = 4
OUT = Path(__file__).resolve().parent
# The palette of bench/plot.py's dark charts.
COLORS = {
    "surface": "#1a1a19", "ink": "#ffffff", "ink2": "#c3c2b7", "muted": "#898781",
    "cell": "#252523", "edge": "#3a3a37", "read": "#3987e5", "trail": "#283c52", "write": "#d95926",
}
SUBSCRIPT = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")
WIDTH, HEIGHT, DPI = 8.0, 3.7, 100   # inches; the GIF is 800 x 370 pixels
CELL = 0.36                          # grid cell edge, inches
STRIP_CELL, STRIP_GAP = 0.1, 0.06    # memory strip cell width and gap between rows, inches


def blend(color, toward, t):
    a, b = np.array(to_rgb(color)), np.array(to_rgb(toward))
    return tuple(a + (b - a) * t)


def sub(*indices):
    return "".join(str(i) for i in indices).translate(SUBSCRIPT)


class Block:
    """One 4 x 4 block as a grid of labeled cells, and optionally its row-major memory strip."""

    def __init__(self, ax, name, x0, top, strip_y=None):
        self.cells = {}
        for r in range(N):
            for c in range(N):
                rect = Rectangle((x0 + c * CELL, top - (r + 1) * CELL), CELL, CELL, linewidth=1)
                ax.add_patch(rect)
                text = ax.text(x0 + (c + 0.5) * CELL, top - (r + 0.5) * CELL, name.lower() + sub(r, c),
                               ha="center", va="center", fontsize=8.5)
                self.cells[r, c] = [(rect, text)]
        ax.text(x0 + N * CELL / 2, top + 0.13, name, ha="center", va="bottom", fontsize=11,
                fontweight="bold", color=COLORS["ink"])
        if strip_y is not None:
            width = N * N * STRIP_CELL + (N - 1) * STRIP_GAP
            left = x0 + N * CELL / 2 - width / 2
            for r in range(N):
                for c in range(N):
                    x = left + (r * N + c) * STRIP_CELL + r * STRIP_GAP
                    rect = Rectangle((x, strip_y), STRIP_CELL, 0.2, linewidth=0.8)
                    ax.add_patch(rect)
                    self.cells[r, c].append((rect, None))
            ax.text(x0 + N * CELL / 2, strip_y + 0.27, f"{name} in memory, row by row", ha="center",
                    va="bottom", fontsize=7.5, color=COLORS["muted"])

    def paint(self, read=(), trail=(), filled=None, target=()):
        """read and trail are cells of A or B. filled maps cells of C to the fraction of their
        multiply-adds done; target cells get an outline."""
        for cell, parts in self.cells.items():
            if cell in read:
                face, ink = COLORS["read"], COLORS["ink"]
            elif cell in trail:
                face, ink = COLORS["trail"], COLORS["ink2"]
            elif filled and filled.get(cell, 0) > 0:
                done = filled[cell]
                face, ink = blend(COLORS["cell"], COLORS["write"], 0.15 + 0.7 * done), COLORS["ink"]
            else:
                face, ink = COLORS["cell"], COLORS["muted"]
            outline = cell in target
            for rect, text in parts:
                rect.set_facecolor(face)
                rect.set_edgecolor(COLORS["ink"] if outline else COLORS["edge"])
                rect.set_linewidth(2 if outline else 1)
                rect.set_zorder(3 if outline else 2)
                if text is not None:
                    text.set_color(ink)
                    text.set_zorder(4)


class Figure:
    def __init__(self, title, subtitle):
        self.fig = plt.figure(figsize=(WIDTH, HEIGHT), dpi=DPI)
        self.fig.patch.set_facecolor(COLORS["surface"])
        ax = self.fig.add_axes((0, 0, 1, 1))
        ax.set_xlim(0, WIDTH)
        ax.set_ylim(0, HEIGHT)
        ax.set_axis_off()
        ax.text(0.25, HEIGHT - 0.2, title, ha="left", va="top", fontsize=12, fontweight="bold", color=COLORS["ink"])
        ax.text(0.25, HEIGHT - 0.48, subtitle, ha="left", va="top", fontsize=9, color=COLORS["ink2"],
                linespacing=1.4)
        gap = 1.0
        left = (WIDTH - 3 * N * CELL - 2 * gap) / 2
        top = HEIGHT - 1.25
        xs = [left + i * (N * CELL + gap) for i in range(3)]
        self.A = Block(ax, "A", xs[0], top)
        self.B = Block(ax, "B", xs[1], top, strip_y=0.62)
        self.C = Block(ax, "C", xs[2], top, strip_y=0.62)
        mid = top - N * CELL / 2
        for x, symbol in ((xs[0] + N * CELL + gap / 2, "×"), (xs[1] + N * CELL + gap / 2, "→")):
            ax.text(x, mid, symbol, ha="center", va="center", fontsize=16, color=COLORS["muted"])
        self.caption = ax.text(0.25, 0.25, "", ha="left", va="center", fontsize=10, family="monospace",
                               color=COLORS["ink"])
        self.counter = ax.text(WIDTH - 0.25, 0.25, "", ha="right", va="center", fontsize=8.5,
                               color=COLORS["muted"])
        self.frames = []

    def snap(self, caption, counter):
        self.caption.set_text(caption)
        self.counter.set_text(counter)
        self.fig.canvas.draw()
        self.frames.append(Image.fromarray(np.asarray(self.fig.canvas.buffer_rgba())[..., :3].copy()))

    def save(self, path, step_ms, hold_ms=2000):
        # One palette for every frame, so colors cannot shift from frame to frame.
        picks = self.frames[:: max(1, len(self.frames) // 7)] + [self.frames[-1]]
        sheet = Image.new("RGB", (self.frames[0].width, self.frames[0].height * len(picks)))
        for i, frame in enumerate(picks):
            sheet.paste(frame, (0, i * frame.height))
        palette = sheet.quantize(colors=128, method=Image.Quantize.MEDIANCUT)
        frames = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in self.frames]
        durations = [step_ms] * (len(frames) - 1) + [hold_ms]
        frames[0].save(path, save_all=True, append_images=frames[1:], duration=durations, loop=0)
        plt.close(self.fig)
        print(f"wrote {path} ({len(frames)} frames, {path.stat().st_size // 1024} KiB)")


def v0():
    """i-j-k: each C element is a dot product, summed into one variable over k."""
    fig = Figure("v0: loop order i-j-k",
                 "Each step is one multiply-add into one running sum, so every add waits for the one before.\n"
                 "B is read down a column: consecutive elements are a whole row apart in memory.")
    done, step = {}, 0
    for i in range(N):
        for j in range(N):
            for k in range(N):
                step += 1
                done[i, j] = (k + 1) / N
                fig.A.paint(read={(i, k)}, trail={(i, c) for c in range(N)})
                fig.B.paint(read={(k, j)}, trail={(r, j) for r in range(N)})
                fig.C.paint(filled=done, target={(i, j)})
                then = f", then c{sub(i, j)} += sum" if k == N - 1 else ""
                fig.snap(f"i={i} j={j} k={k}   sum += a{sub(i, k)} × b{sub(k, j)}{then}",
                         f"multiply-add {step} of {N ** 3}")
    fig.save(OUT / "traversal_v0.gif", step_ms=250)


def v1():
    """i-k-j: each step adds a multiple of one row of B into one row of C."""
    fig = Figure("v1: loop order i-k-j",
                 "Each step updates a whole row of C: 4 independent multiply-adds on rows of B and C that are\n"
                 "adjacent in memory, so one vector instruction does all 4 (8 doubles per zmm register on this CPU).")
    done, step = {}, 0
    for i in range(N):
        for k in range(N):
            step += 1
            for j in range(N):
                done[i, j] = (k + 1) / N
            row = {(i, j) for j in range(N)}
            fig.A.paint(read={(i, k)}, trail={(i, c) for c in range(N)})
            fig.B.paint(read={(k, j) for j in range(N)})
            fig.C.paint(filled=done, target=row)
            fig.snap(f"i={i} k={k}   C row {i} += a{sub(i, k)} × B row {k}",
                     f"step {step} of {N ** 2}, 4 multiply-adds each")
    fig.save(OUT / "traversal_v1.gif", step_ms=650)


if __name__ == "__main__":
    v0()
    v1()
