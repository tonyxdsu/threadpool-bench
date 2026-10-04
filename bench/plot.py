#!/usr/bin/env python3
"""Charts and a summary from a results file written by `make bench-run`.

    python3 bench/plot.py bench/results/<label>.json [--out bench/plots] [--readme README.md]

Each chart is written as <name>.png on a dark background. summary.md shows every chart above
the numbers behind it, as Markdown tables. With --readme, the same summary also replaces
whatever is between the <!-- results:start --> and <!-- results:end --> lines of that README.
"""

import argparse
import json
import math
import os
import posixpath
import re
import statistics
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.ticker import FixedLocator, FuncFormatter, NullLocator  # noqa: E402

# Each implementation keeps its color in every chart. OpenBLAS is context, so it is gray.
THEME = {
    "surface": "#1a1a19", "ink": "#ffffff", "ink2": "#c3c2b7", "muted": "#898781",
    "grid": "#2c2c2a", "axis": "#383835",
    "naive": "#3987e5", "blocked": "#d95926", "openblas": "#898781",
}

TIME_UNITS = {"ns": 1e-9, "us": 1e-6, "ms": 1e-3, "s": 1.0}
COUNTERS = ("IPC", "GHz", "FLOP/cycle", "L1D_miss/FMA", "L2_miss/FMA", "L3_fill/FMA", "DRAM_fill/FMA")


