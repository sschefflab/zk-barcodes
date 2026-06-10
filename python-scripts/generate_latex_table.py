import csv
import os
import statistics
from collections import defaultdict

CSV_PATH = os.path.join(os.path.dirname(__file__), "../zokrates/for-measurement/measurements.csv")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "../zokrates/for-measurement/benchmark_table.tex")

rows = [r for r in csv.DictReader(open(CSV_PATH)) if r["circuit"] == "full_circuit"]

# Build data keyed by (img, max_rows, max_cols, max_ec)
data = {}
for r in rows:
    img = r["image_cols"] + "x" + r["image_rows"]
    key = (img, r["max_rows"], r["max_cols"], r["max_ec_level"],
           r["chunk_size"], r["barcode_cols"] + "x" + r["barcode_rows"])
    data[key] = r

def sort_key(k):
    w, h = map(int, k[0].split("x"))
    return (w * h, int(k[1]) * int(k[2]), int(k[3]))

col_keys = sorted(data.keys(), key=sort_key)
n = len(col_keys)

def mean_se(vals):
    m = statistics.mean(vals)
    se = statistics.stdev(vals) / len(vals)**0.5
    return m, se

def fmt_time(r, prefix="prover"):
    vals = [float(r[f"{prefix}_time_{i}"]) for i in range(1, 6)]
    m = statistics.mean(vals)
    return rf"{m/1000:.2f}"

def fmt_ram(r):
    vals = [float(r[f"prover_ram_{i}"]) for i in range(1, 6)]
    m = statistics.mean(vals)
    return rf"{m/1e6:.2f}"

col_spec = "l" + "r" * n

lines = []
lines.append(r"\begin{table*}[tb]")
lines.append(r"\centering")
lines.append(r"\small")
lines.append(r"\setlength{\tabcolsep}{4pt}")
lines.append(rf"\begin{{tabular}}{{{col_spec}}}")
lines.append(r"\toprule")

# Column header: numbered
header = " & " + " & ".join(rf"\textbf{{{i+1}}}" for i in range(n)) + r" \\"
lines.append(header)
lines.append(r"\midrule")

# Param rows
def param_row(label, vals):
    return label + " & " + " & ".join(vals) + r" \\"

lines.append(param_row(r"\textrm{Image size}",         [k[0] for k in col_keys]))
lines.append(param_row(r"\textrm{Barcode size (px)}",  [k[5] for k in col_keys]))
lines.append(param_row(r"\textrm{Max barcode (logical)}", [rf"{k[1]}$\times${k[2]}" for k in col_keys]))
lines.append(param_row(r"\textrm{Max EC level}",       [k[3] for k in col_keys]))
lines.append(param_row(r"\textrm{Chunk size}",         [k[4] for k in col_keys]))
lines.append(r"\midrule")

# Data rows
lines.append(r"\textrm{Prover time (s)} & " + " & ".join(fmt_time(data[k]) for k in col_keys) + r" \\")
lines.append(r"\textrm{Prover RAM (GB)} & " + " & ".join(fmt_ram(data[k]) for k in col_keys) + r" \\")
lines.append(r"\textrm{Verifier time (s)} & " + " & ".join(fmt_time(data[k], "verifier") for k in col_keys) + r" \\")

lines.append(r"\bottomrule")
lines.append(r"\end{tabular}")
lines.append(
    r"\caption{full circuit benchmark results (mean over 5 runs)}"
)
lines.append(r"\label{tab:benchmark_full_circuit}")
lines.append(r"\end{table*}")

tex = "\n".join(lines)
with open(OUTPUT_PATH, "w") as f:
    f.write(tex)

print(f"Wrote {OUTPUT_PATH} ({n} columns)")
