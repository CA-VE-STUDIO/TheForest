import serial
import atexit
import threading
import queue
import time
import copy

import argparse
import json
import os


# from MappingInterface import  MappingInterface

class SerialManager():

    def __init__(self, id, port, baud_rate=9600, **kwargs):
        self.id = id

        self.serial_read_rate = 10
        self.data_queue = queue.Queue()
        self.write_queue = queue.Queue()

        self.kill_read_thread = threading.Event()

        self.ser = None
        self.serial_status = dict(connected=False, port=port, baud_rate=baud_rate)
        self.ser = self.restart_serial(port, baud_rate)

        atexit.register(self.cleanup)

        # Add lock for thread safety
        self.status_lock = threading.Lock()

    def restart_serial(self, port, baud_rate=None):
        if self.ser:
            self.cleanup()
            self.write_queue.put("kill")
            self.kill_read_thread.set()

        if baud_rate is None:
            baud_rate = self.serial_status["baud_rate"]

        self.serial_status["port"] = port
        self.serial_status["baud_rate"] = baud_rate

        try:
            self.ser = serial.Serial(port, baud_rate)
            self.serial_status["connected"] = True
        except serial.SerialException:
            # Generate a virtual serial port for testing
            print(f"!!!!!!!!!!!!!!!!!!!!!!!! SERIAL PORT: {port} NOT FOUND !!!!!!!!!!!!!!!!!!!!!")
            print(f"!!!!!!!!!!!!!!!!!!!!!!!! SERIAL PORT: {port} NOT FOUND !!!!!!!!!!!!!!!!!!!!!")
            print(f"!!!!!!!!!!!!!!!!!!!!!!!! SERIAL PORT: {port} NOT FOUND !!!!!!!!!!!!!!!!!!!!!")
            print(f"!!!!!!!!!!!!!!!!!!!!!!!! SERIAL PORT: {port} NOT FOUND !!!!!!!!!!!!!!!!!!!!!")
            print(f"!!!!!!!!!!!!!!!!!!!!!!!! SERIAL PORT: {port} NOT FOUND !!!!!!!!!!!!!!!!!!!!!")
            print(f"... creating virtual serial port for testing")
            self.ser = serial.serial_for_url(f"loop://{port}", baudrate=baud_rate)
            self.serial_status["connected"] = False

        self.kill_read_thread = threading.Event()
        self.serial_thread = threading.Thread(
            target=self.read_serial_data,
            args=(self.ser, self.data_queue, self.kill_read_thread),
        )
        self.serial_thread.daemon = True
        self.serial_thread.start()

        self.serial_write_thread = threading.Thread(target=self.write_serial_data, args=(self.ser, self.write_queue,))
        self.serial_write_thread.daemon = True
        self.serial_write_thread.start()

        print(f"Restarted Serial Connection to {port}, {baud_rate}")
        return self.ser

    def cleanup(self):
        print(f"Cleaning up and closing the serial connection for pillar {self.id}")
        if self.ser.is_open:
            self.ser.close()

    def to_dict(self):
        return dict(
            id=self.id, num_tubes=self.num_tubes, num_sensors=self.num_touch_sensors,
            touch_status=self.touch_status, light_status=self.light_status, serial_status=self.serial_status
        )

    def clamp(self, val, b=0, c=255):
        return max(b, min(val, c))

    def read_serial_data(self, serial_port, data_queue, kill_event):
        # This needs implementation in child classes
        return

    def write_serial_data(self, serial_port, write_queue):
        print(f"Serial Write Thread Started With {serial_port}")
        while True:
            try:
                packet = write_queue.get()

                if "kill" in packet:
                    # Method of killing the packet
                    break

                # print("Packet Sending", packet)
                serial_port.write(packet.encode())
            except Exception as e:
                print(f"Error writing data: {e}")
            time.sleep(0.1)

        print("Serial Write Thread Killed")

