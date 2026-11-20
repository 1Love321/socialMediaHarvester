# YouTube API access for Handles and Authorized Handles

Research for issue #2 (map: issue #1). Uses the terms defined in `GLOSSARY.md`.
Sources are primary only: Google developer docs, YouTube API Services policies, and Google Cloud help. I read them on 2026-11-20. The YouTube docs pages showed "Last updated 2026-11-12".

## TL;DR

- **Resolving a Handle** costs 1 unit, once. Call `channels.list?forHandle=@NBA&part=id,contentDetails`, then store the channel id and the uploads playlist id (`contentDetails.relatedPlaylists.uploads`).
- **Listing Posts in the Tracking Window** costs 1 unit per page of 50 items. Page through `playlistItems.list` on the uploads playlist and stop at the first item whose `contentDetails.videoPublishedAt` is older than the window. Do **not** use `search.list`. Since 2026-06-01 it has its own bucket of only 100 calls per day, it caps channel results at 500, and its index lags.
- **Recording Metric Snapshots** costs 1 unit per 50 Posts. Use `videos.list?id=...&part=snippet,statistics,contentDetails,liveStreamingDetails`. There is also a newer option, `videos.batchGetStats` (2026-06-03), with **its own 10,000/day bucket**.
- **Quota.** The default is 10,000 units/day for "all other endpoints", plus the two 100-call buckets. It resets at midnight Pacific Time. The cost per Collection Run per Handle is roughly `2 × ceil(N/50)` units, where N is the number of Posts in the window. At the default 14-day window, 300–500 Handles fit in 10,000/day unless they post very heavily. At 100 days or 4 runs/day they usually do not fit. More quota requires a **YouTube API Compliance Audit** through the Audit and Quota Extension Form.
- **Authorized Handles** add the YouTube Analytics API. It reports watch time, average view duration, subscribers gained/lost, shares, demographics, traffic sources, and so on. It needs the scopes `yt-analytics.readonly` and `youtube.readonly` (plus `yt-analytics-monetary.readonly` for revenue). The Google Cloud app needs **OAuth verification** before outside channel owners can authorize it. Apps in "Testing" lose refresh tokens after **7 days**.
- **Biggest design risk (policy, not quota).** Under the YouTube Developer Policies you **must not store statistics from Non-Authorized Data for more than 30 days**, and all stored API data must be refreshed or deleted within 30 days. That collides with "Metric Snapshots accumulate forever" and with "Frozen Posts are never refreshed". There is a way out: audited "analytics" use cases can apply, through the same quota extension form, to store statistics for **up to 36 months**.

## 1. Resolving a Handle to a channel

- `channels.list` accepts `forHandle`. "The parameter value can be prepended with an `@` symbol", so `GoogleDevelopers` and `@GoogleDevelopers` both work. Only one of `id`, `categoryId`, `mine`, `managedByMe`, `forHandle`, `forUsername` may be given per request. Cost: 1 unit. — https://developers.google.com/youtube/v3/docs/channels/list
- `forHandle` was added on 2024-01-31. — https://developers.google.com/youtube/v3/revision_history
- `part=contentDetails` returns `contentDetails.relatedPlaylists.uploads`, documented as "The ID of the playlist that contains the channel's uploaded videos". — https://developers.google.com/youtube/v3/docs/channels
- `snippet.customUrl` holds the channel's custom URL. Use it to show or verify the Handle. — https://developers.google.com/youtube/v3/docs/channels

**Design implication:** store the channel id (stable) as the Handle's platform id, and keep the `@handle` only as a display name. Handles can be renamed, so re-resolving by channel id is safer. Resolution is a one-time 1-unit cost at onboarding and can be ignored in run budgets.

## 2. Listing every Post in the Tracking Window

**Use `playlistItems.list` on the uploads playlist, not `search.list`.**

- `playlistItems.list`: cost 1 unit, `maxResults` 0–50 (default 5), paged with `pageToken`/`nextPageToken`. — https://developers.google.com/youtube/v3/docs/playlistItems/list
- On a playlist item, `contentDetails.videoPublishedAt` is "the date and time that the video was published to YouTube". `snippet.publishedAt` is when the item was *added to the playlist*. Filter the Tracking Window on `videoPublishedAt`. — https://developers.google.com/youtube/v3/docs/playlistItems
- `search.list` is the wrong tool:
  - Since 2026-06-01 it is charged to its own bucket, with a default of **100 calls/day** (1 per call). — https://developers.google.com/youtube/v3/determine_quota_cost, https://developers.google.com/youtube/v3/revision_history
  - With `channelId` + `type=video`, results are "capped at 500 videos".
  - A non-relevance `order` "can result in a smaller or incomplete result set", especially combined with `publishedAfter`.
  - The docs themselves recommend `playlistItems.list` for recent uploads because the search index can lag.
  - Source for the last three points: https://developers.google.com/youtube/v3/docs/search/list
