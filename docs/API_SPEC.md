# API Specification (summary)

Base path: `/api/v1`

## Public

| Method | Path | Description |
|--------|------|---------------|
| POST | `/ask` | Ask resonance (body: `text`, `timezone`, `save_prompt`) |
| GET | `/daily` | Today’s daily (`?d=YYYY-MM-DD` optional) |
| GET | `/daily/archive` | List published dailies: `{ "entries": [ { "entry_date", "theme_label" }, ... ] }` (newest first) |
| GET | `/map` | Map points (`?tradition=canonical\|thomas\|all`) |
| GET | `/map/node/{id}` | Node detail |
| POST | `/map/query` | Nearest neighbors for arbitrary text |
| POST | `/save/session/{id}` | Mark ask session saved |

## Admin (header `X-Admin-Token`)

| Method | Path | Description |
|--------|------|---------------|
| POST | `/admin/ingest-texts` | Full WEB + Thomas ingest + embeddings |
| POST | `/admin/rebuild-map` | Recompute UMAP `map_points` |
| POST | `/admin/generate-daily` | Generate daily (`?d=` optional). `?replace=true` deletes an existing daily for that date and regenerates (new prompts / model output). |

OpenAPI: `/docs` on the API service.
