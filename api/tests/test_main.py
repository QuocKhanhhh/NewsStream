from datetime import datetime, timezone

from fastapi.testclient import TestClient
from elasticsearch import NotFoundError

from api.app.main import app, build_filters, build_query, build_sort, get_elasticsearch
from api.app.schemas import NewsSort


class FakeElasticsearch:
    def __init__(self):
        self.search_calls = []

    async def search(self, **kwargs):
        self.search_calls.append(kwargs)
        return {
            "hits": {
                "total": {"value": 1},
                "hits": [
                    {
                        "_id": "article-1",
                        "_score": 2.5,
                        "_source": {
                            "title": "AI news",
                            "source": "vnexpress",
                            "language": "vi",
                        },
                    }
                ],
            }
        }


class MissingIndexElasticsearch:
    async def search(self, **kwargs):
        raise NotFoundError(message="index not found", meta=None, body={})


def test_search_query_boosts_title_and_filters_metadata():
    filters = build_filters("vnexpress", "vi", None, None)
    query = build_query("kinh te", filters)

    assert query["bool"]["must"][0]["multi_match"]["fields"] == ["title^3", "description"]
    assert filters == [
        {"term": {"source": "vnexpress"}},
        {"term": {"language": "vi"}},
    ]


def test_time_filter_and_default_browse_sort():
    start = datetime(2026, 10, 1, tzinfo=timezone.utc)
    filters = build_filters(None, None, start, None)

    assert filters == [{"range": {"published_at": {"gte": "2026-10-01T00:00:00+00:00"}}}]
    assert build_sort(NewsSort.relevance, has_query=False) == [
        {"published_at": {"order": "desc", "missing": "_last"}}
    ]


def test_relevance_sort_uses_score_then_recency():
    assert build_sort(NewsSort.relevance, has_query=True)[0] == "_score"


def test_list_news_translates_parameters_to_a_safe_elasticsearch_query():
    fake_client = FakeElasticsearch()
    app.dependency_overrides[get_elasticsearch] = lambda: fake_client
    try:
        with TestClient(app) as client:
            response = client.get("/news", params={"q": "AI", "language": "vi", "page": 2, "page_size": 10})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["items"][0]["id"] == "article-1"
    assert fake_client.search_calls[0]["from_"] == 10
    assert fake_client.search_calls[0]["query"]["bool"]["filter"] == [{"term": {"language": "vi"}}]


def test_list_news_is_empty_before_the_sink_creates_its_index():
    app.dependency_overrides[get_elasticsearch] = MissingIndexElasticsearch
    try:
        with TestClient(app) as client:
            response = client.get("/news")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["total"] == 0
