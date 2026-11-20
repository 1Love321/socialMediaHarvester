# What do platform terms require for storing harvested data?

Research for issue #5 of the wayfinder map (#1). Sources were read on 2026-11-20. Verbatim quotes come from the live pages:

| Source | URL | Version |
|---|---|---|
| YouTube API Services Developer Policies | https://developers.google.com/youtube/terms/developer-policies | Last updated 2026-11-06 |
| YouTube "Additional policies for derived metrics and data storage" | https://developers.google.com/youtube/terms/derived-metrics-policy | Last updated 2026-09-14 |
| YouTube API Services Terms of Service | https://developers.google.com/youtube/terms/api-services-terms-of-service | Last updated 2026-11-06 |
| YouTube API Services revision history | https://developers.google.com/youtube/terms/revision-history | entries up to June 1, 2026 |
| Complying with YouTube Developer Policies (guide) | https://developers.google.com/youtube/terms/developer-policies-guide | Last updated 2026-09-14 |
| Google API Services User Data Policy | https://developers.google.com/terms/api-services-user-data-policy | Last updated February 15, 2024 |
| Meta Platform Terms | https://developers.facebook.com/terms/dfc_platform_terms/ | Last updated February 3, 2026 |
| Meta Developer Policies | https://developers.facebook.com/devpolicy/ | Last updated February 3, 2026 |
| Meta Platform Terms §3.e exceptions | https://developers.facebook.com/terms/3e/ | n/a |
| Meta Data Deletion Request Callback | https://developers.facebook.com/docs/development/create-an-app/app-dashboard/data-deletion-callback/ | n/a |
| Meta Facebook Login manual flow (deauthorize callback) | https://developers.facebook.com/docs/facebook-login/guides/advanced/manual-flow/ | n/a |
| Meta Data Use Checkup | https://developers.facebook.com/docs/resp-plat-initiatives/individual-processes/data-use-checkup/ | n/a |
| Meta Data Protection Assessment | https://developers.facebook.com/docs/resp-plat-initiatives/individual-processes/data-protection-assessment/ | n/a |
| Meta Page Public Content Access feature | https://developers.facebook.com/docs/features-reference/page-public-content-access/ | n/a |
| Instagram Business Discovery | https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/business_discovery/ | n/a |
| Instagram Platform overview | https://developers.facebook.com/docs/instagram-platform/overview/ | n/a |

> **This is engineering research, not legal advice.** Have counsel review it before relying on it, especially before external customers are onboarded.

## TL;DR

1. **YouTube does not allow indefinite storage of Public Data for a plain Handle.** Non-Authorized Data, which means anything fetched without the channel owner's credentials, may be stored for at most **30 days**. After that it must be **deleted or refreshed**. Statistics get an explicit rule: *"an API Client must not store statistics retrieved as Non-Authorized Data for more than 30 days."* Under the default policy, an indefinite, append-only history of Metric Snapshots for a plain YouTube Handle is **not allowed**.
2. **Exception 1 (Authorized Handles).** Statistics, YouTube Analytics data and YouTube Reporting data that were obtained as Authorized Data may be stored *"for as long as is necessary"*. The client must re-check every 30 days that the Authorization is still valid and that the video still exists. All other Authorized Data (titles, descriptions and the rest of the Raw Payload) still follows the 30-day delete-or-refresh rule.
3. **Exception 2 (new in 2026, opt-in).** Developers who are **audited** and have an **accepted analytics use case**, applied for through the quota-extension/audit form, may store statistics (*"views, likes, subs count, comment counts"*) and derived metrics **for up to 36 calendar months**. Text such as titles and descriptions still follows the 30-day rule. This is the only path to a long Metric Snapshot history for plain YouTube Handles.
4. **YouTube revocation.** When an Authorization is revoked through our app, revoke the token immediately and **delete all Authorized Data within 7 days**. When it is revoked from Google's security page, or the token can no longer be refreshed, delete within **30 days**. A user deletion request must be honoured within **7 days**. This conflicts with the current glossary line *"When the Authorization ends, it reverts to a plain Handle and keeps its history."*
5. **Meta (Facebook and Instagram) sets no fixed TTL.** Platform Data may be kept while *"necessary for a legitimate business purpose"*. It must be deleted *"as soon as reasonably possible"* when that purpose ends, when the User requests it or no longer has an account with us, when Meta asks, or when we stop operating the product. Meta's definition of Platform Data includes **derived and aggregated data**, so Metric Snapshots count too. Indefinite storage of Frozen Posts is acceptable on Meta while the business purpose holds, subject to annual Data Use Checkup and Data Protection Assessment and to Meta audits.
6. **Termination clauses.** On termination or suspension, YouTube's ToS requires deleting *all* API Data. Meta can require us to *"stop Processing and delete Platform Data"*. The store must be able to purge by Platform, by Handle and by Authorization.