- **Gotcha (undocumented ordering):** the `playlistItems.list` reference does not state the item order (https://developers.google.com/youtube/v3/docs/playlistItems/list). The stop-when-older-than-window strategy assumes the uploads playlist is newest-first. Verify this empirically. As a safety net, stop only after a full page is entirely outside the window.
- **Gotcha (Shorts and live):** the docs do not say whether Shorts and live streams appear in the uploads playlist, and the Data API has no "is Short" field. `videos.list` does expose `snippet.liveBroadcastContent` (`live`/`upcoming`/`none`) and `liveStreamingDetails`, which is present only for upcoming, live, or completed broadcasts. — https://developers.google.com/youtube/v3/docs/videos. The Analytics API (Authorized Handles only) has a `creatorContentType` dimension with values `SHORTS`, `LIVE_STREAM`, `VIDEO_ON_DEMAND`, `STORY`. — https://developers.google.com/youtube/analytics/dimensions. **Implication:** Post type ("short" vs "video" vs "live") cannot be reliably derived from public data. Leave the type nullable or "unknown" in the common Post model, or test heuristics first.
- **Gotcha (publish date semantics):** `videos.snippet.publishedAt` changes meaning for videos that were uploaded private and later made public (it becomes the time made public), and for unlisted or members-only videos (upload time). — https://developers.google.com/youtube/v3/docs/videos
- **Gotcha (upcoming premieres/streams):** scheduled broadcasts can appear before they are live (`liveBroadcastContent=upcoming`). Decide whether they count as Posts.

## 3. Refreshing metrics (one Metric Snapshot per Tracked Post per run)

- `videos.list`: cost 1 unit no matter which `part`s are requested. `id` takes a comma-separated list. — https://developers.google.com/youtube/v3/docs/videos/list, https://developers.google.com/youtube/v3/determine_quota_cost
  - The reference page does **not** state the maximum number of ids per call. 50 is the widely used limit and matches `maxResults` 1–50. **Verify** before relying on it.
- Public statistics fields: `viewCount`, `likeCount`, `commentCount`. `dislikeCount` "was made private as of December 13, 2021", and `favoriteCount` is deprecated and always 0. — https://developers.google.com/youtube/v3/docs/videos
- **View-count semantics changed recently.** Snapshot series will show breaks at these dates, so note them on charts:
  - From 2025-03-31, Shorts views count every start or replay. — https://developers.google.com/youtube/v3/revision_history
  - From 2026-08-27, all formats count a view from the first frame. — same source
  - From 2026-11-16, view counts include TV co-views. — same source and https://developers.google.com/youtube/v3/docs/videos
- **`videos.batchGetStats` (new 2026-06-03):** returns `statistics.viewCount/likeCount/commentCount`, `snippet.publishTime`, and `contentDetails.duration` for a comma-separated list of ids. Cost: 1 unit, charged to **its own granular bucket with a default of 10,000 units/day**. Auth is not required for public videos. The response has a `summary.failedVideoIds[]` list, which helps detect deleted or private videos. The max ids per call is not stated. — https://developers.google.com/youtube/v3/docs/videos/batchGetStats, https://developers.google.com/youtube/v3/revision_history
  - **Implication:** use `videos.list` only for *new* Posts (title, description, thumbnails, live details; this is the Raw Payload), and `batchGetStats` for snapshot refreshes. That roughly doubles the effective daily budget.
- **Auth for public data:** a plain API key is enough. The official examples call `videos?id=…&key=YOUR_API_KEY&part=snippet,statistics`. — https://developers.google.com/youtube/v3/getting-started
- Use the `fields` parameter to trim payloads. It does not reduce quota, which is per call. — https://developers.google.com/youtube/v3/getting-started, https://developers.google.com/youtube/v3/determine_quota_cost

## 4. Quota: cost per Collection Run and how many Handles fit

Facts — all from https://developers.google.com/youtube/v3/determine_quota_cost and https://developers.google.com/youtube/v3/guides/quota_and_compliance_audits:

- Default allocation: "100 search.list calls, 100 videos.insert calls, and 10,000 units per day combined for all other endpoints". `batchGetStats` has a separate 10,000/day bucket (https://developers.google.com/youtube/v3/revision_history).
- `channels.list`, `playlistItems.list`, and `videos.list` cost 1 unit each.
- "All API requests, including invalid requests, incur a quota cost of at least one point." Retries and 404s cost quota.
- Each extra page costs a full call.
- "Daily quotas reset at midnight Pacific Time (PT)."
- Quota is per Google Cloud project, and you "must create exactly one (1) API Project for that API Client". You cannot shard Handles across projects to multiply quota. — https://developers.google.com/youtube/terms/developer-policies

**Model.** N is the number of Posts in the Tracking Window, i.e. posts/day × window days. Cost per run per Handle (my arithmetic):

- `playlistItems.list` pages = `floor(N/50) + 1` (you need to see one item older than the window to stop)
- `videos.list` pages = `ceil(N/50)`

Daily units = Handles × runs/day × units per run. Handle resolution (1 unit, once) is excluded.

| Posting rate | Window | N | units/run/Handle | 100 H ×1 | 100 H ×4 | 300 H ×1 | 300 H ×4 | 500 H ×1 | 500 H ×4 |
|---|---|---|---|---|---|---|---|---|---|
| 1/day | 14 d | 14 | 2 | 200 | 800 | 600 | 2,400 | 1,000 | 4,000 |
| 1/day | 100 d | 100 | 5 | 500 | 2,000 | 1,500 | 6,000 | 2,500 | **10,000** |
| 5/day | 14 d | 70 | 4 | 400 | 1,600 | 1,200 | 4,800 | 2,000 | 8,000 |
| 5/day | 100 d | 500 | 21 | 2,100 | 8,400 | 6,300 | **25,200** | **10,500** | **42,000** |
| 20/day | 14 d | 280 | 12 | 1,200 | 4,800 | 3,600 | **14,400** | 6,000 | **24,000** |
| 20/day | 100 d | 2,000 | 81 | 8,100 | **32,400** | **24,300** | **97,200** | **40,500** | **162,000** |

Bold means the run exceeds 10,000/day, or sits exactly at it with no headroom for retries or onboarding.

**Max Handles in 10,000 units/day** (10,000 / (runs × units per run)):

| Posting rate | 14 d, 1 run | 14 d, 4 runs | 100 d, 1 run | 100 d, 4 runs |
|---|---|---|---|---|
| 1/day | 5,000 | 1,250 | 2,000 | 500 |
| 5/day | 2,500 | 625 | 476 | 119 |
| 20/day | 833 | 208 | 123 | 30 |

Observations:

- The cost is dominated by Posts in the window, not by Handle count, so a few prolific Handles can dominate. Sports leagues posting many Shorts are an example. The 50-per-page granularity makes Handles with 1 post/day almost free (2 units).
- Moving refreshes to `videos.batchGetStats` takes the `ceil(N/50)` term off the main bucket. The main bucket then pays only for `playlistItems` pages plus `videos.list` for new Posts.
- A manual **Tracking Window Override** of 100 days across all Handles is a burst cost. For example, 500 Handles at 5/day comes to 10,500 units, more than a full day's quota for one run. The scheduler needs a quota budget/ledger and must be able to spread an override run across days.

**Quota increase process.** Sources: https://developers.google.com/youtube/v3/guides/quota_and_compliance_audits and https://developers.google.com/youtube/terms/developer-policies.

- Additional quota requires completing an **API Compliance Audit** against the YouTube API Services Terms. You submit the "YouTube API Services – Audit and Quota Extension Form" (https://support.google.com/youtube/contact/yt_api_form), and a YouTube API Services team member contacts you.
- If you passed an audit in the last 12 months, the same form requests a further extension.
- Failed audits can be appealed (https://support.google.com/youtube/contact/yt_api_appeals). YouTube also runs periodic audits.
- Granted quota may be used only for the approved use case. A changed use case requires re-audit.
- YouTube may curtail quota for projects inactive for 90 consecutive days.
- Since 2026-06-01, quota is moving to "granular" per-method buckets, said to simplify approvals "based on specific method usage". — https://developers.google.com/youtube/v3/revision_history
- No turnaround time is published.
- In practice the audit reviews a working client against the Developer Policies. The policy issues in §6 below must be solved before applying.

## 5. Authorized Handles: Private Data via YouTube Analytics API

**What it exposes (channel reports, `reports.query`, `ids=channel==MINE`):**

- Metrics: `views`, `engagedViews`, `estimatedMinutesWatched`, `averageViewDuration`, `averageViewPercentage`, `likes`, `dislikes`, `comments`, `shares`, `subscribersGained`, `subscribersLost`, `videosAddedToPlaylists`, card and annotation metrics, `audienceWatchRatio`/`relativeRetentionPerformance` (retention), `averageConcurrentViewers`/`peakConcurrentViewers` (live). Revenue and ad metrics (`estimatedRevenue`, `grossRevenue`, `playbackBasedCpm`, `monetizedPlaybacks`) need the monetary scope and YouTube Partner Program membership, otherwise 403. — https://developers.google.com/youtube/analytics/metrics, https://developers.google.com/youtube/analytics/channel_reports
- Dimensions include `video`, `day`, `country`, `ageGroup`, `gender`, `subscribedStatus`, `insightTrafficSourceType`, `deviceType`, and `creatorContentType` (SHORTS / LIVE_STREAM / VIDEO_ON_DEMAND / STORY, from 2019-01-01). — https://developers.google.com/youtube/analytics/dimensions
- The `filters` parameter accepts up to **500 video ids** in one request, so one `reports.query` per Authorized Handle per run can cover the whole Tracking Window. — https://developers.google.com/youtube/analytics/reference/reports/query
- Quota: "Each API request that you make counts as one unit". The limits are a separate API quota shown in the Cloud console. — https://developers.google.com/youtube/analytics/data_model
- Data limits: small-traffic rows and dimensions are thresholded or anonymized, and deleted items are excluded from per-item reports. — https://developers.google.com/youtube/analytics/data_model
- Bulk alternative: the **YouTube Reporting API** delivers daily CSV reports. Reports are kept 60 days (historical backfill reports 30 days), and backfills replace earlier data. — https://developers.google.com/youtube/reporting/v1/reports

**OAuth scopes:**

| Scope | Why |
|---|---|
| `https://www.googleapis.com/auth/yt-analytics.readonly` | Analytics reports (non-monetary) |
| `https://www.googleapis.com/auth/youtube.readonly` | **Required** by `reports.query` since 2018-06-18; also lets `channels.list?mine=true` identify the channel |
| `https://www.googleapis.com/auth/yt-analytics-monetary.readonly` | Only if revenue/ad metrics are wanted |

Sources: https://developers.google.com/youtube/analytics/reference/reports/query, https://developers.google.com/youtube/analytics/revision_history, https://developers.google.com/identity/protocols/oauth2/scopes

## 6. Google Cloud app verification, testing mode, token lifetime

- **Sensitivity.** Google's scope list does not state each scope's class. Sensitive scopes are "indicated in the Google Cloud Console" and "require review by Google". — https://developers.google.com/identity/protocols/oauth2/scopes. Confirm in the console whether the YouTube scopes are sensitive or restricted (expected: sensitive, not restricted).
- **Sensitive-scope verification** needs:
  - verified authorized domains
  - an accurate consent screen (home page, privacy policy on the same domain)
  - a scope justification
  - a **demo video** uploaded to YouTube showing the consent flow and how the data is used

  It "can take up to 10 days". — https://developers.google.com/identity/protocols/oauth2/production-readiness/sensitive-scope-verification
- **Exceptions (no verification needed):** personal use (a few known users), dev/test/staging projects left in "Testing", service-account-only access, and **Internal** apps whose users are all in your Google Workspace/Cloud Identity org. — same source
  - Internal does **not** help here: brand/channel owners such as the NBA's channel managers are outside our org, and authorization from outside the org fails with `org_internal`. — https://support.google.com/cloud/answer/15549945
- **Testing mode:**
  - Up to 100 test users.
  - Each sees a warning screen.
  - "Authorizations by a test user will expire seven days from the time of consent… that [refresh] token will also expire."
  - A Brand Account can authorize if a listed test user manages it. This matters because many YouTube channels are Brand Accounts.

  Source: https://support.google.com/cloud/answer/15549945. Also: "publishing status of 'Testing' is issued a refresh token expiring in 7 days". — https://developers.google.com/identity/protocols/oauth2
- **Production, unverified:** shows the unverified-app screen and has a lifetime **user cap of 100 new users** that "cannot be reset". — https://support.google.com/cloud/answer/15549945
- **"Personal" user type:** only the creator's own account, with no verification and no 7-day expiry. Not useful for many owners. — same source
- **Refresh tokens can still die in production:**
  - when the user revokes access
  - after **6 months unused**
  - when there are too many live tokens (**100 per Google Account per OAuth client**, oldest silently invalidated)
  - when admin policy blocks the app

  Source: https://developers.google.com/identity/protocols/oauth2. **Implication:** an Authorization needs states (active / expired / revoked), and an Authorized Handle reverts to a plain Handle when the token fails, as the glossary already describes.

**Recommendation for the internal phase:** keep the OAuth app in Testing with the few internal owners as test users, and accept the weekly re-consent. Alternatively, publish and verify early if owners outside the team must authorize, which is needed later for external customers anyway. Plan for ~10 days of OAuth verification in addition to the YouTube API audit; these are separate reviews.

## 7. YouTube API Services policy constraints that shape the data model

All from https://developers.google.com/youtube/terms/developer-policies (§III.E.4, §III.E.6, §III.D, §III.L, Definitions) unless noted.

1. **Non-Authorized statistics: 30-day max.** "an API Client must not store statistics retrieved as Non-Authorized Data for more than 30 days". Other Non-Authorized Data (titles, descriptions, the Raw Payload) may be stored only temporarily and must be deleted or refreshed after 30 calendar days.
   - This conflicts with keeping every Metric Snapshot of plain Handles forever.
   - It also conflicts with Frozen Posts never being refreshed. With the default 14-day window, their metadata goes stale after 30 days.
2. **Authorized Data.** Analytics/Reporting API data and statistics *for Authorized Handles* may be stored "for as long as is necessary". The client must re-check the authorization every 30 days and verify every 30 days that the video has not been deleted.
3. **After revocation**, delete the related Authorized Data within 7 calendar days. You must also delete API data for users whose tokens cannot be refreshed, within 30 days at the latest. You must offer a "delete my data" path that completes within 7 days.
4. **The exception that may rescue the design (§III.L, from 2026-06-01).** Audited developers with an **analytics use case** can apply through the quota extension form for permission to "store metrics (e.g., views, likes, subs count, comment counts) from statistical endpoints for **up to 36 calendar months**". Other data (titles, descriptions) still follows the 30-day refresh/delete rule. You accept it in the form under "Section 5: Use Cases… → Analytics & Reporting". The same amendment explicitly allows "track[ing] views between different channels for the purpose of comparison or historical analysis". — https://developers.google.com/youtube/terms/derived-metrics-policy
5. **Aggregation and derived metrics.** Without the amendment, you must not aggregate API Data across channels of different content owners, and must not create derived metrics such as engagement scores or ratios. Brand-level roll-ups and cross-Brand comparison charts need the amendment, or must stay per-owner.
6. **One API project per API client.** No splitting across projects for quota.
7. **Historical display is allowed** if "presented accurately in context of time". Snapshot charts are fine once storage itself is allowed.

## Implications for the design (summary)

- Store channel id + uploads playlist id per YouTube Handle. Discover Posts with `playlistItems.list`, never `search.list`.
- Split new-Post fetch (`videos.list`, which gives the Raw Payload) from snapshot refresh (`videos.batchGetStats`, separate 10k bucket).
- Track a quota ledger per bucket. Schedule runs against it, and spread Tracking Window Override runs across days. Budget for a quota extension audit before scaling past ~300 active Handles or adopting 100-day / multi-run defaults.
- **Retention policy is a first-class requirement.** Metric Snapshots of plain Handles need either a 30-day TTL or an approved §III.L amendment (36 months). Metadata and Raw Payloads need a 30-day refresh-or-delete job, including for Frozen Posts. The model needs a deletion path for revoked Authorizations within 7 days.
- Authorization lifecycle: OAuth verification for external owners, 7-day expiry while in Testing, refresh-token loss handling, and a re-check every 30 days.
- The common Post "type" (short/video/live) is not reliably available from public data.

## Open questions raised

- Does the team accept applying for the §III.L "Analytics & Reporting" amendment? Without it, long-term Metric Snapshot history for plain Handles is not allowed. **This affects the map's core assumption.**
- Verify empirically:
  - uploads-playlist ordering, and whether it includes Shorts and live/premieres
  - the max ids per `videos.list` / `batchGetStats` call
  - the real Analytics API quota shown in the Cloud console
  - the exact sensitivity class of the YouTube scopes in the console
