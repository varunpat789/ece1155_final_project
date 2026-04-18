"""
Congestion generator that will infinitely send packets through the bus. This attacker should be moved to a honeypot
when discovered.
"""

import simpy
from network_layer.communication_bus import CommunicationBus
from network_layer.packet import Packet


class CongestionGenerator:
    def __init__(
        self,
        env: simpy.Environment,
        bus: CommunicationBus,
        attacker_ip: str = "0.0.0.0",
        target: str = "SCADA",
        interval: float = 0.1,
        start_time: float = 0.0,
        stop_time: float | None = None,
    ):
        self.env = env
        self.bus = bus
        self.attacker_ip = attacker_ip
        self.target = target
        self.interval = interval
        self.start_time = start_time
        self.stop_time = stop_time
        self.packets_sent = 0

    def run(self):
        if self.env.now < self.start_time:
            yield self.env.timeout(self.start_time - self.env.now)

        while self.stop_time is None or self.env.now < self.stop_time:
            self.packets_sent += 1
            pkt = Packet(
                source=self.attacker_ip,
                destination=self.target,
                timestamp=self.env.now,
                size=64,
                data={"type": "fake_request", "protocol": "DNP3_SIM"},
            )
            self.bus.send(pkt)
            yield self.env.timeout(self.interval)