## YouTube: the rules in detail

### Definitions (Developer Policies §IV)

> "Authorized Data" means API Data that an active user expressly authorizes an API Client to access or otherwise use through User Credentials.

> "Non-Authorized Data" means API Data accessible by an API Client without User Credentials.

In glossary terms, Public Data about a plain **Handle** (videos.list, channels.list and similar calls made with an API key or with a token that does not belong to that channel) is **Non-Authorized Data**. Data fetched for an **Authorized Handle** with that owner's token is **Authorized Data**, and that includes Public Data fetched that way.

### Storage and refresh (Developer Policies §III.E.4)

- §III.E.4.a, tokens: *"API Clients may store authorization tokens for as long as is necessary provided that those tokens are used only for purposes consistent with the specific consent granted by an active user"*
- §III.E.4.b, authorized statistics and analytics: *"API Clients may store the following types of Authorized Data for as long as is necessary provided that the data is used for purposes consistent with the specific consent granted by an active user … data retrieved through the YouTube Analytics API service, data provided through the YouTube Reporting API service, or statistics provided through other YouTube API services, such as the number of views for a video …"*
  - *"Note that even though an API Client may store this data for more than 30 days, the Client must still ensure every 30 days that it is still authorized by the user to access that data."*
  - *"For example, an API Client may store view counts for a video for more than 30 days, but it must still verify every 30 days that its authorization to access the video uploader's data has not been revoked. The API Client must also verify, every 30 days, that the video has not been deleted."*
  - **This is the explicit statement about statistics over time:** *"To be clear, an API Client must not store statistics retrieved as Non-Authorized Data for more than 30 days. For example, an API Client must not store the subscriber count for a YouTube channel for more than 30 days without authorization from the channel owner."*
- §III.E.4.c, other Authorized Data: *"…for no longer than 30 calendar days. After 30 calendar days, the API Client must either delete or refresh the stored data."*
- §III.E.4.d, Non-Authorized Data: *"API Clients may temporarily store limited amounts of Non-Authorized Data for as long as is necessary for the purposes of the API Client but not longer than 30 calendar days. … after 30 calendar days, the API Client must either delete or refresh the stored data."*
- §III.E.4.e: *"API Clients should reflect metadata changes and viewcount updates as quickly as possible."*
- §III.E.4.f: *"API Clients must display the most updated API Data available … although API Clients may display historical API Data provided that it is presented accurately in context of time."* Metric charts are therefore fine as long as each point is labelled with its observation time.
- §III.E.4.g: *"Your API Clients that access or use user data must provide a way for a user to request that you delete stored data related to that user. … you must then delete it as soon as possible and within 7 calendar days."*
- §III.E.4.h: *"Your API Clients must not (i) replace API Data with similar, independently calculated data, or (ii) access or use API Data to create new or derived data or metrics."* The policy's own example forbids *"a score that factors in likes, total views, or any other API Data."*

