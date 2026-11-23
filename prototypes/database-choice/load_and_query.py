#!/usr/bin/env python3
"""PROTOTYPE (throwaway) for "Which database do we use?" (issue #8).

Loads the same Brands / Handles / Posts / Raw Payloads / Metric Snapshots into
PostgreSQL (jsonb + relational + append-only snapshot table) and MongoDB
(collections + time series collection), then runs the UI's key queries on both
and prints timings, row counts and plan summaries.

    venv/bin/python load_and_query.py real      # wipe, load the real YouTube fetch + synthetic history, query
    venv/bin/python load_and_query.py scale     # add ~31M synthetic snapshots (1 year at the reference load), query
    venv/bin/python load_and_query.py queries   # just re-run the queries
    venv/bin/python load_and_query.py stop      # stop both servers

Everything lives in PROTOTYPE-wipe-me/. Delete that directory to wipe it.
"""
import argparse, copy, datetime as dt, json, random, subprocess, sys, time
from pathlib import Path

import psycopg, psycopg.types.json, pymongo
from pymongo.errors import OperationFailure

HERE = Path(__file__).resolve().parent
SCRATCH = HERE / "PROTOTYPE-wipe-me"
YT = SCRATCH / "youtube"
MONGOD = next((SCRATCH / "bin").glob("mongodb-linux-*/bin/mongod"), None)
MONGO_PORT = 27199
UTC = dt.timezone.utc
NOW = dt.datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
RUN_EVERY = dt.timedelta(hours=6)          # 4 Collection Runs/day
WINDOW = dt.timedelta(days=14)             # Tracking Window
PAYLOAD_TTL = dt.timedelta(days=30)        # Raw Payloads kept 30 days except the latest
BRAND_OF = {"@NBA": "NBA", "@salahm8765": "Test Brand"}


# ---------------------------------------------------------------- servers
PG_BIN = next(SCRATCH.glob("venv/lib/python*/site-packages/pgserver/pginstall/bin"))  # PG 16 from the pgserver wheel
PG_PORT = 55432
PG_OPTS = ("-c listen_addresses=127.0.0.1 -c shared_buffers=2GB -c work_mem=64MB -c maintenance_work_mem=1GB "
           "-c max_wal_size=8GB -c effective_cache_size=8GB -c random_page_cost=1.1 -c dynamic_shared_memory_type=mmap")  # /dev/shm is tiny in this container


def as_pg_user(*cmd):
    # postgres refuses to run as root; pgserver's own wrapper failed here (EIO), so run its binaries via runuser
    return subprocess.run(["runuser", "-u", "pgserver", "--", *cmd], check=True, capture_output=True, text=True)


def pg():
    data = SCRATCH / "pgdata"
    if not (data / "PG_VERSION").exists():
        subprocess.run(["useradd", "-r", "pgserver"], check=False, capture_output=True)
        data.mkdir(exist_ok=True)
        subprocess.run(["chown", "pgserver:", str(data)], check=True)
        as_pg_user(str(PG_BIN / "initdb"), "-D", str(data), "--auth=trust", "--encoding=utf8", "-U", "postgres")
    if subprocess.run(["runuser", "-u", "pgserver", "--", str(PG_BIN / "pg_ctl"), "-D", str(data), "status"],
                      capture_output=True).returncode != 0:
        as_pg_user(str(PG_BIN / "pg_ctl"), "-D", str(data), "-l", "/tmp/pgproto.log", "-w",
                   "-o", f"-p {PG_PORT} -k /tmp {PG_OPTS}", "start")  # socket path must be <107 chars
    conn = psycopg.connect(host="127.0.0.1", port=PG_PORT, user="postgres", dbname="postgres", autocommit=True)
    conn.execute("SET TimeZone='UTC'")
    return conn


def mongo():
    (SCRATCH / "mongodata").mkdir(parents=True, exist_ok=True)
    c = pymongo.MongoClient(port=MONGO_PORT, directConnection=True, serverSelectionTimeoutMS=1500)
    try:
        c.admin.command("ping")
    except Exception:
        subprocess.run([str(MONGOD), "--dbpath", str(SCRATCH / "mongodata"), "--port", str(MONGO_PORT),
                        "--bind_ip", "127.0.0.1", "--replSet", "rs0", "--fork",
                        "--logpath", str(SCRATCH / "mongod.log")], check=True, stdout=subprocess.DEVNULL)
        c = pymongo.MongoClient(port=MONGO_PORT, directConnection=True)
    try:
        c.admin.command("replSetInitiate", {"_id": "rs0", "members": [{"_id": 0, "host": f"127.0.0.1:{MONGO_PORT}"}]})
        time.sleep(2)
    except OperationFailure:
        pass  # already initiated
    for _ in range(30):
        if c.admin.command("hello").get("isWritablePrimary"):
            break
        time.sleep(0.5)
    return c.harvester


