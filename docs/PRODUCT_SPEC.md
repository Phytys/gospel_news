# Gospel Resonance — Product Specification

This repository implements the **Gospel Resonance MVP** as described in the authoritative product brief (version 1.0).

## Thesis

A quiet, text-first app that helps people bring their real inner life to the words of Jesus — through:

1. **Ask** — free-form input → two canonical Gospel passages + one Thomas saying + labeled interpretation.
2. **Daily** — one pairing per calendar day (theme-driven, **not** news-driven).
3. **Map / Explore** — UMAP landscape over embeddings (visualization only; retrieval uses pgvector).

## Non-goals

Not a news app, sermon generator, social feed, or “ask Jesus” chatbot.

## Differentiators (preserved in code)

- **Dual-source:** Every response includes canonical + Thomas; Thomas labeled **noncanonical**.
- **Primary Text vs Interpretation:** Scripture only from DB; all model output explicitly labeled AI-assisted.
- **Map:** UMAP coordinates are **not** used for ranking retrieval.

See the full engineering specification provided by the product owner for acceptance criteria, tone rules, and schema details.
