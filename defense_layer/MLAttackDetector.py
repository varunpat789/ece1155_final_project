"""
Attack predictor class with the goal of identifying threats with machine learning.
"""

class MLAttackDetector:
    def predict(self, features):
        if features["is_honeypot_hit"]:
            return "attack"

        if not features["is_known_source"] and features["time_since_last_packet"] < 1:
            return "attack"

        if features["total_packets_from_source"] > 50:
            return "suspicious"

        return "normal"
