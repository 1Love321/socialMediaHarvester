# One daily purge job applies per-Platform retention; YouTube Frozen Posts are deleted unless Authorized

A single scheduled purge job, owned by the core, applies every retention and deletion rule once a day. Those rules are: Raw Payload age, the 2-year normalized-data cap, YouTube's 30-day cap, Revoked Authorizations, Meta Data Deletion Requests, and Unavailable YouTube Posts. Deletions that happen on demand wait for the job's next run rather than having timers of their own, because every Platform deadline is at least 24 hours away. Each run writes to a Deletion Log (scope, reason, timestamps, row counts, Meta confirmation code) and never logs the content it deleted.

On YouTube, Frozen Posts of plain Handles are **deleted** 30 days after their last fetch rather than refreshed monthly. That leaves only about 44 days of history for plain YouTube Handles, but costs no quota and needs no extra job. Authorized YouTube Handles fetch even their Public Data with the owner's token, so it counts as Authorized Data and may be kept while the Authorization is Active. Their Frozen Posts get a monthly **Retention Refresh**, because YouTube still requires metadata to be refreshed and the video's existence to be checked every 30 days.

The time an Authorization may stay Expired before it becomes Revoked is a per-Platform setting: YouTube 21 days, Meta 30 days. With at most one more day until the purge runs, that keeps YouTube's 30-day "token can't be refreshed" deletion deadline with room to spare. Removing a Handle does not delete its data; it ages out under these rules. Snapshot thinning is allowed but not built.

See [the decision](https://github.com/rahmed12/socialMediaHarvester/issues/13). Builds on ADR 0002, 0005 and 0006.
