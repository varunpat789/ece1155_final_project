"""
Honeypot that can be used to observe and monitor incoming attacks. This honeypot can be used to compile attacker IP
addresses to train the machine learning model and to send to the restricted IP list.
"""

from typing import Any

from defense_layer.MLAttackDetector import MLAttackDetector
from network_layer.communication_bus import CommunicationBus
from network_layer.packet import Packet
from sim_layer.utils import convert_time


class Honeypot:
    FIRST_PACKET_TIME_SINCE_LAST = 999.0

    def __init__(
        self,
        env,
        name: str,
        bus: CommunicationBus,
        known_sources: set[str],
        ml_detector: MLAttackDetector,
    ):
        self.env = env
        self.name = name
        self.bus = bus
        self.known_sources = known_sources
        self.ml_detector = ml_detector
        self.captured_packets: list[Packet] = []
        self.capture_log: list[dict[str, Any]] = []
        self.source_packet_counts: dict[str, int] = {}
        self.last_seen_by_source: dict[str, float] = {}
        self.ml_predictions: list[dict[str, Any]] = []
        self._observed_packet_ids: set[int] = set()

    def run(self):
        while True:
            pkt = yield self.bus.receive(self.name)
            self.observe_packet(pkt)

    def observe_packet(self, pkt: Packet):
        packet_id = id(pkt)
        if packet_id in self._observed_packet_ids:
            return
        self._observed_packet_ids.add(packet_id)

        previous_time = self.last_seen_by_source.get(pkt.source)
        if previous_time is None:
            seconds_since_last_packet = self.FIRST_PACKET_TIME_SINCE_LAST
        else:
            seconds_since_last_packet = self.env.now - previous_time

        total_number_of_packets = self.source_packet_counts.get(pkt.source, 0) + 1
        known_source = pkt.source in self.known_sources

        self.last_seen_by_source[pkt.source] = self.env.now
        self.source_packet_counts[pkt.source] = total_number_of_packets
        self.captured_packets.append(pkt)

        prediction = self.ml_detector.accept_packet(
            packet=pkt,
            known_source=known_source,
            seconds_since_last_packet=seconds_since_last_packet,
            total_number_of_packets=total_number_of_packets,
        )

        self.capture_log.append(
            {
                "time": self.env.now,
                "source": pkt.source,
                "destination": pkt.destination,
                "known_source": known_source,
                "total_packets_from_source": total_number_of_packets,
                "time_since_last_packet": seconds_since_last_packet,
                "prediction": prediction,
                "data": dict(pkt.data),
            }
        )
        self.ml_predictions.append(
            {
                "time": self.env.now,
                "source": pkt.source,
                "prediction": prediction,
                "known_source": known_source,
                "total_packets_from_source": total_number_of_packets,
            }
        )

        if prediction == "attack":
            was_already_blacklisted = self.bus.is_blacklisted(pkt.source)
            self.bus.add_to_blacklist(pkt.source)
            if not was_already_blacklisted:
                print(f"[{convert_time(self.env.now)}] Honeypot blacklisted {pkt.source}")
