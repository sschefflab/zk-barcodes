import csv
import os
import statistics
from collections import defaultdict

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

CSV_PATH = os.path.join(os.path.dirname(__file__), "../zokrates/for-measurement/measurements.csv")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "../zokrates/for-measurement/plots")
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
    "binarize":              "#4e79a7",
    "block_measurement":     "#f28e2b",
    "check_barcode_stats":   "#59a14f",
    "check_num_cw":          "#76b7b2",
    "check_error_correction":"#e15759",
    "codewords_to_chars":    "#b07aa1",
    "words_pipeline":        "#ff9da7",
}


def avg_prover(row):
    return statistics.mean(float(row[f"prover_time_{i}"]) for i in range(1, 6))


def param_label(key):
    img, max_r, max_c, ec, chunk = key
    return f"{img}\n{max_r}x{max_c} ec{ec}"


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

if complete:
    keys = sorted(complete.keys())
    x = np.arange(len(keys))
    bar_width = 0.6

    fig, ax = plt.subplots(figsize=(max(6, len(keys) * 1.4), 5))

    bottoms = np.zeros(len(keys))
    for circuit in SUB_CIRCUITS:
        totals = np.array([sum(complete[k][c] for c in SUB_CIRCUITS) for k in keys])
        vals = np.array([complete[k][circuit] / totals[i] for i, k in enumerate(keys)])
        ax.bar(x, vals, bar_width, bottom=bottoms, label=circuit, color=COLORS[circuit])
        bottoms += vals

    # full_circuit line as fraction of sub-circuit sum
    fc_fracs = []
    for k in keys:
        if "full_circuit" in complete[k]:
            fc_fracs.append(complete[k]["full_circuit"] / sum(complete[k][c] for c in SUB_CIRCUITS))
        else:
            fc_fracs.append(None)

    if any(v is not None for v in fc_fracs):
        fc_x = [xi for xi, v in zip(x, fc_fracs) if v is not None]
        fc_y = [v for v in fc_fracs if v is not None]
        ax.plot(fc_x, fc_y, "ko--", linewidth=1.5, markersize=6, label="full_circuit / sum", zorder=5)

    ax.set_xticks(x)
    ax.set_xticklabels([param_label(k) for k in keys], fontsize=8)
    ax.set_ylabel("Fraction of total sub-circuit time")
    ax.set_ylim(0, 1.05)
    ax.set_title("Sub-circuit time proportions (mean over 5 runs)")
    ax.legend(loc="upper right", fontsize=7, ncol=2)
    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, "plot1_stacked_proportions.png"), dpi=150)
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
for r in fc_rows:
    img = r["image_cols"] + "x" + r["image_rows"]
    combo = (r["max_rows"], r["max_cols"], r["max_ec_level"], r["chunk_size"])
    by_combo[combo][img] = avg_prover(r)

IMAGE_ORDER = ["144x48", "192x144", "384x288", "640x480", "1080x720"]
img_pixels = {img: int(img.split("x")[0]) * int(img.split("x")[1]) for img in IMAGE_ORDER}

if by_combo:
    fig, ax = plt.subplots(figsize=(7, 5))
    for combo, img_times in sorted(by_combo.items()):
        imgs = [img for img in IMAGE_ORDER if img in img_times]
        xs = [img_pixels[img] for img in imgs]
        ys = [img_times[img] for img in imgs]
        label = f"max={combo[0]}x{combo[1]} ec={combo[2]}"
        ax.plot(xs, ys, "o-", label=label)

    ax.set_xlabel("Image pixels (width × height)")
    ax.set_ylabel("Prover time (ms)")
    ax.set_title("full_circuit prover time vs image size")
    ax.legend(fontsize=7)
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"{int(v):,}"))
    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, "plot2_fullcircuit_vs_imagesize.png"), dpi=150)
    plt.close(fig)
    print("Saved plot2_fullcircuit_vs_imagesize.png")
else:
    print("Plot 2: no full_circuit data, skipping")


# ---------------------------------------------------------------------------
# Plot 3: full_circuit time vs max_rows * max_cols (barcode size), fixed image
# Use largest image that has enough variety in max_rows/max_cols
# ---------------------------------------------------------------------------

IMAGE_FOR_PLOT3 = "192x144"

fc_img = [r for r in fc_rows if r["image_cols"] + "x" + r["image_rows"] == IMAGE_FOR_PLOT3]
by_ec = defaultdict(dict)
for r in fc_img:
    barcode_cells = int(r["max_rows"]) * int(r["max_cols"])
    ec = r["max_ec_level"]
    by_ec[ec][barcode_cells] = avg_prover(r)

if any(len(v) >= 2 for v in by_ec.values()):
    fig, ax = plt.subplots(figsize=(7, 5))
    for ec, cell_times in sorted(by_ec.items(), key=lambda x: int(x[0])):
        if len(cell_times) < 2:
            continue
        xs, ys = zip(*sorted(cell_times.items()))
        ax.plot(xs, ys, "o-", label=f"ec={ec}")
    ax.set_xlabel("max_rows × max_cols (logical)")
    ax.set_ylabel("Prover time (ms)")
    ax.set_title(f"full_circuit prover time vs barcode size ({IMAGE_FOR_PLOT3})")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, "plot3_fullcircuit_vs_barcodesize.png"), dpi=150)
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
# Plot 5: check_* + codewords_to_chars vs EC level at 384x288, max=60x20
# ---------------------------------------------------------------------------

