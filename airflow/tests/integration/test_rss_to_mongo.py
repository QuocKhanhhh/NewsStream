import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest


pytestmark = pytest.mark.integration

RSS_FIXTURE = b'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Integration</title>
<item><title>Integration article</title>
<link>http://127.0.0.1:8765/article/1?utm_source=test</link>
<description>A sufficiently long integration description.</description>
</item></channel></rss>'''

MONGO_TEST_URI = os.getenv(
    "MONGO_TEST_URI",
    "mongodb://localhost:27017/?replicaSet=rs0&directConnection=true",
)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/rss+xml")
        self.send_header("Content-Length", str(len(RSS_FIXTURE)))
        self.end_headers()
        self.wfile.write(RSS_FIXTURE)

    def log_message(self, *_args):
        return


@pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION") != "1",
    reason="Set RUN_INTEGRATION=1 after docker compose up",
)
def test_rss_kafka_mongodb_round_trip():
    from pymongo import MongoClient

    from src.clients.https_client import HTTPSClient
    from src.clients.kafka_client import KafkaClient
    from src.exporters.kafka_exporter import KafkaExporter
    from src.models.news import build_news_id
    from src.parser.rss_parser import RSSParser
    from src.sources.rss_source import RSSSource
    from src.validators.news_validator import NewsValidator

    server = ThreadingHTTPServer(("127.0.0.1", 8765), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    expected_id = build_news_id("http://127.0.0.1:8765/article/1")
    mongo = MongoClient(MONGO_TEST_URI)
    collection = mongo.newsdb.news
    collection.delete_many({"_id": expected_id})

    try:
        with HTTPSClient(timeout=5) as http:
            content = RSSSource("http://127.0.0.1:8765", http).fetch()
        records = RSSParser("integration", "en").parse(content)
        valid = NewsValidator({"en"}, min_description_length=20).validate_many(records)

        with KafkaClient(["127.0.0.1:9094"]) as client:
            KafkaExporter(client, "rss_news", "rss_news_dlq").export(valid)

        deadline = time.time() + 60
        while time.time() < deadline:
            if collection.count_documents({"_id": expected_id}) == 1:
                break
            time.sleep(1)

        assert collection.count_documents({"_id": expected_id}) == 1
        assert collection.find_one({"_id": expected_id})["language"] == "en"
    finally:
        server.shutdown()
        mongo.close()


@pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION") != "1",
    reason="Set RUN_INTEGRATION=1 after docker compose up",
)
def test_rss_kafka_mongodb_is_idempotent():
    """Publishing the same RSS article twice must keep one Mongo document."""
    from pymongo import MongoClient

    from src.clients.https_client import HTTPSClient
    from src.clients.kafka_client import KafkaClient
    from src.exporters.kafka_exporter import KafkaExporter
    from src.models.news import build_news_id
    from src.parser.rss_parser import RSSParser
    from src.sources.rss_source import RSSSource
    from src.validators.news_validator import NewsValidator

    server = ThreadingHTTPServer(("127.0.0.1", 8765), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    expected_id = build_news_id("http://127.0.0.1:8765/article/1")
    mongo = MongoClient(MONGO_TEST_URI)
    collection = mongo.newsdb.news
    collection.delete_many({"_id": expected_id})

    try:
        with HTTPSClient(timeout=5) as http:
            content = RSSSource("http://127.0.0.1:8765", http).fetch()
        records = RSSParser("integration-idempotency", "en").parse(content)
        valid = NewsValidator({"en"}, min_description_length=20).validate_many(records)

        with KafkaClient(["127.0.0.1:9094"]) as client:
            exporter = KafkaExporter(client, "rss_news", "rss_news_dlq")
            exporter.export(valid)
            exporter.export(valid)

        deadline = time.time() + 60
        while time.time() < deadline:
            if collection.count_documents({"_id": expected_id}) == 1:
                break
            time.sleep(1)

        assert collection.count_documents({"_id": expected_id}) == 1
        document = collection.find_one({"_id": expected_id})
        assert document is not None
        assert document["_id"] == expected_id
        assert "id" not in document
    finally:
        server.shutdown()
        mongo.close()
