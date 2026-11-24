#!/usr/bin/env python3
"""Probe Instagram Business Discovery against real accounts (wayfinder ticket #17).

Reads the System User token from the environment and NEVER prints it.
Raw responses + usage headers go to OUT_DIR; stdout gets a summary only.

Usage:
  ig_business_discovery.py all                   # run every check, write OUT_DIR/summary.txt
  ig_business_discovery.py part2                 # rerun what the rate limit cut off -> summary-part2.txt
  ig_business_discovery.py debug                 # token type/scopes (needs app secret)
  ig_business_discovery.py order USER [LIMIT] [PAGES]
  ig_business_discovery.py pagesize USER         # try limits 25..1000
  ig_business_discovery.py lookup USER [USER...] # account-level fields, error codes
  ig_business_discovery.py hidden USER [PAGES]   # count Posts missing like/comment/view counts
  ig_business_discovery.py usage N USER          # N light calls, record usage headers
"""
import hashlib, hmac, json, os, sys, time, urllib.error, urllib.parse, urllib.request
from datetime import datetime

API = os.environ.get("SMH_GRAPH_BASE", "https://graph.facebook.com/v27.0")
IG_USER_ID = os.environ.get("SMH_IG_USER_ID", "17841461574270580")  # @imjustasbad
APP_ID = os.environ.get("SMH_META_APP_ID", "1574417158052373")
OUT_DIR = os.environ.get("SMH_PROBE_OUT", "/tmp/ig-bd-probe")
TOKEN = os.environ.get("PLATFORM_SEC_FB_SYSTEM_USER_TOKEN", "")
APP_SECRET = os.environ.get("PLATFORM_SEC_FB_APP_SECRET", "")

MEDIA_FIELDS = "id,timestamp,media_type,media_product_type,like_count,comments_count,view_count,permalink"
USAGE_HEADERS = ("x-app-usage", "x-business-use-case-usage", "x-ad-account-usage", "x-fb-debug")


def scrub(s: str) -> str:
    for secret in (TOKEN, APP_SECRET):
        if secret:
            s = s.replace(secret, "****")
    return s


STOP_PCT = int(os.environ.get("SMH_STOP_PCT", "75"))
STOPPED = []


class UsageHigh(Exception):
    pass


def call(path: str, params: dict, tag: str):
    if STOPPED:
        raise UsageHigh(f"skipped: usage already at {STOPPED[0]}")
    params = dict(params)
    if APP_SECRET and TOKEN:
        params["appsecret_proof"] = hmac.new(APP_SECRET.encode(), TOKEN.encode(), hashlib.sha256).hexdigest()
    url = f"{API}/{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOKEN}"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            status, headers, body = r.status, dict(r.headers), r.read().decode()
    except urllib.error.HTTPError as e:
        status, headers, body = e.code, dict(e.headers), e.read().decode()
    ms = int((time.time() - t0) * 1000)
    usage = {k: v for k, v in headers.items() if k.lower() in USAGE_HEADERS and k.lower() != "x-fb-debug"}
    os.makedirs(OUT_DIR, exist_ok=True)
    fname = os.path.join(OUT_DIR, f"{int(t0*1000)}-{tag}.json")
    with open(fname, "w") as f:
        f.write(scrub(json.dumps({"path": path, "params": {k: v for k, v in params.items() if k != "appsecret_proof"},
                                  "status": status, "ms": ms, "usage": usage, "body": json.loads(body or "null")}, indent=2)))
    for v in usage.values():
        try:
            pct = json.loads(v)
            peak = max(x for x in pct.values() if isinstance(x, (int, float))) if isinstance(pct, dict) else 0
        except Exception:
            peak = 0
        if peak >= STOP_PCT or status == 403:
            STOPPED.append(v if peak >= STOP_PCT else f"HTTP {status}")
    return status, usage, json.loads(body or "null"), ms


def bd(username: str, inner: str, tag: str):
    return call(IG_USER_ID, {"fields": f"business_discovery.username({username}){{{inner}}}"}, tag)