CHECK_CIRCUITS = ["check_barcode_stats", "check_num_cw", "check_error_correction", "codewords_to_chars"]
CHECK_COLORS = {c: COLORS[c] for c in CHECK_CIRCUITS}

plot5_rows = [
    r for r in rows
    if r["image_cols"] + "x" + r["image_rows"] == "384x288"
    and r["max_rows"] == "60"
    and r["max_cols"] == "20"
    and r["circuit"] in CHECK_CIRCUITS
]

by_circuit_ec = defaultdict(dict)
for r in plot5_rows:
    by_circuit_ec[r["circuit"]][int(r["max_ec_level"])] = avg_prover(r)

if by_circuit_ec:
    fig, ax = plt.subplots(figsize=(6, 5))
    for circuit in CHECK_CIRCUITS:
        if circuit not in by_circuit_ec:
            continue
        ec_times = by_circuit_ec[circuit]
        xs, ys = zip(*sorted(ec_times.items()))
        ax.plot(xs, ys, "o-", label=circuit, color=CHECK_COLORS[circuit])
    ax.set_xlabel("max_ec_level")
    ax.set_ylabel("Prover time (ms)")
    ax.set_title("Check circuit times vs EC level\n(384x288, max=60x20)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, "plot5_check_vs_ec.png"), dpi=150)
    plt.close(fig)
    print("Saved plot5_check_vs_ec.png")
else:
    print("Plot 5: no data for 384x288 max=60x20, skipping")


# ---------------------------------------------------------------------------
# Plot 6: full_circuit prover RAM vs image size
# ---------------------------------------------------------------------------

def avg_prover_ram(row):
    return statistics.mean(float(row[f"prover_ram_{i}"]) for i in range(1, 6))

by_combo_ram = defaultdict(dict)
for r in fc_rows:
    img = r["image_cols"] + "x" + r["image_rows"]
    combo = (r["max_rows"], r["max_cols"], r["max_ec_level"], r["chunk_size"])
    by_combo_ram[combo][img] = avg_prover_ram(r)

if by_combo_ram:
    fig, ax = plt.subplots(figsize=(7, 5))
    for combo, img_rams in sorted(by_combo_ram.items()):
        imgs = [img for img in IMAGE_ORDER if img in img_rams]
        xs = [img_pixels[img] for img in imgs]
        ys = [img_rams[img] / 1e6 for img in imgs]  # convert kB to GB
        label = f"max={combo[0]}x{combo[1]} ec={combo[2]}"
        ax.plot(xs, ys, "o-", label=label)

    ax.set_xlabel("Image pixels (width × height)")
    ax.set_ylabel("Prover RAM (GB)")
    ax.set_title("full_circuit prover RAM vs image size")
    ax.legend(fontsize=7)
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"{int(v):,}"))
    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, "plot6_fullcircuit_ram_vs_imagesize.png"), dpi=150)
    plt.close(fig)
    print("Saved plot6_fullcircuit_ram_vs_imagesize.png")
else:
    print("Plot 6: no full_circuit data, skipping")


# ---------------------------------------------------------------------------
# Plot 7: Stacked proportion bar chart for RAM
# ---------------------------------------------------------------------------

by_params_ram = defaultdict(dict)
for r in rows:
    img = r["image_cols"] + "x" + r["image_rows"]
    key = (img, r["max_rows"], r["max_cols"], r["max_ec_level"], r["chunk_size"])
    by_params_ram[key][r["circuit"]] = avg_prover_ram(r)

complete_ram = {k: v for k, v in by_params_ram.items() if all(c in v for c in SUB_CIRCUITS)}

if complete_ram:
    # Order circuits by mean RAM across all complete combos, most to least
    mean_ram = {c: statistics.mean(v[c] for v in complete_ram.values()) for c in SUB_CIRCUITS}
    ram_order = sorted(SUB_CIRCUITS, key=lambda c: mean_ram[c], reverse=True)

    keys = sorted(complete_ram.keys())
    x = np.arange(len(keys))
    bar_width = 0.6

    fig, ax = plt.subplots(figsize=(max(6, len(keys) * 1.4), 5))

    bottoms = np.zeros(len(keys))
    for circuit in ram_order:
        totals = np.array([sum(complete_ram[k][c] for c in SUB_CIRCUITS) for k in keys])
        vals = np.array([complete_ram[k][circuit] / totals[i] for i, k in enumerate(keys)])
        ax.bar(x, vals, bar_width, bottom=bottoms, label=circuit, color=COLORS[circuit])
        bottoms += vals

    # full_circuit RAM line as fraction of sub-circuit sum
    fc_fracs_ram = []
    for k in keys:
        if "full_circuit" in complete_ram[k]:
            fc_fracs_ram.append(complete_ram[k]["full_circuit"] / sum(complete_ram[k][c] for c in SUB_CIRCUITS))
        else:
            fc_fracs_ram.append(None)

    if any(v is not None for v in fc_fracs_ram):
        fc_x = [xi for xi, v in zip(x, fc_fracs_ram) if v is not None]
        fc_y = [v for v in fc_fracs_ram if v is not None]
        ax.plot(fc_x, fc_y, "ko--", linewidth=1.5, markersize=6, label="full_circuit / sum", zorder=5)

    ax.set_xticks(x)
    ax.set_xticklabels([param_label(k) for k in keys], fontsize=8)
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
