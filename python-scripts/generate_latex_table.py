# Generate a latex table of full circuit benchmarks.

import csv
import os
import statistics

CSV_PATH = os.path.join(os.path.dirname(__file__), "../measurements/measurements.csv")
OUTPUT_PATH = os.path.join(
    os.path.dirname(__file__), "../measurements/benchmark_table.tex"
)

rows = [r for r in csv.DictReader(open(CSV_PATH)) if r["circuit"] == "full_circuit"]

# Build data keyed by (img, max_rows, max_cols, max_ec, chunk_size, barcode_px)
data = {}
for r in rows:
    img = r["image_cols"] + "x" + r["image_rows"]
    key = (
        img,
        r["max_rows"],
        r["max_cols"],
        r["max_ec_level"],
        r["chunk_size"],
        r["barcode_cols"] + "x" + r["barcode_rows"],
    )
    data[key] = r


def sort_key(k):
    w, h = map(int, k[0].split("x"))
    return (w * h, int(k[1]) * int(k[2]), int(k[3]))


config_keys = sorted(data.keys(), key=sort_key)
n = len(config_keys)


def fmt_time(r, prefix="prover"):
    vals = [float(r[f"{prefix}_time_{i}"]) for i in range(1, 6)]
    return rf"{statistics.mean(vals) / 1000:.2f}"


def fmt_ram(r):
    vals = [float(r[f"prover_ram_{i}"]) for i in range(1, 6)]
    return rf"{statistics.mean(vals) / 1e6:.2f}"


def rot(text):
    return rf"\rotatebox{{90}}{{\parbox{{0.7cm}}{{\tiny\centering\textbf{{{text}}}}}}}"

# Columns: params + 3 metrics, all centered so narrow rotated headers fit
col_spec = "c" * 5 + "|" + "c" * 3
HEADER = (
    " & ".join([
        rot("Image"),
        rot("Barcode (px)"),
        rot("Max barcode (logical)"),
        rot("Max EC level"),
        rot("Chunk size"),
        rot("Prover time (s)"),
        rot("Prover RAM (GB)"),
        rot("Verifier time (s)"),
    ]) + r" \\"
)

lines = []
lines.append(r"\begin{table}[tb]")
lines.append(r"\caption{full circuit benchmark results (mean over 5 runs)}")
lines.append(r"\label{tab:benchmark_full_circuit}")
lines.append(r"\centering")
lines.append(r"\setlength{\tabcolsep}{4pt}")
lines.append(rf"\begin{{tabular}}{{{col_spec}}}")
lines.append(r"\toprule")
lines.append(HEADER)
lines.append(r"\midrule")

for k in config_keys:
    r = data[k]
    img, max_r, max_c, max_e, chunk, barcode_px = k
    cells = [
        img,
        barcode_px,
        rf"{max_r}$\times${max_c}",
        max_e,
        chunk,
        fmt_time(r),
        fmt_ram(r),
        fmt_time(r, "verifier"),
    ]
    lines.append(" & ".join(cells) + r" \\")

lines.append(r"\bottomrule")
lines.append(r"\end{tabular}")
lines.append(r"\end{table}")

tex = "\n".join(lines)
with open(OUTPUT_PATH, "w") as f:
    f.write(tex)

print(f"Wrote {OUTPUT_PATH} ({n} rows)")
