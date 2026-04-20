from scripts.plot_pred_bps import load_ndjson
import matplotlib.pyplot as plt

if __name__ == "__main__":
    f_streamer = open("experiment/circ/simple_run_1/testdata.ndjson")
    obj = load_ndjson(f_streamer)
    
    t_0 = obj[0]['beginTime']
    count = 0
    t = 1000
    framerates = []
    for i in obj:
        delta = i['beginTime'] - t_0
        if delta < t:
            count += 1
        else:
            framerates.append(count)
            count = 1
            t += 1000 # in ms
    
    plt.plot([i for i in range(len(framerates))], framerates, label="Streamer")
    plt.xlabel("Time (sec)")
    plt.ylabel("Framerate (FPS)")
    plt.legend()
    plt.savefig("framerate.png")