def stop():
    try:
        pymongo.MongoClient(port=MONGO_PORT, directConnection=True).admin.command("shutdown")
    except Exception:
        pass
    subprocess.run(["runuser", "-u", "pgserver", "--", str(PG_BIN / "pg_ctl"), "-D", str(SCRATCH / "pgdata"),
                    "-m", "fast", "stop"], check=False)
    print("stopped")


# ---------------------------------------------------------------- schemas
PG_SCHEMA = """
DROP TABLE IF EXISTS metric_snapshot, handle_snapshot, post, raw_payload, collection_run, handle, brand CASCADE;
CREATE TABLE brand (id bigint PRIMARY KEY, name text NOT NULL);
CREATE TABLE handle (id bigint PRIMARY KEY, brand_id bigint NOT NULL REFERENCES brand, platform text NOT NULL,
  handle text NOT NULL, platform_account_id text, UNIQUE (platform, handle));
CREATE TABLE collection_run (id bigint PRIMARY KEY, started_at timestamptz NOT NULL);
CREATE TABLE raw_payload (id bigint PRIMARY KEY, platform text NOT NULL, subject text NOT NULL,  -- post|handle
  subject_id bigint NOT NULL, label text NOT NULL, endpoint text NOT NULL, api_version text NOT NULL,
  fetched_at timestamptz NOT NULL, payload jsonb NOT NULL);
CREATE INDEX ON raw_payload (fetched_at);
CREATE INDEX ON raw_payload (subject, subject_id, fetched_at DESC);
CREATE TABLE post (id bigint PRIMARY KEY, handle_id bigint NOT NULL REFERENCES handle, platform text NOT NULL,
  platform_post_id text NOT NULL, published_at timestamptz NOT NULL, permalink text, title text, post_type text,
  native_type text, duration text, latest_payload_id bigint, first_seen_at timestamptz, last_seen_at timestamptz,
  UNIQUE (platform, platform_post_id));
CREATE INDEX ON post (handle_id, published_at DESC);
CREATE TABLE metric_snapshot (id bigint PRIMARY KEY, post_id bigint NOT NULL REFERENCES post,
  run_id bigint NOT NULL REFERENCES collection_run, label text NOT NULL, observed_at timestamptz NOT NULL,
  views bigint, likes bigint, comments bigint, shares bigint, saves bigint, reach bigint,
  watch_time_seconds numeric, average_view_duration_seconds numeric, raw_payload_id bigint,
  UNIQUE (post_id, run_id, label));
CREATE INDEX ON metric_snapshot (post_id, observed_at);
CREATE TABLE handle_snapshot (id bigint PRIMARY KEY, handle_id bigint NOT NULL REFERENCES handle,
  run_id bigint NOT NULL REFERENCES collection_run, observed_at timestamptz NOT NULL,
  followers bigint, posts bigint, raw_payload_id bigint, UNIQUE (handle_id, run_id));
"""


def mongo_schema(db):
    db.client.drop_database("harvester")
    db.create_collection("metric_snapshots", timeseries={
        "timeField": "observedAt", "metaField": "meta", "granularity": "hours"})
    db.posts.create_index([("platform", 1), ("platformPostId", 1)], unique=True)
    db.posts.create_index([("brandId", 1), ("publishedAt", -1)])
    db.posts.create_index([("handleId", 1), ("publishedAt", -1)])
    db.raw_payloads.create_index("fetchedAt")
    db.raw_payloads.create_index([("subject", 1), ("subjectId", 1), ("fetchedAt", -1)])
    db.handle_snapshots.create_index([("handleId", 1), ("runId", 1)], unique=True)
    db.metric_snapshots.create_index([("meta.handleId", 1), ("observedAt", 1)])
    db.metric_snapshots.create_index([("meta.postId", 1), ("observedAt", 1)])


