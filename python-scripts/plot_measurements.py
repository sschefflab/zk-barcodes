# Make plots.

import csv
import os
import re
import statistics
from collections import defaultdict

import matplotlib.lines as mlines
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

CSV_PATH = os.path.join(os.path.dirname(__file__), "../measurements/measurements.csv")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "../measurements/plots")
os.makedirs(OUTPUT_DIR, exist_ok=True)

rows = list(csv.DictReader(open(CSV_PATH)))

SUB_CIRCUITS = [
    "binarize",
    "block_measurement",
    "words_pipeline",
    "check_barcode_stats",
    "check_error_correction",
    "check_num_cw",
    "codewords_to_chars",
]

COLORS = {
    "binarize": "#4e79a7",
    "block_measurement": "#f28e2b",
    "check_barcode_stats": "#59a14f",
    "check_num_cw": "#76b7b2",
    "check_error_correction": "#e15759",
    "codewords_to_chars": "#b07aa1",
    "words_pipeline": "#ff9da7",
}

LABELS = {
    "check_barcode_stats": "barcode_metadata",
    "check_error_correction": "error_correction",
    "check_num_cw": "barcode_size",
    "codewords_to_chars": "character_interpretation",
}


def avg_prover(row):
    return statistics.mean(float(row[f"prover_time_{i}"]) for i in range(1, 6))


def se_prover(row):
    vals = [float(row[f"prover_time_{i}"]) for i in range(1, 6)]
    return statistics.stdev(vals) / len(vals) ** 0.5


def se_prover_ram(row):
    vals = [float(row[f"prover_ram_{i}"]) for i in range(1, 6)]
    return statistics.stdev(vals) / len(vals) ** 0.5


def param_label(key):
    img, max_r, max_c, ec, chunk = key
    return f"{img}\n{max_r}x{max_c} ec{ec}\nL={chunk}"


# ---------------------------------------------------------------------------
# Plot 1: Stacked proportion bar chart with full_circuit line
# ---------------------------------------------------------------------------

by_params = defaultdict(dict)
for r in rows:
    img = r["image_cols"] + "x" + r["image_rows"]
    key = (img, r["max_rows"], r["max_cols"], r["max_ec_level"], r["chunk_size"])
    by_params[key][r["circuit"]] = avg_prover(r)

# Only keep combos with all sub-circuits present
complete = {k: v for k, v in by_params.items() if all(c in v for c in SUB_CIRCUITS)}


def sort_key(k):
    img, max_r, max_c, ec, _chunk = k
    w, h = map(int, img.split("x"))
    return (w * h, int(max_r) * int(max_c), int(ec))


if complete:
    keys = sorted(complete.keys(), key=sort_key)
    n = len(keys)
    bar_width = 0.18
    bar_gap = 0.10
    x = np.arange(n) * (bar_width + bar_gap)

    fig, ax = plt.subplots(figsize=(max(4, n * 0.55 + 2), 5))

    bottoms = np.zeros(n)
    for circuit in SUB_CIRCUITS:
        totals = np.array([sum(complete[k][c] for c in SUB_CIRCUITS) for k in keys])
        vals = np.array([complete[k][circuit] / totals[i] for i, k in enumerate(keys)])
        ax.bar(
            x,
            vals,
            bar_width,
            bottom=bottoms,
            label=LABELS.get(circuit, circuit),
            color=COLORS[circuit],
        )
        bottoms += vals

    # full_circuit line as fraction of sub-circuit sum
    # fc_fracs = []
    # for k in keys:
    #     if "full_circuit" in complete[k]:
    #         fc_fracs.append(complete[k]["full_circuit"] / sum(complete[k][c] for c in SUB_CIRCUITS))
    #     else:
    #         fc_fracs.append(None)
    # if any(v is not None for v in fc_fracs):
    #     fc_x = [xi for xi, v in zip(x, fc_fracs) if v is not None]
    #     fc_y = [v for v in fc_fracs if v is not None]
    #     ax.plot(fc_x, fc_y, "ko--", linewidth=1.5, markersize=6, label="full_circuit / sum", zorder=5)

    ax.set_xticks(x)
    ax.set_xticklabels(
        [param_label(k) for k in keys], fontsize=7, rotation=45, ha="right"
    )
    ax.set_ylabel("Fraction of total sub-circuit time")
    ax.set_ylim(0, 1.05)
    ax.set_title("Sub-Circuit Time Proportions (Mean over 5 Runs)")
    handles, labels = ax.get_legend_handles_labels()
    # Matplotlib fills legends column-by-column. To display as:
    #   Row 1: binarize, block_measurement, words_pipeline, (blank)
    #   Row 2: barcode_metadata, error_correction, barcode_size, character_interpretation
    # reorder into column-major order: col1=[0,3], col2=[1,4], col3=[2,5], col4=[blank,6]
    blank = mlines.Line2D([], [], linewidth=0, label="")
    row1 = handles[:3]
    row2 = handles[3:]
    ordered_h = [row1[0], row2[0], row1[1], row2[1], row1[2], row2[2], blank, row2[3]]
    ordered_l = [row1[0].get_label() if hasattr(row1[0], 'get_label') else labels[0],
                 labels[3], labels[1], labels[4], labels[2], labels[5], "", labels[6]]
    ax.legend(handles=ordered_h, labels=ordered_l, loc="upper center",
              bbox_to_anchor=(0.5, -0.22), fontsize=7, ncol=4)
    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, "plot1_stacked_proportions.png"), dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("Saved plot1_stacked_proportions.png")
