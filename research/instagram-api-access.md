# Instagram API access for Handles and Authorized Handles

Research for ticket #3 ("How does Instagram API access work for Handles and Authorized Handles?"), part of the wayfinder map #1.
Researched 2026-11-20 against Meta's developer docs. The current Graph API version is **v27.0**, released 2026-11-04 ([Graph API changelog](https://developers.facebook.com/docs/graph-api/changelog)).
Terms such as Handle, Authorized Handle, Authorization, Post, Metric Snapshot, Collection Run, Tracking Window and Raw Payload are used as defined in `GLOSSARY.md`.

## TL;DR

- **Handle (Public Data)**: the only official route is **Business Discovery**. It is called *through an Instagram professional account that we own*: `GET /<OUR_IG_USER_ID>?fields=business_discovery.username(<handle>){...}`. It works only for **Business/Creator** targets, not personal accounts or age-gated accounts. For each Post it returns public fields such as `id`, `timestamp`, `permalink`, `media_type`, `caption`, `like_count`, `comments_count`, `view_count` (Reels) and `media_url`/`thumbnail_url`. The media edge pages with **cursors only**, so there is no `since`/`until`. To cover a Tracking Window we page from newest to oldest until `timestamp` is older than the window.
- **No per-Post refresh for Handles**: a direct `GET /<media-id>` on another account's media fails. The only way to refresh a Post's metrics is to page that Handle's media edge again, so each Collection Run re-reads the whole window.
- **Authorized Handle (Private Data)**: the owner's token reads their own `/media` (time-based `since`/`until`, up to the 10K most recent) and Insights. Media insights include `views`, `reach`, `saved`, `shares`, `total_interactions`, `likes`, `comments`, `follows`, `profile_visits`, reels watch time and more. Account insights include `reach`, `views`, `accounts_engaged`, follower demographics and more. Insights are delayed by up to 48 hours and kept for up to 2 years.
- **Login path**: Meta now has **three** setups. **Instagram API with Unified Login** (Instagram *or* Facebook credentials, no Page needed, business portfolio required, `graph.facebook.com`) is "recommended for new integrations", and "New Instagram API features are released only for this setup". Business Discovery is available with **Facebook Login and Unified Login**, but **not with Instagram Login**.
- **Tokens**: Instagram Login gives a long-lived token valid for 60 days, refreshable after it is 24 hours old. Facebook Login gives a long-lived user token of about 60 days, and Page tokens have no fixed expiry, but data access lapses after 90 days. Unified Login gives a System User token, and its expiry is chosen in the login configuration.
- **Access level**: Standard Access, which needs no App Review, is enough while only our own accounts and accounts of people with roles on our app are involved. To let **external customers** authorize their own accounts we need **Advanced Access**, which means App Review per permission, Business Verification, Live mode and an annual Data Use Checkup.
- **Rate limits**: Business Discovery uses **Platform Rate Limits**, which count against the *single* user token of our querying account. Meta does not publish that per-user number. Owner endpoints use the Business Use Case formula: 4800 × impressions per 24 hours, per app and app user. Business Discovery for hundreds of Handles is the real throughput risk.

## 1. Public Data for a Handle we don't own: Business Discovery

### How it is called

