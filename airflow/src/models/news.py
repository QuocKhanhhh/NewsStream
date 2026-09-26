from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import hashlib
from dataclasses import asdict
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
@dataclass(frozen=True)
class News:
    _id: str
    source: str
    title: str
    url: str
    language: str
    description: str
    published_at: Optional[datetime]
    scraped_at: datetime
    
    def to_dict(self) -> dict:
        data = asdict(self)
        if self.published_at:
            data["published_at"] = self.published_at.isoformat()
        data["scraped_at"] = self.scraped_at.isoformat()
        return data
    
    
def build_news_id(url: str) -> str:
    """
    Build a unique ID for a news article based on its URL.
    
    Args:
        url (str): The URL of the news article.
    """
    return hashlib.sha256(canonicalize_url(url).encode("utf-8")).hexdigest()


def canonicalize_url(url: str) -> str:
    """Normalize a URL before using it as a stable news identity."""
    value = url.strip()
    parts = urlsplit(value)
    query = [
        (key, item)
        for key, item in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith("utm_")
        and key.lower() not in {"fbclid", "gclid"}
    ]
    return urlunsplit(
        (
            parts.scheme.lower(),
            parts.netloc.lower(),
            parts.path or "/",
            urlencode(query),
            "",
        )
    )

