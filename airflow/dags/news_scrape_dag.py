import logging
import time
from datetime import datetime, timedelta

from airflow.decorators import dag, task

from dags_config import Config
from src.clients.https_client import HTTPClientError, HTTPSClient
from src.clients.kafka_client import KafkaClient
from src.clients.redis_client import RedisClient
from src.config import (
    KAFKA_BOOTSTRAP_SERVERS,
    KAFKA_TOPIC,
    PROXY_ENABLED,
    PROXY_POOL_SIZE,
    PROXY_SOURCE_URL,
    PROXY_TEST_URL,
    REDIS_DB,
    REDIS_HOST,
    REDIS_PORT,
    REDIS_PROXY_KEY,
)
from src.exporters.kafka_exporter import KafkaExporter
from src.metrics import FeedMetrics
from src.parser.rss_parser import RSSParser
from src.proxy.proxy_pool import ProxyPool
from src.proxy.proxy_scraper import ProxyScraper
from src.proxy.proxy_validator import ProxyValidator
from src.sources.rss_source import RSSSource
from src.validators.news_validator import NewsValidator

logger = logging.getLogger(__name__)


@dag(
    dag_id="news_scrape_pipeline",
    schedule="*/10 * * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    default_args={
        "owner": "newsstream",
        "retries": 2,
        "retry_delay": timedelta(minutes=2),
        "retry_exponential_backoff": True,
    },
    tags=["news", "rss", "integration"],
)
def news_scrape_pipeline():
    @task
    def prepare_proxy_pool() -> dict:
        if not PROXY_ENABLED:
            result = {"enabled": False, "proxy_count": 0}
            logger.info("proxy_metrics=%s", result)
            return result

        redis_client = RedisClient(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
        pool = ProxyPool(redis_client, REDIS_PROXY_KEY, max_size=PROXY_POOL_SIZE)

        with HTTPSClient(timeout=20, max_retries=1) as http_client:
            raw_proxies = ProxyScraper(PROXY_SOURCE_URL, http_client).fetch(limit=100)
            results = ProxyValidator(
                http_client=http_client,
                test_url=PROXY_TEST_URL,
                checks=3,
            ).validate_many(raw_proxies)

        valid_results = [result for result in results if result.is_valid]
        pool.replace(valid_results)
        metrics = {
            "enabled": True,
            "scraped": len(raw_proxies),
            "validated": len(results),
            "valid": len(valid_results),
            "stored": min(len(valid_results), PROXY_POOL_SIZE),
        }
        logger.info("proxy_metrics=%s", metrics)
        if not valid_results:
            raise RuntimeError("Proxy pool is empty after validation")
        return metrics

    @task
    def scrape_and_publish(feed: dict, _proxy_status: dict) -> dict:
        started = time.perf_counter()
        metrics = FeedMetrics(source=feed["name"])
        proxy_pool = None

        if PROXY_ENABLED:
            redis_client = RedisClient(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
            proxy_pool = ProxyPool(redis_client, REDIS_PROXY_KEY, max_size=PROXY_POOL_SIZE)

        parser = RSSParser(source=feed["name"], language=feed["language"])
        validator = NewsValidator(
            allowed_languages=set(Config.VALIDATOR_CONFIG["language"]),
            min_description_length=Config.VALIDATOR_CONFIG["description_length"],
        )

        try:
            with HTTPSClient(timeout=30, max_retries=1) as http_client:
                source = RSSSource(
                    url=feed["url"],
                    http_client=http_client,
                    source_name=feed["name"],
                    proxy_pool=proxy_pool,
                    max_proxy_attempts=3,
                )
                content = source.fetch()

            records = parser.parse(content)
            metrics.items_read = len(records)
            valid_records = validator.validate_many(records)
            metrics.items_valid = len(valid_records)
            metrics.items_rejected = metrics.items_read - metrics.items_valid

            with KafkaClient(KAFKA_BOOTSTRAP_SERVERS.split(",")) as kafka_client:
                exporter = KafkaExporter(
                    kafka_client=kafka_client,
                    topic=KAFKA_TOPIC,
                    dlq_topic=f"{KAFKA_TOPIC}_dlq",
                )
                metrics.messages_published = exporter.export(valid_records)
        except HTTPClientError as error:
            metrics.error = str(error)
            metrics.http_status = error.status_code
            # A stale/removed RSS URL, an access policy response, or another
            # permanent 4xx must not consume Airflow retries or block the
            # other mapped RSS tasks. The error remains visible in metrics.
            if error.status_code in {400, 401, 403, 404, 405, 406, 410}:
                logger.warning(
                    "permanent_feed_error source=%s status=%s error=%s",
                    feed["name"],
                    error.status_code,
                    error,
                )
                return metrics.as_dict()
            raise
        except Exception as error:
            metrics.error = str(error)
            raise
        finally:
            metrics.duration_ms = round((time.perf_counter() - started) * 1000, 2)
            metrics.log()

        return metrics.as_dict()

    feeds = [
        {"name": f"{language}_{index}", "url": url, "language": language}
        for language, urls in Config.RSS_FEEDS.items()
        for index, url in enumerate(urls)
    ]

    proxy_status = prepare_proxy_pool()
    scrape_and_publish.partial(_proxy_status=proxy_status).expand(feed=feeds)


news_scrape_pipeline()
