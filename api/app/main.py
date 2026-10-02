from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

from elasticsearch import AsyncElasticsearch, NotFoundError
from fastapi import Depends, FastAPI, HTTPException, Query, Request, status

from .config import Settings, get_settings
from .schemas import FacetBucket, HealthResponse, NewsFacets, NewsItem, NewsPage, NewsSort, to_news_item


def response_body(response: Any) -> dict[str, Any]:
    """Support Elasticsearch client response objects and simple test doubles."""
    return getattr(response, "body", response)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    app.state.elasticsearch = AsyncElasticsearch(settings.elasticsearch_url)
    try:
        yield
    finally:
        await app.state.elasticsearch.close()


app = FastAPI(
    title="NewsStream API",
    version="1.0.0",
    description="Read-only search API backed by Elasticsearch.",
    lifespan=lifespan,
)


def get_elasticsearch(request: Request) -> AsyncElasticsearch:
    return request.app.state.elasticsearch


def build_filters(
    source: str | None,
    language: str | None,
    published_from: datetime | None,
    published_to: datetime | None,
) -> list[dict[str, Any]]:
    filters: list[dict[str, Any]] = []
    if source:
        filters.append({"term": {"source": source}})
    if language:
        filters.append({"term": {"language": language}})
    if published_from or published_to:
        time_range: dict[str, str] = {}
        if published_from:
            time_range["gte"] = published_from.isoformat()
        if published_to:
            time_range["lte"] = published_to.isoformat()
        filters.append({"range": {"published_at": time_range}})
    return filters


def build_query(query: str | None, filters: list[dict[str, Any]]) -> dict[str, Any]:
    if not query:
        return {"bool": {"filter": filters}} if filters else {"match_all": {}}
    return {
        "bool": {
            "must": [
                {
                    "multi_match": {
                        "query": query,
                        "fields": ["title^3", "description"],
                        "type": "best_fields",
                    }
                }
            ],
            "filter": filters,
        }
    }


def build_sort(sort: NewsSort, has_query: bool) -> list[dict[str, Any]]:
    if sort == NewsSort.published_at_asc:
        return [{"published_at": {"order": "asc", "missing": "_last"}}]
    if sort == NewsSort.published_at_desc or not has_query:
        return [{"published_at": {"order": "desc", "missing": "_last"}}]
    return ["_score", {"published_at": {"order": "desc", "missing": "_last"}}]


@app.get("/health", response_model=HealthResponse, tags=["operations"])
async def health(
    elasticsearch: AsyncElasticsearch = Depends(get_elasticsearch),
    settings: Settings = Depends(get_settings),
) -> HealthResponse:
    try:
        cluster = response_body(await elasticsearch.cluster.health())
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Elasticsearch is unavailable") from exc
    return HealthResponse(status="ok", cluster_status=cluster["status"], index=settings.elasticsearch_index)


@app.get("/news", response_model=NewsPage, tags=["news"])
async def list_news(
    q: str | None = Query(default=None, max_length=200),
    source: str | None = Query(default=None, max_length=100),
    language: str | None = Query(default=None, max_length=20),
    published_from: datetime | None = None,
    published_to: datetime | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort: NewsSort = NewsSort.relevance,
    elasticsearch: AsyncElasticsearch = Depends(get_elasticsearch),
    settings: Settings = Depends(get_settings),
) -> NewsPage:
    if published_from and published_to and published_from > published_to:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="published_from must be before published_to")

    normalized_query = q.strip() if q else None
    filters = build_filters(source, language, published_from, published_to)
    try:
        result = response_body(
            await elasticsearch.search(
                index=settings.elasticsearch_index,
                query=build_query(normalized_query, filters),
                from_=(page - 1) * page_size,
                size=page_size,
                sort=build_sort(sort, bool(normalized_query)),
                track_total_hits=True,
            )
        )
    except NotFoundError:
        # The index is created lazily by the sink connector after its first record.
        return NewsPage(items=[], total=0, page=page, page_size=page_size)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Elasticsearch search is unavailable") from exc

    total = result["hits"]["total"]
    return NewsPage(
        items=[to_news_item(hit) for hit in result["hits"]["hits"]],
        total=total["value"] if isinstance(total, dict) else total,
        page=page,
        page_size=page_size,
    )


@app.get("/news/facets", response_model=NewsFacets, tags=["news"])
async def news_facets(
    source: str | None = Query(default=None, max_length=100),
    language: str | None = Query(default=None, max_length=20),
    published_from: datetime | None = None,
    published_to: datetime | None = None,
    elasticsearch: AsyncElasticsearch = Depends(get_elasticsearch),
    settings: Settings = Depends(get_settings),
) -> NewsFacets:
    filters = build_filters(source, language, published_from, published_to)
    query = {"bool": {"filter": filters}} if filters else {"match_all": {}}
    try:
        result = response_body(
            await elasticsearch.search(
                index=settings.elasticsearch_index,
                query=query,
                size=0,
                aggs={
                    "sources": {"terms": {"field": "source", "size": 50}},
                    "languages": {"terms": {"field": "language", "size": 50}},
                },
            )
        )
    except NotFoundError:
        return NewsFacets(sources=[], languages=[])
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Elasticsearch facets are unavailable") from exc

    aggregations = result["aggregations"]
    return NewsFacets(
        sources=[FacetBucket(key=bucket["key"], count=bucket["doc_count"]) for bucket in aggregations["sources"]["buckets"]],
        languages=[FacetBucket(key=bucket["key"], count=bucket["doc_count"]) for bucket in aggregations["languages"]["buckets"]],
    )


@app.get("/news/{news_id}", response_model=NewsItem, tags=["news"])
async def get_news(
    news_id: str,
    elasticsearch: AsyncElasticsearch = Depends(get_elasticsearch),
    settings: Settings = Depends(get_settings),
) -> NewsItem:
    try:
        result = response_body(await elasticsearch.get(index=settings.elasticsearch_index, id=news_id))
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="News article not found") from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Elasticsearch lookup is unavailable") from exc
    return to_news_item(result)
