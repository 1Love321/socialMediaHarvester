# How does Facebook Page API access work for Handles and Authorized Handles?

Research for issue #4 (map #1). Researched 2026-11-20 against Meta's developer docs. The current Graph API version is **v27.0** (released 2026-11-04) ([changelog](https://developers.facebook.com/docs/graph-api/changelog)). Terms follow `GLOSSARY.md`: Handle, Authorized Handle, Authorization, Post, Metric Snapshot, Collection Run, Tracking Window, Raw Payload.

## TL;DR

- **Handles (Pages we don't own):** the only official Graph API route is the **Page Public Content Access (PPCA)** feature. It needs App Review plus Business Verification, and may need extra contracts. PPCA is still listed and has no deprecation notice. Its stated allowed use, "Analyze and/or display posts and engagement on Pages", matches our use case. Approval is a manual review. Expect friction, not a formality.
- **What PPCA gives a Handle Collection Run:** Post content fields; `shares.count`; reactions total and per-type counts via `reactions.summary(total_count)`; comments `total_count` via `summary=true`; and Page `fan_count`/`followers_count`. It gives **no** views, reach, impressions, or video views. Insights need the ANALYZE task on the Page, which means an Authorization.
- **Feed caps:** about 600 ranked published posts per year per Page, and at most 100 per request. A 14-day Tracking Window fits easily. A 100-day window on a high-volume Page could exceed the ranked cap.
- **Authorized Handles:** one Facebook Login Authorization with `pages_show_list`, `pages_read_engagement`, `read_insights`, `instagram_basic`, and `instagram_manage_insights` lets us call `/me/accounts`. That returns a Page access token for **every** Page the user granted. Each Page's `instagram_business_account` field gives the linked IG professional account. One Authorization therefore fans out to N Facebook Authorized Handles plus up to N Instagram Authorized Handles.
- **Token lifetimes:** short-lived user token lasts hours. Long-lived user token lasts about 60 days. A Page token derived from a long-lived user token has **no expiration date**, but it can be invalidated. Data access expires 90 days after the user's last activity. A Business Manager System User token does not expire by time.
- **Meta Content Library:** it is the "intended" public-content route, but only for not-for-profit academic or public-interest researchers. It runs in a secure clean room. **Not usable** for this tool.
- **Insights churn:** Meta removed impressions-family metrics in 2025-2026 and replaced them with `*_media_view` "views" metrics. Store metrics as an open name/value set, not fixed columns.

## 1. Pages we don't own (Handles)

### 1.1 Which feature: PPCA vs PPMA

- **PPCA** "allows an app access to the Pages Search API and to read public data for Pages. Readable data includes business metadata, public comments and posts." Allowed usage: "Analyze and/or display posts and engagement on Pages." ([PPCA](https://developers.facebook.com/docs/features-reference/page-public-content-access))
- **Page Public Metadata Access (PPMA)** covers only Page metadata, such as Like and follower counts and "about" info. PPMA "is superseded by the Page Public Content Access (PPCA) feature". Apps that need the Page feed edge or comments must request PPCA instead. An app with PPCA can't also request PPMA. ([PPMA](https://developers.facebook.com/docs/features-reference/page-public-metadata-access))
- Without PPCA, a live app "will not be able to see any Page public content". ([PPCA](https://developers.facebook.com/docs/features-reference/page-public-content-access))

**Conclusion: we need PPCA.** PPMA alone cannot read Posts.

### 1.2 Requirements and approval difficulty

- PPCA requires App Review "before your app can access live data". It is "only available with business verification". "You may also need to sign additional contracts." ([PPCA](https://developers.facebook.com/docs/features-reference/page-public-content-access))
- **Business Verification** confirms a legitimate business entity. It must be done by an Admin of a Business (Business Manager), not by an individual. It is required for Advanced Access. ([Business verification](https://developers.facebook.com/docs/development/release/business-verification))
- **Standard vs Advanced access:** apps are "automatically approved for Standard Access" to all permissions and features of their app type. Standard Access features are active only for users **with a role on the app**. Advanced Access requires Business Verification plus App Review per feature or permission. ([Access levels](https://developers.facebook.com/docs/graph-api/overview/access-levels))
- **Is PPCA still available?** Yes. The feature reference page is live and carries no deprecation notice ([PPCA](https://developers.facebook.com/docs/features-reference/page-public-content-access)). The Page reference still documents PPCA/PPMA access rules ([Page](https://developers.facebook.com/docs/graph-api/reference/page)).
- **How hard is approval?** Meta publishes no approval rate or SLA. The review is manual and screencast-based. Reviewers reject submissions when the screencast does not show the feature being needed. In a 2019 rejection, reviewers suggested `read_insights` instead. An OSCE guide (c. 2020) calls PPCA review "the most difficult" step in getting public API access. These are secondary or anecdotal sources ([OSCE guidelines PDF](https://www.osce.org/files/f/documents/d/b/483644.pdf), [coderevolution forum](https://coderevolution.ro/support/plugins/fb-to-post-app-review-rejected/)).
  - *Inference:* an internal analytics tool that shows posts and engagement for public brand or sports Pages fits the stated allowed usage word for word. The main risks are the Business Verification paperwork, a convincing screencast, and possible extra contracts. **Budget weeks and a possible rejection loop.** Build so Facebook Handles can be disabled until approval lands.

### 1.3 Tokens and calls for Handles

- For published, unrestricted Pages, read public data with an **App access token or User access token** plus PPCA/PPMA. Restricted Pages (age or region) need the app user to meet the restriction. Apps with PPCA "can access only public data". ([Page](https://developers.facebook.com/docs/graph-api/reference/page))
- For PPCA, Meta recommends a **System User access token** "to avoid rate limiting issues". ([Page feed](https://developers.facebook.com/docs/graph-api/reference/page/feed), [Page](https://developers.facebook.com/docs/graph-api/reference/page))
- Calls: `GET /{page-id}/posts` (or `/feed`, `/published_posts`) with `fields=id,message,created_time,updated_time,permalink_url,full_picture,attachments,status_type,shares,reactions.summary(total_count).limit(0),comments.summary(true).limit(0)`. Field names come from the [Page feed](https://developers.facebook.com/docs/graph-api/reference/page/feed) and [Post](https://developers.facebook.com/docs/graph-api/reference/post) references.
- **Doc inconsistency:** the Post reference also says "A page access token with the pages_manage_posts permission and Page Public Content Access Feature are required to read publicly shared Page posts. The person requesting the access token must be an admin of the Page." ([Post](https://developers.facebook.com/docs/graph-api/reference/post)). That contradicts the Page reference's App/User-token rule above. Verify empirically in development mode during the spike.

### 1.4 Fields and engagement counts available for Handles

| Data | How | Source |
|---|---|---|
| Post content: `id`, `message`, `created_time`, `updated_time`, `permalink_url`, `full_picture`, `attachments`, `status_type`, `is_published` | Post fields | [Page feed](https://developers.facebook.com/docs/graph-api/reference/page/feed) |
| Shares count | `shares.count`. "The share count may include deleted posts and posts you cannot see for privacy reasons." | [Page feed](https://developers.facebook.com/docs/graph-api/reference/page/feed), [Post](https://developers.facebook.com/docs/graph-api/reference/post) |
| Reactions total | `reactions.summary(total_count)` | [Reactions](https://developers.facebook.com/docs/graph-api/reference/object/reactions) |
| Reactions per type (LIKE, LOVE, WOW, HAHA, SORRY, ANGRY) | `reactions.type(LOVE).limit(0).summary(total_count)`. Use field aliases to get all types in one call. "like" includes "care". | [Reactions](https://developers.facebook.com/docs/graph-api/reference/object/reactions) |
| Comments total | `comments.summary(true)` gives `total_count`. `filter=stream` includes replies; `toplevel` does not. It "can be greater than or equal to the actual number of comments returned". | [Comments](https://developers.facebook.com/docs/graph-api/reference/object/comments) |
| Page follower/like count | `fan_count` (PPCA/PPMA). On New Pages Experience Pages it returns the followers count. `followers_count` also exists. | [Page](https://developers.facebook.com/docs/graph-api/reference/page) |
| Views, reach, impressions, video views, clicks | **Not available.** Insights need a Page token from a user with the ANALYZE task. | [Page insights](https://developers.facebook.com/docs/graph-api/reference/page/insights), [Insights](https://developers.facebook.com/docs/graph-api/reference/insights) |

Privacy limits: "Other Users' or Pages' reactions are unavailable". We get counts only, not who reacted ([Reactions](https://developers.facebook.com/docs/graph-api/reference/object/reactions)). Comment `id`s are withheld under PPCA without the MODERATE task ([Comments](https://developers.facebook.com/docs/graph-api/reference/object/comments)). That is fine, because comments are out of scope. User information appears only with a Page token ([Page feed](https://developers.facebook.com/docs/graph-api/reference/page/feed)).

### 1.5 Feed limits relevant to the Tracking Window

- About **600 ranked, published posts per year** are returned. `limit` is at most 100 per request; higher values return an error. "Expired posts" are no longer viewable. ([Page feed](https://developers.facebook.com/docs/graph-api/reference/page/feed))
- **Video posts require the requester to be a Page admin.** **Reels** are listed via the Page `video_reels` edge, not the feed. ([Page feed](https://developers.facebook.com/docs/graph-api/reference/page/feed))
  - *Implication:* for Handles, Reels and video posts may be missing or partial. This is an open question for the spike.
- Several legacy Post fields (`caption`, `description`, `link`, `name`, `object_id`, `source`, `type`) are deprecated on feed/posts endpoints since v3.3 ([Post](https://developers.facebook.com/docs/graph-api/reference/post)).

## 2. Pages we own or are authorized for (Authorized Handles)

### 2.1 Permissions

From the [Permissions reference](https://developers.facebook.com/docs/permissions):

- `pages_show_list`: list the Pages a person manages.
- `pages_read_engagement`: read content posted by the Page, plus metadata. Depends on `pages_show_list`.
- `pages_read_user_content`: user-generated content on the Page. Probably not needed, since comments are out of scope.
- `read_insights`: "read the Insights data for Pages … the person owns". Depends on `pages_read_engagement` and `pages_show_list`.
- `instagram_basic`: IG professional account profile and media. Depends on `pages_read_user_content` and `pages_show_list`.
- `instagram_manage_insights`: IG insights. Depends on `instagram_basic`, `pages_read_engagement`, and `pages_show_list`.
- `business_management`: needed only if Pages are reached through Business Manager.

Access levels for the internal phase: if every authorizing person has a role on our app, **Standard Access with no App Review is enough**. For external customers we need Advanced Access, which means App Review per permission plus Business Verification ([Access levels](https://developers.facebook.com/docs/graph-api/overview/access-levels), [Business verification](https://developers.facebook.com/docs/development/release/business-verification)).

### 2.2 One Authorization yields many Page tokens and linked Instagram accounts

1. Run Facebook Login (for Business). The user picks which Pages and IG accounts to grant and returns a short-lived user token ([IG get started](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-facebook-login/get-started)).
2. Exchange it for a **long-lived user token** (`grant_type=fb_exchange_token`, about 60 days) ([Long-lived tokens](https://developers.facebook.com/docs/facebook-login/guides/access-tokens/get-long-lived)).
3. Call `GET /me/accounts` with the long-lived user token. It returns the ID and a Page access token **for each Page** the user granted. "Store each ID and token separately." ([Pages API overview](https://developers.facebook.com/docs/pages-api/overview), [Long-lived tokens](https://developers.facebook.com/docs/facebook-login/guides/access-tokens/get-long-lived))
4. For each Page, call `GET /{page-id}?fields=instagram_business_account` to get the linked **IG professional account ID**. That account is then readable at `/{ig-user-id}/media` ([IG get started](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-facebook-login/get-started)). Only Business and Creator IG accounts work, not consumer accounts ([IG with FB Login](https://developers.facebook.com/docs/instagram-platform/instagram-api-with-facebook-login)).

**Model implication:** one Authorization maps to many Authorized Handles across two Platforms. Each holds its own Page token, or uses the IG path with the Page/user token. The Authorization stores the user token plus its granted scopes. Revoking it disables all of its Authorized Handles.

### 2.3 Insights for Authorized Handles

- `/{page-id}/insights` and `/{post-id}/insights` need `read_insights` and `pages_read_engagement`, plus a Page token from a person with the **ANALYZE** task ([Page insights](https://developers.facebook.com/docs/graph-api/reference/page/insights), [Insights](https://developers.facebook.com/docs/graph-api/reference/insights)).
- Current post metrics include:
  - `post_media_view` (replaces `post_impressions`) and `post_total_media_view_unique` (replaces `post_impressions_unique`)
  - `post_reactions_by_type_total`
  - `post_clicks` and `post_clicks_by_type`
  - `post_video_views`, `post_video_avg_time_watched`, and `post_video_complete_views_30s`, among others

  Sources: [Insights](https://developers.facebook.com/docs/graph-api/reference/insights), [v25 changelog](https://developers.facebook.com/docs/graph-api/changelog/version25.0), [Deprecated metrics](https://developers.facebook.com/documentation/pages-api/platforminsights/page/deprecated-metrics).
- **Deprecations:**
  - Nov 15, 2025: `impressions` replaced by `views` on all versions, and `page_fans*` replaced by `page_follows*` ([Meta blog 2025-08-15](https://developers.facebook.com/blog/post/2025/08/15/page-insights-api-updates/), [Deprecated metrics](https://developers.facebook.com/documentation/pages-api/platforminsights/page/deprecated-metrics)).
  - v25 / "by June 15, 2026": the `*_impressions_unique`, reach-family, and `post_video_views_unique` metrics return errors on all versions ([v25 changelog](https://developers.facebook.com/docs/graph-api/changelog/version25.0), [Insights](https://developers.facebook.com/docs/graph-api/reference/insights)).
  - The deprecated-metrics page dates the `*_unique` removals to June 15, **2025**, while the Insights reference says **2026**. Either way they are gone now.
- **Constraints:**
  - Only the last **2 years** of insights are available.
  - `since`/`until` covers at most 90 days.
  - Page Insights is only available for Pages with **100+ likes**.

  Source: [Insights](https://developers.facebook.com/docs/graph-api/reference/insights).

## 3. Token lifetimes and invalidation

| Token | Lifetime | Source |
|---|---|---|
| Short-lived user token | Hours (about 1-2 h) | [Long-lived tokens](https://developers.facebook.com/docs/facebook-login/guides/access-tokens/get-long-lived), [Access tokens](https://developers.facebook.com/docs/facebook-login/guides/access-tokens) |
| Long-lived user token | About 60 days. An expired token can't be exchanged; the user must log in again. | [Long-lived tokens](https://developers.facebook.com/docs/facebook-login/guides/access-tokens/get-long-lived) |
| Page token from a long-lived user token | "Do not have an expiration date", but can be invalidated (for example, the user loses the Page role) | [Long-lived tokens](https://developers.facebook.com/docs/facebook-login/guides/access-tokens/get-long-lived) |
| System User token (Business Manager) | Doesn't expire by time; "still subject to invalidation" | [Access tokens](https://developers.facebook.com/docs/facebook-login/guides/access-tokens) |
| Data access | Expires **90 days** after the user was last active. Re-authorize with `auth_type=reauthorize`. Check with `debug_token` / `data_access_expiration_time`. | [Auth vs data](https://developers.facebook.com/docs/facebook-login/auth-vs-data) |

Meta warns: "Do not depend on these lifetimes remaining the same" ([Access tokens](https://developers.facebook.com/docs/facebook-login/guides/access-tokens)). The auth-vs-data page lists Page and business permissions such as `pages_read_engagement` and `business_management` as **not** subject to data-access expiry, though it doesn't spell out how that applies to Page tokens ([Auth vs data](https://developers.facebook.com/docs/facebook-login/auth-vs-data)).

**Implications:**
- Store the token per Authorized Handle.
- Probe each token with `debug_token` on every Collection Run.
- On failure, mark the Authorization as needing re-authorization rather than failing silently.

## 4. Rate limits

From [Rate limiting](https://developers.facebook.com/docs/graph-api/overview/rate-limiting):

- **Pages API with a Page or System User token** is under **Business Use Case (BUC)** limits: calls per 24 h = 4800 × number of engaged users (of that Page). The `X-Business-Use-Case-Usage` header reports usage, including `estimated_time_to_regain_access`.
- **App or User token** is under **Platform** limits: calls per hour = 200 × number of users (DAU). Watch the `X-App-Usage` header.
- When both could apply, BUC wins. No PPCA-specific numbers are documented.

**Implication:**
- An internal tool has few app users, so Platform limits are small. That is why Meta recommends a System User token for PPCA.
- Batch fields to cut calls. Each Post needs one call, or use `?ids=` batching or `/posts` with nested summaries.
- Hundreds of Handles × (1 page + ~1 call per 100 posts) per run is modest. Respect the headers and add backoff.

## 5. Meta Content Library: is it the intended route?

- MCL and its API are Meta's sanctioned route for broad public content. They include Page posts with "number of reactions, shares, views and more", which is more than PPCA gives (views) ([MCL](https://transparency.meta.com/researchtools/meta-content-library/)).
- **Eligibility:** the applicant must be affiliated with an academic institution or a not-for-profit whose primary purpose is scientific or public-interest research. Applications are independently reviewed. Data is analyzed inside secure clean rooms (Meta Secure Research Environment or SOMAR VDE) ([MCL](https://transparency.meta.com/researchtools/meta-content-library/), [Computing platforms](https://developers.facebook.com/docs/content-library-and-api/get-access/computing-platform-comparison/)).
- **Verdict: not usable** for an internal or commercial harvester. There is no eligibility, and the data can't be piped into our own DB. PPCA is the only official option for Handles.

## 6. Meta Platform Terms constraints

From the [Platform Terms](https://developers.facebook.com/terms/):

- Process Platform Data only for permitted purposes and as described in our privacy policy (§3.a.viii, §4.c).
- Delete it when no longer needed for a legitimate business purpose, or on user or Meta request (§3.d.i).
- Selling or licensing Platform Data is prohibited (§3.a.iv). This matters for the later external-customer phase.
- Security must meet industry standards (§6.a.i). Meta may audit (§7.c).

**Implication:** keeping every Metric Snapshot and Raw Payload indefinitely needs a stated retention purpose. Plan a deletion path for each Authorization and each Handle.

## 7. Implications for the design

1. **Two collection modes per Platform adapter.**
   - Handle: PPCA, a System User or app token, and public counts only.
   - Authorized Handle: a Page token, plus insights.

   The Metric Snapshot must allow metric sets to differ by access mode.
2. **Metric Snapshot as name→value pairs, not fixed columns.** Meta renamed impressions to views in 2025-2026. Keep the Raw Payload for re-derivation.
3. **Authorization fans out:** one Facebook Login gives N Page tokens plus up to N IG professional accounts. Instagram Authorized Handles likely ride on the same Facebook Authorization; see the Instagram ticket.
4. **Tracking Window vs feed cap:** 14 days is fine. A 100-day override on very active Pages may hit the ~600 ranked posts per year cap. Reels and videos need separate edges or admin rights.
5. **Facebook Handles are gated by PPCA approval and Business Verification.** Authorized Handles work immediately under Standard Access for app-role users. Ship Authorized Handles first, and keep Handles feature-flagged.
6. **Token health:** check with `debug_token` each Collection Run, detect expiry or invalidation, and drive a re-authorization flow. Page tokens don't time-expire, but data access and roles can lapse.

## Open questions (not resolvable from docs)

- Does the PPCA approval queue in 2026 accept internal brand-monitoring tools? No official stats exist; only applying will tell.
- Which token actually works for PPCA reads (App, System User, or Page token with `pages_manage_posts`)? The docs conflict. Spike this in dev mode with an admin-owned test Page.
- Under PPCA, are video posts and Reels on non-owned Pages returned, and with which counts?
- Does `followers_count` work under PPCA for non-owned Pages, or only `fan_count`?
