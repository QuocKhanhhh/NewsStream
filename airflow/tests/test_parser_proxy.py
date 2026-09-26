import unittest
from unittest.mock import Mock, patch

from src.parser.rss_parser import RSSParser
from src.proxy.proxy_pool import ProxyPool
from src.proxy.proxy_scraper import ProxyScraper
from src.proxy.proxy_validator import ProxyValidator
from src.proxy.proxy_validator import ProxyValidationResult


RSS = b'''<?xml version="1.0"?><rss version="2.0"><channel><title>Feed</title>
<item><title><![CDATA[ <b>Match &amp; result </b> ]]></title>
<link>https://example.com/article/1</link><description>  A &amp; useful <i>description</i>. </description>
</item><item><description>missing title</description><link>https://example.com/2</link></item>
</channel></rss>'''


class RSSParserTests(unittest.TestCase):
    def test_parse_cleans_text_and_skips_incomplete_items(self):
        records = RSSParser("site", "en").parse(RSS)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].title, "Match & result")
        self.assertEqual(records[0].description, "A & useful")
        self.assertEqual(records[0].url, "https://example.com/article/1")

    def test_extract_url_supports_atom_link_objects(self):
        item = Mock(link=Mock(href=" https://example.com "))
        self.assertEqual(RSSParser._extract_url(item), "https://example.com")


class ProxyTests(unittest.TestCase):
    def test_scraper_parses_and_limits_proxy_table(self):
        html = b'''<table class="table"><tbody>
        <tr><td>1.2.3.4</td><td>8080</td><td>x</td><td>x</td><td>x</td><td>x</td><td>yes</td></tr>
        <tr><td>5.6.7.8</td><td>3128</td><td>x</td><td>x</td><td>x</td><td>x</td><td>no</td></tr>
        </tbody></table>'''
        http = Mock()
        http.get.return_value = html
        result = ProxyScraper("https://proxy-list", http).fetch(limit=1)
        self.assertEqual(result, [{"http": "https://1.2.3.4:8080", "https": "https://1.2.3.4:8080"}])

    def test_scraper_requires_a_table(self):
        with self.assertRaises(ValueError):
            ProxyScraper("url", Mock())._parse_proxy_table(b"<html />", 10)

    @patch("src.proxy.proxy_validator.time.sleep")
    def test_validator_calculates_health(self, sleep):
        http = Mock()
        http.get.side_effect = [None, RuntimeError("down"), None]
        result = ProxyValidator(http, "https://test", checks=3).validate({"http": "http://p"})
        self.assertEqual(result.health, 2 / 3)
        self.assertTrue(result.is_valid)
        self.assertEqual(sleep.call_count, 3)

    def test_proxy_pool_delegates_to_redis_client(self):
        redis = Mock()
        redis.get_first.return_value = {"http": "http://p"}
        pool = ProxyPool(redis, "key")
        self.assertEqual(pool.get(), {"http": "http://p"})
        pool.remove_current()
        pool.replace([{"http": "http://p"}])
        redis.remove_first.assert_called_once_with(key="key")
        redis.replace_list.assert_called_once_with(key="key", values=[{"http": "http://p"}])

    def test_proxy_pool_deduplicates_and_limits(self):
        redis = Mock()
        pool = ProxyPool(redis, "key", max_size=1)
        proxies = [
            {"http": "http://p", "https": "http://p"},
            {"http": "http://p", "https": "http://p"},
            {"http": "http://q", "https": "http://q"},
        ]
        pool.replace(proxies)
        redis.replace_list.assert_called_once_with(
            key="key", values=[{"http": "http://p", "https": "http://p"}]
        )

    def test_proxy_pool_sorts_validation_results_by_health(self):
        redis = Mock()
        pool = ProxyPool(redis, "key", max_size=2)
        low = ProxyValidationResult({"http": "http://low", "https": "http://low"}, 0.67, True)
        high = ProxyValidationResult({"http": "http://high", "https": "http://high"}, 1.0, True)
        pool.replace([low, high])
        redis.replace_list.assert_called_once_with(
            key="key",
            values=[
                {"http": "http://high", "https": "http://high"},
                {"http": "http://low", "https": "http://low"},
            ],
        )


if __name__ == "__main__":
    unittest.main()