else:
    print("Plot 1: no complete parameter combos yet, skipping")


# ---------------------------------------------------------------------------
# Plot 2: full_circuit time vs image size
# Separate line per (max_rows, max_cols, ec, chunk) combo
# ---------------------------------------------------------------------------

fc_rows = [r for r in rows if r["circuit"] == "full_circuit"]

by_combo = defaultdict(dict)
by_combo_se = defaultdict(dict)
for r in fc_rows:
    img = r["image_cols"] + "x" + r["image_rows"]
    combo = (r["max_rows"], r["max_cols"], r["max_ec_level"], r["chunk_size"])
    by_combo[combo][img] = avg_prover(r)
    by_combo_se[combo][img] = se_prover(r)

IMAGE_ORDER = ["144x48", "192x144", "384x288", "640x480", "1080x720"]
img_pixels = {
    img: int(img.split("x")[0]) * int(img.split("x")[1]) for img in IMAGE_ORDER
}

target_combo = next(
    (c for c in by_combo if c[0] == "3" and c[1] == "3" and c[2] == "1"),
    None,
)

if target_combo:
    img_times = by_combo[target_combo]
    imgs = [img for img in IMAGE_ORDER if img in img_times]
    xs = [img_pixels[img] for img in imgs]
    ys = [img_times[img] / 1000 for img in imgs]
    ses = [by_combo_se[target_combo][img] / 1000 for img in imgs]

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.errorbar(xs, ys, yerr=ses, fmt="o-", capsize=4)

    ax.set_xlabel("Image pixels (width × height)")
    ax.set_ylabel("Prover time (s)")
    ax.set_title("full_circuit prover time vs image size (max=3x3, ec=1)")
    ax.set_ylim(bottom=0)
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"{int(v):,}"))
    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, "plot2_fullcircuit_vs_imagesize.png"), dpi=150)
    plt.close(fig)
    print("Saved plot2_fullcircuit_vs_imagesize.png")
else:
    print("Plot 2: no full_circuit data for max=3x3 ec=1, skipping")


# ---------------------------------------------------------------------------
# Plot 3: full_circuit time vs max_rows * max_cols (barcode size), fixed image
# Use largest image that has enough variety in max_rows/max_cols
# ---------------------------------------------------------------------------

IMAGE_FOR_PLOT3 = "384x288"

fc_img = [
    r for r in fc_rows if r["image_cols"] + "x" + r["image_rows"] == IMAGE_FOR_PLOT3
]
by_ec = defaultdict(dict)
by_ec_se = defaultdict(dict)
for r in fc_img:
    barcode_cells = int(r["max_rows"]) * int(r["max_cols"])
    ec = r["max_ec_level"]
    by_ec[ec][barcode_cells] = avg_prover(r)
    by_ec_se[ec][barcode_cells] = se_prover(r)

