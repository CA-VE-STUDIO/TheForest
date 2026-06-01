import sys
sys.path.insert(0, "../src")

from sound_manager import Oscillator

from threading import Thread
from time import sleep
import time
import signal
import random

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from collections import deque

OSCILLATORS = 6

###############

def threaded_function(id, pulse_state, phase_state):
    phase = random.uniform(0.1, 0.9)
    o = Oscillator(id, phase_0=phase, phase_d=0.05, alpha=0.01)
    while True:
        o.step(pulse_state, phase_state)
        sleep(1)

def signal_handler(sig, frame):
    for i,t in threads:
        t.join()
    print('Exiting...')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

###############

# Parameters
window_seconds = 20      # visible x-axis range
max_points = 1000

# Data storage
times = deque(maxlen=max_points)
y1 = deque(maxlen=max_points)
y2 = deque(maxlen=max_points)
y3 = deque(maxlen=max_points)
y4 = deque(maxlen=max_points)
y5 = deque(maxlen=max_points)
y6 = deque(maxlen=max_points)

# Figure setup
fig, ax = plt.subplots()

line1, = ax.plot([], [], label="Signal 1")
line2, = ax.plot([], [], label="Signal 2")
line3, = ax.plot([], [], label="Signal 3")
line4, = ax.plot([], [], label="Signal 4")
line5, = ax.plot([], [], label="Signal 5")
line6, = ax.plot([], [], label="Signal 6")

ax.legend()
ax.set_xlabel("Time (s)")
ax.set_ylabel("Value")
ax.set_ylim([0,1.0])

start_time = time.time()

def update(frame):
    t = time.time() - start_time

    # Example data sources
    times.append(t)
    y1.append(phase_state[0])
    y2.append(phase_state[1])
    y3.append(phase_state[2])
    y4.append(phase_state[3])
    y5.append(phase_state[4])
    y6.append(phase_state[5])

    # Update line data
    line1.set_data(times, y1)
    line2.set_data(times, y2)
    line3.set_data(times, y3)
    line4.set_data(times, y4)
    line5.set_data(times, y5)
    line6.set_data(times, y6)

    # Scrolling x-axis
    xmin = max(0, t - window_seconds)
    xmax = xmin + window_seconds
    ax.set_xlim(xmin, xmax)

    # Autoscale y-axis to current data
    ax.relim()
    ax.autoscale_view(scalex=False, scaley=True)

    return line1, line2, line3

###############

threads = {}
pulse_state = {}
phase_state = {}

if __name__ == "__main__":
    
    for i in range(OSCILLATORS):
        pulse_state[i] = 0

    for i in range(OSCILLATORS):
        threads[i] = Thread(target = threaded_function, args = (i,pulse_state,phase_state,))
        threads[i].start()

    ani = FuncAnimation(
        fig,
        update,
        interval=50,      # milliseconds between updates
        blit=False,
        cache_frame_data=False
    )

    plt.show()

    # while True:
    #     try:
    #         print(phase_state, "\n")
    #     except KeyboardInterrupt:
    #         # for i,t in threads:
    #         #     t.join()

    #         print("Exiting...")
    #         sys.exit(0)
