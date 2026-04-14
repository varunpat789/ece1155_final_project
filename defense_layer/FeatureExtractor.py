"""
A feature extractor class with the purpose of converting raw packets into ML-friendly values.
"""

class FeatureExtractor:
    def __init__(self, known_sources, honeypot_names):
        self.known_sources = known_sources
        self.honeypot_names = honeypot_names
        self.last_seen = {}
        self.source_counts = {}

    def extract(self, packet, current_time):
        previous_time = self.last_seen.get(packet.source)
        time_since_last = 999 if previous_time is None else current_time - previous_time

        self.last_seen[packet.source] = current_time
        self.source_counts[packet.source] = self.source_counts.get(packet.source, 0) + 1

        return {
            "timestamp": current_time,
            "source": packet.source,
            "destination": packet.destination,
            "size": packet.size,
            "message_type": packet.data.get("type", "unknown"),
            "is_known_source": int(packet.source in self.known_sources),
            "is_honeypot_hit": int(packet.destination in self.honeypot_names),
            "time_since_last_packet": time_since_last,
            "total_packets_from_source": self.source_counts[packet.source],
        }
