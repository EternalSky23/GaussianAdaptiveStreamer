import re
import matplotlib.pyplot as plt

def iperf_parse(fp):
    results = []
    times = []
    r = re.compile(r"[0-9]+\.[0-9]+ [A-Za-z]?bits/sec", re.IGNORECASE)
    r2 = re.compile(r"[0-9]+\.[0-9]+-")
    for line in fp:
        line = line.strip()
        if "- -" in line:
            break
        if not "/sec" in line:
            continue
        
        obj = r.search(line).group(0).split()
        rate = float(obj[0])
        if "M" in obj[1]:
            rate *= 1000
        elif "K" not in obj[1]:
            rate /= 1000

        time = float(r2.search(line).group(0)[:-1])
        results.append(rate)
        times.append(time)

    return [times, results]

def streamer_parse(fp):
    results = []
    r = re.compile(r"[0-9]+[\.]?[0-9]*[\sA-Za-z]*B/s")
    
    for line in fp:
        result = r.search(line).group(0)[:-3].strip()
        if result[-1] == 'i': # To Kbps
            if result[-2] == 'M':
                results.append(float(result[:-2]) * 8388.608)
            elif result[-2] == 'K':
                results.append(float(result[:-2]) * 8.192)
            else:
                results.append(float(result[:-2]) * 0.008)
    
    time = [i for i in range(len(results))]
    return [time, results]

if __name__ == "__main__":
    baseline_log = open("exp_log/train/baseline/baseline1.txt", "r")
    tigas_log = open("exp_log/train/tigas/output1.txt", "r")

    streamer_results = streamer_parse(tigas_log)
    baseline_results = iperf_parse(baseline_log)
    
    plt.plot(streamer_results[0], streamer_results[1], label="Streamer")
    plt.plot(baseline_results[0], baseline_results[1], label="Baseline")
    plt.xlabel("Time (sec)")
    plt.ylabel("Throughput (Kbps)")
    plt.legend()
    plt.savefig("throughput.png")