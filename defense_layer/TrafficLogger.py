"""
Traffic Logger class that records every packet seen by SCADA, honeypots, and bus.
"""

class TrafficLogger:
    def __init__(self):
        self.records = []

    def log_packet(self, packet, current_time, label="unknown"):
        self.records.append({
            "timestamp": current_time,
            "source": packet.source,
            "destination": packet.destination,
            "size": packet.size,
            "message_type": packet.data.get("type", "unknown"),
            "label": label,
        })
