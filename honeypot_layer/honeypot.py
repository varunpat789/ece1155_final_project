"""
Honeypot that can be used to observe and monitor incoming attacks. This honeypot can be used to compile attacker IP
addresses to train the machine learning model and to send to the restricted IP list.
"""

from sim_layer.utils import convert_time

class Honeypot:
    def __init__(self, env, name, bus):
        self.env = env
        self.name = name
        self.bus = bus
        self.captured_packets = []

    def run(self):
        while True:
            pkt = yield self.bus.receive(self.name)
            self.captured_packets.append(pkt)
            print(f"[{convert_time(self.env.now)}] Honeypot captured packet from {pkt.source}: {pkt.data}")
