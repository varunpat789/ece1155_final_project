"""
Congestion generator that will infinitely send packets through the bus. This attacker should be moved to a honeypot
when discovered.
"""

from network_layer.packet import Packet

class CongestionGenerator:
    def __init__(self, env, bus, attacker_ip="0.0.0.0", target="SCADA", interval=0.1):
        self.env = env
        self.bus = bus
        self.attacker_ip = attacker_ip
        self.target = target
        self.interval = interval

    def run(self):
        while True:
            pkt = Packet(
                source=self.attacker_ip,
                destination=self.target,
                timestamp=self.env.now,
                size=64,
                data={"type": "fake_request", "protocol": "DNP3_SIM"},
            )
            self.bus.send(pkt)
            yield self.env.timeout(self.interval)
