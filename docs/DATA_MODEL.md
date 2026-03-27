# Data model

Postgres 16 + pgvector.

## Core

- **source_texts** — verses, passages, sayings (UUID PK, `tradition`, `chunk_type`, `ref_label`, `text`, `theme_tags`, …)
- **text_embeddings** — one row per source text per `(embedding_model, embedding_dim, embedding_version)`
- **map_points** — UMAP x/y per source text (`projection_name` e.g. `umap_v1`)
- **daily_entries** — immutable published daily record
- **user_sessions_ask** — ask sessions (optional persistence)
- **users**, **user_notes**, **daily_theme_signals** — saved/journal/editorial (MVP partial)

See `apps/api/app/models.py` for columns.
