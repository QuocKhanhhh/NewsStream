import unittest
from unittest.mock import patch


class ConfigTests(unittest.TestCase):
    def test_defaults_are_available(self):
        from src import config

        self.assertEqual(config.KAFKA_TOPIC, "rss_news")
        self.assertEqual(config.REDIS_PORT, 6379)
        self.assertEqual(config.REDIS_DB, 0)

    def test_environment_overrides_are_read_on_import(self):
        with patch.dict(
            "os.environ",
            {"KAFKA_TOPIC": "test-topic", "REDIS_PORT": "6380"},
            clear=False,
        ):
            import importlib
            from src import config

            reloaded = importlib.reload(config)
            self.assertEqual(reloaded.KAFKA_TOPIC, "test-topic")
            self.assertEqual(reloaded.REDIS_PORT, 6380)


if __name__ == "__main__":
    unittest.main()
