"""
Attack predictor class with the goal of identifying threats with machine learning.
"""

from typing import Any
from network_layer.packet import Packet


class MLAttackDetector:
    def __init__(self):
        self.records: list[dict[str, Any]] = []

    def predict(self, features: dict[str, Any]) -> str:
        if not features["is_known_source"] and features["total_packets_from_source"] > 250:
            return "attack"

        return "normal"

    def accept_packet(
        self,
        packet: Packet,
        known_source: bool,
        seconds_since_last_packet: float,
        total_number_of_packets: int,
    ) -> str:
        features: dict[str, Any] = {
            "is_known_source": known_source,
            "total_packets_from_source": total_number_of_packets,
            "time_since_last_packet": seconds_since_last_packet,
            "original_packet": packet,
            "is_honeypot_hit": False,
        }
        prediction = self.predict(features)
        self.records.append({**features, "prediction": prediction})
        return prediction