if any(len(v) >= 2 for v in by_ec.values()):
    fig, ax = plt.subplots(figsize=(7, 5))
    for ec, cell_times in sorted(by_ec.items(), key=lambda x: int(x[0])):
        if len(cell_times) < 2:
            continue
        xs, ys = zip(*sorted(cell_times.items()))
        ys = [y / 1000 for y in ys]
        ses = [by_ec_se[ec][x] / 1000 for x in xs]
        ax.errorbar(xs, ys, yerr=ses, fmt="o-", capsize=4, label=f"ec={ec}")
    ax.set_xlabel("max_rows × max_cols (logical)")
    ax.set_ylabel("Prover time (s)")
    ax.set_title(f"full_circuit prover time vs barcode size ({IMAGE_FOR_PLOT3})")
    ax.set_ylim(bottom=0)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(
        os.path.join(OUTPUT_DIR, "plot3_fullcircuit_vs_barcodesize.png"), dpi=150
    )
    plt.close(fig)
    print("Saved plot3_fullcircuit_vs_barcodesize.png")
else:
    print(f"Plot 3: not enough full_circuit variety at {IMAGE_FOR_PLOT3}, skipping")


# ---------------------------------------------------------------------------
# Plot 4: full_circuit time vs max_ec_level (commented out - insufficient data)
# ---------------------------------------------------------------------------

# IMAGE_FOR_PLOT4 = "192x144"
#
# by_img_barcode = defaultdict(dict)
# for r in fc_rows:
#     img = r["image_cols"] + "x" + r["image_rows"]
#     if img != IMAGE_FOR_PLOT4:
#         continue
#     key = (img, r["max_rows"], r["max_cols"])
#     by_img_barcode[key][int(r["max_ec_level"])] = avg_prover(r)
#
# best = max(by_img_barcode.items(), key=lambda x: len(x[1]), default=None)
#
# if best and len(best[1]) >= 2:
#     key, ec_times = best
#     fig, ax = plt.subplots(figsize=(6, 5))
#     xs, ys = zip(*sorted(ec_times.items()))
#     ax.plot(xs, ys, "o-")
#     ax.set_xlabel("max_ec_level")
#     ax.set_ylabel("Prover time (ms)")
#     ax.set_xticks(xs)
#     ax.set_ylim(bottom=0)
#     ax.set_title(f"full_circuit prover time vs EC level\n(image={key[0]}, max={key[1]}x{key[2]})")
#     fig.tight_layout()
#     fig.savefig(os.path.join(OUTPUT_DIR, "plot4_fullcircuit_vs_ec.png"), dpi=150)
#     plt.close(fig)
#     print("Saved plot4_fullcircuit_vs_ec.png")
# else:
#     print("Plot 4: not enough full_circuit EC level variety, skipping")


# ---------------------------------------------------------------------------
# Plot 5: check_* + codewords_to_chars vs EC level at 384x288, max=90x30
# ---------------------------------------------------------------------------

CHECK_CIRCUITS = [
    "check_barcode_stats",
    "check_num_cw",
    "check_error_correction",
    "codewords_to_chars",
]
CHECK_COLORS = {c: COLORS[c] for c in CHECK_CIRCUITS}

plot5_rows = [
    r
    for r in rows
    if r["image_cols"] + "x" + r["image_rows"] == "384x288"
    and r["max_rows"] == "90"
    and r["max_cols"] == "30"
    and r["circuit"] in CHECK_CIRCUITS
]

by_circuit_ec = defaultdict(dict)
by_circuit_ec_se = defaultdict(dict)
for r in plot5_rows:
    by_circuit_ec[r["circuit"]][int(r["max_ec_level"])] = avg_prover(r)
    by_circuit_ec_se[r["circuit"]][int(r["max_ec_level"])] = se_prover(r)

