# OffCampusReview collection

Collected October 24, 2026 from the public OffCampusReview website at the user's request. This database is a local research collection, not a publication license or verification of the reviews' claims.

## Result

- Database: `var/offcampusreview.sqlite3`.
- Machine-readable coverage: `var/offcampusreview.collection.json`.
- 720 distinct source review records across 30 schools.
- 676 records include review text; 44 are rating-only records with no written comment.
- 67 records are associated with Virginia Tech.
- Initial discovery exhausted 818 public page URLs, including the 503 advertised campus pages, public landlord pages, and listing pages.
- A supplemental pass recovered long text records and checked the site's public listing “Show all” endpoint. Listing snippets never replace a full review.
- No sign-in, private/admin endpoint, CAPTCHA bypass, or private dataset export was used.

This is the accessible public collection at crawl time, not a guarantee about hidden, removed, unpublished, or future reviews. Site counts can differ between the public university directory, school pages and cached indexes. Actual stored source records determine the reported count.

## Tables

| Table | Purpose |
|---|---|
| `reviews` | Source review ID, school and landlord context, source property ID, rating/text, review date/lease period, reported categories/tags, text scope, hashes and retrieval timestamps |
| `review_pages` | Every recorded public page/API URL supporting a review ID |
| `pages` | HTTP result, parsed and advertised counts when available, content hash, collection time and errors |
| `schools` | Public directory names/slugs and reported counts, including zero-count campuses |
| `source_policies` | Robots provenance and the reviewed reuse-policy limitation |
| `collection_runs` | Completed/interrupted runs, start times and coverage summaries |

Review dates and lease periods are source-provided context, not guarantees of present conditions. `felt_safe` is an individual respondent's subjective report, not a safety rating. The collection does not establish current housing quality or availability.

Structured author/account fields, email addresses and precise property addresses are excluded. Original review text is retained as provided and may itself contain personal information; it has not been automatically de-identified.

## Access and reuse boundary

[Robots](https://www.offcampusreview.com/robots.txt) permits public page access and explicitly permits the university directory and listing-review endpoint used here. This controls crawling; it is not a content license.

The [terms](https://www.offcampusreview.com/terms-conditions) say contributors retain ownership of their user content and grant rights to OffCampusReview. A third-party license for Roomwise to republish or process all reviews was not established by that text. Each stored record therefore has `reuse_permission = 'not_established'` and `collection_scope = 'user_requested_local_research'`.

The collection is excluded from Git and Docker through `var/` exclusions. There is no public review-text API, no automatic Gemma ingestion, no model training, no generated resident quotation, and no public summary enabled by this import. Existing “wish I knew” output remains unavailable until permitted use, reviewed property matching and evidence queries are implemented.

Before using the corpus beyond this local collection: establish the permitted storage/display/model scope, define retention and source-removal handling, review sensitive text, and map review subjects to canonical Roomwise properties. Do not assume similarly named landlords are identical.

## Inspect locally

```sql
SELECT school_slug, COUNT(*) AS review_count
FROM reviews GROUP BY school_slug ORDER BY review_count DESC;

SELECT landlord_name, rating, review_text, published_at, lease_period, text_scope
FROM reviews WHERE school_slug = 'virginia-tech';

SELECT url, status, error FROM pages WHERE error IS NOT NULL;
```

Use `tools/backend/collect_offcampusreview.py` for discovery and `tools/backend/supplement_offcampusreview.py` for supplemental recovery. Both are bounded and respect robots; the collector stops on rate limiting. Import is idempotent by source ID, not a request to duplicate the corpus. A rerun can update current text, but a full automated deletion/retention mirror is not yet implemented.

## Verification

Parser tests cover split JSON chunks, byte-length-framed UTF-8 long text, reference resolution, malformed scripts and public URL boundaries. Storage tests cover deduplication, multiple source links, whitelisted metadata, rating-only records and preservation of full text when a listing snippet is encountered. The SQLite integrity check passed. The backend test suite passes with the collector tests included.

See [BACKLOG.md](BACKLOG.md) for remaining backend work.
