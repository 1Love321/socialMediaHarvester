# Social Media Harvester

Collects posts and engagement data from social media platforms for a set of tracked handles, and stores it for later viewing and analysis.

## Language

### Sources

**Platform**:
A social media service the harvester collects from (e.g. YouTube, Facebook, Instagram; later TikTok, X).
_Avoid_: Network, provider, site

**Brand**:
A real-world organization or person whose Handles are grouped together across Platforms (e.g. the NBA).
_Avoid_: Client, entity, company, team

**Handle**:
A single account on a Platform, identified by its platform-specific name or id (e.g. `@NBA` on YouTube). By default only its Public Data is collected.
_Avoid_: Channel, profile, page, Watched Handle, Public Handle

**Authorization**:
An owner's grant allowing the harvester to read Private Data for one Handle. It is Active while it works; it ends as Expired (stopped working without the owner withdrawing; can be reconnected, and becomes Revoked if not reconnected in time), Revoked (consent withdrawn, or the Handle disconnected by staff) or Replaced (a newer Authorization for the same Handle took over). Each grant is a new Authorization; a Handle has at most one Active one.
_Avoid_: Connection, link, token (the token is an implementation detail of an Authorization)

**Authorized Handle**:
A Handle covered by an Active Authorization; both Public and Private Data are collected for it. When the Authorization ends, it stays tracked as a plain Handle and keeps whatever history its Platform's rules allow (a Revoked Authorization can require deleting the data fetched under it).
_Avoid_: Connected Account, Private Handle, Linked Handle

**Platform Login**:
The way an owner logs into one Platform to grant an Authorization, offered as one "Connect" option per Platform (e.g. Connect Instagram). Each Platform has its own, even when two Platforms share the same company login behind the scenes.
_Avoid_: Login (on its own), Authorizer, Connect Flow, Login Provider

**Connect Link**:
A short-lived link, scoped to one Brand, that lets an account owner who is not a user of the harvester run Platform Logins and grant Authorizations; the accounts they connect land under that Brand.
_Avoid_: Invite, onboarding link

**System Credential**:
Access that belongs to us rather than to an account owner, used to read Public Data (e.g. the Instagram account we own for looking up other accounts, a Platform API key). It is not an Authorization and covers no Handle.
_Avoid_: Service account, app token, Authorization

### Data

**Public Data**:
Content and metrics any viewer of the Platform can see, such as posts and their public like/comment/view counts.

**Private Data**:
Data the Platform only releases to the Handle's owner, obtained solely through an Authorization (e.g. insights, reach, audience demographics).
_Avoid_: Scraped data, hidden data

**Post**:
A single piece of content published by a Handle (video, photo, reel, status), as we store it in a shape common to all Platforms. It always reflects the latest Raw Payload received for it; its metrics live in its Metric Snapshots, not on the Post.
_Avoid_: Item, content, media

**Post Type**:
The normalized category of a Post, the same set across all Platforms (video, short, live, image, carousel, reel, text, link, or unknown when the Platform doesn't reveal it). The Platform's own type label is kept next to it.
_Avoid_: Kind, media type, format

**Unavailable Post**:
A previously collected Post that the Platform no longer returns (deleted, made private, or removed). It keeps its history but receives no new Metric Snapshots.
_Avoid_: Deleted post, missing post

**Raw Payload**:
A Post's or a Handle's part of the Platform's response from one fetch, with its content unchanged. It is the source of truth: the Post, each Metric Snapshot and each Handle Snapshot are derived from Raw Payloads and can be re-derived from them while they are kept. Older Raw Payloads are deleted after a set time, except the latest one for each Post and Handle.
_Avoid_: Source JSON, original

**Metric Snapshot**:
The engagement counts (views, likes, comments, etc.) of a Post as observed at one moment, from a single fetch of either Public Data or Private Data, never both. A count the Platform didn't give is recorded as not given, never as zero. Snapshots accumulate: a new observation always adds a new snapshot and never replaces an earlier one.
_Avoid_: Stats, current metrics

**Handle Snapshot**:
The account-wide counts of a Handle (followers, subscribers, number of posts) as observed during one Collection Run. Like Metric Snapshots, they accumulate.
_Avoid_: Profile stats, account stats

### Collection

**Harvester**:
The part of the harvester that knows how to collect from one Platform; adding a Platform means adding its Harvester.
_Avoid_: Connector, client, adapter

**Harvest**:
Everything a Harvester brings back for one Handle in one Collection Run: Raw Payloads labelled Public or Private, the Handle's account counts, Posts the Platform says are gone, and whether it finished or stopped early on quota.
_Avoid_: Batch, result, fetch

**Collection Run**:
One pass over a Handle that collects every Post within its Tracking Window and records a Metric Snapshot for each. It ends Completed, Partial (stopped early because the Platform's quota ran out; what it collected is kept and the Handle gets a fresh run once quota returns) or Failed (an error persisted after retries; the Handle waits for its next scheduled run).
_Avoid_: Sync, crawl, scrape, job

**Collection Schedule**:
A Handle's own set of clock times at which its regular Collection Runs start (e.g. every day at 09:00, or every day at 01:00 and 17:00). Each Handle has its own, so Handles start at different times. Manually triggered runs are not part of it and don't change it.
_Avoid_: Cron, job, interval, frequency

**Tracking Window**:
How many days back from now a Collection Run looks: every Post published within it is collected if new and refreshed if already known (default 14 days).
_Avoid_: History Window, backfill period, refresh period, lookback

**Tracking Window Override**:
A different Tracking Window given to a single manually triggered Collection Run (e.g. 100 days to catch up after a long outage); the Handle's Tracking Window itself is unchanged.
_Avoid_: Backfill, temporary window

**Tracked Post**:
A Post published within its Handle's Tracking Window; it receives a new Metric Snapshot on each Collection Run.

**Frozen Post**:
A Post older than its Handle's Tracking Window; it keeps its past Metric Snapshots but receives no new ones.
_Avoid_: Archived post, stale post
