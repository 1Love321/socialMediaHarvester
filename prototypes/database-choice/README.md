# PROTOTYPE (throwaway): Which database do we use?

Answers [Which database do we use? Prototype with real YouTube data](https://github.com/rahmed12/socialMediaHarvester/issues/8).
**Verdict: PostgreSQL** (ADR 0007 on `main`). This branch is never merged; it is kept as the primary source.

## What it does

| File | Who runs it | What |
|---|---|---|
| `setup.sh` | human | venv with `pgserver` (bundles PostgreSQL 16.2 binaries), `psycopg`, `pymongo`; MongoDB 8.0.4 tarball. Everything in `PROTOTYPE-wipe-me/` (git-ignored). |
| `fetch_youtube.py` | human (key via hidden prompt, never saved) | One real fetch of `@salahm8765` and `@NBA`: channel, 20 uploads-playlist pages, `videos.list` for the newest 200, Shorts probe, max-ids probes. Raw responses + `findings.json`. ~50 units. |
| `load_and_query.py real` | agent | Loads the real fetch plus synthetic history (4 runs/day, 14-day Tracking Window, Raw Payload per fetch, 30-day payload retention) into both DBs; runs the queries. |
| `load_and_query.py scale` | agent | Adds one year at the reference load: 50 Brands, 500 Handles, 3 Posts/Handle/day, ~30M Metric Snapshots, ~3M Raw Payloads. ~35 min. |
| `load_and_query.py queries --handle @synthetic_0_0` | agent | Re-runs Q1-Q7 against a Handle with a full year of history. |

## Environment workarounds (dev container: no Docker, no sudo, runs as root)

- **No Docker**, so PostgreSQL comes from the `pgserver` wheel and MongoDB from the official tarball.
- **PostgreSQL refuses to run as root.** `pgserver`'s own wrapper failed here (`OSError: [Errno 5] Input/output error` on `initdb`), so the binaries are run directly via `runuser -u pgserver` (a system user `pgserver` is created with `useradd -r`).
- **Unix socket path too long.** The repo path exceeds Linux's ~107-char socket path limit, so the socket goes to `/tmp` (`-k /tmp`) and the log to `/tmp/pgproto.log`. PostgreSQL listens on `127.0.0.1:55432`.
- **`/dev/shm` is 64 MB**, which breaks parallel queries (`could not resize shared memory segment`); start with `-c dynamic_shared_memory_type=mmap`.
- **`pg_ctl start` launched from Python fails in this sandbox** although the same command works from a shell, so start it by hand:
  ```
  B=$PWD/PROTOTYPE-wipe-me/venv/lib/python3.11/site-packages/pgserver/pginstall/bin
  runuser -u pgserver -- $B/pg_ctl -D $PWD/PROTOTYPE-wipe-me/pgdata -l /tmp/pgproto.log -w -o "-p 55432 -k /tmp -c listen_addresses=127.0.0.1 -c shared_buffers=2GB -c work_mem=64MB -c maintenance_work_mem=1GB -c max_wal_size=8GB -c effective_cache_size=8GB -c random_page_cost=1.1 -c dynamic_shared_memory_type=mmap" start
  ```
- PostgreSQL got `shared_buffers=2GB` because MongoDB's cache defaults to ~50% of RAM; stock 128 MB would be an unfair comparison.
- MongoDB runs as a one-node replica set on `127.0.0.1:27199` (needed to test transactions).
- MongoDB needed an extra index `{meta.postId, observedAt}` on the time series collection, or Q3 was a collection scan.

## Results (2026-11-23; 4 cores, 19 GB RAM)

30.1M Metric Snapshots, 547,566 Posts, 3.0M Raw Payloads. Best of 3 runs, warm cache. Both databases returned identical results.

| | PostgreSQL 16 | MongoDB 8.0 |
|---|---|---|
| Q1 Posts by Brand, last 14 days, + current metrics (50) | **0.9 ms** | 20 ms (`$lookup` into time series) |
| Q2 Posts by Handle, last 14 days (50) | **0.1 ms** | 0.3 ms |
| Q3 Metric history of one Post (56 snapshots) | **0.2 ms** | 0.7 ms |
| Q4 Per-Handle daily views (latest per Post per day), 30 days | 46 ms | **6 ms** |
| Q5 Raw Payloads due in tomorrow's deletion run (82,647) | **9.6 s** | 40 s |
| Q6 Retried run writes the same snapshot twice | **rejected by `UNIQUE (post_id, run_id, label)`** | 2 copies stored; time series refuse unique indexes |
| Q7 Post update + snapshot in one transaction | **OK** | refused: no transactional writes to time series |
| Storage | 11.7 GB (raw_payload 6.1, metric_snapshot 5.6) | **1.7 GB** (raw_payloads 1.2, metric_snapshots 0.4) |
| Bulk load of the year | 21 min | **8 min** |

- PostgreSQL compresses a value only above ~2 KB (TOAST threshold). Real YouTube payloads average **1.8 KB** in `jsonb`, so they are stored uncompressed; `toast_tuple_target=128` did not change that, and this build lacks lz4. Synthetic payloads are near-copies of one template, which flatters MongoDB's block compression.
- Neither TTL nor any index expresses "delete after 30 days except the latest per Post/Handle", so both need a scheduled job (Q5).

## YouTube facts confirmed with real data

- Uploads playlist is **newest-first**: 0 inversions across 1,000 `@NBA` items (`contentDetails.videoPublishedAt`).
- It **includes Shorts** (22 of the newest 60 `@NBA` uploads answer 200 on `youtube.com/shorts/<id>`; both `@salahm8765` uploads are Shorts) and **live streams** (9 of 200 have `liveStreamingDetails`).
- **Max 50 ids** per `videos.list` and per `videos:batchGetStats` (51 → HTTP 400). The path is `videos:batchGetStats`.
- `videos:batchGetStats` without `part` returns only `id` + `etag`, no statistics.
- `@NBA` posts **~41 Posts/day** (1,000 uploads 2026-10-30 → 2026-11-23), far above the 3/day reference load.
- Analytics API quota: 100,000 queries/day, 720/min (recorded in the setup ticket, #7).
