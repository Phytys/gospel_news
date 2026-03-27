# Digest Investigation — Why 0 Entries on First Run?

> **Note:** This note is about an **RSS / digest** pipeline and scripts that may not exist in the current Gospel Resonance tree. The live MVP (Ask, Daily, Map) is documented in [README.md](../README.md). Treat the commands below as **historical** unless those modules are present in your checkout.


## Current Status: **Working**

- **RSS:** 10 sources, 34 candidates fetched ✓
- **DB:** 5+ NewsItems, 3 DigestEntry for today ✓
- **Live:** https://gospellens.resonancehub.app shows 3 digest entries ✓

## Why the First Manual Run Returned 0 Entries

**Most likely:** The manual `run_digest` we ran immediately after deploy completed the loop but added 0 entries because:

1. **Session / commit timing** — New `NewsItem` rows are inserted and committed, then `recent_items` is queried. In some edge cases the query might not yet see the newly committed rows in the same session.

2. **RSS fetch from container** — The first run may have had network issues (DNS, firewall, or RSS feed timeouts) so `fetch_rss_candidates` returned an empty list. No candidates → no new items → empty `recent_items` → 0 entries.

3. **Worker ran first** — The worker is scheduled for 06:30 SGT. If it ran before our manual run and already created 3 entries, our manual run would have seen `existing_ranks >= stories_per_day` and returned early without adding more. But the output was "0 entries", so the digest object itself had 0 entries at that moment.

**Conclusion:** The most plausible explanation is that on the first run, `recent_items` was empty (e.g. RSS fetch failed or returned nothing from inside the container at that moment). Later runs (including the worker) succeeded.

## Fix Applied: Strong's Numbers in Scripture Text

The eBible `eng-web_usfm.zip` includes Strong's concordance markup like `|strong="G2400"` in the text. This was showing up in the UI.

**Fix:** Added a regex in `_clean_usfm()` to strip `|strong="..."` patterns before storing.

**To apply:** Re-run scripture ingest to refresh stored text:

```bash
docker compose -f docker-compose.prod.yml exec api python -m app.scripts.ingest_scripture
```

This will re-download, re-parse (with the new cleaning), and re-embed. Existing digest entries will keep their current scripture refs; new digests will use the cleaned text.

## Recommendations

1. **Add logging** — Log RSS candidate count, `recent_items` count, and per-item success/failure to make future debugging easier.
2. **Retry logic** — Add retries for `extract_article_text` and OpenRouter calls (some news sites block or throttle).
3. **Health check** — Add an endpoint that verifies RSS fetch, DB connectivity, and OpenRouter reachability.
