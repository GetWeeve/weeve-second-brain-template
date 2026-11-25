# Retrieval scope and measurements

The core uses exact word and heading matching over latest permitted source revisions and approved active topics. It returns up to three cited excerpts inside the requested UTF-8 byte budget. It does not stem words or infer synonyms. A query for “renewal” can miss a passage containing “renewed”; report that gap or try the source's terminology.

Each permitted source is read and hashed once per query, including when multiple topics share it. The cache lasts only for that query, avoiding stale persistent permissions/revisions. Work still grows with permitted corpus size, and whole UTF-8 files are read before excerpts are selected. A 5 MB per-source cap does not bound total workspace memory; split exports into focused sources and keep scope modest. There is no measured universal file-count limit.

Run `python3 benchmark.py` for temporary synthetic corpora of 20, 100 and 300 tiny text sources. It reports exact-locator recall, median/max local latency, emitted bytes and an intentional synonym miss. Use `--sizes 20 100 --repeats 3` to adjust within bounded limits. No models, real files or network are involved.

A local macOS/Python 3.9.6 run on 24 November 2026 found 9/9 exact-locator hits for each size, with median query times about 3 ms, 13 ms and 37 ms respectively. These two-line sources and exact identifiers are deliberately simple; they do not measure semantic recall, large transcript behavior, model answer quality or performance on another laptop. Re-run before sizing a real deployment.

Consider an optional index only after measuring representative permitted exports and missed questions. Evaluate recall, source attribution, byte/token budget, latency, revision invalidation and privacy together. PageIndex and other retrieval approaches are research directions, not installed or benchmarked adapters. See [architecture and sources](architecture.md).