- The query runs on **the app user's own Instagram professional account ID**, and the target is named by username. Example: `GET /17841405309211844?fields=business_discovery.username(bluebottle){followers_count,media_count}`. Source: [Business Discovery guide](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-facebook-login/business-discovery).
- **So yes, we need an Instagram professional account of our own** to act through, together with a token for it. Under Facebook Login, that account must be linked to a Facebook Page we can administer. Under Unified Login, it must sit in a business portfolio. Sources: [Business Discovery reference](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/business_discovery), [Platform overview](https://developers.facebook.com/docs/instagram-platform/overview).
- **Permissions**: a Facebook User access token with `instagram_basic`, `instagram_manage_insights` and `pages_read_engagement`. If the Page role was granted via Business Manager, the token also needs `ads_management` or `ads_read`. Source: [Business Discovery reference](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/business_discovery).
- **Which login setups support it**: the reference page says "Available for the Instagram API with Facebook Login". The guide adds that it is "available with both the Instagram API with Facebook Login and the Instagram API with Unified Login". It is not listed for Instagram Login, whose features are comment moderation, publishing, media insights, mentions and messaging. Sources: [Business Discovery guide](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-facebook-login/business-discovery), [Instagram API with Instagram Login](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login).

### Which accounts

- It returns data about "other Instagram Business or Creator IG Users". Personal/consumer accounts are out of reach: the Facebook Login setup "cannot access Instagram consumer accounts". Sources: [Business Discovery reference](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/business_discovery), [Instagram API with Facebook Login](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-facebook-login).
- "Data about age-gated Instagram professional accounts will not be returned." For example, alcohol or gambling brands may come back empty. Source: [Business Discovery guide](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-facebook-login/business-discovery).

### Which fields and metrics are public

- **Account level**: `followers_count`, `media_count`, `id` (the examples), plus the other public IG User fields. Source: [Business Discovery reference](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/business_discovery).
- **Post level**: the IG Media fields marked *Public* are `alt_text`, `caption`, `comments_count`, `id`, `is_shared_to_feed`, `media_audio_type`, `media_product_type`, `media_type`, `media_url`, `owner`, `permalink`, `shortcode`, `thumbnail_url`, `timestamp`, `username`, `view_count` and `reposts_count`, plus the `children` edge for albums. Source: [IG Media reference](https://developers.facebook.com/docs/instagram-platform/reference/instagram-media).
- `like_count` is not tagged "Public" in the IG Media field table. However, the Business Discovery guide's own example returns `comments_count`, `like_count` and `view_count` for another account's media, so in practice it is available. Source: [Business Discovery guide](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-facebook-login/business-discovery).
- **`view_count`**: introduced 2025-06-16 and "only available using the Business Discovery API for Instagram Reels". It includes paid and organic views. Since 2026-04-22 it "returns combined Instagram and Facebook views for crossposted video content". Sources: [Instagram Platform changelog](https://developers.facebook.com/docs/instagram-platform/changelog), [Business Discovery guide](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-facebook-login/business-discovery).
- **Not available via Business Discovery**: `saved_count`, `shares_count` and `total_views_count` (use `view_count` instead), and all Insights such as reach. Source: [IG Media reference](https://developers.facebook.com/docs/instagram-platform/reference/instagram-media).
- **Hidden counts**: "the `like_count` field is omitted if the media owner has hidden like counts". The same applies to hidden comments, views, reposts and shares, where the field is simply absent. Source: [IG Media reference](https://developers.facebook.com/docs/instagram-platform/reference/instagram-media).
- **`media_url` is optional**. It is omitted for video with copyrighted or licensed audio, for flagged video, and for reels whose owner disabled downloads. The docs say to "Treat `media_url` as an optional field in your app" and fall back to `permalink` or `thumbnail_url`. This changed on 2026-07-30. Sources: [Instagram Platform changelog](https://developers.facebook.com/docs/instagram-platform/changelog), [Business Discovery reference](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/business_discovery).
- **Stories** are not part of the media edge. Stories use a separate `/stories` endpoint, and only for the account's own Stories. Source: [IG User Media reference](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media).

### Can we list every Post within a Tracking Window and refresh it?

- **Pagination**: "The `/media` edge supports cursor-based pagination ... the response will include `before` and `after` cursors ... the response will not include `previous` or `next` fields, so you will have to use the `before` and `after` cursors to construct `previous` and `next` query strings manually." Source: [Business Discovery reference](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/business_discovery).
- The docs don't mention `since`/`until` for the Business Discovery media edge. On the Facebook Login setup, the User Insights edge is "the only endpoint that supports time-based pagination", and "Ordering results is not supported". Source: [Instagram API with Facebook Login](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-facebook-login).
- **Implication**: to cover a Tracking Window, page newest to oldest and stop at the first Post whose `timestamp` is older than the window. The newest-first order is how the own-account `/media` edge behaves ("the most recently created media"), but it is **not stated for Business Discovery**. It needs confirming in a spike, together with the maximum page size (Graph field expansion `media.limit(n)` and `media.after(cursor)`). Source: [IG User Media reference](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media).
- **Refresh**: "performing a `GET` on any returned IG Media will fail due to insufficient permissions". A Post from a plain Handle can therefore only be refreshed by re-reading the Handle's media edge, and each Collection Run re-pages the whole Tracking Window. This fits the existing Collection Run model. Source: [Business Discovery guide](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-facebook-login/business-discovery).
- A long window, such as a 100-day Tracking Window Override for a Handle posting 10 or more times a day, means many pages per Handle per run (see the rate-limit section).

## 2. Private Data for an Authorized Handle

### Own media

- `GET /<IG_USER_ID>/media` "Returns a maximum of 10K of the most recently created media". It supports `since`/`until` (Unix timestamps). Stories are excluded and come from `/stories`. Source: [IG User Media reference](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media).
- An Authorized Handle can therefore list its Tracking Window directly by time. For its own media, the owner token can also `GET /<media-id>` and read non-public fields. On Facebook Login these include `like_count`, `saved_count`, `shares_count` and `reposts_count` (added 2026-04-22). Sources: [IG Media reference](https://developers.facebook.com/docs/instagram-platform/reference/instagram-media), [Instagram Platform changelog](https://developers.facebook.com/docs/instagram-platform/changelog).

### Media Insights (per Post)

- **Feed**: `comments`, `likes`, `saved`, `shares`, `reposts`, `views`, `reach`, `total_interactions`, `facebook_views`, `follows`, `profile_visits`, `profile_activity`.
- **Reels**: the same engagement set plus `crossposted_views`, `ig_reels_avg_watch_time`, `ig_reels_video_view_total_time` (in development) and `reels_skip_rate` (in development).
- **Story**: `views`, `reach`, `shares`, `replies`, `navigation`, `link_clicks`, and others.
- `total_views`, `total_likes` and `total_comments` (organic + paid) are **Facebook Login only**.
- Source for this list: [IG Media Insights reference](https://developers.facebook.com/docs/instagram-platform/reference/instagram-media/insights).

Limitations, all from the same [IG Media Insights reference](https://developers.facebook.com/docs/instagram-platform/reference/instagram-media/insights):

- Data "can be delayed up to 48 hours".
- Data is "stored for up to 2 years".
- There are no insights for media inside albums (album children).
- Story metrics are only available for 24 hours, and values under 5 return error 10.
- An unavailable metric returns an empty set, not 0.
- The insights webhook is not supported on Instagram Login.

### Account (User) Insights

- Metrics: `accounts_engaged`, `comments`, `engaged_audience_demographics`, `follower_demographics`, `follows_and_unfollows`, `likes`, `profile_links_taps`, `reach`, `replies`, `reposts`, `saves`, `shares`, `total_interactions`, `views`. Demographic metrics require the `timeframe` parameter. Source: [IG User Insights reference](https://developers.facebook.com/docs/instagram-platform/api-reference/instagram-user/insights).
- Thresholds: `follower_count` and `online_followers` are unavailable under 100 followers, demographics return only the top 45, and data may be delayed by 48 hours. Source: same page.

### Permissions per setup

- **Instagram Login**: `instagram_business_basic` and `instagram_business_manage_insights` (Instagram User token, `graph.instagram.com`).
- **Facebook Login**: `instagram_basic`, `instagram_manage_insights` and `pages_read_engagement`, plus `ads_*` when the Page role came from Business Manager.
- **Unified Login**: `instagram_basic` and `instagram_manage_insights`, plus `business_management` for token management.
- Sources: [IG Media Insights reference](https://developers.facebook.com/docs/instagram-platform/reference/instagram-media/insights), [Unified Login permissions](https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-unified-login/permissions).

## 3. Deprecated and removed metrics (2024 to 2026)

Source for this section: [Instagram Platform changelog](https://developers.facebook.com/docs/instagram-platform/changelog) and [IG User Insights reference](https://developers.facebook.com/docs/instagram-platform/api-reference/instagram-user/insights).

| Metric | Status |
|---|---|
| `video_views` (media) | Removed in v21.0, and in all versions from 2025-01-08 |
| `profile_views`, `website_clicks`, `email_contacts`, `phone_call_clicks`, `text_message_clicks`, `get_direction_clicks` (user) | Removed in v21.0, and in all versions from 2025-01-08 |
| `impressions` (media and user), `plays`, `clips_replays_count`, `ig_reels_aggregated_all_plays_count` (media) | Deprecated in v22.0 (2025-01-21), and in all versions from 2025-04-21. Replaced by **`views`**. For media created on or after 2024-07-02, requests return an error. |
| Demographic timeframes `last_14_days`, `last_30_days`, `last_90_days`, `prev_month` | Removed in v20.0, and in all versions from 2024-08-19 |
| Instagram Basic Display API | Deprecated 2024-12-04; all requests error |
| Old Instagram Login scopes (`business_basic`, etc.) | Replaced by `instagram_business_*` on 2025-01-27 |

These metrics were added in the same period, all versions:

- `view_count` on Business Discovery (2025-06).
- `reels_skip_rate`, `reposts`, `crossposted_views` and `facebook_views` (2025-12).
- `total_likes`, `total_comments` and `total_views`, plus the `reposts_count`, `saved_count` and `shares_count` fields (2026-04).
- `is_ai_generated` and `link_clicks` (2026-06).

**Implication**: model metrics as an open-ended name and value set per Metric Snapshot rather than fixed columns. Meta renames and retires metrics roughly yearly, and the Raw Payload keeps whatever was returned.

## 4. Login paths compared

| | Unified Login (new) | Instagram Login | Facebook Login |
|---|---|---|---|
| Meta's recommendation | "recommended for new integrations"; "New Instagram API features are released only for this setup" | Existing Instagram Login integrations | Existing Page-linked integrations |
| Owner logs in with | Instagram or Facebook | Instagram | Facebook |
| Facebook Page | Not required | Not required | Required (and admin-equivalent tasks on it) |
| Business portfolio | Required | Not required | Depends |
| Token | Business Integration System User token, owned by the business portfolio | Instagram User token | Facebook User or Page token |
| Host | graph.facebook.com | graph.instagram.com | graph.facebook.com |
| Business Discovery | Yes | No | Yes |
| Hashtag search | Yes | No | Yes |
| Insights | Yes | Yes | Yes |

Sources: [Platform overview](https://developers.facebook.com/docs/instagram-platform/overview), [Instagram API with Unified Login](https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-unified-login), [Business Discovery guide](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-facebook-login/business-discovery).

Notes on the setups:

- On the Facebook Login setup, Meta's App Review docs say "your app can use only one login type". Source: [Instagram App Review](https://developers.facebook.com/docs/instagram-platform/app-review).
- Collaborators can't read data on co-authored media. Only the publisher can. Source: [Platform overview](https://developers.facebook.com/docs/instagram-platform/overview).
- If an app only serves our own accounts, it "do[es] not need to implement a login flow". Tokens can be obtained manually through the App Dashboard. Source: [Platform overview](https://developers.facebook.com/docs/instagram-platform/overview).

## 5. Token lifetimes and refresh

- **Instagram Login**:
  - The authorization code and the short-lived token each last 1 hour.
  - The long-lived token is "valid for 60 days". It is refreshed via `GET graph.instagram.com/refresh_access_token?grant_type=ig_refresh_token` if it is at least 24 hours old and not yet expired.
  - "Tokens that have not been refreshed in 60 days will expire and can no longer be refreshed."
  - Source: [Business Login for Instagram](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/business-login).
- **Facebook Login**:
  - A long-lived User token "generally lasts about 60 days".
  - Long-lived Page tokens "do not have an expiration date and only expire or are invalidated under certain conditions".
  - Source: [Long-lived tokens](https://developers.facebook.com/docs/facebook-login/guides/access-tokens/get-long-lived).
  - Separately, **data access expires 90 days** after the user's last activity. The token still authenticates, but "your app can't access their data" until the user re-authorizes (`auth_type=reauthorize`).
  - Unused permissions may also expire after 90 days. Some permissions, such as `ads_read` and `read_insights`, don't expire.
  - Source: [Data access expiration](https://developers.facebook.com/docs/facebook-login/auth-vs-data).
- **Unified Login**:
  - The System User token "belongs to your client's business portfolio, not to the person who logged in", and it keeps working if that person leaves.
  - Expiry is chosen in the login configuration. Tokens are refreshed through the Business Integration System User Access Token Management API, using the client's business ID.
  - The token stops working if the client removes the app or moves the Instagram account to another portfolio. In that case the app should stop retrying and ask the client to reconnect.
  - Source: [Unified Login authentication](https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-unified-login/authentication).

**Implication for Authorization**: store the token together with its expiry, the business ID, the IG account IDs and the config_id (Meta's own recommendation). Run a scheduled refresh well before 60 days where the setup needs one. Treat token-invalid errors as "Authorization ended", which reverts the Authorized Handle to a plain Handle.

## 6. Rate limits for hundreds of Handles

- Business Discovery and Hashtag Search are subject to **Platform Rate Limits**. All other Instagram endpoints use Instagram **Business Use Case (BUC)** limits. Source: [Platform overview, Rate Limiting](https://developers.facebook.com/docs/instagram-platform/overview).
- **BUC**: "Calls within 24 hours = 4800 * Number of Impressions", counted per app and app-user pair on a rolling 24 hours. "Impressions" means how often the account's content was seen in the last 24 hours, so this is generous for big Authorized Handles. Source: [Graph API rate limiting](https://developers.facebook.com/docs/graph-api/overview/rate-limiting).
- **Platform limits**:
  - App tokens get "Calls within one hour = 200 * Number of Users" (users = the app's daily active users).
  - User tokens count against a per-user rolling one-hour limit whose value Meta **does not publish**.
  - Errors: 4 (app), 17 (user), 613 (custom), and 80002 for the Instagram BUC limit.
  - Usage headers: `X-App-Usage` and `X-Business-Use-Case-Usage` (the latter includes `estimated_time_to_regain_access`).
  - "Once throttled, stop making calls", because continued calls extend the block.
  - Source: [Graph API rate limiting](https://developers.facebook.com/docs/graph-api/overview/rate-limiting).
- **Implication**: every Business Discovery call goes through one querying user (our own IG account). Hundreds of Handles × (pages per Tracking Window) per Collection Run all land on that one unpublished per-user budget, and on an app budget that scales with daily active users, which is about 1 for an internal tool.
  - The harvester needs a **rate-limit-aware scheduler**: read `X-App-Usage`, back off on codes 4/17/613, and spread Handles over the polling interval.
  - Business Discovery can request account fields and a page of media in **one call**, so a 14-day window for a typical sports account is likely 1 to 3 calls per Handle per run.
  - The real per-user ceiling must be measured in a spike.

## 7. Standard vs Advanced Access, App Review, Business Verification

- **Standard Access** is the default and is auto-approved. Permissions "can only be requested from app users who have a role on the requesting app". "If your app only serves your Instagram professional account or an account you manage, Standard Access is all your app needs." Sources: [Access levels](https://developers.facebook.com/docs/graph-api/overview/access-levels), [Platform overview](https://developers.facebook.com/docs/instagram-platform/overview).
- **Advanced Access** is "required if your app serves Instagram professional accounts that you don't own or manage and can be used by app users who do not have a role on your app". It "requires App Review and Business Verification", the app must be in Live mode, and there is an annual Data Use Checkup. Sources: [Platform overview](https://developers.facebook.com/docs/instagram-platform/overview), [Access levels](https://developers.facebook.com/docs/graph-api/overview/access-levels), [Unified Login permissions](https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-unified-login/permissions).
- Meta also warns: "Because of the limited scope of Standard Access, some features might not work properly until your app has been granted Advanced Access". Business Discovery under Standard Access needs to be confirmed in a spike. Source: [Platform overview](https://developers.facebook.com/docs/instagram-platform/overview).
- **App Review**: one screencast per permission, test credentials, and at least one successful API call per permission. Review applies to Tech Providers serving multiple businesses. "My app is only for a business I own or manage" needs Standard Access and no review. Source: [Instagram App Review](https://developers.facebook.com/docs/instagram-platform/app-review).
- **Mapping to our phases**:
  - **Internal phase**: Standard Access. Our querying IG account and our team's Authorized Handles, where the owners are given app roles.
  - **External customers**: Advanced Access for `instagram_basic` and `instagram_manage_insights` (and `pages_*` if on Facebook Login), plus Business Verification of our company.

## 8. Platform Terms constraints relevant to storage

Source for this section: [Meta Platform Terms](https://developers.facebook.com/terms/).

- Delete Platform Data when it is "no longer necessary for a legitimate business purpose", when we stop operating the service, or when a user requests deletion (§3.d.i.2). Provide "an easily accessible and clearly marked way" to request deletion (§3.d.i.1).
- There is no selling or licensing of Platform Data (§3.a.iv), and no building of user profiles without consent (§3.a.v).
- Tech-Provider rules (§5.b) apply once customers' data is processed on their behalf: process it for the client's purpose and keep each client's data separate.

## Design implications for the map

1. Instagram **Handle** collection = Business Discovery through **one platform-owned Instagram professional account**, which also needs a Page or business portfolio. That account and its token become a configured system credential. It is not an Authorization of the Handle.
2. A Collection Run for a Handle re-pages the media edge newest to oldest until a Post is older than the Tracking Window, cursor by cursor. There is no time filter and no per-Post refresh. Metric Snapshot for a plain Handle = `like_count`, `comments_count`, `view_count` (Reels only, IG+FB combined for crossposts). Any of these may be absent when the owner hides counts, so model them as nullable.
3. **Authorized Handle** = also read `/media` (`since`/`until`) and Media Insights per Post (`views`, `reach`, `saved`, `shares`, `total_interactions`, …). Insights lag by up to 48 hours, and album children have no insights.
4. Prefer the **Unified Login** setup for the owner hook. It is Meta's recommended setup, accepts Instagram or Facebook credentials, needs no Page, gives a portfolio-owned token, and supports Business Discovery. It does require customers to have a business portfolio.
5. Metric names must be data, not schema, because Meta has deprecated or renamed about 10 metrics in the last two years.
6. Throughput is bounded by an unpublished per-user Platform Rate Limit on our single querying account. A scheduler with usage-header backoff is needed. Measure the limit early.
7. External customers trigger Advanced Access, App Review, Business Verification and Tech-Provider obligations.

## Open questions (need a spike, not more reading)

- Is the order of Business Discovery `media` guaranteed newest-first, and what is the maximum `media.limit(n)` page size?
- What is the real per-user Platform Rate Limit for Business Discovery calls from one account? Can we legitimately use several querying accounts to spread the load?
- Does Business Discovery work under Standard Access with a Unified Login System User token, or only with a Facebook User token, as the reference's permission list implies?
- What does a Business Discovery call return for creators who hide likes, and for age-gated accounts: an error, or an empty result?
