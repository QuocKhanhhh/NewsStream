import logging
from datetime import datetime, timezone
from urllib.parse import urlparse
from src.models.news import News, build_news_id, canonicalize_url

logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass

class NewsValidator:
    def __init__(self, allowed_languages: set[str], min_description_length: int = 20):
        self.allowed_languages = allowed_languages
        self.min_description_length = min_description_length
        
    def validate(self, news: News) -> News:
        errors = []
        if not isinstance(news._id, str) or not news._id.strip():
            errors.append("_id is empty")

        if not isinstance(news.source, str) or not news.source.strip():
            errors.append("source is empty")

        if not isinstance(news.title, str) or not news.title.strip():
            errors.append("title is empty")

        if not isinstance(news.url, str) or not news.url.strip():
            errors.append("url is empty")
        elif not self._is_valid_url(news.url):
            errors.append("url is invalid")

        if news.url and news._id and news._id != build_news_id(news.url):
            errors.append("_id does not match url")

        if not isinstance(news.description, str) or len(news.description.strip()) < self.min_description_length:
            errors.append("description is too short")

        if not isinstance(news.language, str) or news.language.strip().lower() not in self.allowed_languages:
            errors.append(
                f"unsupported language: {news.language}"
            )

        if not self._is_utc_datetime(news.scraped_at):
            errors.append("scraped_at must be timezone-aware UTC")

        if news.published_at is not None and not self._is_utc_datetime(news.published_at):
            errors.append("published_at must be timezone-aware UTC")

        if errors:
            raise ValidationError(
                f"Invalid news '{news._id}': {', '.join(errors)}"
            )

        return news
    
    def validate_many(self, records : list[News]) -> list[News]:
        valid_records = []
        seen_ids = set()
        for record in records:
            try:
                if record._id in seen_ids:
                    raise ValidationError(f"Duplicate news _id: {record._id}")
                valid_record = self.validate(record)
                valid_records.append(valid_record)
                seen_ids.add(record._id)
            except ValidationError as e:
                logger.warning("Validation error: %s", e)
        return valid_records

    @staticmethod
    def _is_utc_datetime(value: datetime) -> bool:
        return (
            isinstance(value, datetime)
            and value.tzinfo is not None
            and value.utcoffset() == timezone.utc.utcoffset(value)
        )
    
    @staticmethod
    def _is_valid_url(url: str) -> bool:
        parsed = urlparse(canonicalize_url(url))
        return parsed.scheme in {"http", "https"} and bool(
            parsed.hostname
        )
        
    