if by_circuit_ec:
    fig, ax = plt.subplots(figsize=(6, 5))
    for circuit in CHECK_CIRCUITS:
        if circuit not in by_circuit_ec:
            continue
        ec_times = by_circuit_ec[circuit]
        xs, ys = zip(*sorted(ec_times.items()))
        ys = [y / 1000 for y in ys]
        ses = [by_circuit_ec_se[circuit][x] / 1000 for x in xs]
        ax.errorbar(
            xs,
            ys,
            yerr=ses,
            fmt="o-",
            capsize=4,
            label=LABELS.get(circuit, circuit),
            color=CHECK_COLORS[circuit],
        )
    ax.set_xlabel("max_ec_level")
    ax.set_ylabel("Prover time (s)")
    ax.set_title("Check circuit times vs EC level\n(384x288, max=90x30)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, "plot5_check_vs_ec.png"), dpi=150)
    plt.close(fig)
    print("Saved plot5_check_vs_ec.png")
else:
    print("Plot 5: no data for 384x288 max=90x30, skipping")


# ---------------------------------------------------------------------------
# Plot 6: full_circuit prover RAM vs image size
# ---------------------------------------------------------------------------


def avg_prover_ram(row):
    return statistics.mean(float(row[f"prover_ram_{i}"]) for i in range(1, 6))


by_combo_ram = defaultdict(dict)
by_combo_ram_se = defaultdict(dict)
for r in fc_rows:
    img = r["image_cols"] + "x" + r["image_rows"]
    combo = (r["max_rows"], r["max_cols"], r["max_ec_level"], r["chunk_size"])
    by_combo_ram[combo][img] = avg_prover_ram(r)
    by_combo_ram_se[combo][img] = se_prover_ram(r)

target_combo_ram = next(
    (c for c in by_combo_ram if c[0] == "3" and c[1] == "3" and c[2] == "1"),
    None,
)

if target_combo_ram:
    img_rams = by_combo_ram[target_combo_ram]
    imgs = [img for img in IMAGE_ORDER if img in img_rams]
    xs = [img_pixels[img] for img in imgs]
    ys = [img_rams[img] / 1e6 for img in imgs]
    ses = [by_combo_ram_se[target_combo_ram][img] / 1e6 for img in imgs]

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.errorbar(xs, ys, yerr=ses, fmt="o-", capsize=4)

    ax.set_xlabel("Image pixels (width × height)")
    ax.set_ylabel("Prover RAM (GB)")
    ax.set_title("full_circuit prover RAM vs image size (max=3x3, ec=1)")
    ax.set_ylim(bottom=0)
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"{int(v):,}"))
    fig.tight_layout()
    fig.savefig(
        os.path.join(OUTPUT_DIR, "plot6_fullcircuit_ram_vs_imagesize.png"), dpi=150
    )
    plt.close(fig)
    print("Saved plot6_fullcircuit_ram_vs_imagesize.png")
else:
    print("Plot 6: no full_circuit data for max=3x3 ec=1, skipping")


# ---------------------------------------------------------------------------
# Plot 7: Stacked proportion bar chart for RAM
# ---------------------------------------------------------------------------

by_params_ram = defaultdict(dict)
for r in rows:
    img = r["image_cols"] + "x" + r["image_rows"]
    key = (img, r["max_rows"], r["max_cols"], r["max_ec_level"], r["chunk_size"])
    by_params_ram[key][r["circuit"]] = avg_prover_ram(r)

complete_ram = {
    k: v for k, v in by_params_ram.items() if all(c in v for c in SUB_CIRCUITS)
}

