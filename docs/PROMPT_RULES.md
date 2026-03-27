# Prompt rules

1. **No generated scripture** — models select only IDs from retrieved candidates; UI text comes from `source_texts`.
2. **No first-person Jesus** — enforced in system prompts (`prompts_messages.py`).
3. **Thomas** — always treated as noncanonical in UX copy.
4. **Relation labels** — `Resonates with` | `Deepens` | `Contrasts with` | `Grounds`.
5. **JSON-only** outputs for Ask/Daily selection; Pydantic validation in `prompts_contracts.py`.

Refine prompts here as `PROMPT_VERSION` increments.
