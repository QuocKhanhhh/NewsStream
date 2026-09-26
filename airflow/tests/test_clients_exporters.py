import json
import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from src.clients.kafka_client import KafkaClient
from src.clients.redis_client import RedisClient
from src.exporters.kafka_exporter import ExportError, KafkaExporter
from src.models.news import News


class ClientTests(unittest.TestCase):
    @patch("src.clients.kafka_client.KafkaProducer")
    def test_kafka_client_serializes_and_publishes(self, producer_cls):
        producer = producer_cls.return_value
        producer.send.return_value.get.return_value = "metadata"
        client = KafkaClient(["kafka:9092"])
        self.assertEqual(client.publish("topic", {"x": "é"}, key="id"), "metadata")
        args, kwargs = producer.send.call_args
        self.assertEqual(args[0], "topic")
        self.assertEqual(kwargs["value"], {"x": "é"})
        self.assertEqual(kwargs["key"], b"id")
        client.flush()
        client.close()

    @patch("src.clients.redis_client.redis.Redis")
    def test_redis_client_replaces_and_reads_json(self, redis_cls):
        client = RedisClient()
        redis = redis_cls.return_value
        pipe = redis.pipeline.return_value.__enter__.return_value
        client.replace_list("proxies", [{"http": "http://p"}])
        pipe.delete.assert_called_once_with("proxies")
        pipe.rpush.assert_called_once_with("proxies", json.dumps({"http": "http://p"}))
        pipe.execute.assert_called_once_with()
        redis.lindex.return_value = json.dumps({"http": "http://p"})
        self.assertEqual(client.get_first("proxies"), {"http": "http://p"})


class KafkaExporterTests(unittest.TestCase):
    def test_export_includes_stable_mongodb_id_in_value(self):
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        record = News("stable-id", "site", "title", "https://example.com", "en", "description long enough", None, now)
        kafka = Mock()

        KafkaExporter(kafka, "news").export([record])

        self.assertEqual(kafka.publish.call_args.kwargs["key"], "stable-id")
        self.assertEqual(kafka.publish.call_args.kwargs["message"]["_id"], "stable-id")

    def test_export_counts_successes_and_skips_failures(self):
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        record = News("id", "site", "title", "https://example.com", "en", "description long enough", None, now)
        another = News("id-2", "site", "title", "https://example.com/2", "en", "description long enough", None, now)
        kafka = Mock()
        kafka.publish.side_effect = [None, RuntimeError("failed")]
        exporter = KafkaExporter(kafka, "news")
        with self.assertRaises(ExportError) as context:
            exporter.export([record, another])
        self.assertEqual(len(context.exception.failed_records), 1)
        self.assertEqual(kafka.publish.call_count, 2)

    def test_failed_record_is_sent_to_dlq_before_error_is_raised(self):
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        record = News("id", "site", "title", "https://example.com", "en", "description long enough", None, now)
        kafka = Mock()
        kafka.publish.side_effect = [RuntimeError("broker unavailable"), None]

        with self.assertRaises(ExportError):
            KafkaExporter(kafka, "news", "news_dlq").export([record])

        self.assertEqual(kafka.publish.call_args_list[0].kwargs["topic"], "news")
        self.assertEqual(kafka.publish.call_args_list[1].kwargs["topic"], "news_dlq")


if __name__ == "__main__":
    unittest.main()
