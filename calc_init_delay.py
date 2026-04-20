import matplotlib.pyplot as plt
from scripts.plot_pred_bps import load_ndjson
import re
import numpy as np
from statistics import fmean, stdev

name_mapping = {
    "train": "Train",
    "drjohnson": "Dr Johnson",
    "room": "Room",
    "playroom": "Playroom"
}

def plotGroupBarChart(results: dict, label_value: list, xlabel: str, ylabel: str, filename: str):
    x = np.arange(len(label_value))  # the label locations
    width = 0.35  # the width of the bars
    multiplier = 0
    fig, ax = plt.subplots(layout='constrained')

    multiplier += 0.5
    for name, delays in results.items():
        offset = width * multiplier
        rects = ax.bar(x + offset, delays, width, label=name)
        ax.bar_label(rects, padding=2)
        multiplier += 1

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_xticks(x + width, label_value)
    ax.legend(loc="upper center", ncols=2, bbox_to_anchor=(0.7, 1.1))

    plt.yscale("log")
    plt.savefig(filename)
    plt.clf()

def plotGroupBarChartWithError(results: dict, std: dict, label_value: list, xlabel: str, ylabel: str, filename: str):
    x = np.arange(len(label_value))  # the label locations
    width = 0.25  # the width of the bars
    multiplier = 0
    fig, ax = plt.subplots(layout='constrained')

    multiplier += 0.5
    for name, delays in results.items():
        offset = width * multiplier
        rects = ax.bar(x + offset, delays, width, label=name)
        ax.bar_label(rects, padding=2, fmt="{:.3f}")
        multiplier += 1

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_xticks(x + width, [name_mapping[i] for i in label_value])
    ax.legend(loc="upper center", ncols=2, bbox_to_anchor=(0.7, 1.1))

    plt.yscale("log")
    plt.savefig(filename)
    plt.clf()

def calc_delay(scene: str):
    N = 6

    tigas = []
    baseline = []
    # TIGAS
    for i in range(1, N+1):
        f = open(f"experiment/{scene}_{i}/simple_run_1/testdata.ndjson")
        first_obj = load_ndjson(f)[0]
        tigas.append((first_obj['endTime'] - first_obj['beginTime']) / 1000)
        f.close()

    # Baseline
    for i in range(1, N+1):
        f = open(f"exp_log/{scene}/baseline/baseline{i}.txt")
        result_flag = False
        for line in f:
            line = line.strip()
            if not line: continue

            if line[0] != '-' and not result_flag:
                continue
            else: 
                result_flag = True

            if line[-8:] == "receiver": # Here we get the total time as delay
                r = re.compile(r"-[0-9]+[\.]?[0-9]*")
                match = r.search(line).group(0)[1:]
                baseline.append(float(match))

    return tigas, baseline

def average(array: list):
    return sum(array) / len(array)

if __name__ == "__main__":
    tigas, baseline = calc_delay("train")
    plotGroupBarChart({"TIGAS": tigas, "Baseline": baseline}, [i+1 for i in range(6)],
                    "Camera Trajectories", "Initial Delay (sec)", "init_delay")
    
    scenes = ["train", "playroom", "room", "drjohnson"]
    results = {}
    
    mean = {"TIGAS": [], "Baseline": []}
    std = {"TIGAS": [], "Baseline": []}
    for scene in scenes:
        delay_tigas, delay_baseline = calc_delay(scene)
        tigas_avg, baseline_avg = fmean(delay_tigas), fmean(delay_baseline)
        tigas_std, baseline_std = stdev(delay_tigas), stdev(delay_baseline)

        mean["TIGAS"].append(tigas_avg)
        mean["Baseline"].append(baseline_avg)
        std["TIGAS"].append(tigas_std)
        std["Baseline"].append(baseline_std)

    plotGroupBarChartWithError(mean, std, scenes, "Scenes", "Average Initial Delay (sec)", "scenes_delay.png")