class Pillar(SerialManager):

    def __init__(self, id, port, baud_rate=9600, **kwargs):

        self.num_tubes = kwargs.get("num_tubes", 6)
        self.num_touch_sensors = kwargs.get("num_tubes", 6)
        self.touch_status = [False for _ in range(self.num_touch_sensors)]
        self.previous_received_status = []

        self.light_status = [(0, 0, 0) for _ in range(self.num_tubes)]

        super().__init__(id, port, baud_rate, **kwargs)

    def get_touch_status(self, tube_id):
        return self.touch_status[tube_id]

    def get_all_touch_status(self):
        return self.touch_status

    # def get_light_status(self, tube_id):
    #     return self.light_status[tube_id]

    def set_touch_status(self, touch_status):
        # Do the filter here
        
        self.touch_status = touch_status #[:-1]
        # print(f"UPDATING TOUCH STATUS to: {touch_status}")

    def set_touch_status_tube(self, tube_id, status):
        self.touch_status[tube_id] = bool(status)

    def read_serial_data(self, serial_port, data_queue, kill_event):
        print(f"Serial Read Thread Started With {serial_port}")
        while True:
            try:

                if kill_event.is_set():
                    break

                response = serial_port.readline().decode().strip()
                # print("RECEIVEDDDDD", response)
                if response.startswith("CAP,") or response.startswith("BUTTONS:"):
                    if response.startswith("CAP,"):
                        payload = response.split(",", 1)[1]
                    else:
                        payload = response.split(":", 1)[1]

                    status = [token.strip().rstrip(";") for token in payload.split(",") if token.strip()]
                    try:
                        parsed = [bool(int(i)) for i in status]
                        # print(f"[SERIAL][BUTTONS] raw='{response}' parsed={parsed}")
                        data_queue.put(parsed)
                    except ValueError:
                        print(f"[WARNING] Could not parse button payload: {response}")

            except Exception as e:
                pass
                # print(f"Error reading data: {e}")

        print("Serial Read Thread Killed")

    def read_from_serial_queue(self):
        # Handle touch sensor data
        try:
            while not self.data_queue.empty():
                received_status = self.data_queue.get_nowait()

                # Ensure received_status has the correct length
                if len(received_status) != self.num_touch_sensors:
                    print(
                        f"[WARNING] Received touch status has {len(received_status)} sensors, expected {self.num_touch_sensors}")
                    # Pad with False if too short
                    if len(received_status) < self.num_touch_sensors:
                        received_status.extend([False] * (self.num_touch_sensors - len(received_status)))
                    # Truncate if too long
                    if len(received_status) > self.num_touch_sensors:
                        received_status = received_status[:self.num_touch_sensors]

                # Get a thread-safe copy of the previous status
                with self.status_lock:
                    previous_status = self.previous_received_status.copy() if self.previous_received_status else []

                # Only update and print if status changed
                if received_status != previous_status:
                    # print(f"[TOUCH] Processing touch status: {received_status}")
                    self.set_touch_status(received_status)
                    # Thread-safe update of previous status
                    with self.status_lock:
                        self.previous_received_status = received_status.copy()
                    # Handle end of touch event
                    self.handle_end_of_touch(received_status)
        except queue.Empty:
            pass
        except Exception as e:
            print(f"[ERROR] Error processing touch data: {e}")

    def reset_touch_status(self):
        self.touch_status = [0 for _ in range(self.num_touch_sensors)]

    def handle_end_of_touch(self, received_status):
        if all(status == 0 for status in received_status):  # All touch sensors are inactive
            self.reset_touch_status()
            # Function to send a WebSocket message to frontend
            self.notify_frontend_touch_reset()

    def notify_frontend_touch_reset(self):
        reset_message = json.dumps({"type": "touch_reset", "pillar_id": self.id})
        # Placeholder for actual WebSocket sending logic
        # send_to_all_clients(reset_message)  # You need to implement this based on your WebSocket setup
        

# Reads from serial port: format is {id:value}
class Tentacle(SerialManager):

    def __init__(self, id, port, baud_rate=9600, **kwargs):

        self.num_tentacles = kwargs.get("num_tentacles", 5)
        self.msg_len = kwargs.get("msg_len", 9)
        self.tentacle_status = [0 for _ in range(self.num_tentacles)]

        super().__init__(id, port, baud_rate, **kwargs)

    def read_serial_data(self, serial_port, data_queue, kill_event):
        print(f"Serial Read Thread Started With {serial_port}")
        while True:
            try:
                if kill_event.is_set():
                    break

                response = serial_port.read(self.msg_len).decode().strip()
                r_ = response.split(':')
                tid = int(r_[0])
                val = int(r_[1])
                self.tentacle_status[tid] = val
                # print(">>>>>>>>>>>>> ", tid, val)
                
                # data_queue.put(self.tentacle_status)

            except Exception as e:
                pass
                # print(f"Error reading data: {e}")

        print("Serial Read Thread Killed")

    def get_all_tentacle_status(self):
        return self.tentacle_status

    # def read_from_serial_queue(self):
    #     # Read and parse esp32 data
    #     try:
    #         while not self.data_queue.empty():
    #             data = self.data_queue.get_nowait()
    #             print("[TENTACLE STATUS] ", data)

    #             if len(data) != self.num_tentacles:
    #                 pass

                # # Get a thread-safe copy of the previous status
                # with self.status_lock:
                #     previous_status = self.previous_received_status.copy() if self.previous_received_status else []

                # # Only update and print if status changed
                # if received_status != previous_status:
                #     # print(f"[TOUCH] Processing touch status: {received_status}")
                #     self.set_touch_status(received_status)
                #     # Thread-safe update of previous status
                #     with self.status_lock:
                #         self.previous_received_status = received_status.copy()
                #     # Handle end of touch event
                #     self.handle_end_of_touch(received_status)
        # except queue.Empty:
        #     pass
        # except Exception as e:
        #     print(f"[ERROR] Error processing touch data: {e}")