if complete_ram:
    # Order circuits by mean RAM across all complete combos, most to least
    mean_ram = {
        c: statistics.mean(v[c] for v in complete_ram.values()) for c in SUB_CIRCUITS
    }
    ram_order = sorted(SUB_CIRCUITS, key=lambda c: mean_ram[c], reverse=True)

    keys = sorted(complete_ram.keys(), key=sort_key)
    n = len(keys)
    bar_width = 0.18
    bar_gap = 0.10
    x = np.arange(n) * (bar_width + bar_gap)

    fig, ax = plt.subplots(figsize=(max(4, n * 0.55 + 2), 5))

    bottoms = np.zeros(n)
    for circuit in ram_order:
        totals = np.array([sum(complete_ram[k][c] for c in SUB_CIRCUITS) for k in keys])
        vals = np.array(
            [complete_ram[k][circuit] / totals[i] for i, k in enumerate(keys)]
        )
        ax.bar(
            x,
            vals,
            bar_width,
            bottom=bottoms,
            label=LABELS.get(circuit, circuit),
            color=COLORS[circuit],
        )
        bottoms += vals

    # full_circuit RAM line as fraction of sub-circuit sum
    # fc_fracs_ram = []
    # for k in keys:
    #     if "full_circuit" in complete_ram[k]:
    #         fc_fracs_ram.append(complete_ram[k]["full_circuit"] / sum(complete_ram[k][c] for c in SUB_CIRCUITS))
    #     else:
    #         fc_fracs_ram.append(None)
    # if any(v is not None for v in fc_fracs_ram):
    #     fc_x = [xi for xi, v in zip(x, fc_fracs_ram) if v is not None]
    #     fc_y = [v for v in fc_fracs_ram if v is not None]
    #     ax.plot(fc_x, fc_y, "ko--", linewidth=1.5, markersize=6, label="full_circuit / sum", zorder=5)

    ax.set_xticks(x)
    ax.set_xticklabels(
        [param_label(k) for k in keys], fontsize=7, rotation=45, ha="right"
    )
    ax.set_ylabel("Fraction of total sub-circuit RAM")
    ax.set_ylim(0, 1.05)
    ax.set_title("Sub-circuit RAM proportions (mean over 5 runs)")
    ax.legend(loc="upper right", fontsize=7, ncol=2)
    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, "plot7_stacked_ram_proportions.png"), dpi=150)
    plt.close(fig)
    print("Saved plot7_stacked_ram_proportions.png")
else:
    print("Plot 7: no complete parameter combos yet, skipping")


# ---------------------------------------------------------------------------
# SP1 zkvm log parsing helpers
# ---------------------------------------------------------------------------

SP1_DIR = os.path.join(os.path.dirname(__file__), "../sp1-pdf417/proof-runs")


def parse_elapsed_ms(s):
    """Parse '/usr/bin/time --verbose' elapsed string to milliseconds."""
    s = s.strip()
    if ":" in s:
        parts = s.split(":")
        if len(parts) == 2:  # m:ss.cc
            return (int(parts[0]) * 60 + float(parts[1])) * 1000
        else:  # h:mm:ss
            return (int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])) * 1000
    return float(s) * 1000


def parse_sp1_log(path):
    """Return (list_of_elapsed_ms, list_of_ram_kb) for 5 iterations."""
    with open(path) as f:
        text = f.read()
    # Split on iteration boundaries
    blocks = re.split(r"--- Iteration \d+ of \d+ ---", text)[1:]
    times, rams = [], []
    for block in blocks:
        t = re.search(r"Elapsed \(wall clock\) time \(h:mm:ss or m:ss\): (.+)", block)
        r = re.search(r"Maximum resident set size \(kbytes\): (\d+)", block)
        if t and r:
            times.append(parse_elapsed_ms(t.group(1)))
            rams.append(int(r.group(1)))
    return times, rams


# Build SP1 data keyed by (img, max_rows, max_cols, ec)
# Filename pattern: prove-output-barcode_r{R}_c{C}_e{E}_{W}x{H}-*.log
sp1_data = {}  # key -> {"times": [...], "rams": [...]}
if os.path.isdir(SP1_DIR):
    for fname in os.listdir(SP1_DIR):
        m = re.match(
            r"prove-output-barcode_r(\d+)_c(\d+)_e(\d+)_(\d+x\d+)-\d{8}-\d{6}\.log",
            fname,
        )
        if not m:
            continue
        max_r, max_c, ec, img = m.group(1), m.group(2), m.group(3), m.group(4)
        key = (img, max_r, max_c, ec)
        times, rams = parse_sp1_log(os.path.join(SP1_DIR, fname))
        if len(times) == 5:
            sp1_data[key] = {"times": times, "rams": rams}


def sp1_sort_key(k):
    img, max_r, max_c, ec = k
    w, h = map(int, img.split("x"))
    return (w * h, int(max_r) * int(max_c), int(ec))


def sp1_label(k):
    img, max_r, max_c, ec = k
    return f"{img}\n{max_r}x{max_c} ec{ec}"


