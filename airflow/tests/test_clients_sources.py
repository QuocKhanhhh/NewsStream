import unittest
from unittest.mock import Mock, patch

from src.clients.https_client import HTTPClientError, HTTPSClient
from src.sources.rss_source import RSSFeeds, RSSSource


class HTTPSClientTests(unittest.TestCase):
    def test_get_passes_timeout_and_proxies_and_returns_content(self):
        client = HTTPSClient(timeout=7, user_agent="TestAgent")
        response = Mock(content=b"payload", status_code=200, headers={})
        client.session.get = Mock(return_value=response)

        self.assertEqual(client.get("https://example.com", {"https": "http://proxy:1"}), b"payload")
        client.session.get.assert_called_once_with(
            "https://example.com", proxies={"https": "http://proxy:1"}, timeout=7
        )
        response.raise_for_status.assert_called_once_with()

    def test_context_manager_closes_session(self):
        client = HTTPSClient()
        client.close = Mock()
        with client as same_client:
            self.assertIs(same_client, client)
        client.close.assert_called_once_with()

    @patch("src.clients.https_client.time.sleep")
    def test_get_retries_rate_limit_with_backoff(self, sleep):
        client = HTTPSClient(max_retries=1, backoff_factor=0.5)
        first = Mock(status_code=429, headers={"Retry-After": "0"})
        second = Mock(status_code=200, headers={}, content=b"ok")
        client.session.get = Mock(side_effect=[first, second])

        self.assertEqual(client.get("https://example.com"), b"ok")
        self.assertEqual(client.session.get.call_count, 2)
        sleep.assert_called_once_with(0.0)

    def test_get_raises_typed_error_for_permanent_http_status(self):
        client = HTTPSClient()
        response = Mock(status_code=404, headers={}, content=b"not found")
        client.session.get = Mock(return_value=response)

        with self.assertRaises(HTTPClientError) as raised:
            client.get("https://example.com/missing")

        self.assertEqual(raised.exception.status_code, 404)
        self.assertFalse(raised.exception.proxy_error)
        response.raise_for_status.assert_not_called()


class RSSSourceTests(unittest.TestCase):
    def test_fetch_delegates_to_http_client(self):
        http = Mock()
        http.get.return_value = b"rss"
        source = RSSSource("https://feed", http, proxy={"http": "http://p"})
        self.assertEqual(source.fetch(), b"rss")
        http.get.assert_called_once_with("https://feed", proxies={"http": "http://p"})

    def test_fetch_removes_bad_proxy_and_retries_with_next_one(self):
        http = Mock()
        http.get.side_effect = [RuntimeError("bad proxy"), b"rss"]
        pool = Mock()
        pool.acquire.side_effect = [
            {"http": "http://bad"},
            {"http": "http://good"},
        ]
        source = RSSSource("https://feed", http, proxy_pool=pool, max_proxy_attempts=2)

        self.assertEqual(source.fetch(), b"rss")
        pool.remove.assert_called_once_with({"http": "http://bad"})
        pool.release.assert_called_once_with({"http": "http://good"})

    def test_fetch_keeps_proxy_when_source_returns_rate_limit(self):
        http = Mock()
        http.get.side_effect = HTTPClientError("rate limited", status_code=429)
        pool = Mock()
        pool.acquire.return_value = {"http": "http://good"}
        source = RSSSource("https://feed", http, proxy_pool=pool, max_proxy_attempts=1)

        with self.assertRaises(HTTPClientError):
            source.fetch()
        pool.remove.assert_not_called()
        pool.release.assert_called_once_with({"http": "http://good"})

    def test_feed_metadata_is_immutable(self):
        feed = RSSFeeds("site", "https://feed", "en")
        with self.assertRaises(AttributeError):
            feed.language = "vi"


if __name__ == "__main__":
    unittest.main()
