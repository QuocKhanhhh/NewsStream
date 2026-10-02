# NewsStream API

Read-only FastAPI service over the Elasticsearch news index. It does not write to MongoDB, Kafka, or Elasticsearch.

## Run

```powershell
docker compose up --build api
```

The API is available at `http://localhost:8000`; interactive OpenAPI documentation is at `http://localhost:8000/docs`.

## Endpoints

- `GET /health`
- `GET /news?q=ai&source=vnexpress&language=vi&page=1&page_size=20&sort=relevance`
- `GET /news/{id}`
- `GET /news/facets?language=vi`

`GET /news` supports full-text search over `title` and `description`, exact filters for `source` and `language`, date-range filters (`published_from`, `published_to`), pagination, and sorting. The API never accepts raw Elasticsearch DSL from callers.
