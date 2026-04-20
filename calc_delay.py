import matplotlib.pyplot as plt
import numpy as np
from statistics import fmean, stdev

from scripts.plot_pred_bps import load_ndjson

ABRS = ["Simple", "L2A", "LoL+"]

def getAbrsInitDelay(exp_name: str):
    result = {}

    for abr in ABRS:
        f = open(f"experiment/{exp_name}/{abr.lower()}_run_1/testdata.ndjson")
        first_obj = load_ndjson(f)[0]
        result[abr] = first_obj['endTime'] - first_obj['beginTime']
        f.close()

    return result

def plotGroupBarChart(results: dict, label_value: list, xlabel: str, ylabel: str, filename: str, fmt="{:.2f}"):
    x = np.arange(len(label_value))  # the label locations
    width = 0.26  # the width of the bars
    multiplier = 0
    fig, ax = plt.subplots(layout='constrained')

    for abr, delays in results.items():
        offset = width * multiplier
        if abr == "Simple": abr = "Latency (Ours)"
        rects = ax.bar(x + offset, delays, width, label=abr)
        ax.bar_label(rects, padding=3, fmt=fmt)
        multiplier += 1

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_xticks(x + width, label_value)
    ax.legend(loc='upper center', ncols=3, bbox_to_anchor=(0.7, 1.1))

    plt.savefig(filename)
    plt.clf()


def getAbrsResponseTime(exp_name: str):
    result = {}

    for abr in ABRS:
        f = open(f"experiment/{exp_name}/{abr.lower()}_run_1/testdata.ndjson")
        objs = load_ndjson(f)
        result[abr] = []

        for obj in objs:
            result[abr].append(obj['endTime'] - obj['beginTime'])

    return result

def plotMetrics(results: dict, xlabel: str, ylabel: str, filename="img.png"):
    for abr, result in results.items():
        if abr == "Simple": abr = "Latency"
        plt.plot([i for i in range(len(result))], result, label=abr, linewidth=0.7)

    plt.legend()
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.savefig(filename)
    plt.clf()

def getProfileMetrics(exp_name: str):
    result = {}

    for abr in ABRS:
        f = open(f"experiment/{exp_name}/{abr.lower()}_run_1/testdata.ndjson")
        objs = load_ndjson(f)
        result[abr] = []

        for obj in objs:
            result[abr].append(obj['profile'])

    return result

def getProfileChanges(exp_name: str):
    result = {}

    for abr in ABRS:
        f = open(f"experiment/{exp_name}/{abr.lower()}_run_1/testdata.ndjson")
        objs = load_ndjson(f)

        prev = -1
        changes = -1
        for obj in objs:
            currentProfile = obj['profile']
            if currentProfile != prev: 
                changes += 1
                prev = currentProfile
                
        result[abr] = changes
    
    return result

def main(exp_names: list, label_value: list, xlabel: str):
    assert len(exp_names) == len(label_value)

    # results = {"Simple": [], "L2A": [], "LoL+": []}
    # for exp_name in exp_names:
    #     result = getAbrsInitDelay(exp_name)
    #     for abr in ABRS:
    #         results[abr].append(result[abr])

    # plotInitDelay(results, label_value)

    results_avg_restime = {"Simple": [], "L2A": [], "LoL+": []}
    for i in range(len(exp_names)):
        results = getAbrsResponseTime(exp_names[i])
        plotMetrics(results, "Frame", "Response Time (ms)", f"{label_value[i]}.png")
        for abr, values in results.items():
            results_avg_restime[abr].append(average(values))
    plotGroupBarChart(results_avg_restime, label_value, xlabel, 'Average Response Time (ms)', 'avg_response.png')

    results_avg_abr = {"Simple": [], "L2A": [], "LoL+": []}
    for i in range(len(exp_names)):
        results = getProfileMetrics(exp_names[i])
        # plotMetrics(results, "Frame", "Profile Level", f"{label_value[i]}_profile.png")
        for abr, values in results.items():
            results_avg_abr[abr].append(average(values))
    plotGroupBarChart(results_avg_abr, label_value, xlabel, 'Average Profile Quality Level', 'avg_profile.png')

    changes = {"Simple": [], "L2A": [], "LoL+": []}
    for i in range(len(exp_names)):
        results = getProfileChanges(exp_names[i])
        for abr, values in results.items():
            changes[abr].append(values)
    plotGroupBarChart(changes, label_value, xlabel, 'Total Profile Changes', 'change_profile.png', fmt="%d")

    return results_avg_restime, results_avg_abr, changes