def err(body):
    e = (body or {}).get("error") or {}
    return f"error code={e.get('code')} subcode={e.get('error_subcode')} type={e.get('type')}: {e.get('message')}"


def ts(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S%z")


def cmd_debug():
    if not APP_SECRET:
        print("app secret not set; skipping debug_token"); return
    st, _, body, _ = call("debug_token", {"input_token": TOKEN, "access_token": f"{APP_ID}|{APP_SECRET}"}, "debug")
    d = (body or {}).get("data", {})
    keep = {k: d.get(k) for k in ("type", "app_id", "application", "is_valid", "expires_at", "data_access_expires_at", "scopes", "granular_scopes")}
    print(st, json.dumps(keep, indent=1) if d else err(body))


def cmd_order(user, limit="50", pages="4"):
    after, all_ts, n = None, [], 0
    for p in range(int(pages)):
        media = f"media.limit({limit})" + (f".after({after})" if after else "") + f"{{{MEDIA_FIELDS}}}"
        st, usage, body, ms = bd(user, f"username,followers_count,media_count,{media}", f"order-{user}-p{p}")
        if st != 200:
            print(f"page {p}: HTTP {st} {err(body)}"); break
        m = body["business_discovery"].get("media", {})
        data = m.get("data", [])
        page_ts = [ts(x["timestamp"]) for x in data]
        inversions = sum(1 for a, b in zip(page_ts, page_ts[1:]) if b > a)
        print(f"page {p}: {len(data)} items, {ms} ms, inversions={inversions}, "
              f"first={data[0]['timestamp'] if data else '-'} last={data[-1]['timestamp'] if data else '-'} usage={usage}")
        if inversions:
            for i, (a, b) in enumerate(zip(page_ts, page_ts[1:])):
                if b > a:
                    print(f"   inversion at index {i}->{i+1}: {data[i]['timestamp']} then {data[i+1]['timestamp']} ({data[i]['permalink']})")
        all_ts += page_ts
        n += len(data)
        after = m.get("paging", {}).get("cursors", {}).get("after")
        if not after or not m.get("paging", {}).get("next", True):
            print("no more pages"); break
    inv = sum(1 for a, b in zip(all_ts, all_ts[1:]) if b > a)
    print(f"total {n} items, overall inversions={inv}, paging keys last page={list(m.get('paging', {}).keys()) if st == 200 else '-'}")


def cmd_pagesize(user):
    for lim in (25, 50, 100, 200, 500, 1000):
        st, usage, body, ms = bd(user, f"media.limit({lim}){{id,timestamp}}", f"pagesize-{user}-{lim}")
        got = len(body["business_discovery"].get("media", {}).get("data", [])) if st == 200 else None
        print(f"limit {lim}: HTTP {st}, returned {got}, {ms} ms" + ("" if st == 200 else f" {err(body)}") + f" usage={usage}")


def cmd_lookup(*users):
    for u in users:
        st, usage, body, ms = bd(u, "id,username,name,followers_count,follows_count,media_count,media.limit(3){" + MEDIA_FIELDS + "}", f"lookup-{u}")
        if st == 200:
            b = body["business_discovery"]
            media = b.get("media", {}).get("data", [])
            print(f"@{u}: OK followers={b.get('followers_count')} media_count={b.get('media_count')} "
                  f"keys={sorted(k for k in b if k != 'media')} media_returned={len(media)}")
        else:
            print(f"@{u}: HTTP {st} {err(body)}")


def cmd_hidden(user, pages="4"):
    after, rows = None, []
    for p in range(int(pages)):
        media = "media.limit(100)" + (f".after({after})" if after else "") + f"{{{MEDIA_FIELDS}}}"
        st, _, body, _ = bd(user, media, f"hidden-{user}-p{p}")
        if st != 200:
            print(f"HTTP {st} {err(body)}"); break
        m = body["business_discovery"].get("media", {})
        rows += m.get("data", [])
        after = m.get("paging", {}).get("cursors", {}).get("after")
        if not after:
            break
    by_type = {}
    for r in rows:
        t = f"{r.get('media_type')}/{r.get('media_product_type')}"
        c = by_type.setdefault(t, {"n": 0, "no_like": 0, "no_comments": 0, "no_view": 0})
        c["n"] += 1
        c["no_like"] += "like_count" not in r
        c["no_comments"] += "comments_count" not in r
        c["no_view"] += "view_count" not in r
    print(f"@{user}: {len(rows)} posts; missing-field counts by type: {json.dumps(by_type)}")


def cmd_usage(n, user):
    for i in range(int(n)):
        st, usage, body, ms = bd(user, "followers_count", f"usage-{i}")
        print(f"{i}: HTTP {st} {ms} ms {usage}" + ("" if st == 200 else f" {err(body)}"))
        if st != 200:
            break


class Tee:
    def __init__(self, path):
        self.f = open(path, "w")
    def write(self, s):
        sys.__stdout__.write(s); self.f.write(scrub(s)); self.f.flush()
    def flush(self):
        sys.__stdout__.flush(); self.f.flush()


def section(title, fn, *args):
    print(f"\n=== {title}")
    try:
        fn(*args)
    except Exception as e:  # keep going; record the failure
        print(f"FAILED: {type(e).__name__}: {scrub(str(e))}")


def cmd_all():
    os.makedirs(OUT_DIR, exist_ok=True)
    summary = os.path.join(OUT_DIR, "summary.txt")
    sys.stdout = Tee(summary)
    print(f"run at {datetime.now().astimezone().isoformat()} api={API} ig_user={IG_USER_ID} app_secret_set={bool(APP_SECRET)}")
    section("token debug", cmd_debug)
    section("page size @nba", cmd_pagesize, "nba")
    for u in ("nba", "natgeo", "nike", "espn"):
        section(f"order @{u} (limit 50, 6 pages)", cmd_order, u, "50", "6")
    section("lookup: big brands, age-gated (alcohol/gambling), personal-ish, nonexistent", cmd_lookup,
            "nba", "jackdaniels_us", "budweiser", "heineken", "absolutvodka", "draftkings", "fanduel",
            "zuck", "instagram", "smh_no_such_user_zz91x")
    for u in ("nba", "natgeo", "kimkardashian", "cristiano"):
        section(f"hidden counts @{u}", cmd_hidden, u, "3")
    section("usage headers over 30 light calls", cmd_usage, "30", "nba")
    print(f"\nraw responses in {OUT_DIR}")
    sys.stdout = sys.__stdout__
    print(f"\nSummary written to {summary}")


def cmd_part2():
    """Rerun what the first run's rate limit cut off; light calls first, stop at SMH_STOP_PCT."""
    os.makedirs(OUT_DIR, exist_ok=True)
    summary = os.path.join(OUT_DIR, "summary-part2.txt")
    sys.stdout = Tee(summary)
    print(f"run at {datetime.now().astimezone().isoformat()} stop at {STOP_PCT}%")
    section("is the limit cleared? (1 light call)", cmd_usage, "1", "nba")
    section("lookup: brands, age-gated (alcohol/gambling), personal-ish, nonexistent", cmd_lookup,
            "jackdaniels_us", "budweiser", "heineken", "absolutvodka", "draftkings", "fanduel",
            "zuck", "instagram", "smh_no_such_user_zz91x")
    section("usage cost of 10 light calls", cmd_usage, "10", "natgeo")
    for u in ("kimkardashian", "cristiano", "selenagomez"):
        section(f"hidden counts @{u}", cmd_hidden, u, "1")
    print(f"\nstopped early: {STOPPED[0]}" if STOPPED else "\ncompleted without hitting the stop")
    sys.stdout = sys.__stdout__
    print(f"\nSummary written to {summary}")


if __name__ == "__main__":
    if not TOKEN:
        sys.exit("Meta System User token is not in the environment (see issue #18).")
    cmd, *args = sys.argv[1:] or ["help"]
    fn = globals().get(f"cmd_{cmd}")
    if not fn:
        sys.exit(__doc__)
    fn(*args)
