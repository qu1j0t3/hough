import csv
import math

import numpy as np
import termplotlib as tpl


def histogram(results_file):
    with open("results.csv", newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        res = []
        for row in reader:
            if row["Computed angle"]:
                res.append(abs(float(row["Computed angle"])))
    counts, bin_edges = np.histogram(res, bins=20, range=(0, int(math.ceil(max(res)))))

    labels = [
        "{:.2f}° - {:.2f}°".format(bin_edges[k], bin_edges[k + 1])
        for k in range(len(bin_edges) - 1)
    ]
    fig = tpl.figure()
    fig.barh(
        counts,
        labels=labels,
        max_width=40,
        bar_width=1,
        show_vals=True,
        force_ascii=False,
    )

    print("\n=== Skew statistics ===")
    fig.show()

    print(f"Samples: {len(res)}")
    print(f"50th percentile: {np.percentile(res, 50):1.2f}°")
    print(f"90th percentile: {np.percentile(res, 90):1.2f}°")
    print(f"99th percentile: {np.percentile(res, 99):1.2f}°")