# ---------------------------------------------------------------------------
# Plots 8 & 9: zkvm vs full_circuit (one bar per full_circuit run)
#
# Actual barcode params used for a circuit run:
#   actual_r = min(21, max_rows), actual_c = min(13, max_cols), actual_e = min(5, max_ec)
# We look up the SP1 run keyed on (img, actual_r, actual_c, actual_e).
# ---------------------------------------------------------------------------


def fc_to_sp1_key(img, max_r, max_c, max_e):
    return (
        img,
        str(min(21, int(max_r))),
        str(min(13, int(max_c))),
        str(min(5, int(max_e))),
    )


def fc_sort_key(fc_key):
    img, max_r, max_c, max_e = fc_key
    w, h = map(int, img.split("x"))
    return (w * h, int(max_r) * int(max_c), int(max_e))


def fc_label(fc_key):
    img, max_r, max_c, max_e = fc_key
    return f"{img}\nmax={max_r}x{max_c}\nec{max_e}"


# Collect all full_circuit runs that have a matching SP1 run
fc_time_map = {}  # (img, max_r, max_c, max_e) -> avg prover time ms
fc_time_raw_map = {}  # (img, max_r, max_c, max_e) -> [5 prover times ms]
fc_ram_map = {}  # (img, max_r, max_c, max_e) -> avg prover ram kB
fc_ram_raw_map = {}  # (img, max_r, max_c, max_e) -> [5 prover rams kB]
for r in rows:
    if r["circuit"] != "full_circuit":
        continue
    img = r["image_cols"] + "x" + r["image_rows"]
    fc_key = (img, r["max_rows"], r["max_cols"], r["max_ec_level"])
    times = [float(r[f"prover_time_{i}"]) for i in range(1, 6)]
    rams = [float(r[f"prover_ram_{i}"]) for i in range(1, 6)]
    fc_time_map[fc_key] = statistics.mean(times)
    fc_time_raw_map[fc_key] = times
    fc_ram_map[fc_key] = statistics.mean(rams)
    fc_ram_raw_map[fc_key] = rams

matched_fc_keys = sorted(
    [k for k in fc_time_map if fc_to_sp1_key(*k) in sp1_data],
    key=fc_sort_key,
)

# ---------------------------------------------------------------------------
# Plot 8: zkvm vs full_circuit prover time (side-by-side bars)
# ---------------------------------------------------------------------------

if matched_fc_keys:
    bar_width = 0.18
    bar_gap = 0.02
    group_gap = 0.12   # space between adjacent bar groups
    img_gap = 0.30     # extra space between different image sizes
    group_w = bar_width * 2 + bar_gap
    step = group_w + group_gap
    x = []
    pos = 0.0
    for i, k in enumerate(matched_fc_keys):
        if i > 0 and k[0] != matched_fc_keys[i - 1][0]:
            pos += img_gap
        x.append(pos)
        pos += step
    x = np.array(x)

    fig, ax = plt.subplots(figsize=(max(4, len(matched_fc_keys) * step * 1.8), 5))

    zkvm_times = [
        statistics.mean(sp1_data[fc_to_sp1_key(*k)]["times"]) / 1000
        for k in matched_fc_keys
    ]
    zkvm_times_se = [
        statistics.stdev(sp1_data[fc_to_sp1_key(*k)]["times"])
        / 1000
        / len(sp1_data[fc_to_sp1_key(*k)]["times"]) ** 0.5
        for k in matched_fc_keys
    ]
    fc_times = [fc_time_map[k] / 1000 for k in matched_fc_keys]
    fc_times_se = [
        statistics.stdev(fc_time_raw_map[k]) / 1000 / len(fc_time_raw_map[k]) ** 0.5
        for k in matched_fc_keys
    ]

    ax.bar(
        x - bar_width / 2 - bar_gap / 2,
        fc_times,
        bar_width,
        label="Our System",
        color="#f28e2b",
        hatch="///",
        yerr=fc_times_se,
        capsize=4,
        error_kw={"elinewidth": 1.2},
    )
    ax.bar(
        x + bar_width / 2 + bar_gap / 2,
        zkvm_times,
        bar_width,
        label="zkVM",
        color="#4e79a7",
        yerr=zkvm_times_se,
        capsize=4,
        error_kw={"elinewidth": 1.2},
    )

    ax.set_xticks(x)
    ax.set_xticklabels([fc_label(k) for k in matched_fc_keys], fontsize=8)
    ax.set_ylabel("Prover time (s)")
    ax.set_title("Our System vs zkVM: Prover Time")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, "plot8_zkvm_vs_fullcircuit_time.png"), dpi=150)
    plt.close(fig)
    print("Saved plot8_zkvm_vs_fullcircuit_time.png")
