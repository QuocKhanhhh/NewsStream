import hashlib
import re
from datetime import datetime, timezone
from html import unescape
from typing import Any, Optional
import atoma
from src.models import News
from src.models.news import build_news_id, canonicalize_url
from src.parser.base_parser import BaseParser


class RSSParser(BaseParser):
    def __init__(self, source: str, language: str):
        self.source = source
        self.language = language
        
    def parse(self, content: bytes) -> list[News]:
        """
        Parses the given RSS feed content and returns a list of News objects.

        Args:
            content (bytes): The RSS feed content to be parsed.
        """
        try:
            feed = atoma.parse_rss_bytes(content)
        except Exception as rss_error:
            try:
                feed = atoma.parse_atom_bytes(content)
            except Exception as atom_error:
                raise ValueError("Content is neither valid RSS nor Atom") from atom_error
        
        records = []
        for item in feed.items:
            news = self._parse_item(item)
            if news:
                records.append(news)
        return records
    
    def _parse_item(self, item: Any) -> Optional[News]:
        """
        Parses an individual RSS feed item and returns a News object.

        Args:
            item (Any): The RSS feed item to be parsed.
        """
        title = self._clean_text(getattr(item, "title", None))
        url = self._extract_url(item)
        
        if not title or not url:
            return None
        
        description = self._clean_text(getattr(item, "description", None))
        pub_date = getattr(item, "published", None)
        url = canonicalize_url(url)
        
        return News(
            _id=build_news_id(url),
            title=title,
            url=url,
            description=description,
            source=self.source,
            language=self.language,
            published_at=pub_date if isinstance(pub_date, datetime) else None,
            scraped_at=datetime.now(timezone.utc),
        )
        
        
    @staticmethod
    def _extract_url(item: Any) -> str:
        link = getattr(item, "link", None)
        
        if isinstance(link, str):
            return link.strip()
        
        if link is not None:
            href = getattr(link, "href", None)
            if href:
                return href.strip()
        
        return ""
    
    @staticmethod
    def _clean_text(text: Optional[str]) -> str:
        if text is None:
            return ""
        text = unescape(str(text))  # Unescape HTML entities
        text = re.sub(r"<[^>]+>", "", text)  # Remove HTML tags
        text = re.sub(r"\s+", " ", text)  # Normalize whitespace
        return text.strip()
    
    @staticmethod
    def _build_news_id(url: str) -> str:
        """
        Generates a unique ID for the news item based on its URL.

        Args:
            url (str): The URL of the news item.
        """
        return build_news_id(url)