class Results:
    """Median time and counters of every benchmark in a Google Benchmark JSON file."""

    def __init__(self, path):
        data = json.loads(Path(path).read_text())
        self.context = data["context"]
        self.failed = []
        repetitions, medians = {}, {}
        for run in data["benchmarks"]:
            key = self._key(run["run_name"])
            if run.get("error_occurred"):
                self.failed.append(f"{run['run_name']}: {run.get('error_message', '')}")
            elif run.get("run_type") == "aggregate":
                if run.get("aggregate_name") == "median":
                    medians[key] = run
            else:
                repetitions.setdefault(key, []).append(run)
        # Prefer the individual repetitions; fall back to Google Benchmark's own medians when the
        # file was written with --benchmark_report_aggregates_only.
        self.points = {key: self._summarize(repetitions.get(key) or [medians[key]])
                       for key in set(repetitions) | set(medians)}

        self.block_size = int(self.context.get("block_size", 0))
        parallel_ns = {dict(args)["n"] for family, args in self.points if family == "BM_BlockedParallel"}
        self.fixed_n = max(parallel_ns) if parallel_ns else None
        l1 = self.cache(1)
        self.threads_per_core = l1.get("num_sharing", 1) if l1 else 1
        self.cores = max(1, self.context.get("num_cpus", 1) // self.threads_per_core)

    @staticmethod
    def _key(run_name):
        family = run_name.split("/")[0]
        args = tuple(sorted((k, int(v)) for k, v in re.findall(r"(\w+):(\d+)", run_name)))
        return family, args

    @staticmethod
    def _summarize(runs):
        seconds = [run["real_time"] * TIME_UNITS[run["time_unit"]] for run in runs]
        point = {"seconds": statistics.median(seconds), "fastest": min(seconds), "slowest": max(seconds),
                 "reps": len(runs), "cv": None}
        if len(seconds) > 1:
            point["cv"] = statistics.stdev(seconds) / statistics.fmean(seconds)
        for counter in COUNTERS:
            values = [run[counter] for run in runs if counter in run]
            if values:
                point[counter] = statistics.median(values)
        return point

    def get(self, family, **args):
        return self.points.get((family, tuple(sorted(args.items()))))

    def series(self, family, vary, **fixed):
        """[(x, point)] for one family, varying one argument with all the others fixed."""
        out = []
        for (fam, args), point in self.points.items():
            args = dict(args)
            if fam == family and set(args) == set(fixed) | {vary} and all(args[k] == v for k, v in fixed.items()):
                out.append((args[vary], point))
        return sorted(out, key=lambda item: item[0])

    def cache(self, level):
        for cache in self.context.get("caches", []):
            if cache["level"] == level and cache["type"] in ("Data", "Unified"):
                return cache
        return None

    def tile_sweep_workers(self):
        """Worker count of the parallel tile sweep: the one measured at the most tile sizes."""
        counts = {}
        for family, args in self.points:
            args = dict(args)
            if family == "BM_BlockedParallel" and args["n"] == self.fixed_n:
                counts[args["workers"]] = counts.get(args["workers"], 0) + 1
        return max(counts, key=counts.get) if counts else None

    def repetitions(self):
        return max((p["reps"] for p in self.points.values()), default=0)


def gflops(n, point, time="seconds"):
    return 2.0 * n ** 3 / point[time] / 1e9


def gflops_range(n, point):
    """(lowest, highest) GFLOP/s over the repetitions."""
    return gflops(n, point, "slowest"), gflops(n, point, "fastest")


def fmt_bytes(size):
    for unit, scale in (("MiB", 1 << 20), ("KiB", 1 << 10)):
        if size >= scale:
            return f"{size / scale:g} {unit}"
    return f"{size} B"


def fmt_ms(seconds):
    ms = seconds * 1e3
    return f"{ms:.3g}" if ms < 100 else f"{ms:,.0f}"


def fmt_num(value, digits=3):
    return "-" if value is None else f"{value:.{digits}g}"


# ---------------------------------------------------------------------------------------------
# Chart scaffolding
# ---------------------------------------------------------------------------------------------

def new_figure(theme, title, subtitle, width=9.0, height=5.0, ncols=1, legend=True):
    fig, axes = plt.subplots(1, ncols, figsize=(width, height), dpi=200, squeeze=False)
    fig.patch.set_facecolor(theme["surface"])
    band = 1.2 if legend else 0.95   # inches above the plots for title, subtitle and legend
    fig.subplots_adjust(left=0.8 / width, right=1 - 0.35 / width, bottom=0.7 / height,
                        top=1 - band / height, wspace=0.3)
    fig.text(0.3 / width, 1 - 0.2 / height, title, fontsize=13, fontweight="bold",
             color=theme["ink"], ha="left", va="top")
    fig.text(0.3 / width, 1 - 0.5 / height, subtitle, fontsize=9.5, color=theme["ink2"],
             ha="left", va="top")
    for ax in axes[0]:
        style_axes(ax, theme)
    return fig, list(axes[0])


def style_axes(ax, theme):
    ax.set_facecolor(theme["surface"])
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(theme["axis"])
        ax.spines[side].set_linewidth(0.8)
    ax.grid(axis="y", which="major", color=theme["grid"], linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(which="both", colors=theme["axis"], labelcolor=theme["ink2"], labelsize=8.5,
                   length=3, width=0.8)
    ax.xaxis.label.set_color(theme["ink2"])
    ax.yaxis.label.set_color(theme["ink2"])
    ax.xaxis.label.set_size(9)
    ax.yaxis.label.set_size(9)


def add_legend(fig, theme, entries, height, lines=True):
    handles = [Line2D([0], [0], color=color, linewidth=2 if lines else 0, marker="o", markersize=6,
                      markerfacecolor=color, markeredgecolor=theme["surface"])
               for _, color in entries]
    fig.legend(handles, [name for name, _ in entries], loc="upper left",
               bbox_to_anchor=(0.25 / fig.get_figwidth(), 1 - 0.72 / height), ncol=len(entries),
               frameon=False, fontsize=9, labelcolor=theme["ink2"], handlelength=1.8,
               columnspacing=1.8, borderaxespad=0)


def plot_line(ax, theme, xs, ys, color, zorder=3):
    ax.plot(xs, ys, color=color, linewidth=2, solid_capstyle="round", solid_joinstyle="round",
            marker="o", markersize=6.5, markerfacecolor=color, markeredgecolor=theme["surface"],
            markeredgewidth=1.5, zorder=zorder)


def plot_ranges(ax, xs, lows, highs, color, horizontal=False):
    """Thin bars from the slowest to the fastest repetition, drawn under the markers."""
    draw = ax.hlines if horizontal else ax.vlines
    draw(xs, lows, highs, colors=color, linewidth=1.2, alpha=0.5, zorder=2)


def label_point(ax, theme, x, y, text, dx=7, dy=0, ha="left"):
    ax.annotate(text, (x, y), xytext=(dx, dy), textcoords="offset points", fontsize=8.5,
                color=theme["ink"], ha=ha, va="center", zorder=5)


def fixed_ticks(axis, values, fmt=lambda v: f"{v:,.0f}"):
    axis.set_major_locator(FixedLocator(values))
    axis.set_major_formatter(FuncFormatter(lambda v, _: fmt(v)))
    axis.set_minor_locator(NullLocator())


def mark_x(ax, theme, x, text, ha="left"):
    """A vertical reference line with a small label at the top of the plot."""
    ax.axvline(x, color=theme["axis"], linewidth=0.8, zorder=1)
    offset = 4 if ha == "left" else -4
    ax.annotate(text, (x, 1), xycoords=("data", "axes fraction"), xytext=(offset, -4),
                textcoords="offset points", fontsize=8, color=theme["muted"], ha=ha, va="top")


# ---------------------------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------------------------

def chart_throughput(results, theme):
    naive = results.series("BM_Naive", "n")
    blocked = results.series("BM_Blocked", "n", bs=results.block_size)
    if not naive or not blocked:
        return None
    height = 5.0
    fig, (ax,) = new_figure(
        theme, "Naive vs cache-blocked multiply, one thread",
        f"GFLOP/s for n x n doubles (tile {results.block_size}): median of {results.repetitions()} runs, "
        "bars span the slowest to fastest run",
        height=height)
    sizes = sorted({n for n, _ in naive} | {n for n, _ in blocked})
    peak = 0.0
    for points, color in ((naive, theme["naive"]), (blocked, theme["blocked"])):
        xs = [n for n, _ in points]
        ys = [gflops(n, p) for n, p in points]
        ranges = [gflops_range(n, p) for n, p in points]
        plot_ranges(ax, xs, [lo for lo, _ in ranges], [hi for _, hi in ranges], color)
        plot_line(ax, theme, xs, ys, color)
        label_point(ax, theme, xs[-1], ys[-1], f"{ys[-1]:.1f}")
        peak = max(peak, max(hi for _, hi in ranges))
    ax.set_xscale("log")
    fixed_ticks(ax.xaxis, sizes)
    ax.set_xlim(sizes[0] / 1.15, sizes[-1] * 1.25)
    ax.set_ylim(0, peak * 1.2)
    ax.set_xlabel("Matrix size n (log scale)")
    ax.set_ylabel("GFLOP/s")
    for level in (2, 3):
        cache = results.cache(level)
        if cache:
            n_fill = math.sqrt(cache["size"] / 24)   # three n x n matrices of 8-byte doubles
            if sizes[0] < n_fill < sizes[-1]:
                mark_x(ax, theme, n_fill, f"A, B, C outgrow L{level}\n({fmt_bytes(cache['size'])})")
    add_legend(fig, theme, [("multiplyNaive", theme["naive"]), ("multiplyBlocked", theme["blocked"])], height)
    return fig


def chart_cache(results, theme):
    naive = results.series("BM_Naive", "n")
    blocked = results.series("BM_Blocked", "n", bs=results.block_size)
    metrics = [(key, title) for key, title in (("L1D_miss/FMA", "Missed L1"), ("L2_miss/FMA", "Missed L2"),
                                              ("DRAM_fill/FMA", "Came from DRAM"))
               if any(key in p for _, p in naive + blocked)]
    if not naive or not blocked or not metrics:
        return None
    # Where the naive loop's working set outgrows each cache: one column of B is n cache lines,
    # all of B is 8n^2 bytes, and the three matrices are 24n^2 bytes.
    l1, l2, l3 = results.cache(1), results.cache(2), results.cache(3)
    markers = {
        "L1D_miss/FMA": (l1["size"] / 64, "a column of B\noutgrows L1") if l1 else None,
        "L2_miss/FMA": (math.sqrt(l2["size"] / 8), "B outgrows L2") if l2 else None,
        "DRAM_fill/FMA": (math.sqrt(l3["size"] / 24), "A, B, C\noutgrow L3") if l3 else None,
    }
    height = 4.4
    fig, axes = new_figure(
        theme, "Where each multiply-add's data came from",
        "Hardware-counter events per FMA, one thread, by matrix size n (log scales). "
        "Lines: where naive's working set outgrows a cache.",
        width=10.0, height=height, ncols=len(metrics))
    sizes = sorted({n for n, _ in naive})
    for ax, (key, title) in zip(axes, metrics):
        values = []
        for points, color in ((naive, theme["naive"]), (blocked, theme["blocked"])):
            pairs = [(n, p[key]) for n, p in points if p.get(key, 0) > 0]
            if pairs:
                plot_line(ax, theme, [n for n, _ in pairs], [v for _, v in pairs], color)
                values += [v for _, v in pairs]
        ax.set_xscale("log")
        ax.set_yscale("log")
        fixed_ticks(ax.xaxis, [s for s in sizes if s in (100, 300, 1000, 3000)] or sizes)
        # Start at a power of ten so even the smallest values have a labeled tick to read against.
        ax.set_ylim(10 ** math.floor(math.log10(min(values))), max(values) * 8)   # room for labels
        ax.yaxis.set_major_formatter(FuncFormatter(
            lambda v, _: f"{v:g}" if v >= 0.001 else f"$10^{{{round(math.log10(v))}}}$"))
        ax.yaxis.set_minor_locator(NullLocator())
        ax.set_title(title, loc="left", fontsize=10, color=theme["ink"], pad=8)
        ax.set_xlabel("n")
        marker = markers.get(key)
        if marker and sizes[0] < marker[0] < sizes[-1]:
            mark_x(ax, theme, marker[0], marker[1], ha="right" if marker[0] > sizes[-1] / 3 else "left")
    axes[0].set_ylabel("Events per FMA")
    add_legend(fig, theme, [("multiplyNaive", theme["naive"]), ("multiplyBlocked", theme["blocked"])], height)
    return fig


def chart_scaling(results, theme):
    n = results.fixed_n
    serial = results.get("BM_Blocked", n=n, bs=results.block_size)
    ours = results.series("BM_BlockedParallel", "workers", n=n, bs=results.block_size)
    if not serial or not ours:
        return None
    openblas = results.series("BM_OpenBLAS", "workers", n=n)
    openblas_1 = results.get("BM_OpenBLAS", n=n, workers=1)
    height = 5.0
    fig, (ax,) = new_figure(
        theme, "Speedup from more workers",
        f"n = {n}, against each implementation's own one-thread median; bars span the slowest to fastest run",
        height=height)
    max_workers = max(w for w, _ in ours)
    if max_workers > results.cores:
        ax.axvspan(results.cores, max_workers + 0.6, color=theme["grid"], alpha=0.4, linewidth=0, zorder=0)
        ax.annotate("SMT: two threads share a core", ((results.cores + max_workers) / 2, 1),
                    xycoords=("data", "axes fraction"), xytext=(0, -4), textcoords="offset points",
                    fontsize=8, color=theme["muted"], ha="center", va="top")
    ax.plot([1, results.cores], [1, results.cores], color=theme["muted"], linewidth=1, zorder=2)
    ax.annotate("linear", (results.cores, results.cores), xytext=(-4, 4), textcoords="offset points",
                fontsize=8, color=theme["muted"], ha="right", va="bottom")

    entries = [("multiplyBlockedParallel (your pool)", theme["blocked"])]
    lines = [(ours, serial, theme["blocked"])]
    if openblas and openblas_1:
        entries.append(("OpenBLAS", theme["openblas"]))
        lines.append((openblas, openblas_1, theme["openblas"]))
    top = 0.0
    for points, base, color in lines:
        xs = [w for w, _ in points]
        ys = [base["seconds"] / p["seconds"] for _, p in points]
        highs = [base["seconds"] / p["fastest"] for _, p in points]
        plot_ranges(ax, xs, [base["seconds"] / p["slowest"] for _, p in points], highs, color)
        plot_line(ax, theme, xs, ys, color, zorder=4 if color == theme["blocked"] else 3)
        label_point(ax, theme, xs[-1], ys[-1], f"{ys[-1]:.1f}x")
        top = max(top, max(highs))
    workers = sorted({w for w, _ in ours})
    fixed_ticks(ax.xaxis, workers)
    ax.set_xlim(0.4, max_workers + 0.6)
    ax.set_ylim(0, max(top, results.cores) * 1.12)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}x"))
    ax.set_xlabel("Workers (threads)")
    ax.set_ylabel("Speedup")
    add_legend(fig, theme, entries, height)
    return fig


def chart_tiles(results, theme):
    n = results.fixed_n
    workers = results.tile_sweep_workers()
    panels = [(results.series("BM_Blocked", "bs", n=n), "1 thread (multiplyBlocked)")]
    if workers:
        panels.append((results.series("BM_BlockedParallel", "bs", n=n, workers=workers),
                       f"{workers} workers (multiplyBlockedParallel)"))
    panels = [(points, title) for points, title in panels if len(points) > 1]
    if not panels:
        return None
    height = 4.4
    fig, axes = new_figure(
        theme, "Tile size sweep",
        f"GFLOP/s by tile edge at n = {n}, bars span the slowest to fastest run. "
        "Lines: where one tile of B (edge² x 8 bytes) fills L1 and L2.",
        width=10.0, height=height, ncols=len(panels), legend=False)
    for ax, (points, title) in zip(axes, panels):
        xs = [bs for bs, _ in points]
        ys = [gflops(n, p) for _, p in points]
        ranges = [gflops_range(n, p) for _, p in points]
        plot_ranges(ax, xs, [lo for lo, _ in ranges], [hi for _, hi in ranges], theme["blocked"])
        plot_line(ax, theme, xs, ys, theme["blocked"])
        best = max(range(len(xs)), key=lambda i: ys[i])
        label_point(ax, theme, xs[best], ranges[best][1], f"best: {xs[best]}", dy=10, dx=0, ha="center")
        ax.set_xscale("log", base=2)
        fixed_ticks(ax.xaxis, [x for x in xs if x & (x - 1) == 0])   # label the powers of two
        ax.set_xlim(xs[0] / 1.3, xs[-1] * 1.3)
        ax.set_ylim(0, max(hi for _, hi in ranges) * 1.25)
        ax.set_title(title, loc="left", fontsize=10, color=theme["ink"], pad=8)
        ax.set_xlabel("Tile edge (log scale)")
        ax.set_ylabel("GFLOP/s")
        for level in (1, 2):
            cache = results.cache(level)
            if cache:
                edge = math.sqrt(cache["size"] / 8)
                if xs[0] < edge < xs[-1]:
                    mark_x(ax, theme, edge, f"L{level}", ha="left")
    return fig


def headline_rows(results):
    """(label, color key, workers, point) for the implementations compared at the fixed size."""
    n, cores = results.fixed_n, results.cores
    max_workers = max((w for w, _ in results.series("BM_BlockedParallel", "workers", n=n, bs=results.block_size)),
                      default=None)
    candidates = [
        ("multiplyNaive", "naive", 1, results.get("BM_Naive", n=n)),
        ("multiplyBlocked", "blocked", 1, results.get("BM_Blocked", n=n, bs=results.block_size)),
    ]
    for workers in sorted({cores, max_workers} - {None}):
        candidates.append(("multiplyBlockedParallel", "blocked", workers,
                           results.get("BM_BlockedParallel", n=n, bs=results.block_size, workers=workers)))
    for workers in sorted({1, cores, max_workers} - {None}):
        candidates.append(("OpenBLAS dgemm", "openblas", workers, results.get("BM_OpenBLAS", n=n, workers=workers)))
    return [row for row in candidates if row[3] is not None]


def chart_headline(results, theme):
    rows = headline_rows(results)
    if len(rows) < 2:
        return None
    n = results.fixed_n
    height = 4.6
    fig, (ax,) = new_figure(
        theme, f"Matrix multiply throughput at n = {n}",
        f"GFLOP/s on a log scale: median of {results.repetitions()} runs, bars span the slowest to fastest run",
        height=height)
    fig.subplots_adjust(left=2.6 / fig.get_figwidth())
    labels = [f"{name}, {w} {'thread' if w == 1 else 'threads'}" for name, _, w, _ in rows]
    values = [gflops(n, point) for _, _, _, point in rows]
    ys = list(range(len(rows)))[::-1]
    ax.grid(axis="y", which="major", visible=False)
    ax.grid(axis="x", which="major", color=theme["grid"], linewidth=0.8)
    ranges = [gflops_range(n, point) for _, _, _, point in rows]
    for y, value, (low, high), (_, color_key, _, _) in zip(ys, values, ranges, rows):
        plot_ranges(ax, [y], [low], [high], theme[color_key], horizontal=True)
        ax.plot([value], [y], marker="o", markersize=8, color=theme[color_key],
                markeredgecolor=theme["surface"], markeredgewidth=1.5, zorder=3)
        label_point(ax, theme, high, y, f"{value:.3g}", dx=8)
    lowest, highest = min(low for low, _ in ranges), max(high for _, high in ranges)
    ax.set_xscale("log")
    ticks = [t for t in (1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000) if lowest / 2 <= t <= highest * 2]
    fixed_ticks(ax.xaxis, ticks, lambda v: f"{v:g}")
    ax.set_xlim(lowest / 1.6, highest * 2.2)
    ax.set_yticks(ys)
    ax.set_yticklabels(labels)
    ax.tick_params(axis="y", length=0, labelsize=9)
    ax.set_ylim(-0.7, len(rows) - 0.3)
    ax.spines["left"].set_visible(False)
    ax.set_xlabel("GFLOP/s (log scale)")
    entries = [("Naive", theme["naive"]), ("Blocked, yours", theme["blocked"])]
    if any(key == "openblas" for _, key, _, _ in rows):
        entries.append(("OpenBLAS reference", theme["openblas"]))
    add_legend(fig, theme, entries, height, lines=False)
    return fig


# ---------------------------------------------------------------------------------------------
# summary.md
# ---------------------------------------------------------------------------------------------

def table(header, rows):
    """A Markdown table, leaving out columns with no data in any row, such as the OpenBLAS
    columns of a run filtered to the blocked benchmarks."""
    keep = [i for i in range(len(header)) if any(str(row[i]) != "-" for row in rows)]
    lines = ["| " + " | ".join(header[i] for i in keep) + " |", "|" + "|".join("---:" if i else "---" for i in keep) + "|"]
    lines += ["| " + " | ".join(str(row[i]) for i in keep) + " |" for row in rows]
    return "\n".join(lines)


def images(charts, image_dir, *names_and_alts):
    """Markdown for the charts among (name, alt text) pairs that were written."""
    return [line for name, alt in names_and_alts if name in charts
            for line in (f"![{alt}]({posixpath.join(image_dir, name + '.png')})", "")]


def cache_summary(results):
    """The data caches with the scope of each size, e.g. "L1d 48 KiB and L2 1 MiB per core, L3
    96 MiB shared by all 8 cores". Google Benchmark lists one instance of each cache and how many
    hardware threads share it."""
    groups = {}
    for c in results.context.get("caches", []):
        if c["type"] not in ("Data", "Unified"):
            continue
        sharing = (c.get("num_sharing") or 0) // results.threads_per_core   # cores per instance
        scope = ("" if sharing < 1 else "per core" if sharing == 1
                 else f"shared by all {sharing} cores" if sharing >= results.cores else f"per {sharing} cores")
        name = f"L{c['level']}d" if c["type"] == "Data" else f"L{c['level']}"
        groups.setdefault(scope, []).append(f"{name} {fmt_bytes(c['size'])}")
    return ", ".join(f"{' and '.join(sizes)} {scope}".strip() for scope, sizes in groups.items())


def summary(results, label, charts, image_dir="", level=1):
    """The summary as Markdown. image_dir is the charts' folder relative to the file the summary
    goes in, and level is the heading level of its title."""
    ctx = results.context
    n, bs, cores = results.fixed_n, results.block_size, results.cores
    h1, h2 = "#" * level, "#" * (level + 1)
    machine = [ctx.get("cpu"), f"{cores} cores, {ctx.get('num_cpus')} hardware threads", cache_summary(results)]
    out = [f"{h1} Benchmark results: {label}", ""]
    out.append("- Machine: " + "; ".join(part for part in machine if part))
    out.append(f"- Build: {ctx.get('compiler', '?')}, `{ctx.get('cxxflags', '?')}`, git {ctx.get('git', '?')}")
    if "openblas" in ctx and any(family == "BM_OpenBLAS" for family, _ in results.points):
        out.append(f"- Reference: {ctx['openblas']}")
    out.append(f"- Run: {ctx.get('date', '')}, median of {results.repetitions()} repetitions, "
               f"wall-clock time, every result checked with Freivalds' algorithm")
    if results.failed:
        out += ["", "**Failed correctness check:**", ""] + [f"- {f}" for f in results.failed]

    naive = results.get("BM_Naive", n=n)
    rows = []
    for name, _, workers, point in headline_rows(results):
        same_openblas = results.get("BM_OpenBLAS", n=n, workers=workers)
        rows.append([
            name, workers, fmt_ms(point["seconds"]), f"{gflops(n, point):.3g}",
            f"{naive['seconds'] / point['seconds']:.3g}x" if naive else "-",
            f"{same_openblas['seconds'] / point['seconds']:.1%}" if same_openblas else "-",
            f"{point['cv']:.1%}" if point["cv"] is not None else "-",
        ])
    if rows:
        out += ["", f"{h2} Headline: n = {n}, tile {bs}", ""]
        out += images(charts, image_dir, ("headline", f"GFLOP/s of each implementation at n = {n}"))
        out.append(table(["Implementation", "Threads", "Time (ms)", "GFLOP/s", "vs naive",
                          "vs OpenBLAS, same threads", "CV"], rows))

    naive_s = dict(results.series("BM_Naive", "n"))
    blocked_s = dict(results.series("BM_Blocked", "n", bs=bs))
    openblas_s = dict(results.series("BM_OpenBLAS", "n", workers=1))
    rows = []
    for size in sorted(set(naive_s) | set(blocked_s)):
        a, b, o = naive_s.get(size), blocked_s.get(size), openblas_s.get(size)
        rows.append([
            size, fmt_num(gflops(size, a) if a else None), fmt_num(gflops(size, b) if b else None),
            f"{a['seconds'] / b['seconds']:.2f}x" if a and b else "-", fmt_num(gflops(size, o) if o else None),
            fmt_num(a and a.get("L1D_miss/FMA")), fmt_num(b and b.get("L1D_miss/FMA")),
            fmt_num(a and a.get("L2_miss/FMA")), fmt_num(b and b.get("L2_miss/FMA")),
            fmt_num(a and a.get("DRAM_fill/FMA")), fmt_num(b and b.get("DRAM_fill/FMA")),
        ])
    if rows:
        out += ["", f"{h2} By matrix size, one thread", ""]
        out += images(charts, image_dir, ("throughput_vs_size", "GFLOP/s of naive and blocked by matrix size"),
                      ("cache_misses", "Cache misses per multiply-add by matrix size"))
        out += ["GFLOP/s, then hardware-counter events per multiply-add (N = naive, B = blocked).", "",
                table(["n", "Naive", "Blocked", "Blocked / naive", "OpenBLAS", "L1D miss N", "L1D miss B",
                       "L2 miss N", "L2 miss B", "DRAM fill N", "DRAM fill B"], rows)]

    serial = results.get("BM_Blocked", n=n, bs=bs)
    openblas_1 = results.get("BM_OpenBLAS", n=n, workers=1)
    openblas_w = dict(results.series("BM_OpenBLAS", "workers", n=n))
    rows = []
    for workers, p in results.series("BM_BlockedParallel", "workers", n=n, bs=bs):
        speedup = serial["seconds"] / p["seconds"] if serial else None
        o = openblas_w.get(workers)
        rows.append([
            workers, fmt_ms(p["seconds"]), f"{gflops(n, p):.3g}", fmt_num(speedup),
            f"{speedup / min(workers, cores):.0%}" if speedup else "-",
            fmt_num(p.get("GHz")), fmt_num(p.get("IPC")), fmt_num(p.get("L1D_miss/FMA")),
            f"{gflops(n, o):.3g}" if o else "-",
            fmt_num(openblas_1["seconds"] / o["seconds"]) if o and openblas_1 else "-",
        ])
    if rows:
        out += ["", f"{h2} Thread scaling: n = {n}, tile {bs}", ""]
        out += images(charts, image_dir, ("thread_scaling", f"Speedup by number of workers at n = {n}"))
        out += [f"Speedup is against single-threaded multiplyBlocked; efficiency divides it by the physical cores "
                f"in use (at most {cores}). GHz is the average clock of the busy cores; IPC is per hardware thread.", "",
                table(["Workers", "Time (ms)", "GFLOP/s", "Speedup", "Efficiency", "GHz", "IPC", "L1D miss/FMA",
                       "OpenBLAS GFLOP/s", "OpenBLAS speedup"], rows)]

    workers = results.tile_sweep_workers()
    parallel_t = dict(results.series("BM_BlockedParallel", "bs", n=n, workers=workers)) if workers else {}
    rows = []
    for tile, p in results.series("BM_Blocked", "bs", n=n):
        q = parallel_t.get(tile)
        rows.append([tile, f"{gflops(n, p):.3g}", fmt_num(p.get("IPC")), fmt_num(p.get("L1D_miss/FMA")),
                     fmt_num(p.get("L2_miss/FMA")), f"{gflops(n, q):.3g}" if q else "-"])
    if rows:
        out += ["", f"{h2} Tile sweep: n = {n}", ""]
        out += images(charts, image_dir, ("tile_sweep", f"GFLOP/s by tile size at n = {n}"))
        out.append(table(["Tile", "1 thread GFLOP/s", "IPC", "L1D miss/FMA", "L2 miss/FMA",
                          f"{workers} workers GFLOP/s"], rows))
    return "\n".join(out) + "\n"


README_START, README_END = "<!-- results:start -->", "<!-- results:end -->"


def update_readme(path, results, label, charts, out):
    """Replaces everything between the results markers of a README with the summary, one heading
    level down so it nests under the README's title. The rest of the README is left alone."""
    readme = Path(path)
    text = readme.read_text()
    start, end = text.find(README_START), text.find(README_END)
    if start < 0 or end < start:
        print(f"skipped {readme}: no {README_START} and {README_END} lines in it")
        return
    image_dir = Path(os.path.relpath(out, readme.parent)).as_posix()
    section = summary(results, label, charts, image_dir, level=2)
    # Blank lines around the section, so the end marker cannot run on into its last table.
    readme.write_text(text[:start + len(README_START)] + "\n\n" + section + "\n" + text[end:])
    print(f"updated {readme}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("results", help="JSON file written by make bench-run")
    parser.add_argument("--out", default="bench/plots", help="output directory (default: bench/plots)")
    parser.add_argument("--readme", help=f"also put the summary in this README, between its {README_START} "
                                         f"and {README_END} lines")
    args = parser.parse_args()

    results = Results(args.results)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    charts = {"headline": chart_headline, "throughput_vs_size": chart_throughput,
              "cache_misses": chart_cache, "thread_scaling": chart_scaling, "tile_sweep": chart_tiles}
    written = set()
    for name, make in charts.items():
        path = out / f"{name}.png"
        fig = make(results, THEME)
        if fig is None:
            path.unlink(missing_ok=True)   # so the folder never mixes in a chart from an older run
            print(f"skipped {name}: no data for it in {args.results}")
            continue
        fig.savefig(path, facecolor=THEME["surface"])
        plt.close(fig)
        written.add(name)
        print(f"wrote {path}")
    label = Path(args.results).stem
    (out / "summary.md").write_text(summary(results, label, written))
    print(f"wrote {out / 'summary.md'}")
    if args.readme:
        update_readme(args.readme, results, label, written, out)
    for failure in results.failed:
        print(f"FAILED correctness check: {failure}")


if __name__ == "__main__":
    main()
