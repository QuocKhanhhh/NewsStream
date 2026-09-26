import os


KAFKA_BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS",
    "kafka:9092",
)

KAFKA_TOPIC = os.getenv(
    "KAFKA_TOPIC",
    "rss_news",
)

REDIS_HOST = os.getenv(
    "REDIS_HOST",
    "redis",
)

REDIS_PORT = int(os.getenv(
    "REDIS_PORT",
    "6379",
))

REDIS_DB = int(os.getenv(
    "REDIS_DB",
    "0",
))

REDIS_PROXY_KEY = os.getenv(
    "REDIS_PROXY_KEY",
    "proxies",
)

PROXY_SOURCE_URL = os.getenv(
    "PROXY_SOURCE_URL",
    "https://free-proxy-list.net/",
)

PROXY_TEST_URL = os.getenv(
    "PROXY_TEST_URL",
    "https://www.google.com",
)

PROXY_ENABLED = os.getenv("PROXY_ENABLED", "false").lower() == "true"

PROXY_POOL_SIZE = int(os.getenv("PROXY_POOL_SIZE", "10"))
