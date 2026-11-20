# Which database candidates fit Raw Payloads, common Posts and Metric Snapshots?

Research for issue #6. Researched 2026-11-20. Terms (Brand, Handle, Post, Raw Payload, Metric Snapshot, Collection Run, Tracking Window) as defined in `GLOSSARY.md`.

**Scope:** this note produces a shortlist only. The final database choice is made in the prototype ticket (#8).

## TL;DR

- **The data is mostly relational, with JSON at one edge.** Brand → Handle → Post → Metric Snapshot is a strict hierarchy that the UI filters and aggregates across. Only the Raw Payload is opaque JSON. "The APIs return JSON" argues for a good JSON column type, not for a document database.
- **The volume is small.** At the reference load, about 31 M Metric Snapshots and about 0.55 M Posts per year (see the estimate below). A single, unremarkable PostgreSQL instance handles this without a time-series engine.
- **Shortlist for #8:**
  1. **PostgreSQL** with `jsonb` for Raw Payloads, normal tables for Brand/Handle/Post, and an append-only `metric_snapshot` table, range-partitioned by month if needed. **Recommended.**
  2. **MongoDB** with regular collections, plus a time series collection for Metric Snapshots. This is the challenger that tests the "NoSQL because JSON" assumption directly.
- **TimescaleDB is not on the shortlist.** It remains an optional PostgreSQL extension to add later if snapshot volume grows by an order of magnitude. The features that make it worth having are under the Timescale License, and the CloudNativePG extension image ships only the Apache-2 edition (details below).
- **ClickHouse and Cassandra are out.** Both are poor fits for the relational part and for the update-in-place Post refresh.

## Data volume estimate

Reference load: 500 Handles × ~3 new Posts/day each, Tracking Window 14 days, 4 Collection Runs/day. These are back-of-envelope figures, not measurements.

| Quantity | Formula | Result |
|---|---|---|
| New Posts / day | 500 × 3 | 1,500 |
| New Posts / year | 1,500 × 365 | ~0.55 M rows |
| Tracked Posts at any moment | 1,500 × 14 | ~21,000 |
| Metric Snapshots / day | 21,000 × 4 | ~84,000 |
| **Metric Snapshots / year** | 84,000 × 365 | **~31 M rows** |
| Snapshots / year with a 100-day window (worst case, if made the default) | 1,500 × 100 × 4 × 365 | ~219 M rows |
| Snapshot storage / year (~100–150 B/row incl. index, narrow row: post id, timestamp, ~6 counters) | 31 M × ~0.12 kB | ~3–5 GB |
| Raw Payload storage / year, **one payload per Post** (assume ~2–10 kB of JSON each) | 0.55 M × ~5 kB | ~3 GB |
| Raw Payload storage / year, **one payload per fetch** (every Collection Run) | 31 M × ~5 kB | ~150 GB before compression |

The 100-day Tracking Window Override is a one-off manual Collection Run, so it adds a spike, not a steady rate.

The biggest unknown is not the database. It is **whether a Raw Payload is kept once per Post (or per change) or once per fetch.** That choice changes storage by roughly 50×. It is raised as an open question at the end.

## The three data shapes

| Shape | Nature | Access pattern |
|---|---|---|
| Brand / Handle / Post (common model) | Relational hierarchy, small to medium, Posts updated in place on refresh | Filter by Brand, Handle, Platform and date range; joins up the hierarchy |
| Raw Payload | Opaque JSON per Platform, schema owned by the Platform | Write once, read rarely (debugging, re-mapping into Post); occasional ad-hoc queries |
| Metric Snapshot | Append-only time series, narrow rows, never overwritten | Range scan for one Post; aggregate per Handle or Brand per day or week |

## Candidates

### 1. PostgreSQL (plain, with JSONB)

**Raw Payload.** PostgreSQL has a `jsonb` type: "stored in a decomposed binary format that makes it slightly slower to input ... but significantly faster to process", and it supports indexing ([PG JSON types](https://www.postgresql.org/docs/current/datatype-json.html)). There is one caveat for a field defined as "exactly as received": `jsonb` "does not preserve white space, does not preserve the order of object keys" and keeps only the last value of a duplicate key. The `json` type instead stores "an exact copy of the input text" ([same page](https://www.postgresql.org/docs/current/datatype-json.html)). If byte-exact fidelity matters, use `json` or `text` for the archive copy. Otherwise `jsonb` is the documented default recommendation.

**Querying JSON.** GIN indexes on `jsonb` support containment and existence queries, using either `jsonb_ops` or the smaller `jsonb_path_ops`. Expression indexes such as `GIN ((jdoc -> 'tags'))` are "likely to be smaller and faster" for known paths ([PG JSON indexing](https://www.postgresql.org/docs/current/datatype-json.html)). The UI does not need any of this, because it queries the common Post. It is a nice-to-have for ad-hoc investigation.

**Large values.** Payloads over about 2 kB are compressed and/or moved out of line transparently by TOAST, once a row is wider than `TOAST_TUPLE_THRESHOLD` (normally 2 kB). Compression is configurable per column ([PG TOAST](https://www.postgresql.org/docs/current/storage-toast.html)). Raw Payloads therefore do not bloat the main heap that Post queries scan, as long as they live in their own table or column.

**Metric Snapshot.** This is a plain append-only table, with a unique key on (post, Collection Run) so a retried Collection Run cannot double-write. At around 31 M rows/year, a B-tree on `(post_id, observed_at)` serves the per-Post chart. Optional extras:
- **Declarative range partitioning** by month. Dropping or detaching old partitions "entirely avoid[s] the VACUUM overhead caused by a bulk DELETE", and partition pruning skips irrelevant months. Caveats: new partitions must be created ahead of time ("an appropriate partition must be added manually"), and unique keys must include the partition key ([PG partitioning](https://www.postgresql.org/docs/current/ddl-partitioning.html)).
- **BRIN** on `observed_at`. It is "designed for handling very large tables in which certain columns have some natural correlation with their physical location", which is exactly the shape of append-only timestamps ([PG BRIN](https://www.postgresql.org/docs/current/brin.html)).

**Aggregated charts** (per Handle or Brand per day). A SQL `GROUP BY date_trunc(...)` over snapshots joined to Post and Handle. If that gets slow, a materialized rollup table refreshed after each Collection Run is enough at this volume.

**Spring (Boot 4.2.0, Java 25).** Spring Boot 4.2.0 requires Java 17+ and is compatible up to Java 27 ([Boot system requirements](https://docs.spring.io/spring-boot/system-requirements.html)). Boot 4.2.0 manages `spring-data-jpa` 4.2.0, `hibernate-core` 7.4.15.Final, the `org.postgresql:postgresql` driver 42.7.14, Flyway 12.11.0, Liquibase 5.0.4 and `testcontainers-postgresql` 2.0.5 ([Boot dependency versions](https://docs.spring.io/spring-boot/appendix/dependency-versions/coordinates.html)). Hibernate provides a JSON JDBC type mapping, `JsonJdbcType` ("Specialized type mapping for JSON and the JSON SQL data type") ([Hibernate Javadoc](https://docs.hibernate.org/orm/7.1/javadocs/org/hibernate/type/descriptor/jdbc/JsonJdbcType.html)). The Raw Payload column can be mapped with `@JdbcTypeCode(SqlTypes.JSON)` and a JSON library (Jackson) on the classpath. That annotation is common practice; the Hibernate guide covers it under "Mapping embeddable types to UDTs or to JSON" ([Hibernate Introduction](https://docs.hibernate.org/orm/7.0/introduction/html_single/Hibernate_Introduction.html)). Time-bucket aggregate queries are easier as native SQL or `JdbcClient` than as JPQL.

**Local.** Spring Boot Docker Compose support auto-detects containers named `postgres` (`JdbcConnectionDetails`) ([Boot dev services](https://docs.spring.io/spring-boot/reference/features/dev-services.html)).

**Kubernetes.** CloudNativePG is an Apache-2.0 operator and a CNCF Incubating project ([CNPG repo](https://github.com/cloudnative-pg/cloudnative-pg)). It also manages `Backup`, `Pooler`, `Database` and `ImageCatalog` resources ([same](https://github.com/cloudnative-pg/cloudnative-pg)).

**Licensing.** PostgreSQL License (permissive).

**Team familiarity cost (judgment).** Lowest. JPA and SQL are the default Spring path, and the relational model maps one-to-one onto the glossary.

### 2. PostgreSQL + TimescaleDB (extension on candidate 1)

**What it adds.** Hypertables are "PostgreSQL tables that automatically partition your time-series data by time" into chunks ([Timescale hypertables](https://www.tigerdata.com/docs/use-timescale/latest/hypertables)). This removes the manual partition creation that plain PostgreSQL requires. Continuous aggregates are "a kind of hypertable that is refreshed automatically in the background", built on `time_bucket` and incrementally maintained. Real-time aggregation is off by default since v2.13 ([continuous aggregates](https://www.tigerdata.com/docs/use-timescale/latest/continuous-aggregates/about-continuous-aggregates)). Together these are a natural fit for the per-Handle and per-Brand metric charts.

**Licensing catch.** Per the editions page, **continuous aggregates, columnstore/compression ("Hypercore") and retention policies are Community Edition only (Timescale License, TSL)**. The Apache-2 edition has only core hypertable operations such as `create_hypertable` and `drop_chunks`. The TSL forbids selling the Community Edition as a service ([Timescale editions](https://www.tigerdata.com/docs/about/latest/timescaledb-editions)). That is fine for an internal tool, but it matters if the harvester is ever offered to customers as a hosted product (see the minimal owner hook on the map).

**Kubernetes catch.** Timescale's own Helm charts repo was "archived by the owner on Jan 18, 2024" and is "no longer maintained" ([timescale/helm-charts](https://github.com/timescale/helm-charts)). The vendor's current guide runs TimescaleDB on CloudNativePG as an extension container, `ghcr.io/cloudnative-pg/timescaledb-oss`, and needs Kubernetes 1.31+ with the `ImageVolume` feature gate ([Tiger Data CNPG guide](https://www.tigerdata.com/docs/integrate/configuration-deployment/cloudnativepg)). CloudNativePG lists that image as **"TimescaleDB Apache-2 Edition"** ([CNPG extension containers](https://github.com/cloudnative-pg/postgres-extensions-containers)). **The easy Kubernetes path therefore lacks continuous aggregates, compression and retention policies**, the features that justify TimescaleDB here. Getting them needs a custom or community image.

**Local.** Spring Boot's Docker Compose detection does not list a Timescale image. A custom image can be made to work with the `org.springframework.boot.service-connection: postgres` label if it behaves like the standard image ([Boot dev services](https://docs.spring.io/spring-boot/reference/features/dev-services.html)).

**Verdict.** It is overkill at ~31 M rows/year. It stays an upgrade path that does not change the schema: the same tables, with `create_hypertable` on `metric_snapshot` later.

### 3. MongoDB (regular collections + time series collection)

**Raw Payload.** This is the natural fit: store the API response as a document as-is. This is where the "APIs return JSON" intuition is correct.

**Common Post model.** Workable as documents, with optional `$jsonSchema` validation that rejects invalid inserts and updates by default ([Mongo schema validation](https://www.mongodb.com/docs/manual/core/schema-validation/)). However, Brand → Handle → Post filtering and per-Brand aggregation need either denormalization (copying `brandId` and `platform` onto each Post and snapshot) or `$lookup`.

**Metric Snapshot.** Time series collections use columnar, compressed bucket storage with an automatic compound index on `metaField` + `timeField` ([Mongo time series](https://www.mongodb.com/docs/manual/core/timeseries-collections/)). That is a good shape for snapshots, with `metaField = {postId, handleId, brandId, platform}`. The documented limitations matter for this design ([Mongo time series limitations](https://www.mongodb.com/docs/manual/core/timeseries/timeseries-limitations/)):
- **No unique indexes.** A retried Collection Run cannot be made idempotent by a unique constraint.
- **"You cannot write to time series collections in transactions."** Upserting the Post and appending its snapshot cannot be atomic.
- **No schema validation and no change streams.**
- **Updates can only match on and modify the `metaField`.** If a Post moves Handle or Brand (re-assignment), fixing old snapshots is limited.
- **`timeField` and `metaField` are fixed at creation, and a collection cannot be converted to or from time series.**

**Spring.** Spring Boot auto-configures `MongoClient` and `MongoTemplate` via `spring-boot-starter-data-mongodb` ([Boot NoSQL](https://docs.spring.io/spring-boot/reference/data/nosql.html)). Boot 4.2.0 manages `spring-data-mongodb` 5.2.0, `mongodb-driver-sync` 5.13.0 and `testcontainers-mongodb` 2.0.5 ([Boot dependency versions](https://docs.spring.io/spring-boot/appendix/dependency-versions/coordinates.html)). Spring Data MongoDB supports time series collections through `@TimeSeries` or `CollectionOptions.timeSeries(...)`, including `expireAfter` ([Spring Data MongoDB](https://docs.spring.io/spring-data/mongodb/reference/mongodb/template-collection-management.html)).

**Local.** Docker Compose auto-detects containers named `mongo` ([Boot dev services](https://docs.spring.io/spring-boot/reference/features/dev-services.html)).

**Kubernetes.** The MongoDB Controllers for Kubernetes (MCK) operator is Apache-2.0, manages Community Edition replica sets, and replaces the old Community Operator, whose best-effort support ended in November 2025 ([mongodb-kubernetes](https://github.com/mongodb/mongodb-kubernetes)).

**Licensing.** MongoDB Community Server is under the SSPL. The SSPL is "not ... approved by the OSI". Its Section 13 copyleft applies only when offering MongoDB itself as a service to third parties, and "There is no copyleft condition for other SaaS applications that use MongoDB as a database" ([SSPL FAQ](https://www.mongodb.com/legal/licensing/server-side-public-license/faq)). That is fine for this tool, but some organisations ban non-OSI licences by policy.

**Team familiarity cost (judgment).** Medium. Spring Data MongoDB repositories feel like JPA. However, relational-style UI queries become aggregation pipelines, and the team must design for denormalization.

### 4. Others, briefly

- **ClickHouse.** An excellent engine for snapshot analytics, and Boot even detects `clickhouse/clickhouse-server` containers ([Boot dev services](https://docs.spring.io/spring-boot/reference/features/dev-services.html)). But updating a Post in place relies on patterns like ReplacingMergeTree, where "Data deduplication occurs only during a merge" and "it does not guarantee the absence of duplicates", so `FINAL` is needed for correct reads ([ClickHouse ReplacingMergeTree](https://clickhouse.com/docs/engines/table-engines/mergetree-family/replacingmergetree)). It is a poor home for the relational model. Out of scope at this volume; possibly a future analytics side-store.
- **Cassandra.** Modeling is "query-driven"; "joins are not supported ... so all required fields must be grouped together in a single table" and data is denormalized per query ([Cassandra data modeling](https://cassandra.apache.org/doc/latest/cassandra/developing/data-modeling/intro.html)). It is built for write volumes orders of magnitude above ~84 k rows/day, and a bad fit for ad-hoc Brand/Handle/date filtering. Out.

## Comparison

| Criterion | PostgreSQL (JSONB) | PG + TimescaleDB | MongoDB (+ time series) |
|---|---|---|---|
| Raw Payload | Good (`jsonb`; `json`/`text` if byte-exact) | Same as PG | Best (native document) |
| Brand/Handle/Post model | Best (FKs, joins, constraints) | Same as PG | OK (denormalize or `$lookup`) |
| Metric Snapshot | Good at ~31 M rows/yr; partition by month if needed | Best (hypertables, continuous aggregates; TSL) | Good storage, but no unique index or transactional writes |
| UI: Posts by Brand/Handle/Platform/date | Plain SQL + indexes | Same | Needs denormalized fields + compound indexes |
| UI: per-Post chart | Index range scan | Same | `metaField` + time index |
| UI: per-Handle/Brand aggregate chart | `GROUP BY date_trunc`, rollup table if needed | Continuous aggregate (TSL) | Aggregation pipeline over time series |
| Spring Boot 4.2 support | First-class (JPA 4.2, Hibernate 7.4, Flyway) | Same, plus native SQL for TS functions | First-class (Spring Data MongoDB 5.2) |
| Local (Docker Compose) | Auto-detected | Custom label needed | Auto-detected |
| Kubernetes | CloudNativePG (Apache-2, CNCF) | CNPG + extension image (Apache-2 edition only) | MCK operator (Apache-2) |
| Licence | PostgreSQL (permissive) | Apache-2 core / TSL for key features | SSPL (non-OSI; internal use fine) |
| Familiarity cost (judgment) | Low | Low-medium | Medium |

## Recommendation for the prototype ticket (#8)

Prototype **PostgreSQL (JSONB)** as the primary candidate and **MongoDB** as the challenger, using the same small slice in each:
1. Store one YouTube Post with its Raw Payload.
2. Append Metric Snapshots across simulated Collection Runs.
3. Query Posts by Brand, Handle, Platform and date.
4. Render a per-Post and a per-Brand daily metric series.

Seed ~31 M synthetic snapshots (one year at the reference load) to check the aggregate-query latency of both.

Expected outcome (judgment, to be confirmed by #8): PostgreSQL wins on the relational model, idempotent snapshot writes and operational simplicity, while matching MongoDB on JSON storage. Keep TimescaleDB as a later, schema-compatible upgrade.

## Open questions raised

1. **Raw Payload granularity.** Is the Raw Payload stored once per Post (first or latest fetch), only when it changes, or on every fetch? This drives storage by about 50× (~3 GB vs ~150 GB/yr). The glossary ("The Platform's response for a Post exactly as received") does not settle it.
2. **"Exactly as received".** Is semantic JSON equality enough (`jsonb` reorders keys and drops duplicates), or must the bytes be preserved?
3. **Snapshot retention and downsampling.** Snapshots "accumulate indefinitely". Is it acceptable to downsample Frozen Posts' history later, for example to daily, or must every snapshot be kept forever?
4. **Aggregation semantics for Handle/Brand charts.** A per-Handle "views on day D" is presumably the sum over Posts of each Post's *latest* snapshot that day. That last-value-per-Post-then-sum definition should be pinned down before choosing indexes or rollups.
5. **Hosted-product future.** If the harvester is ever offered to customers as a service, re-check the TimescaleDB TSL and SSPL terms.
