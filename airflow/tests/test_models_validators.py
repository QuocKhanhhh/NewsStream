import unittest
from datetime import datetime, timezone

from src.models.news import News, build_news_id
from src.validators.news_validator import NewsValidator, ValidationError


def make_news(**changes):
    values = {
        "_id": build_news_id("https://example.com/news/1"),
        "source": "example",
        "title": "A title",
        "url": "https://example.com/news/1",
        "language": "en",
        "description": "A sufficiently long description for validation.",
        "published_at": None,
        "scraped_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }
    values.update(changes)
    return News(**values)


class NewsModelTests(unittest.TestCase):
    def test_id_is_deterministic_sha256(self):
        self.assertEqual(build_news_id("https://example.com"), build_news_id("https://example.com"))
        self.assertEqual(len(build_news_id("https://example.com")), 64)

    def test_to_dict_serializes_datetimes(self):
        news = make_news(published_at=datetime(2026, 1, 2, tzinfo=timezone.utc))
        data = news.to_dict()
        self.assertIn("_id", data)
        self.assertNotIn("id", data)
        self.assertEqual(data["published_at"], "2026-01-02T00:00:00+00:00")
        self.assertEqual(data["scraped_at"], "2026-01-01T00:00:00+00:00")


class NewsValidatorTests(unittest.TestCase):
    def setUp(self):
        self.validator = NewsValidator({"en", "vi"}, min_description_length=20)

    def test_valid_record_is_returned(self):
        news = make_news()
        self.assertIs(self.validator.validate(news), news)

    def test_invalid_record_reports_all_errors(self):
        news = make_news(_id="", url="bad", description="short", language="fr")
        with self.assertRaisesRegex(ValidationError, "_id is empty.*url is invalid.*description is too short.*unsupported language"):
            self.validator.validate(news)

    def test_id_must_match_canonical_url(self):
        news = make_news(_id="wrong-id")
        with self.assertRaisesRegex(ValidationError, "_id does not match url"):
            self.validator.validate(news)

    def test_validate_many_keeps_only_valid_records(self):
        records = [make_news(), make_news(_id="", description="short")]
        self.assertEqual(self.validator.validate_many(records), [records[0]])


if __name__ == "__main__":
    unittest.main()
