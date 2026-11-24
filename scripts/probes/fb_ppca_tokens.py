#!/usr/bin/env python3
"""Probe which token reads non-owned Facebook Page Posts (wayfinder ticket #15).

Reads secrets from the environment and NEVER prints them (scrubbed from all output).
Raw responses go to OUT_DIR; stdout gets a summary only.

Tokens tried:
  system  - System User token        (PLATFORM_SEC_FB_SYSTEM_USER_TOKEN)
  app     - app access token          (APP_ID|PLATFORM_SEC_FB_APP_SECRET)
  user    - user token, if present    (PLATFORM_SEC_FB_USER_TOKEN, optional)
  page    - our own Page token, derived from the user token via me/accounts (control)

Usage: fb_ppca_tokens.py [PAGE ...]   (default: nba cnn)
"""
import hashlib, hmac, json, os, sys, time, urllib.error, urllib.parse, urllib.request

API = os.environ.get("SMH_GRAPH_BASE", "https://graph.facebook.com/v27.0")
APP_ID = os.environ.get("SMH_META_APP_ID", "1574417158052373")
OWN_PAGE_ID = os.environ.get("SMH_FB_OWN_PAGE_ID", "119616907904733")  # Instagram reeltedt
OUT_DIR = os.environ.get("SMH_PROBE_OUT", os.path.join(os.path.dirname(os.path.abspath(__file__)), "out"))
APP_SECRET = os.environ.get("PLATFORM_SEC_FB_APP_SECRET", "")
SYSTEM = os.environ.get("PLATFORM_SEC_FB_SYSTEM_USER_TOKEN", "")
USER = os.environ.get("PLATFORM_SEC_FB_USER_TOKEN", "")
SECRETS = [s for s in (APP_SECRET, SYSTEM, USER) if s]

POST_FIELDS = ("id,created_time,message,permalink_url,status_type,shares,"
               "reactions.summary(total_count).limit(0),comments.summary(total_count).limit(0)")


def scrub(s: str) -> str:
    for secret in sorted(SECRETS, key=len, reverse=True):
        s = s.replace(secret, "****")
    return s


def call(token: str, path: str, params: dict, tag: str, proof: bool = True):
    params = dict(params)
    if proof and APP_SECRET and token and "|" not in token:
        params["appsecret_proof"] = hmac.new(APP_SECRET.encode(), token.encode(), hashlib.sha256).hexdigest()
    params["access_token"] = token
    url = f"{API}/{path}?{urllib.parse.urlencode(params)}"
    t0 = time.time()
    try:
        with urllib.request.urlopen(urllib.request.Request(url), timeout=60) as r:
            status, headers, body = r.status, dict(r.headers), r.read().decode()
    except urllib.error.HTTPError as e:
        status, headers, body = e.code, dict(e.headers), e.read().decode()
    usage = {k: v for k, v in headers.items() if "usage" in k.lower()}
    try:
        parsed = json.loads(body or "null")
    except ValueError:
        parsed = body[:500]
    os.makedirs(OUT_DIR, exist_ok=True)
    safe = {k: v for k, v in params.items() if k not in ("access_token", "appsecret_proof")}
    with open(os.path.join(OUT_DIR, f"{int(t0*1000)}-{tag}.json"), "w") as f:
        f.write(scrub(json.dumps({"path": path, "params": safe, "status": status, "usage": usage, "body": parsed}, indent=2)))
    return status, parsed


def gist(status, body):
    if isinstance(body, dict) and "error" in body:
        e = body["error"]
        return scrub(f"HTTP {status} code {e.get('code')}/{e.get('error_subcode')}: {e.get('message')}")
    if isinstance(body, dict) and isinstance(body.get("data"), list):
        d = body["data"]
        first = d[0] if d else {}
        r = first.get("reactions", {}).get("summary", {}).get("total_count")
        c = first.get("comments", {}).get("summary", {}).get("total_count")
        s = first.get("shares", {}).get("count")
        return f"HTTP {status} OK: {len(d)} items; first={first.get('id')} {first.get('created_time')} reactions={r} comments={c} shares={s} keys={sorted(first)}"
    if isinstance(body, dict):
        return scrub(f"HTTP {status} OK: {json.dumps(body)[:300]}")
    return f"HTTP {status}: {str(body)[:200]}"


