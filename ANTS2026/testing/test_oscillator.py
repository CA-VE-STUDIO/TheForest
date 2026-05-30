import sys
sys.path.insert(0, "../src")

from sound_manager import Oscillator

from threading import Thread
from time import sleep
import signal
import random

OSCILLATORS = 6

###############

def threaded_function(id, pulse_state):
    a = random.uniform(0.1, 1.0)
    o = Oscillator(id, activation=a, activation_incr=0.05)
    while True:
        o.step(pulse_state)
        sleep(1)

def signal_handler(sig, frame):
    for i,t in threads:
        t.join()
    print('Exiting...')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

###############

if __name__ == "__main__":
    
    pulse_state = {}
    for i in range(OSCILLATORS):
        pulse_state[i] = 0

    threads = {}
    for i in range(OSCILLATORS):
        threads[i] = Thread(target = threaded_function, args = (i,pulse_state,))
        threads[i].start()

    # while True:
    #     try:
    #         continue
    #     except KeyboardInterrupt:
    #         for i,t in threads:
    #             t.join()

    #         print("Exiting...")
    #         sys.exit()