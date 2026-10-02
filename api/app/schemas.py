from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class NewsSort(StrEnum):
    relevance = "relevance"
    published_at_desc = "published_at_desc"
    published_at_asc = "published_at_asc"


class NewsItem(BaseModel):
    id: str
    source: str | None = None
    title: str | None = None
    url: str | None = None
    language: str | None = None
    description: str | None = None
    published_at: datetime | None = None
    scraped_at: datetime | None = None
    score: float | None = None

    model_config = {"extra": "allow"}


class NewsPage(BaseModel):
    items: list[NewsItem]
    total: int
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)


class FacetBucket(BaseModel):
    key: str
    count: int


class NewsFacets(BaseModel):
    sources: list[FacetBucket]
    languages: list[FacetBucket]


class HealthResponse(BaseModel):
    status: str
    cluster_status: str
    index: str


def to_news_item(hit: dict[str, Any]) -> NewsItem:
    return NewsItem(id=hit["_id"], score=hit.get("_score"), **hit.get("_source", {}))
