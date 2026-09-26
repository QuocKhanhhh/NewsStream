class Config:
    PROXY_WEBPAGE = "https://free-proxy-list.net/"
    TESTING_URL = "https://google.com"

    # Feeds that returned usable RSS/XML in the latest integration run.
    # Sources with permanent 4xx responses are disabled until a verified
    # replacement URL is available from the publisher.
    RSS_FEEDS = {
        "en": [
            "https://www.eyefootball.com/football_news.xml",
            "https://www.101greatgoals.com/feed/",
            "https://deadspin.com/rss",
        ],
        "pl": [
            "https://sportowefakty.wp.pl/rss.xml",
            "https://weszlo.com/feed/",
            "https://futbolnews.pl/feed",
            "https://igol.pl/feed/",
        ],
        "es": [
            "https://www.mundodeportivo.com/rss/futbol",
            "https://www.abc.es/rss/feeds/abc_Futbol.xml",
        ],
        "vi": [
            "https://vnexpress.net/rss/the-thao.rss",
        ],
    }

    VALIDATOR_CONFIG = {
        "description_length": 100,
        "language": ["en", "pl", "es", "de", "vi"],
        "title_length": 100,
        "title_words": 10,
        "description_words": 20,
    }