def out(line=""):
    print(line)
    with open(os.path.join(OUT_DIR, "summary.txt"), "a") as f:
        f.write(line + "\n")


def debug_token(name, token):
    if not (APP_SECRET and token):
        return
    st, b = call(f"{APP_ID}|{APP_SECRET}", "debug_token", {"input_token": token}, f"debug-{name}")
    d = (b or {}).get("data", {}) if isinstance(b, dict) else {}
    out(f"  debug_token: type={d.get('type')} valid={d.get('is_valid')} app={d.get('application')} "
        f"expires={d.get('expires_at')} scopes={d.get('scopes')}")


def probe(name, token, pages, proof=True):
    out(f"\n=== token: {name} ===")
    debug_token(name, token)
    for page in pages:
        st, b = call(token, page, {"fields": "id,name,fan_count,followers_count,link,verification_status"}, f"{name}-{page}-page", proof)
        out(f"  [{page}] page fields: {gist(st, b)}")
        pid = b.get("id", page) if isinstance(b, dict) else page
        for edge in ("posts", "feed", "published_posts"):
            st, b = call(token, f"{pid}/{edge}", {"fields": POST_FIELDS, "limit": 5}, f"{name}-{page}-{edge}", proof)
            out(f"  [{page}] /{edge}: {gist(st, b)}")
        st, b = call(token, pid, {"fields": f"posts.limit(3){{{POST_FIELDS}}}"}, f"{name}-{page}-nested", proof)
        out(f"  [{page}] nested posts field: {gist(st, b)}")
        st, b = call(token, f"{pid}/posts", {"fields": "id,created_time", "limit": 5}, f"{name}-{page}-posts-min", proof)
        out(f"  [{page}] /posts (id,created_time only): {gist(st, b)}")


def main():
    pages = sys.argv[1:] or ["nba", "cnn"]
    os.makedirs(OUT_DIR, exist_ok=True)
    open(os.path.join(OUT_DIR, "summary.txt"), "w").close()
    out(f"API={API} app={APP_ID} pages={pages} at {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}")
    out(f"present: app_secret={bool(APP_SECRET)} system_token={bool(SYSTEM)} user_token={bool(USER)}")
    if APP_SECRET:
        st, b = call(f"{APP_ID}|{APP_SECRET}", APP_ID, {"fields": "id,name,category,link"}, "app-info")
        out(f"app info: {gist(st, b)}")
    if SYSTEM:
        probe("system", SYSTEM, pages)
        st, b = call(SYSTEM, OWN_PAGE_ID, {"fields": "id,name,access_token"}, "system-own-page-token")
        ptok = b.get("access_token") if isinstance(b, dict) else None
        if ptok:
            SECRETS.append(ptok)
            out(f"\nown Page token via System User: obtained for {b.get('name')} ({b.get('id')})")
            probe("page-via-system", ptok, pages)
        else:
            out(f"\nno own Page token via System User: {gist(st, b)}")
    if APP_SECRET and os.environ.get("SMH_SKIP_APP") != "1":
        probe("app", f"{APP_ID}|{APP_SECRET}", pages)
    if USER:
        probe("user", USER, pages)
        st, b = call(USER, "me/accounts", {"fields": "id,name,access_token"}, "user-accounts")
        own = next((p for p in (b.get("data", []) if isinstance(b, dict) else []) if p.get("id") == OWN_PAGE_ID), None)
        if own:
            SECRETS.append(own["access_token"])
            probe("page", own["access_token"], pages + [OWN_PAGE_ID])
        else:
            out(f"\nno own Page token from me/accounts: {gist(st, b)}")


if __name__ == "__main__":
    main()
