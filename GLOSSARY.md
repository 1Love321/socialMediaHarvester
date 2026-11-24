# Social Media Harvester

Collects posts and engagement data from social media platforms for a set of tracked handles, and stores it for later viewing and analysis.

## Language

### People

**Viewer**:
A member of our team who can look at all Brands, Handles, Posts and their charts, but cannot start or change anything.
_Avoid_: Reader, guest, Client

**Operator**:
A member of our team who can do everything a Viewer can, and also keeps collection running: starts Manual Runs, works the alert page and restarts Stopped Handles. Cannot change what is collected or deleted.
_Avoid_: Staff, runner, support

**Admin**:
A member of our team who can do everything an Operator can, and also decides what is collected and deleted: manages Brands, Handles, Collection Schedules, Authorizations, purges and user accounts.
_Avoid_: Staff, superuser, owner (an owner is the account holder who grants an Authorization)

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
An owner's grant allowing the harvester to read Private Data for one Handle. It is Active while it works; it ends as Expired (stopped working without the owner withdrawing; can be reconnected, and becomes Revoked if not reconnected within its Platform's set number of days), Revoked (consent withdrawn, or the Handle disconnected by an Admin) or Replaced (a newer Authorization for the same Handle took over). Each grant is a new Authorization; a Handle has at most one Active one.
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
A previously collected Post that the Platform no longer returns (deleted, made private, or removed). It receives no new Metric Snapshots; it keeps its history unless its Platform's rules require deleting it (YouTube does).
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

**Deletion Log**:
The record of what the harvester deleted and why (a retention rule, a Revoked Authorization, a deletion request, a whole-Platform purge): the scope, when it was requested and completed, and how much was removed, never the deleted content itself.
_Avoid_: Audit trail, purge history

### Collection

**Harvester**:
The part of the harvester that knows how to collect from one Platform; adding a Platform means adding its Harvester.
_Avoid_: Connector, client, adapter

**Harvest**:
Everything a Harvester brings back for one Handle in one Collection Run: Raw Payloads labelled Public or Private, the Handle's account counts, Posts the Platform says are gone, and whether it finished or stopped early because the Platform's Rate Limit was reached.
_Avoid_: Batch, result, fetch

**Collection Run**:
One pass over a Handle that collects every Post within its Tracking Window and records a Metric Snapshot for each. It ends Completed, Partial (stopped early because the Platform's Rate Limit was reached; what it collected is kept and the Handle gets a fresh run once the limit allows) or Failed (an error persisted after retries; the Handle waits for its next scheduled run).
_Avoid_: Sync, crawl, scrape, job

**Collection Schedule**:
A Handle's own set of clock times at which its regular Collection Runs start (e.g. every day at 09:00, or every day at 01:00 and 17:00). Each Handle has its own, so Handles start at different times. Manual Runs are not part of it and don't change it.
_Avoid_: Cron, job, interval, frequency

**Manual Run**:
A Collection Run that an Operator or Admin starts by hand rather than one from a Collection Schedule. It can cover one Handle, one Brand on one Platform, one Brand on all its Platforms, or a whole Platform; each Handle covered gets its own Collection Run, which goes ahead of scheduled runs. It may carry a Tracking Window Override and never changes anyone's Collection Schedule.
_Avoid_: Ad-hoc run, forced sync, refresh now

**Rate Limit**:
The cap a Platform puts on how much we may collect from it in a given period (e.g. YouTube's daily units, Instagram's app-wide hourly usage). Each Platform has its own. When it is reached, Collection Runs wait; part of it is held back for Manual Runs. Some Platforms call this a "quota" (YouTube does); it is the same thing.
_Avoid_: Quota (except when quoting a Platform's own docs or API), budget, allowance

**Stopped Handle**:
A Handle whose Collection Schedule has been halted because its Platform reported a lasting problem with it (e.g. unknown username, account gone). It gets no scheduled Collection Runs until an Operator or Admin acts on it; its history is kept.
_Avoid_: Disabled handle, dead handle, paused handle

**Retention Refresh**:
A periodic re-fetch of Frozen Posts that a Platform's rules require us to refresh rather than leave untouched (e.g. YouTube Posts of Authorized Handles, monthly). It renews the Post, checks that it still exists and adds one Metric Snapshot. It is not a Collection Run and has lower priority than Collection Runs.
_Avoid_: Re-sync, revalidation

**Tracking Window**:
How many days back from now a Collection Run looks: every Post published within it is collected if new and refreshed if already known (default 14 days).
_Avoid_: History Window, backfill period, refresh period, lookback

**Tracking Window Override**:
A different Tracking Window given to a Manual Run (e.g. 100 days to catch up after a long outage); the Handle's Tracking Window itself is unchanged.
_Avoid_: Backfill, temporary window

**Tracked Post**:
A Post published within its Handle's Tracking Window; it receives a new Metric Snapshot on each Collection Run.

**Frozen Post**:
A Post older than its Handle's Tracking Window; it keeps its past Metric Snapshots (for as long as its Platform's rules allow) and receives no new ones from Collection Runs, only from a Retention Refresh.
_Avoid_: Archived post, stale post