else:
    print("Plot 8: no matching zkvm + full_circuit combos, skipping")


# ---------------------------------------------------------------------------
# Plot 9: zkvm vs full_circuit prover RAM (side-by-side bars)
# ---------------------------------------------------------------------------

if matched_fc_keys:
    bar_width = 0.18
    bar_gap = 0.02
    group_gap = 0.12
    img_gap = 0.30
    group_w = bar_width * 2 + bar_gap
    step = group_w + group_gap
    x = []
    pos = 0.0
    for i, k in enumerate(matched_fc_keys):
        if i > 0 and k[0] != matched_fc_keys[i - 1][0]:
            pos += img_gap
        x.append(pos)
        pos += step
    x = np.array(x)

    fig, ax = plt.subplots(figsize=(max(4, len(matched_fc_keys) * step * 1.8), 5))

    zkvm_rams = [
        statistics.mean(sp1_data[fc_to_sp1_key(*k)]["rams"]) / 1e6
        for k in matched_fc_keys
    ]
    zkvm_rams_se = [
        statistics.stdev(sp1_data[fc_to_sp1_key(*k)]["rams"])
        / 1e6
        / len(sp1_data[fc_to_sp1_key(*k)]["rams"]) ** 0.5
        for k in matched_fc_keys
    ]
    fc_rams = [fc_ram_map[k] / 1e6 for k in matched_fc_keys]
    fc_rams_se = [
        statistics.stdev(fc_ram_raw_map[k]) / 1e6 / len(fc_ram_raw_map[k]) ** 0.5
        for k in matched_fc_keys
    ]

    ax.bar(
        x - bar_width / 2 - bar_gap / 2,
        fc_rams,
        bar_width,
        label="Our System",
        color="#f28e2b",
        hatch="///",
        yerr=fc_rams_se,
        capsize=4,
        error_kw={"elinewidth": 1.2},
    )
    ax.bar(
        x + bar_width / 2 + bar_gap / 2,
        zkvm_rams,
        bar_width,
        label="zkVM",
        color="#4e79a7",
        yerr=zkvm_rams_se,
        capsize=4,
        error_kw={"elinewidth": 1.2},
    )

    ax.set_xticks(x)
    ax.set_xticklabels([fc_label(k) for k in matched_fc_keys], fontsize=8)
    ax.set_ylabel("Prover RAM (GB)")
    ax.set_title("Our System vs zkVM: Prover RAM")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, "plot9_zkvm_vs_fullcircuit_ram.png"), dpi=150)
    plt.close(fig)
    print("Saved plot9_zkvm_vs_fullcircuit_ram.png")
else:
    print("Plot 9: no matching zkvm + full_circuit combos, skipping")


# ---------------------------------------------------------------------------
# Scatter helpers for plots 10 & 11
# ---------------------------------------------------------------------------

from itertools import cycle

LINE_COLORS = [
    "#4e79a7",
    "#f28e2b",
    "#59a14f",
    "#e15759",
    "#b07aa1",
    "#76b7b2",
    "#ff9da7",
]
FC_MARKER = "o"
ZKVM_MARKER = "s"


