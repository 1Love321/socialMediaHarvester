#!/usr/bin/env python3
"""PROTOTYPE (throwaway) for "Which database do we use?" (issue #8).

One real YouTube fetch for a few Handles. Writes every API response unchanged to
PROTOTYPE-wipe-me/youtube/ and answers the ticket's side questions in findings.json.

The API key is read with a hidden prompt (or from $YT_API_KEY) and is never printed,
logged or written to disk. Run it yourself:

    python3 prototypes/database-choice/fetch_youtube.py

Quota: roughly 40-60 units of the 10,000/day Data API bucket, plus a few calls to
the batchGetStats bucket.
"""
import getpass, json, os, sys, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path

HANDLES = ["@salahm8765", "@NBA"]
MAX_PLAYLIST_PAGES = 20          # up to 1,000 uploads per Handle (ordering check)
VIDEOS_FOR_PAYLOADS = 200        # newest N per Handle get a full videos.list payload
SHORTS_PROBE = 60                # newest N per Handle checked via youtube.com/shorts/<id>
API = "https://www.googleapis.com/youtube/v3/"

OUT = Path(__file__).resolve().parent / "PROTOTYPE-wipe-me" / "youtube"
OUT.mkdir(parents=True, exist_ok=True)
KEY = os.environ.get("YT_API_KEY") or getpass.getpass("YouTube Data API key (hidden): ").strip()
calls = []


def get(path, params, save_as=None):
    """GET an API path; returns (status, json). Logs the URL WITHOUT the key."""
    safe = API + path + "?" + urllib.parse.urlencode(params)
    url = safe + "&" + urllib.parse.urlencode({"key": KEY})
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            status, body = r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        status = e.code
        try:
            body = json.loads(e.read())
        except Exception:
            body = {"error": "non-json body"}
    fetched_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    calls.append({"path": path, "params": params, "status": status, "fetchedAt": fetched_at})
    if save_as:
        (OUT / save_as).write_text(json.dumps(
            {"fetchedAt": fetched_at, "endpoint": path, "params": params, "status": status, "response": body}))
    print(f"  {status}  {path}  {json.dumps(params)[:110]}")
    return status, body


def is_short(video_id):
    """youtube.com/shorts/<id> answers 200 for a Short, redirects (303) to /watch otherwise."""
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None
    opener = urllib.request.build_opener(NoRedirect)
    req = urllib.request.Request(f"https://www.youtube.com/shorts/{video_id}", method="HEAD",
                                 headers={"User-Agent": "Mozilla/5.0"})
    try:
        return opener.open(req, timeout=15).status == 200
    except urllib.error.HTTPError as e:
        return False if e.code in (301, 302, 303, 307, 308) else None
    except Exception:
        return None


findings = {"handles": {}, "maxIds": {}}
all_ids = []

for handle in HANDLES:
    print(f"\n== {handle}")
    slug = handle.lstrip("@")
    st, ch = get("channels", {"forHandle": handle, "part": "snippet,contentDetails,statistics"},
                 f"channel_{slug}.json")
    if st != 200 or not ch.get("items"):
        print(f"  !! could not resolve {handle}"); continue
    uploads = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

    items, token, pages = [], None, 0
    while pages < MAX_PLAYLIST_PAGES:
        params = {"playlistId": uploads, "part": "snippet,contentDetails,status", "maxResults": 50}
        if token: params["pageToken"] = token
        st, pl = get("playlistItems", params, f"playlist_{slug}_p{pages:02d}.json")
        pages += 1
        if st != 200: break
        items += pl.get("items", [])
        token = pl.get("nextPageToken")
        if not token: break

    # Ordering: is the uploads playlist newest-first by videoPublishedAt?
    pub = [i["contentDetails"].get("videoPublishedAt") for i in items]
    pub_known = [p for p in pub if p]
    inversions = [(k, pub_known[k], pub_known[k + 1]) for k in range(len(pub_known) - 1)
                  if pub_known[k] < pub_known[k + 1]]
    ids = [i["contentDetails"]["videoId"] for i in items]
    all_ids += ids

    # Full videos.list payloads for the newest N (these become Raw Payloads + Posts)
    live, upcoming, vids = 0, 0, []
    newest = ids[:VIDEOS_FOR_PAYLOADS]
    for b in range(0, len(newest), 50):
        st, vl = get("videos", {"id": ",".join(newest[b:b + 50]),
                                "part": "snippet,contentDetails,statistics,liveStreamingDetails,status"},
                     f"videos_{slug}_b{b // 50:02d}.json")
        for v in vl.get("items", []) if st == 200 else []:
            vids.append(v)
            live += "liveStreamingDetails" in v
            upcoming += v["snippet"].get("liveBroadcastContent") == "upcoming"

    shorts = [(vid, is_short(vid)) for vid in ids[:SHORTS_PROBE]]
    findings["handles"][handle] = {
        "channelId": ch["items"][0]["id"],
        "uploadsPlaylist": uploads,
        "playlistItemsSeen": len(items),
        "playlistPages": pages,
        "newestFirstInversions": len(inversions),
        "inversionSamples": inversions[:5],
        "itemsWithoutVideoPublishedAt": len(pub) - len(pub_known),
        "newestPublished": pub_known[0] if pub_known else None,
        "oldestPublishedSeen": pub_known[-1] if pub_known else None,
        "videosListReturned": len(vids),
        "withLiveStreamingDetails": live,
        "upcoming": upcoming,
        "shortsProbe": {"checked": len(shorts), "shorts": sum(1 for _, s in shorts if s),
                        "notShorts": sum(1 for _, s in shorts if s is False),
                        "unknown": sum(1 for _, s in shorts if s is None)},
    }

# Max ids per call. videos.list documents 50; batchGetStats documents none.
print("\n== max ids per call")
for n in (50, 51):
    st, body = get("videos", {"id": ",".join(all_ids[:n]), "part": "id"})
    findings["maxIds"][f"videos.list n={n}"] = {"status": st, "returned": len(body.get("items", [])),
                                                 "error": (body.get("error") or {}).get("message")}
bgs_path = None
for candidate in ("videos:batchGetStats", "videos/batchGetStats"):
    st, body = get(candidate, {"id": ",".join(all_ids[:5])})
    findings["maxIds"][f"{candidate} probe"] = {"status": st, "error": (body.get("error") or {}).get("message")}
    if st == 200:
        bgs_path = candidate
        (OUT / "batchGetStats_sample.json").write_text(json.dumps(body))
        break
if bgs_path:
    for n in (50, 51, 100, 200, 500):
        if n > len(all_ids): break
        st, body = get(bgs_path, {"id": ",".join(all_ids[:n])})
        findings["maxIds"][f"{bgs_path} n={n}"] = {
            "status": st, "returned": len(body.get("items", [])),
            "error": (body.get("error") or {}).get("message")}
        if st != 200: break

findings["calls"] = calls
(OUT / "findings.json").write_text(json.dumps(findings, indent=2))
print(f"\nDone: {len(calls)} calls. Files in {OUT}")
print("Tell Claude it's done; findings.json and the payloads contain no key.")