# ---------------------------------------------------------------- writer (same rows to both)
class Writer:
    """Buffers rows and writes identical data to PG (COPY) and Mongo (insert_many)."""
    COLS = {
        "brand": ["id", "name"],
        "handle": ["id", "brand_id", "platform", "handle", "platform_account_id"],
        "collection_run": ["id", "started_at"],
        "raw_payload": ["id", "platform", "subject", "subject_id", "label", "endpoint", "api_version", "fetched_at", "payload"],
        "post": ["id", "handle_id", "platform", "platform_post_id", "published_at", "permalink", "title", "post_type",
                 "native_type", "duration", "latest_payload_id", "first_seen_at", "last_seen_at"],
        "metric_snapshot": ["id", "post_id", "run_id", "label", "observed_at", "views", "likes", "comments", "shares",
                            "saves", "reach", "watch_time_seconds", "average_view_duration_seconds", "raw_payload_id"],
        "handle_snapshot": ["id", "handle_id", "run_id", "observed_at", "followers", "posts", "raw_payload_id"],
    }
    ORDER = list(COLS)  # FK order

    def __init__(self, conn, db, flush_at=50_000):
        self.conn, self.db, self.flush_at = conn, db, flush_at
        self.buf = {t: [] for t in self.COLS}
        self.ctx = {}  # post_id/handle_id -> denormalized fields for Mongo
        self.n = {t: 0 for t in self.COLS}
        self.t_pg = self.t_mongo = 0.0
        self.pending = 0

    def add(self, table, row):
        self.buf[table].append(row)
        self.pending += 1

    def maybe_flush(self):
        """Call only at a Post boundary, so a Post and its snapshots land in the same flush."""
        if self.pending >= self.flush_at:
            self.flush()

    def flush(self):
        for t in self.ORDER:
            rows = self.buf[t]
            if not rows:
                continue
            cols = self.COLS[t]
            t0 = time.perf_counter()
            with self.conn.cursor() as cur, cur.copy(f"COPY {t} ({','.join(cols)}) FROM STDIN") as cp:
                for r in rows:
                    cp.write_row([psycopg.types.json.Jsonb(r[c]) if c == "payload" else r[c] for c in cols])
            t1 = time.perf_counter()
            self.db[self.mongo_coll(t)].insert_many([self.to_mongo(t, r) for r in rows], ordered=False)
            self.t_pg += t1 - t0
            self.t_mongo += time.perf_counter() - t1
            self.n[t] += len(rows)
            self.buf[t] = []
        self.pending = 0

    @staticmethod
    def mongo_coll(t):
        return {"brand": "brands", "handle": "handles", "collection_run": "collection_runs",
                "raw_payload": "raw_payloads", "post": "posts", "metric_snapshot": "metric_snapshots",
                "handle_snapshot": "handle_snapshots"}[t]

    def to_mongo(self, t, r):
        camel = lambda s: s.split("_")[0] + "".join(w.title() for w in s.split("_")[1:])
        if t == "metric_snapshot":
            p = self.ctx[("post", r["post_id"])]
            d = {"_id": r["id"], "observedAt": r["observed_at"], "runId": r["run_id"], "rawPayloadId": r["raw_payload_id"],
                 "meta": {"postId": r["post_id"], "handleId": p["handleId"], "brandId": p["brandId"],
                          "platform": p["platform"], "label": r["label"]}}
            for k in ("views", "likes", "comments", "shares", "saves", "reach",
                      "watch_time_seconds", "average_view_duration_seconds"):
                if r[k] is not None:
                    d[camel(k)] = r[k]
            return d
        d = {("_id" if k == "id" else camel(k)): v for k, v in r.items()}
        if t == "handle":
            self.ctx[("handle", r["id"])] = {"brandId": r["brand_id"], "platform": r["platform"]}
        if t == "post":  # denormalize brand onto Post (needed for "Posts by Brand" without $lookup)
            h = self.ctx[("handle", r["handle_id"])]
            d["brandId"] = h["brandId"]
            self.ctx[("post", r["id"])] = {"handleId": r["handle_id"], **h}
        return d


class Ids:
    def __init__(self, start=1):
        self.v = start

    def __call__(self):
        self.v += 1
        return self.v - 1