def scatter_lines(ax, metric_fn_fc, metric_fn_zkvm, ylabel):
    by_combo = defaultdict(
        list
    )  # (max_r, max_c, max_e) -> [(img_pixels, fc_val, zkvm_val)]
    for k in matched_fc_keys:
        img, max_r, max_c, max_e = k
        w, h = map(int, img.split("x"))
        px = w * h
        sp1_key = fc_to_sp1_key(*k)
        by_combo[(max_r, max_c, max_e)].append(
            (px, metric_fn_fc(k), metric_fn_zkvm(sp1_key))
        )

    color_cycle = cycle(LINE_COLORS)
    fc_handle = zkvm_handle = None
    for combo, points in sorted(
        by_combo.items(), key=lambda x: (int(x[0][0]) * int(x[0][1]), int(x[0][2]))
    ):
        points.sort()
        xs, fc_ys, zkvm_ys = zip(*points)
        max_r, max_c, max_e = combo
        color = next(color_cycle)
        ax.plot(
            xs,
            fc_ys,
            FC_MARKER + "-",
            color=color,
            label=f"max={max_r}x{max_c} ec={max_e}",
        )
        ax.plot(xs, zkvm_ys, ZKVM_MARKER + "--", color=color)
        if fc_handle is None:
            fc_handle = mlines.Line2D(
                [0],
                [0],
                marker=FC_MARKER,
                color="k",
                linestyle="-",
                label="Our System",
            )
            zkvm_handle = mlines.Line2D(
                [0], [0], marker=ZKVM_MARKER, color="k", linestyle="--", label="zkVM"
            )

    color_cycle = cycle(LINE_COLORS)
    combo_handles = [
        mlines.Line2D(
            [0],
            [0],
            marker=FC_MARKER,
            color=next(color_cycle),
            linestyle="-",
            label=f"max={r}x{c_} ec={e}",
        )
        for r, c_, e in sorted(
            by_combo.keys(), key=lambda x: (int(x[0]) * int(x[1]), int(x[2]))
        )
    ]
    shape_handles = [fc_handle, zkvm_handle] if fc_handle else []

    leg1 = ax.legend(
        handles=shape_handles, fontsize=7, loc="upper left", title="System"
    )
    ax.add_artist(leg1)
    ax.legend(
        handles=combo_handles, fontsize=7, loc="upper right", title="Config", ncol=1
    )
    ax.set_xlabel("Image pixels (width × height)")
    ax.set_ylabel(ylabel)
    ax.set_yscale("log")
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"{int(v):,}"))


# ---------------------------------------------------------------------------
# Plot 10: zkvm vs full_circuit prover time (scatter, seconds)
# ---------------------------------------------------------------------------

if matched_fc_keys:
    fig, ax = plt.subplots(figsize=(8, 5))
    scatter_lines(
        ax,
        metric_fn_fc=lambda k: fc_time_map[k] / 1000,
        metric_fn_zkvm=lambda sp1_key: statistics.mean(sp1_data[sp1_key]["times"])
        / 1000,
        ylabel="Prover time (s)",
    )
    ax.set_title("Our System vs zkVM: Prover Time")
    fig.tight_layout()
    fig.savefig(
        os.path.join(OUTPUT_DIR, "plot10_zkvm_vs_fullcircuit_time_scatter.png"), dpi=150
    )
    plt.close(fig)
    print("Saved plot10_zkvm_vs_fullcircuit_time_scatter.png")
else:
    print("Plot 10: no matching zkvm + full_circuit combos, skipping")


# ---------------------------------------------------------------------------
# Plot 11: zkvm vs full_circuit prover RAM (scatter, GB)
# ---------------------------------------------------------------------------

if matched_fc_keys:
    fig, ax = plt.subplots(figsize=(8, 5))
    scatter_lines(
        ax,
        metric_fn_fc=lambda k: fc_ram_map[k] / 1e6,
        metric_fn_zkvm=lambda sp1_key: statistics.mean(sp1_data[sp1_key]["rams"]) / 1e6,
        ylabel="Prover RAM (GB)",
    )
    ax.set_title("Our System vs zkVM: Prover RAM")
    fig.tight_layout()
    fig.savefig(
        os.path.join(OUTPUT_DIR, "plot11_zkvm_vs_fullcircuit_ram_scatter.png"), dpi=150
    )
    plt.close(fig)
    print("Saved plot11_zkvm_vs_fullcircuit_ram_scatter.png")
else:
    print("Plot 11: no matching zkvm + full_circuit combos, skipping")
