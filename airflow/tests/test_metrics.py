import unittest
from src.metrics import FeedMetrics


class FeedMetricsTests(unittest.TestCase):
    def test_metrics_are_serializable(self):
        metrics = FeedMetrics(source="en_0", items_read=4, items_valid=3)
        self.assertEqual(metrics.as_dict()["items_valid"], 3)
        self.assertIsNone(metrics.as_dict()["error"])