def average(array: list):
    return sum(array) / len(array)

def plotGroupBarChartWithError(results: dict, std: dict, label_value: list, xlabel: str, ylabel: str, filename: str):
    x = np.arange(len(label_value))  # the label locations
    width = 0.25  # the width of the bars
    multiplier = 0
    fig, ax = plt.subplots(layout='constrained')

    multiplier += 0.5
    for name, delays in results.items():
        offset = width * multiplier
        rects = ax.bar(x + offset, delays, width, label=name)
        ax.bar_label(rects, padding=2, fmt="{:.1f}")
        multiplier += 1

    # plot std as error bar
    multiplier = 0.5
    for name, errors in std.items():
        offset = width * multiplier
        ax.errorbar(x + offset, results[name], yerr=errors, fmt='none', ecolor='black', capsize=5)
        multiplier += 1

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_xticks(x + width, [i for i in label_value])
    ax.legend(loc="upper center", ncols=3, bbox_to_anchor=(0.7, 1.1))

    plt.savefig(filename)
    plt.clf()

if __name__ == "__main__":
    scene_name = "train"
    # user_id = 1

    # main([f"{scene_name}/{name}" for name in exp_names], label_value, "Loss Rate")

    all_restime, all_abr, all_change = {"Simple": [], "L2A": [], "LoL+": []}, {"Simple": [], "L2A": [], "LoL+": []}, {"Simple": [], "L2A": [], "LoL+": []}
    for user_id in range(1, 5):
        exp_names = [f"user{user_id}_20ms", f"user{user_id}_20ms_0.01%", f"user{user_id}_20ms_0.05%", 
                     f"user{user_id}_20ms_0.1%", f"user{user_id}_20ms_1%"]
        label_value = ["0%", "0.01%", "0.05%", "0.1%", "1%"]

        # exp_names = [f"user{user_id}_5ms", f"user{user_id}_10ms", f"user{user_id}_20ms", 
        #             f"user{user_id}_40ms", f"user{user_id}_80ms"]
        # label_value = ["5ms", "10ms", "20ms", "40ms", "80ms"]

        restime, abr, change = main([f"{scene_name}/{name}" for name in exp_names], label_value, "Loss Rate")
        for abr_algo in ["Simple", "L2A", "LoL+"]:
            all_restime[abr_algo].append(restime[abr_algo])
            all_abr[abr_algo].append(abr[abr_algo])
            all_change[abr_algo].append(change[abr_algo])

    # calc mean and std
    restime_mean, restime_std = {}, {}
    abr_mean, abr_std = {}, {}
    change_mean, change_std = {}, {}
    # only calculate one axis since the x-axis is the same for all
    for abr_algo in ["Simple", "L2A", "LoL+"]:
        restime_mean[abr_algo] = [average(x) for x in zip(*all_restime[abr_algo])]
        restime_std[abr_algo] = [stdev(x) for x in zip(*all_restime[abr_algo])]
        abr_mean[abr_algo] = [average(x) for x in zip(*all_abr[abr_algo])]
        abr_std[abr_algo] = [stdev(x) for x in zip(*all_abr[abr_algo])]
        change_mean[abr_algo] = [average(x) for x in zip(*all_change[abr_algo])]
        change_std[abr_algo] = [stdev(x) for x in zip(*all_change[abr_algo])]
    # print("restime_mean:", restime_mean)
    # print("restime_std:", restime_std)
    # print("abr_mean:", abr_mean)
    # print("abr_std:", abr_std)
    # print("change_mean:", change_mean)
    # print("change_std:", change_std)

    plotGroupBarChartWithError(restime_mean, restime_std, label_value, "Loss Rate", "Average Response Time (ms)", "avg_response_error.png")
    plotGroupBarChartWithError(abr_mean, abr_std, label_value, "Loss Rate", "Average Profile Quality Level", "avg_profile_error.png")
    plotGroupBarChartWithError(change_mean, change_std, label_value, "Loss Rate", "Total Profile Changes", "change_profile_error.png")