def runs_between(start, end):
    """Collection Run times on the 6-hour grid in [start, end]."""
    t = start.replace(hour=(start.hour // 6) * 6, minute=0, second=0, microsecond=0)
    if t < start:
        t += RUN_EVERY
    while t <= end:
        yield t
        t += RUN_EVERY


def run_id_for(t):
    """Grid ticks get hour-number ids; the real fetch (off-grid) gets a seconds-based id, so they never collide."""
    on_grid = t.minute == 0 and t.second == 0 and t.microsecond == 0 and t.hour % 6 == 0
    return int(t.timestamp()) // 3600 if on_grid else int(t.timestamp())


def growth(t, published, final, now=NOW):
    """Synthetic lifetime-to-date count at time t, rising toward `final` at `now`."""
    if final is None:
        return None
    age, total = (t - published).total_seconds(), max((now - published).total_seconds(), 1)
    return int(final * max(0.0, min(1.0, age / total)) ** 0.5)


# ---------------------------------------------------------------- real load
def load_real(w, ids):
    files = sorted(YT.glob("channel_*.json"))
    if not files:
        sys.exit(f"No fetch found in {YT}. Run fetch_youtube.py first.")
    brands, runs = {}, set()
    for f in files:
        doc = json.loads(f.read_text())
        ch = doc["response"]["items"][0]
        handle = "@" + f.stem.removeprefix("channel_")
        bname = BRAND_OF.get(handle, handle)
        if bname not in brands:
            brands[bname] = ids()
            w.add("brand", {"id": brands[bname], "name": bname})
        hid = ids()
        w.add("handle", {"id": hid, "brand_id": brands[bname], "platform": "youtube", "handle": handle,
                         "platform_account_id": ch["id"]})
        fetched = dt.datetime.fromisoformat(doc["fetchedAt"].replace("Z", "+00:00"))
        stats = ch["statistics"]
        # Handle Snapshot history: one per run over the last 30 days (synthetic except the last)
        for t in list(runs_between(fetched - PAYLOAD_TTL, fetched)) + [fetched]:
            rid = run_id_for(t)
            if rid not in runs:
                runs.add(rid); w.add("collection_run", {"id": rid, "started_at": t})
            pl = copy.deepcopy(ch)
            pl["statistics"]["subscriberCount"] = str(growth(t, fetched - dt.timedelta(days=3650),
                                                             int(stats.get("subscriberCount", 0)), fetched))
            pid = ids()
            w.add("raw_payload", {"id": pid, "platform": "youtube", "subject": "handle", "subject_id": hid,
                                  "label": "public", "endpoint": "channels.list", "api_version": "v3",
                                  "fetched_at": t, "payload": pl})
            w.add("handle_snapshot", {"id": ids(), "handle_id": hid, "run_id": rid, "observed_at": t,
                                      "followers": int(pl["statistics"]["subscriberCount"]),
                                      "posts": int(stats.get("videoCount", 0)), "raw_payload_id": pid})

        for vf in sorted(YT.glob(f"videos_{handle[1:]}_*.json")):
            vdoc = json.loads(vf.read_text())
            vfetched = dt.datetime.fromisoformat(vdoc["fetchedAt"].replace("Z", "+00:00"))
            for v in vdoc["response"].get("items", []):
                sn, st, cd = v["snippet"], v.get("statistics", {}), v.get("contentDetails", {})
                if sn.get("liveBroadcastContent") == "upcoming":
                    continue  # upcoming premieres/streams are skipped
                published = dt.datetime.fromisoformat(sn["publishedAt"].replace("Z", "+00:00"))
                post_id = ids()
                # history: every run from publish (max 14-day Tracking Window) to the real fetch
                times = [t for t in runs_between(max(published, vfetched - WINDOW), vfetched)] + [vfetched]
                last_payload = None
                snaps, payloads = [], []
                for i, t in enumerate(times):
                    last = i == len(times) - 1
                    vals = {k: growth(t, published, int(st[s]) if s in st else None, vfetched)
                            for k, s in (("views", "viewCount"), ("likes", "likeCount"), ("comments", "commentCount"))}
                    pl = copy.deepcopy(v)
                    pl["statistics"] = {s: str(vals[k]) for k, s in
                                        (("views", "viewCount"), ("likes", "likeCount"), ("comments", "commentCount"))
                                        if vals[k] is not None}
                    rp = ids()
                    payloads.append({"id": rp, "platform": "youtube", "subject": "post", "subject_id": post_id,
                                     "label": "public", "endpoint": "videos.list", "api_version": "v3",
                                     "fetched_at": t, "payload": pl})
                    rid = run_id_for(t)
                    if rid not in runs:
                        runs.add(rid); w.add("collection_run", {"id": rid, "started_at": t})
                    snaps.append({"id": ids(), "post_id": post_id, "run_id": rid, "label": "public", "observed_at": t,
                                  **vals, "shares": None, "saves": None, "reach": None, "watch_time_seconds": None,
                                  "average_view_duration_seconds": None, "raw_payload_id": rp})
                    last_payload = rp
                w.add("post", {"id": post_id, "handle_id": hid, "platform": "youtube", "platform_post_id": v["id"],
                               "published_at": published, "permalink": f"https://www.youtube.com/watch?v={v['id']}",
                               "title": sn.get("title"), "post_type": "live" if "liveStreamingDetails" in v else "video",
                               "native_type": "video", "duration": cd.get("duration"),
                               "latest_payload_id": last_payload, "first_seen_at": times[0], "last_seen_at": times[-1]})
                for p in payloads:
                    w.add("raw_payload", p)
                for s in snaps:
                    w.add("metric_snapshot", s)
                w.maybe_flush()
    w.flush()


# ---------------------------------------------------------------- synthetic scale load
def load_scale(w, ids, brands=50, handles_per_brand=10, posts_per_handle_day=3, days=365):
    """Reference load from the research ticket: 500 Handles x 3 Posts/day, 14-day window, 4 runs/day.
    One Raw Payload per fetch kept only for the last 30 days, plus the latest per Post (per ADR 0006)."""
    template = next(iter(json.loads(f.read_text())["response"]["items"]
                         for f in sorted(YT.glob("videos_NBA_*.json"))), [None])[0]
    if template is None:
        sys.exit("Need a real NBA videos payload as a template; run fetch_youtube.py.")
    rnd = random.Random(8)
    start = NOW - dt.timedelta(days=days)
    for t in runs_between(start, NOW):
        w.add("collection_run", {"id": run_id_for(t), "started_at": t})
    w.flush()  # (existing run ids from the real load may collide; COPY would fail, so skip those below)
    handles = []
    for b in range(brands):
        bid = ids()
        w.add("brand", {"id": bid, "name": f"Synthetic Brand {b}"})
        for h in range(handles_per_brand):
            hid = ids()
            handles.append(hid)
            w.add("handle", {"id": hid, "brand_id": bid, "platform": "youtube", "handle": f"@synthetic_{b}_{h}",
                             "platform_account_id": f"UCsynthetic{b}x{h}"})
    total_posts = len(handles) * posts_per_handle_day * days
    t0, made = time.perf_counter(), 0
    for d in range(days):
        day = start + dt.timedelta(days=d)
        for hid in handles:
            for k in range(posts_per_handle_day):
                published = day + dt.timedelta(seconds=rnd.randrange(86400))
                post_id = ids()
                final = {"views": rnd.randrange(100, 2_000_000)}
                final["likes"], final["comments"] = final["views"] // 30, final["views"] // 400
                times = list(runs_between(published, min(published + WINDOW, NOW)))
                if not times:
                    continue
                end = times[-1]
                latest = None
                for i, t in enumerate(times):
                    vals = {k2: growth(t, published, v, end) for k2, v in final.items()}
                    rp = None
                    if t >= NOW - PAYLOAD_TTL or i == len(times) - 1:
                        rp = ids()
                        pl = copy.deepcopy(template)
                        pl["id"] = f"syn{post_id}"
                        pl["statistics"] = {"viewCount": str(vals["views"]), "likeCount": str(vals["likes"]),
                                            "commentCount": str(vals["comments"])}
                        w.add("raw_payload", {"id": rp, "platform": "youtube", "subject": "post", "subject_id": post_id,
                                              "label": "public", "endpoint": "videos.list", "api_version": "v3",
                                              "fetched_at": t, "payload": pl})
                        latest = rp
                    w.add("metric_snapshot", {"id": ids(), "post_id": post_id, "run_id": run_id_for(t), "label": "public",
                                              "observed_at": t, **vals, "shares": None, "saves": None, "reach": None,
                                              "watch_time_seconds": None, "average_view_duration_seconds": None,
                                              "raw_payload_id": rp})
                # Post is added after its snapshots, but flush() writes tables in FK order and
                # maybe_flush() only runs at Post boundaries, so a Post and its snapshots always flush together.
                w.add("post", {"id": post_id, "handle_id": hid, "platform": "youtube",
                               "platform_post_id": f"syn{post_id}", "published_at": published,
                               "permalink": None, "title": f"Synthetic post {post_id}", "post_type": "video",
                               "native_type": "video", "duration": "PT1M", "latest_payload_id": latest,
                               "first_seen_at": times[0], "last_seen_at": end})
                w.maybe_flush()
                made += 1
        if d % 10 == 0:
            el = time.perf_counter() - t0
            print(f"  day {d}/{days}: {made:,}/{total_posts:,} posts, {w.n['metric_snapshot']:,} snapshots, "
                  f"{el:,.0f}s (pg {w.t_pg:,.0f}s, mongo {w.t_mongo:,.0f}s)", flush=True)
    w.flush()


# ---------------------------------------------------------------- queries
def timed(fn, repeat=3):
    best, out = None, None
    for _ in range(repeat):
        t0 = time.perf_counter()
        out = fn()
        el = (time.perf_counter() - t0) * 1000
        best = el if best is None else min(best, el)
    return best, out


def pg_plan(conn, sql, args):
    with conn.cursor() as cur:
        cur.execute("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + sql, args)
        p = cur.fetchone()[0][0]["Plan"]
    nodes = []
    def walk(n):
        nodes.append(n["Node Type"] + (f"({n['Index Name']})" if "Index Name" in n else ""))
        for c in n.get("Plans", []):
            walk(c)
    walk(p)
    return " > ".join(dict.fromkeys(nodes))


def mongo_plan(coll, pipeline):
    ex = coll.database.command("explain", {"aggregate": coll.name, "pipeline": pipeline, "cursor": {}},
                               verbosity="executionStats")
    s = json.dumps(ex, default=str)
    stages = [k for k in ("IXSCAN", "COLLSCAN", "FETCH", "SORT", "GROUP", "$lookup", "EXPRESS", "TS_MODIFY") if k in s]
    return ",".join(stages)


def queries(conn, db, handle="@NBA"):
    with conn.cursor() as cur:
        cur.execute("ANALYZE")
        cur.execute("SELECT h.id, b.id, h.handle FROM handle h JOIN brand b ON b.id=h.brand_id "
                    "WHERE h.handle=%s UNION ALL (SELECT h.id, b.id, h.handle FROM handle h "
                    "JOIN brand b ON b.id=h.brand_id ORDER BY h.id DESC LIMIT 1) LIMIT 1", (handle,))
        hid, bid, hname = cur.fetchone()
        cur.execute("SELECT id FROM post WHERE handle_id=%s ORDER BY (published_at < now() - interval '15 days') DESC, "
                    "published_at DESC LIMIT 1", (hid,))
        post_id = cur.fetchone()[0]
        counts = {t: cur.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in
                  ("brand", "handle", "post", "metric_snapshot", "raw_payload", "handle_snapshot")}
        size = cur.execute("SELECT pg_size_pretty(pg_database_size(current_database()))").fetchone()[0]
    mstats = db.command("dbStats")
    print(f"\nRows: {counts}\nPostgreSQL size: {size} | MongoDB size: {mstats['storageSize'] / 2**20:,.0f} MB "
          f"data + {mstats['indexSize'] / 2**20:,.0f} MB index  (Handle {hname}, Post id {post_id})")
    since, until = NOW - dt.timedelta(days=14), NOW + dt.timedelta(days=1)

    Q = []
    # Q1 Posts by Brand + date range, with current (latest Public) metrics, newest first, page of 50
    q1_sql = """SELECT p.id, p.title, p.published_at, s.views, s.likes, s.comments
      FROM post p JOIN handle h ON h.id=p.handle_id
      LEFT JOIN LATERAL (SELECT views, likes, comments FROM metric_snapshot m
                         WHERE m.post_id=p.id AND m.label='public' ORDER BY observed_at DESC LIMIT 1) s ON true
      WHERE h.brand_id=%s AND p.published_at >= %s AND p.published_at < %s
      ORDER BY p.published_at DESC LIMIT 50"""
    q1_mongo = [{"$match": {"brandId": bid, "publishedAt": {"$gte": since, "$lt": until}}},
                {"$sort": {"publishedAt": -1}}, {"$limit": 50},
                {"$lookup": {"from": "metric_snapshots", "let": {"pid": "$_id"}, "as": "s", "pipeline": [
                    {"$match": {"$expr": {"$and": [{"$eq": ["$meta.postId", "$$pid"]}, {"$eq": ["$meta.label", "public"]}]}}},
                    {"$sort": {"observedAt": -1}}, {"$limit": 1}]}},
                {"$project": {"title": 1, "publishedAt": 1, "s.views": 1, "s.likes": 1, "s.comments": 1}}]
    Q.append(("Q1 Posts by Brand, last 14 days, + current metrics (50)", q1_sql, (bid, since, until), "posts", q1_mongo))
    # Q2 Posts by Handle + date range
    q2_sql = "SELECT id, title, published_at FROM post WHERE handle_id=%s AND published_at>=%s AND published_at<%s ORDER BY published_at DESC LIMIT 50"
    q2_mongo = [{"$match": {"handleId": hid, "publishedAt": {"$gte": since, "$lt": until}}},
                {"$sort": {"publishedAt": -1}}, {"$limit": 50}, {"$project": {"title": 1, "publishedAt": 1}}]
    Q.append(("Q2 Posts by Handle, last 14 days (50)", q2_sql, (hid, since, until), "posts", q2_mongo))
    # Q3 Metric history for one Post
    q3_sql = "SELECT observed_at, views, likes, comments FROM metric_snapshot WHERE post_id=%s AND label='public' ORDER BY observed_at"
    q3_mongo = [{"$match": {"meta.postId": post_id, "meta.label": "public"}}, {"$sort": {"observedAt": 1}},
                {"$project": {"_id": 0, "observedAt": 1, "views": 1, "likes": 1, "comments": 1}}]
    Q.append(("Q3 Metric history of one Post", q3_sql, (post_id,), "metric_snapshots", q3_mongo))
    # Q4 Per-Handle daily total: sum over Posts of each Post's latest snapshot per day, last 30 days
    q4_sql = """SELECT day, sum(views) FROM (
        SELECT DISTINCT ON (m.post_id, date_trunc('day', m.observed_at))
               m.post_id, date_trunc('day', m.observed_at) AS day, m.views
        FROM metric_snapshot m JOIN post p ON p.id=m.post_id
        WHERE p.handle_id=%s AND m.label='public' AND m.observed_at >= %s
        ORDER BY m.post_id, date_trunc('day', m.observed_at), m.observed_at DESC) x
      GROUP BY day ORDER BY day"""
    q4_mongo = [{"$match": {"meta.handleId": hid, "meta.label": "public", "observedAt": {"$gte": NOW - PAYLOAD_TTL}}},
                {"$sort": {"observedAt": 1}},
                {"$group": {"_id": {"p": "$meta.postId", "d": {"$dateTrunc": {"date": "$observedAt", "unit": "day"}}},
                            "views": {"$last": "$views"}}},
                {"$group": {"_id": "$_id.d", "views": {"$sum": "$views"}}}, {"$sort": {"_id": 1}}]
    Q.append(("Q4 Per-Handle daily views (latest per Post per day), 30 days", q4_sql, (hid, NOW - PAYLOAD_TTL),
              "metric_snapshots", q4_mongo))

    print(f"\n{'query':62} {'PG ms':>9} {'rows':>5} {'Mongo ms':>9} {'rows':>5}")
    for name, sql, args, coll, pipe in Q:
        def run_pg():
            with conn.cursor() as cur:
                return cur.execute(sql, args).fetchall()
        tp, rp = timed(run_pg)
        tm, rm = timed(lambda: list(db[coll].aggregate(pipe)))
        print(f"{name:62} {tp:9.1f} {len(rp):5} {tm:9.1f} {len(rm):5}")
        print(f"   PG plan:    {pg_plan(conn, sql, args)}\n   Mongo plan: {mongo_plan(db[coll], pipe)}")
        if name.startswith("Q4"):
            mismatch = [(a, b) for a, b in zip(rp, rm) if int(a[1] or 0) != int(b['views'] or 0)]
            print(f"   results agree: {not mismatch and len(rp) == len(rm)}")

    # Q5 Retention: count Raw Payloads that the 30-day rule would delete (older than 30 days, not latest of its subject)
    cutoff = NOW - PAYLOAD_TTL + dt.timedelta(days=1)  # i.e. what tomorrow's daily deletion run finds
    q5_sql = """SELECT count(*) FROM raw_payload r WHERE r.fetched_at < %s
                AND EXISTS (SELECT 1 FROM raw_payload n WHERE n.subject=r.subject AND n.subject_id=r.subject_id
                            AND n.fetched_at > r.fetched_at)"""
    q5_mongo = [{"$match": {"fetchedAt": {"$lt": cutoff}}},
                {"$lookup": {"from": "raw_payloads", "as": "newer", "let": {"s": "$subject", "i": "$subjectId", "f": "$fetchedAt"},
                             "pipeline": [{"$match": {"$expr": {"$and": [{"$eq": ["$subject", "$$s"]},
                                                                           {"$eq": ["$subjectId", "$$i"]},
                                                                           {"$gt": ["$fetchedAt", "$$f"]}]}}},
                                          {"$limit": 1}, {"$project": {"_id": 1}}]}},
                {"$match": {"newer.0": {"$exists": True}}}, {"$count": "n"}]
    tp, rp = timed(lambda: conn.execute(q5_sql, (cutoff,)).fetchall(), repeat=1)
    tm, rm = timed(lambda: list(db.raw_payloads.aggregate(q5_mongo)), repeat=1)
    print(f"{'Q5 Raw Payloads due for deletion (30 days, keep latest)':62} {tp:9.1f} {rp[0][0]:5} {tm:9.1f} "
          f"{(rm[0]['n'] if rm else 0):5}")
    with conn.cursor() as cur:
        sizes = cur.execute("SELECT relname, pg_size_pretty(pg_total_relation_size(oid)) FROM pg_class "
                            "WHERE relkind='r' AND relnamespace='public'::regnamespace "
                            "ORDER BY pg_total_relation_size(oid) DESC LIMIT 4").fetchall()
    msz = {c: db.command("collStats", c) for c in ("raw_payloads", "metric_snapshots", "posts")}
    print("   PG sizes (table+toast+indexes): " + ", ".join(f"{n} {z}" for n, z in sizes))
    print("   Mongo sizes (storage+indexes):  " + ", ".join(
        f"{c} {(v['storageSize'] + v['totalIndexSize']) / 2**30:.2f} GB" for c, v in msz.items()))
    print("   (Mongo TTL indexes can't express 'except the latest', so both need a scheduled job)")

    # Q6 Idempotency: a retried Collection Run writes the same snapshot again
    with conn.cursor() as cur:
        s = cur.execute("SELECT * FROM metric_snapshot WHERE post_id=%s ORDER BY observed_at DESC LIMIT 1", (post_id,)).fetchone()
        cols = [d.name for d in cur.description]
        row = dict(zip(cols, s))
        row["id"] = 10**15
        try:
            cur.execute("INSERT INTO metric_snapshot (%s) VALUES (%s)" % (",".join(cols), ",".join(["%s"] * len(cols))),
                        list(row.values()))
            pg_dup = "ACCEPTED duplicate"
        except psycopg.errors.UniqueViolation:
            pg_dup = "rejected by UNIQUE (post_id, run_id, label)"
    m = db.metric_snapshots.find_one({"meta.postId": post_id}, sort=[("observedAt", -1)])
    m["_id"] = 10**15
    db.metric_snapshots.insert_one(m)
    n = db.metric_snapshots.count_documents({"meta.postId": post_id, "runId": m["runId"], "meta.label": m["meta"]["label"]})
    db.metric_snapshots.delete_many({"_id": 10**15})
    try:
        db.metric_snapshots.create_index([("meta.postId", 1), ("runId", 1)], unique=True)
        mongo_unique = "unique index created"
    except OperationFailure as e:
        mongo_unique = f"unique index refused: {e.details.get('errmsg', '')[:80]}"
    print(f"\nQ6 Retried run, same snapshot twice:  PG {pg_dup}  |  Mongo stored {n} copies; {mongo_unique}")

    # Q7 Atomic: update Post + append its snapshot + its payload in one transaction
    try:
        with conn.transaction():
            conn.execute("UPDATE post SET last_seen_at=now() WHERE id=%s", (post_id,))
            conn.execute("UPDATE post SET last_seen_at=last_seen_at WHERE id=%s", (post_id,))
        pg_tx = "OK"
    except Exception as e:
        pg_tx = f"failed: {e}"
    try:
        with db.client.start_session() as s, s.start_transaction():
            db.posts.update_one({"_id": post_id}, {"$set": {"lastSeenAt": NOW}}, session=s)
            db.metric_snapshots.insert_one({"_id": 10**15 + 1, "observedAt": NOW, "meta": {"postId": post_id}}, session=s)
            s.abort_transaction()
        mg_tx = "OK"
    except OperationFailure as e:
        mg_tx = f"refused: {e.details.get('errmsg', str(e))[:90]}"
    print(f"Q7 Post update + snapshot in one transaction:  PG {pg_tx}  |  Mongo {mg_tx}")


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["real", "scale", "queries", "stop"])
    ap.add_argument("--days", type=int, default=365)
    ap.add_argument("--handles-per-brand", type=int, default=10)
    ap.add_argument("--handle", default="@NBA", help="Handle (and its Brand) the queries target")
    a = ap.parse_args()
    if a.mode == "stop":
        return stop()
    conn, db = pg(), mongo()
    if a.mode == "real":
        conn.execute(PG_SCHEMA)
        mongo_schema(db)
        w = Writer(conn, db)
        load_real(w, Ids(1))
        print(f"loaded real fetch: {w.n}\n  write time: PG {w.t_pg:.1f}s, Mongo {w.t_mongo:.1f}s")
    elif a.mode == "scale":
        start = max(conn.execute("SELECT coalesce(max(id),0) FROM metric_snapshot").fetchone()[0],
                    conn.execute("SELECT coalesce(max(id),0) FROM raw_payload").fetchone()[0],
                    conn.execute("SELECT coalesce(max(id),0) FROM post").fetchone()[0],
                    conn.execute("SELECT coalesce(max(id),0) FROM handle_snapshot").fetchone()[0]) + 1
        # real-load run ids overlap the synthetic grid: clear them so COPY doesn't collide (FKs re-satisfied below)
        existing = {r[0] for r in conn.execute("SELECT id FROM collection_run").fetchall()}
        w = Writer(conn, db)
        orig_add = w.add
        w.add = lambda t, r: None if (t == "collection_run" and r["id"] in existing) else orig_add(t, r)
        load_scale(w, Ids(start), handles_per_brand=a.handles_per_brand, days=a.days)
        print(f"loaded synthetic: {w.n}\n  write time: PG {w.t_pg:,.0f}s, Mongo {w.t_mongo:,.0f}s")
    queries(conn, db, a.handle)


if __name__ == "__main__":
    main()