The guide (https://developers.google.com/youtube/terms/developer-policies-guide) lists this among the things not to do: *"Store a user's information indefinitely. If a user requests that you delete their data or if you're unable to verify their authorization, you must do so within 30 days."*

### The 2026 derived-metrics and storage amendment (Developer Policies §III.L)

§III.L: *"These policies are only applicable to audited developers with analytics use cases that have explicitly applied for permission to create additional metrics, store statistical data, or both, through the standard quota extension request from (starting June 01, 2026)."*

From the derived-metrics policy page, under "Data Storage":

> "If your use case is accepted for additional derived metrics, you may store some statistical data for a duration beyond 30 days. Policy III E.4.b, E.4.c, and E.4.d are amended to allow accepted API Clients to store metrics (e.g., views, likes, subs count, comment counts) from statistical endpoints for up to 36 calendar months. Derived metrics (such as sentiment analysis) based on retrieved data may also be stored for up to 36 calendar months. Other data (such as video titles, creator names, descriptions, and comment text) must still follow the 30-day refresh and deletion policy in Section III(4)."

The same page explicitly allows leaderboards and historical comparison under an accepted use case: *"You may rank channel performance or track views between different channels for the purpose of comparison or historical analysis."* Its example is *"A 'History of YouTube' line graph showing the 36-month subscriber growth curves of different creators."* It also says: *"You must distinguish these metrics from metrics sourced from API Data."* To accept, the developer selects *"Section 5: Use Cases, API Integration, and Feature Implementation" then "Analytics & Reporting"* in the request form.

Revision history: the policy was added on May 4, 2026, and its storage allowance was clarified on June 1, 2026.

### Aggregation (Developer Policies §III.E.2)

> "Do not aggregate API Data except that you may only aggregate API Data relating to YouTube channels that are under the same content owner as recognized by YouTube pursuant to content licensing agreement(s) … Such aggregated API Data must only be viewable by that content owner."

> "Do not aggregate API Data or otherwise use API Data or YouTube API Services to gain insights into YouTube's usage, revenue, or any other aspects of YouTube's business."

### Revocation and deletion (Developer Policies §III.D.2 "Revocation")

- *"Every API Client must provide a clearly explained and easy way for users to revoke any authorization consent…"*
- *"When a user revokes consent through this mechanism, the API Client must programmatically revoke that token right away…"*
- *"…following revocation of consent through this mechanism, you and your API Clients must delete all Authorized Data that was accessed or stored pursuant to that consent. That deletion should happen as soon as possible and must take place within 7 calendar days of the revocation."*
- *"When a user revokes consent through that page [Google security settings], you and your API Clients must also delete all API Data related to that user… your API Clients will need to periodically reconfirm that its authorization tokens are still valid and delete API Data associated with users whose authorization tokens cannot be refreshed."*
- *"…all such deletions should happen as soon as possible and must take place within 30 calendar days of that revocation."*

Authorized Data must also stay with the user: *"API Clients must not display or allow access to Authorized Data to anyone other than the authorizing user or agents expressly approved by that user."* (§III.E.3)

### Termination, audits and quota (YouTube ToS and Developer Policies)

- ToS §24.3: *"Upon any suspension, notice of any discontinuance, or termination … you will immediately stop accessing and using all YouTube Property and delete all YouTube API Services (including all API Data) … including from your servers. At YouTube's request, you will certify your deletion…"*
- ToS: *"YouTube may monitor, review and inspect your API Client(s), and monitor and audit your access to and use of the YouTube API Services, at any time and without further notice to you…"*
- Developer Policies §III.D.3: *"If your API Client reaches the quota limit for a service, you can apply for a quota extension by completing an API Compliance Audit where you must specify the use case…"* The revision history (July 1, 2021) says an audit is needed for *"more than the default quota allocation of 10,000 units."*
- ToS: *"Each API Client will provide and adhere to a published privacy policy…"* The Developer Policies (§III.A.2) also require that privacy policy to link to Google's security settings page.

### Google API Services User Data Policy

This policy applies alongside the YouTube policies to Google user data obtained through OAuth. Its relevant points:

- *"You must disclose all user data that you access, use, store, delete, or share…"*
- The additional "Limited Use" and security-assessment requirements apply to *"Sensitive and Restricted Scopes"*. The policy defers to *"each product's User Data and Developer Policy"*, and for YouTube that is the Developer Policies above. It notes: *"If your app is only used by users within your own domain, then these requirements do not apply."* Channel owners outside our Workspace domain are not covered by that exemption.

## Meta (Facebook and Instagram): the rules in detail

### Scope

The Meta Developer Policies define Platform as the APIs that *"retrieve data from Meta and any other Meta Products"* and say: *"To use Platform, you agree to and must comply with these Developer Policies and all other Developer Docs, which are all … incorporated by reference into the Platform Terms."* The Instagram Graph API, Business Discovery, the Facebook Pages API and Page Public Content Access are all part of Meta Platform, so one set of terms governs both Facebook and Instagram. The old standalone Instagram Platform Policy page at help.instagram.com no longer serves substantive text.

Platform Terms §12 (Glossary), "Platform Data":

> "any information, data, or other content you obtain from us, through Platform or through your App, whether directly or indirectly … including data anonymized, aggregated, or derived from such data. Platform Data includes all Meta Product access tokens, app secrets, Meta user IDs, email addresses, profile pictures and usernames."

Metric Snapshots, Raw Payloads and anything we compute from them are therefore all Platform Data. Meta draws no public-versus-private line for retention.

### Retention and deletion (Platform Terms §3.d)

> "i. Unless required to keep Platform Data under applicable law or regulation, you must … do the following:
> 1. Update or delete Platform Data promptly after receiving a request from us or the User to do so and give Users an easily accessible and clearly marked way to ask for their Platform Data to be modified or deleted.
> 2. Delete all Platform Data as soon as reasonably possible in the following cases:
>    a. When retaining the Platform Data is no longer necessary for a legitimate business purpose that is consistent with these Terms and all other applicable terms and policies;
>    b. When you stop operating the product or service through which the Platform Data was acquired;
>    c. When we request you delete the Platform Data for the protection of Users …;
>    d. When a User requests their Platform Data be deleted or no longer has an account with you (unless the Platform Data has been aggregated, obscured, or de-identified so that it cannot be associated with a particular User, browser, or device), or for Tech Providers, when a User or the Client requests their Platform Data be deleted or the Client no longer has an account with you;
>    e. When required by applicable law or regulations; or
>    f. As required under Section 7 …"

Meta's terms contain **no 30-day refresh rule and no fixed maximum age**.

Privacy policy, §4.b: *"Your privacy policy must clearly explain what data you are Processing, how you are Processing it, the purposes for which you are Processing it, and how Users may request deletion of that data."*

Purpose limits, §3.a: §3.a.vii forbids *"materially changing the scope of Processing of previously collected Platform Data, unless … you first re-submit your App and receive our approval through App Review."* §3.a.viii forbids *"Processing Platform Data for purposes other than the applicable permitted purposes set forth in Meta's Developer Docs."* The Page Public Content Access feature has the allowed usage *"to analyze and/or display posts and engagement on Pages"* and *"requires successful completion of the App Review process"* plus *"business verification"*.

### Deletion and deauthorization callbacks

- Data Deletion Request Callback docs: *"Apps that access user data must provide a way for users to request that their data be deleted. In accordance with Meta's Platform Terms, all apps must inform users in their privacy policy how to request deletion of their data. Additionally, apps can implement a data deletion request callback…"* The callback *"must do the following: Initiate the deletion of any data your app has from Facebook about the user. Return a JSON response that contains a URL where the user can check the status of their deletion request and an alphanumeric confirmation code."* The FAQ adds: *"Every 21 days, you will receive an alert including the user identifiers you are required to delete…"*
- Deauthorize callback (Facebook Login manual-flow docs): *"we allow them to provide a de-authorize callback URL which will be pinged whenever this occurs. You can enable a deauthorize callback through the App Dashboard."* Meta's terms do not tie a separate deletion deadline to deauthorization alone. Deletion is triggered by a User's deletion request, the User no longer having an account with us, or loss of business purpose (§3.d.i.2).

### Compliance, audits and termination (Platform Terms §7)

- Audits: *"We or Third-Party Auditors may conduct an Audit, no more than once a calendar year unless there is a Necessary Condition…"*. Audit rights survive *"until 1 year after"* we demonstrate that all Platform Data has been deleted.
- Enforcement can include *"requiring that you stop Processing and delete Platform Data"*. Also: *"We may suspend or end your App's access to any Platform APIs, permissions, or features that your App has not used or accessed within a 28-day period."*
- Data Use Checkup: *"an annual assessment that evaluates whether a developer's continued use of and access to specific data via Meta APIs is in compliance…"*. It is required for live apps with advanced access, and the developer must *"Answer questions about your data handling practices."*
- Data Protection Assessment: *"an annual requirement for apps accessing certain types of data"*, with *"60 days to complete the assessment or risk losing platform access."*

### Tech Provider (relevant once external customers authorize their accounts)

Platform Terms §5.b: a Tech Provider *"will only use Platform and Process Platform Data on behalf of and at the direction of your Client … and not for your own purposes or another Client's"*, and *"will ensure that Platform Data you maintain on behalf of one Client is maintained separately from that of other Clients"*. Deletion, per §3.d.i.2.d, is required *"when a User or the Client requests their Platform Data be deleted or the Client no longer has an account with you"*.

### Media URLs (Instagram)

Instagram Platform overview: *"The CDN URL is privacy-aware and will not return the media when the content has been deleted or has expired."* Stored `media_url` values will go stale. Media download is already out of scope, so this only matters for display links.

## Summary table

| Data kind | Platform | Storage rule (source) | Design implication |
|---|---|---|---|
| Metric Snapshots of a plain **Handle** (Public Data, no owner token) | YouTube | Non-Authorized statistics may be kept for **at most 30 days** (§III.E.4.b, last paragraph; §III.E.4.d). With an accepted audited analytics use case, **up to 36 calendar months** (derived-metrics policy). | A per-Platform retention policy is needed for Metric Snapshots. Default: purge YouTube snapshots older than 30 days for plain Handles. To get history, apply for the §III.L analytics use case, then cap at 36 months. The glossary promise "earlier ones are never overwritten" needs a retention caveat. |
| Metric Snapshots of an **Authorized Handle** | YouTube | Authorized statistics and Analytics/Reporting data may be kept *"as long as is necessary"*. Authorization must be re-verified, and the video checked as not deleted, **every 30 days** (§III.E.4.b). | Indefinite history is allowed while the Authorization is active. A job must check token validity and video existence at least every 30 days, even for Frozen Posts. |
| Post metadata and **Raw Payload** (titles, descriptions, thumbnails, etc.) | YouTube | Authorized or not: **delete or refresh within 30 days** (§III.E.4.c and d). This still applies under the 36-month amendment. | Frozen Posts cannot sit untouched. Either refresh them cheaply at least every 30 days (`videos.list` takes up to 50 ids per call) or delete their metadata and Raw Payload. A Raw Payload is a snapshot of text data, so keep only the latest one, or expire older ones after 30 days. |
| Derived metrics (engagement rate, scores, Brand roll-ups) | YouTube | Forbidden by default (§III.E.4.h). Cross-owner aggregation is forbidden (§III.E.2). Allowed only under an accepted analytics use case, clearly labelled as ours, and stored for up to 36 months. | Do not persist or display computed metrics, or roll up YouTube data across Brands, until the use case is accepted. Raw counts are the safe default. |
| Data on **Authorization revoked** | YouTube | Revoke the token immediately. Delete all Authorized Data within **7 days** if revoked in our app, or within **30 days** if revoked via Google or the token stops refreshing (§III.D.2). | This contradicts "reverts to a plain Handle and keeps its history". On revocation, purge everything fetched under that Authorization: Private Data, plus statistics and metadata retained beyond the 30-day Non-Authorized limit. Data needs **provenance**, meaning which Authorization (if any) it was fetched under. |
| User deletion request | YouTube | Provide a delete mechanism. Delete within **7 days** (§III.E.4.g). | Need a purge-by-Handle/owner operation with an SLA. |
| Tokens | YouTube | Keep *"as long as is necessary"* for the consented purpose (§III.E.4.a). | Store encrypted. Delete the token on revocation. |
| Everything on API termination | YouTube | Delete all API Data, and certify on request (ToS §24.3). | Need a Platform-wide purge. |
| Metric Snapshots (any Handle) | Facebook / Instagram | No TTL. Keep while *"necessary for a legitimate business purpose"*. Derived and aggregated data is still Platform Data (§3.d, §12.l). | Indefinite snapshot history for Frozen Posts is acceptable. Document the business purpose and a retention period in the privacy policy, because Data Use Checkup and the Data Protection Assessment will ask. |
| Post and **Raw Payload** | Facebook / Instagram | Same rule. Update or delete *"promptly"* when asked by Meta or the User (§3.d.i.1). | No forced refresh. Frozen Posts may stay frozen. Expect deleted Posts and expired CDN URLs. |
| Private Data (Insights) of an **Authorized Handle** | Facebook / Instagram | Same rule. Delete when the User requests it or *"no longer has an account with you"* (§3.d.i.2.d). | Implement the Data Deletion Request callback (status URL plus confirmation code) and the deauthorize callback. Revocation is not by itself a hard delete trigger, but the business purpose usually ends with it. Default to purging Private Data and decide case by case for the rest. |
| External customers' data (future) | Facebook / Instagram | Tech Provider rules: process only for that Client and keep each Client's data separate (§5.b). | The owner hook needs a per-Client (tenant) partition of Platform Data. |
| External customers' data (future) | YouTube | Authorized Data may be shown only to the authorizing user or agents they approve (§III.E.3). Per-owner aggregation only (§III.E.2). | Same need for tenant isolation. Internal staff viewing a customer's data needs that customer's express approval. |

## Implications for Frozen Posts and Metric Snapshots

- **Meta:** Frozen Posts and all their Metric Snapshots may be kept indefinitely, provided a documented legitimate business purpose exists and deletion requests and callbacks are honoured.
- **YouTube, plain Handle:** under the default policy, Frozen Posts cannot keep snapshots or metadata more than 30 days old. Under an accepted §III.L analytics use case, snapshots (counts only) may be kept for 36 months. Metadata and Raw Payload must still be refreshed or deleted within 30 days, so a Frozen YouTube Post needs at least a monthly lightweight metadata refresh, or must be reduced to `{video id, snapshots}`. A fresh `videos.list` call also returns current statistics, so a "metadata refresh" collects a new count as a side effect. Whether the system records it as a new Metric Snapshot is a design choice.
- **YouTube, Authorized Handle:** snapshots may be kept indefinitely while the Authorization stays valid. A 30-day authorization and existence check is still required, and everything is deleted on revocation.

## Open questions this raises for the map

1. **Do we apply for YouTube's §III.L analytics use case (36-month storage plus derived metrics)?** Without it, YouTube Metric Snapshot history for plain Handles is capped at 30 days, which undermines the product's core value for YouTube. Applying requires a quota extension and a compliance audit, and we will need one anyway beyond 10,000 units per day for hundreds of Handles.
2. **Glossary conflict:** "Authorized Handle … When the Authorization ends, it reverts to a plain Handle and keeps its history" violates the YouTube revocation rule and should be reworded. Metric Snapshot "earlier ones are never overwritten" also needs a retention caveat.
3. **Provenance model:** each Post, Raw Payload and Metric Snapshot needs to record whether it was fetched under an Authorization, and which one, so revocation purges are possible. Snapshots also need a retention policy per Platform and per data kind.
4. **Brand roll-ups:** combining YouTube data across Handles of different content owners is restricted (§III.E.2). Comparing NBA versus other Brands is the "leaderboard / historical comparison" case that needs the accepted analytics use case.
5. **Frozen Posts on YouTube** need a monthly refresh or reduction job, which costs quota.
6. **Meta app setup:** App Review for Page Public Content Access and business verification, the Data Deletion Request URL, the deauthorize callback, a privacy policy URL, the annual Data Use Checkup, and possibly the Data Protection Assessment.
